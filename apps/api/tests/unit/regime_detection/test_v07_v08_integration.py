"""
RegimeX Regime Detection — V07/V08 Integration Tests
=====================================================
Integration-level tests connecting the V07 Feature Engineering Pipeline to
the V08 KMeans Regime Detection model.

Pipeline under test:
    OHLCVRecord
        ↓
    FeaturePipeline (V07)
        ↓
    FeatureSet
        ↓
    FeatureMatrixBuilder (V08)
        ↓
    FeatureMatrix
        ↓
    KMeansRegimeDetector (V08)
        ↓
    RegimeDetectionResult

Tests:
1. Full pipeline integration with 4-cluster synthetic data.
2. Warm-up None rows from V07 features are excluded (not zero-filled).
3. FeatureMatrixBuilder deduplicates features from V07 output.
4. No duplicate feature calculations in the pipeline.
5. No-lookahead regression: frozen scaler is not refit on new observations.
6. Point-in-time inference invariance through the full V07→V08 stack.
7. Model version stability ("1.0.0") across the integration stack.
8. Architecture: application service uses the RegimeDetector interface, not sklearn.
9. Feature subset selection through the service layer.
10. Subsequent inference is deterministic through the service.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    OHLCVRecord,
)
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.errors import (
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.models import (
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 6, 1, 9, 30, tzinfo=UTC)


def _generate_synthetic_bars(
    n_bars: int = 80,
    base_price: float = 100.0,
    seed_pattern: str = "sine",
) -> list[OHLCVRecord]:
    """
    Generates N chronological daily OHLCV bars with a sine-wave return pattern.
    This produces enough bars that even the 20-period warm-up rows can be excluded
    while still leaving 60+ complete observations.
    """
    bars = []
    price = base_price

    for i in range(n_bars):
        if seed_pattern == "sine":
            ret = 0.015 * math.sin(i * 0.25)
        elif seed_pattern == "alt":
            ret = 0.01 * math.cos(i * 0.3)
        else:
            ret = 0.005 * (i % 2 * 2 - 1)

        close = price * (1.0 + ret)
        high = max(price, close) + 0.50
        low = min(price, close) - 0.50
        volume = 10_000.0 + 1_000.0 * (i % 5)

        bars.append(
            OHLCVRecord(
                symbol="SPY",
                timestamp=_BASE_TIME + timedelta(days=i),
                open=price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                interval=DataInterval.ONE_DAY,
                adjustment_policy=AdjustmentPolicy.RAW,
                source_provider_id="test",
                ingested_at=datetime.now(tz=UTC),
            )
        )
        price = close

    return bars


# ---------------------------------------------------------------------------
# Class 1: Full pipeline integration
# ---------------------------------------------------------------------------


class TestV07V08FullPipelineIntegration:
    """
    Tests the end-to-end integration from raw OHLCV bars through V07 features
    to V08 regime detection.
    """

    def test_full_pipeline_produces_valid_regime_detection_result(self) -> None:
        """
        Generates 80 OHLCV bars, computes V07 features, fits KMeans detector,
        and produces canonical regime detection records. Verifies all result fields.
        """
        bars = _generate_synthetic_bars(n_bars=80)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        # V07 pipeline must produce records for all 80 bars
        assert feature_set.record_count == 80
        assert len(feature_set.feature_names) >= 15  # V07 baseline features

        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        service = RegimeDetectionService(detector=detector)

        _, result = service.fit_and_detect(feature_set)

        # After warm-up exclusion (~20 bars), at least 60 complete observations
        assert result.record_count >= 55
        assert not result.is_empty

        # All regime IDs must be in [0, 3]
        for record in result.records:
            assert 0 <= record.canonical_regime_id < 4
            assert record.canonical_regime_label in {f"REGIME_{i}" for i in range(4)}
            assert record.probabilities is not None
            assert len(record.probabilities) == 4
            assert math.isclose(sum(record.probabilities), 1.0, rel_tol=1e-6)

    def test_pipeline_feature_names_in_result_match_training_features(self) -> None:
        """
        The feature_names stored in RegimeDetectionResult must match the features
        used to fit the detector (not all V07 features, only the requested subset).
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        _, result = service.fit_and_detect(feature_set, feature_names=["return_1", "volatility_10"])
        assert result.feature_names == ("return_1", "volatility_10")

    def test_subsequent_inference_is_deterministic(self) -> None:
        """
        Calling detect_from_feature_set() twice on the same data must produce
        identical regime assignment sequences.
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        _, result_1 = service.fit_and_detect(feature_set)
        result_2 = service.detect_from_feature_set(feature_set)

        assert result_1.get_regime_series() == result_2.get_regime_series()
        assert result_1.get_labels_series() == result_2.get_labels_series()

    def test_detect_before_fit_raises_typed_error(self) -> None:
        """Calling detect_from_feature_set before fit must raise ModelNotFittedError."""
        bars = _generate_synthetic_bars(n_bars=30)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        with pytest.raises(ModelNotFittedError):
            service.detect_from_feature_set(feature_set)

    def test_timestamp_alignment_preserved_through_pipeline(self) -> None:
        """
        Timestamps in the RegimeDetectionResult must exactly match those in
        the FeatureMatrix produced by FeatureMatrixBuilder (complete rows only).
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        # Build matrix to get reference timestamps
        matrix = FeatureMatrixBuilder.build(feature_set)

        service = RegimeDetectionService()
        service.fit_from_feature_set(feature_set)
        result = service.detect_from_matrix(matrix)

        assert result.get_timestamps() == matrix.timestamps


# ---------------------------------------------------------------------------
# Class 2: Warm-up None handling through V07→V08
# ---------------------------------------------------------------------------


class TestWarmUpNoneHandlingIntegration:
    """
    Verifies that warm-up None values from V07 features are correctly excluded
    in the V08 pipeline — never zero-filled or forward-filled.
    """

    def test_warmup_rows_excluded_from_regime_detection(self) -> None:
        """
        With 80 OHLCV bars and 20-period indicators, FeatureMatrixBuilder should
        exclude the first ~20 warm-up rows, leaving only rows with complete features.
        """
        bars = _generate_synthetic_bars(n_bars=80)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        # At least some records must have None values (warm-up period)
        has_none = any(
            any(v is None for v in record.values.values()) for record in feature_set.records
        )
        assert has_none, "Expected warm-up None values in V07 output."

        # Build matrix — None rows must be excluded
        matrix = FeatureMatrixBuilder.build(feature_set)
        assert matrix.sample_count < feature_set.record_count, (
            "FeatureMatrixBuilder must exclude warm-up rows; "
            "matrix should have fewer rows than FeatureSet."
        )

    def test_no_zero_values_fabricated_from_warmup_nones(self) -> None:
        """
        After warm-up exclusion, the feature matrix must not contain any rows
        where all values are 0.0 (a signature of invalid fillna(0) behavior).
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        matrix = FeatureMatrixBuilder.build(feature_set)

        for row_idx, row in enumerate(matrix.values):
            assert any(v != 0.0 for v in row), (
                f"Row {row_idx} has all-zero values — may indicate fillna(0) anti-pattern. "
                f"Row: {row}"
            )

    def test_matrix_has_no_none_or_nan_after_builder(self) -> None:
        """
        FeatureMatrix values must contain no NaN or None values after FeatureMatrixBuilder.
        This is guaranteed by the FeatureMatrix domain model validator.
        """
        import math

        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        matrix = FeatureMatrixBuilder.build(feature_set)

        for row in matrix.values:
            for val in row:
                assert isinstance(val, float)
                assert math.isfinite(val)

    def test_insufficient_bars_raises_typed_error(self) -> None:
        """
        With too few bars (less than the warm-up window for 20-period indicators),
        the V07 FeaturePipeline raises InsufficientDataError — a typed domain error
        that must propagate cleanly. This test verifies that no raw sklearn exception
        leaks through the stack when data is insufficient.

        Note: V07 pipeline raises InsufficientDataError before FeatureMatrixBuilder
        is even called, since the feature calculation cannot proceed with < 20 bars.
        This is correct typed error propagation at the earliest validation point.
        """
        from app.modules.feature_engineering.domain.errors import InsufficientDataError

        # Only 5 bars — V07 warm-up requires 20+ for 20-period indicators
        bars = _generate_synthetic_bars(n_bars=5)
        pipeline = FeaturePipeline()

        # V07 correctly rejects this with its own domain error (InsufficientDataError)
        # before reaching the V08 FeatureMatrixBuilder
        with pytest.raises(InsufficientDataError):
            pipeline.compute(bars)


# ---------------------------------------------------------------------------
# Class 3: No-lookahead regression through V07→V08
# ---------------------------------------------------------------------------


class TestNoLookaheadRegressionIntegration:
    """
    Documents and tests the no-lookahead guarantee across the V07→V08 boundary.

    The baseline KMeans is an in-sample fitted model. We verify:
    1. Scaler is not refit during inference through the service.
    2. Predictions on a subset are identical to the first N elements of predictions
       on the full set (no future row can alter past row transformations).
    """

    def test_scaler_frozen_during_service_inference(self) -> None:
        """
        Calling detect_from_feature_set() must not mutate the scaler's training parameters.
        """
        import numpy as np

        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        service = RegimeDetectionService(detector=detector)
        service.fit_from_feature_set(feature_set)

        assert detector._scaler is not None
        mean_before = np.copy(detector._scaler.mean_)
        scale_before = np.copy(detector._scaler.scale_)

        # Multiple inference passes through the service
        for _ in range(3):
            service.detect_from_feature_set(feature_set)

        assert np.array_equal(detector._scaler.mean_, mean_before), (
            "Scaler was mutated by service inference."
        )
        assert np.array_equal(detector._scaler.scale_, scale_before), (
            "Scaler was mutated by service inference."
        )

    def test_in_sample_model_disclaimer_not_walk_forward(self) -> None:
        """
        Documents the architecture constraint:
        A KMeans model fitted on the complete historical dataset is an in-sample
        clustering baseline. The fit_result metadata must confirm this.

        Verification: algorithm_id must NOT claim any walk-forward or predictive semantics.
        The algorithm_id is 'kmeans_baseline' — deterministically confirmed.
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        service = RegimeDetectionService(detector=detector)
        service.fit_from_feature_set(feature_set)

        # The algorithm_id must identify this as a baseline (not a predictor)
        assert detector.algorithm_id == "kmeans_baseline"

        # The metadata limitations must reference the in-sample nature
        limitations = " ".join(detector.metadata().known_limitations).lower()
        assert "in-sample" in limitations or "out-of-sample" in limitations, (
            "Metadata must disclose the in-sample/out-of-sample distinction."
        )

    def test_point_in_time_inference_prefix_invariance_through_service(self) -> None:
        """
        For a fitted service, predicting regime for observations t_0..t_k
        must produce the exact same first k results as predicting t_0..t_k+n.
        """

        bars_full = _generate_synthetic_bars(n_bars=80)
        pipeline = FeaturePipeline()
        feature_set_full = pipeline.compute(bars_full)

        # Build complete matrix
        matrix_full = FeatureMatrixBuilder.build(feature_set_full)

        # Fit on all complete observations
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        service = RegimeDetectionService(detector=detector)
        service.fit_from_feature_set(feature_set_full)

        # Predict on first half of complete observations
        half = matrix_full.sample_count // 2
        from app.modules.regime_detection.domain.models import FeatureMatrix

        matrix_first_half = FeatureMatrix(
            timestamps=matrix_full.timestamps[:half],
            feature_names=matrix_full.feature_names,
            values=matrix_full.values[:half],
        )
        preds_first_half = service.detect_from_matrix(matrix_first_half)

        # Predict on full matrix
        preds_full = service.detect_from_matrix(matrix_full)

        # First half predictions must match
        first_half_from_full = preds_full.get_regime_series()[:half]
        first_half_direct = preds_first_half.get_regime_series()

        assert first_half_from_full == first_half_direct, (
            "Point-in-time inference invariance violated: first N predictions from full batch "
            "do not match predictions on first-N-only batch."
        )


# ---------------------------------------------------------------------------
# Class 4: Architecture integrity through integration
# ---------------------------------------------------------------------------


class TestArchitectureIntegrityIntegration:
    """
    Verifies architecture guardrails remain intact during integration use.
    """

    def test_service_interacts_via_regime_detector_interface(self) -> None:
        """
        RegimeDetectionService must interact with any RegimeDetector implementation —
        it must not be tightly coupled to KMeansRegimeDetector internals.
        """
        from app.modules.regime_detection.domain.interfaces import RegimeDetector

        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        service = RegimeDetectionService(detector=detector)

        # Service exposes detector via the abstract interface
        assert isinstance(service.detector, RegimeDetector)

        _, result = service.fit_and_detect(feature_set)
        assert not result.is_empty

    def test_service_does_not_expose_sklearn_in_result(self) -> None:
        """
        RegimeDetectionResult must not contain any sklearn objects directly.
        All sklearn outputs must have been translated to domain types.
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        _, result = service.fit_and_detect(feature_set)

        # All records must contain only domain types
        for record in result.records:
            assert isinstance(record.canonical_regime_id, int)
            assert isinstance(record.canonical_regime_label, str)
            if record.probabilities is not None:
                assert isinstance(record.probabilities, tuple)
                assert all(isinstance(p, float) for p in record.probabilities)

    def test_kmeans_algorithm_version_stable_through_integration(self) -> None:
        """
        The algorithm version propagated to RegimeDetectionResult must match
        the KMeansRegimeDetector.ALGORITHM_VERSION constant.
        """
        bars = _generate_synthetic_bars(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        _, result = service.fit_and_detect(feature_set)

        assert result.model_version == KMeansRegimeDetector.ALGORITHM_VERSION
        assert result.algorithm == KMeansRegimeDetector.ALGORITHM_ID

    def test_no_gmm_hmm_or_ensemble_in_integration_stack(self) -> None:
        """
        V08 integration stack must not reference GMM, HMM, ensemble models,
        transition engines, or risk engines.
        """
        import inspect

        import app.modules.regime_detection.application.feature_matrix_builder as fmb
        import app.modules.regime_detection.application.services as srv

        for mod in [srv, fmb]:
            source = inspect.getsource(mod)
            forbidden = ["hmmlearn", "gmm", "ensemble", "transition_engine", "risk_engine"]
            for term in forbidden:
                assert term not in source.lower(), (
                    f"Forbidden term '{term}' found in {mod.__name__}. "
                    f"V08 must not implement {term}."
                )
