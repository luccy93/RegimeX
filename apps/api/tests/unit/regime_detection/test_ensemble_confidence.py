"""
RegimeX Regime Detection — Ensemble Confidence Scoring Tests
============================================================
Comprehensive test suite verifying deterministic, explainable consensus support
confidence scoring for the Regime Model Ensemble (V11 Commit 02).

Guarantees Verified:
- Basic scoring: unanimous agreement (1.0), partial agreement (2/3, 1/3), single active model.
- Weighted scoring: custom weights, dominant models, skipped/unavailable model exclusion.
- Tie handling: un-inflated confidence upon deterministic tie-breaking (e.g. exactly 0.50).
- Failure policies: FAIL_FAST, SKIP_UNAVAILABLE, minimum usable models enforcement.
- Validation & Numerical safety: invariant enforcement, non-positive weight rejection,
  NaN/inf rejection, row-sum simplex invariance.
- Anti-leakage & Determinism: point-in-time calculation, no future leakage, immutability.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.errors import (
    EnsembleExecutionError,
    EnsembleModelUnavailableError,
    InsufficientUsableModelsError,
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    DetectorMetadata,
    EnsembleConfidence,
    EnsembleModelConfig,
    EnsembleTieBreaker,
    FailurePolicy,
    FeatureMatrix,
    FitResult,
    ModelState,
)
from app.modules.regime_detection.infrastructure.ensemble.aggregation import (
    EnsembleAggregator,
)
from app.modules.regime_detection.infrastructure.models.ensemble import (
    RegimeModelEnsemble,
)


def _ts(offset_hours: int = 0) -> datetime:
    """Generate deterministic UTC timestamp."""
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    return base + timedelta(hours=offset_hours)


def _make_feature_matrix(n_rows: int = 6) -> FeatureMatrix:
    """Create deterministic feature matrix for tests."""
    timestamps = tuple(_ts(i) for i in range(n_rows))
    feature_names = ("f_return", "f_volatility")
    values = tuple((float(i % 3) * 0.5, float(i % 3) * 0.2 + 0.1) for i in range(n_rows))
    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=values,
    )


class MockDetector(RegimeDetector):
    """Deterministic mock detector for isolating ensemble confidence logic."""

    def __init__(
        self,
        algorithm_id: str,
        predictions: tuple[int, ...] = (0, 1, 0, 1, 0, 1),
        fail_fit: bool = False,
        fail_predict: bool = False,
    ) -> None:
        self._id = algorithm_id
        self._predictions = predictions
        self._fail_fit = fail_fit
        self._fail_predict = fail_predict
        self._state = ModelState.UNFITTED
        self._fit_result: FitResult | None = None

    @property
    def algorithm_id(self) -> str:
        return self._id

    @property
    def algorithm_version(self) -> str:
        return "1.0.0"

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    def fit(self, feature_matrix: FeatureMatrix) -> MockDetector:
        if self._fail_fit:
            raise RuntimeError(f"Mock fit failure for {self._id}")
        self._fit_result = FitResult(
            model_name=self._id,
            model_version="1.0.0",
            algorithm="Mock",
            n_clusters=max(self._predictions) + 1 if self._predictions else 2,
            random_state=42,
            feature_names=feature_matrix.feature_names,
            training_sample_count=feature_matrix.sample_count,
            training_start=feature_matrix.timestamps[0],
            training_end=feature_matrix.timestamps[-1],
            inertia=0.0,
            iterations=1,
            cluster_profiles=(),
        )
        self._state = ModelState.FITTED
        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        if self._fail_predict:
            raise RuntimeError(f"Mock predict failure for {self._id}")
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._id)
        n = feature_matrix.sample_count
        if len(self._predictions) >= n:
            return self._predictions[:n]
        return tuple(self._predictions[i % len(self._predictions)] for i in range(n))

    def predict_proba(self, feature_matrix: FeatureMatrix) -> tuple[tuple[float, ...], ...] | None:
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._id)
        k = max(self._predictions) + 1 if self._predictions else 2
        preds = self.predict(feature_matrix)
        rows: list[tuple[float, ...]] = []
        for p in preds:
            row = [0.0] * k
            row[p] = 1.0
            rows.append(tuple(row))
        return tuple(rows)

    def get_params(self) -> dict[str, object]:
        return {"algorithm_id": self._id}

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            algorithm_id=self._id,
            algorithm_version="1.0.0",
            algorithm_family="Mock",
            description="Mock detector for unit testing",
        )


# ===========================================================================
# 1. Basic Confidence Scoring Tests
# ===========================================================================


class TestBasicConfidenceScoring:
    def test_unanimous_models_confidence_one(self) -> None:
        """3 models agreeing on regime 0 produce confidence 1.0."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,), "m2": (0,), "m3": (0,)}
        aligned_preds = {"m1": (0,), "m2": (0,), "m3": (0,)}
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0}
        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (0,)
        record = records[0]
        assert record.confidence == 1.0
        assert record.is_unanimous is True
        assert record.agreement_count == 3
        assert record.total_models == 3
        assert record.disagreeing_models == ()

        breakdown = record.confidence_breakdown
        assert breakdown.score == 1.0
        assert breakdown.supporting_model_count == 3
        assert breakdown.active_model_count == 3
        assert breakdown.supporting_weight == 3.0
        assert breakdown.total_active_weight == 3.0
        assert breakdown.agreement_ratio == 1.0
        assert breakdown.is_unanimous is True
        assert breakdown.disagreeing_models == ()

    def test_two_thirds_agreement_equal_weights(self) -> None:
        """2 models vote regime 1, 1 model votes regime 2 -> confidence is 2/3."""
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (1,), "m3": (2,)}
        aligned_preds = {"m1": (1,), "m2": (1,), "m3": (2,)}
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0}
        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (1,)
        record = records[0]
        assert abs(record.confidence - 2.0 / 3.0) < 1e-6
        assert record.is_unanimous is False
        assert record.agreement_count == 2
        assert record.total_models == 3
        assert record.disagreeing_models == ("m3",)

        breakdown = record.confidence_breakdown
        assert abs(breakdown.score - 2.0 / 3.0) < 1e-6
        assert breakdown.supporting_model_count == 2
        assert breakdown.active_model_count == 3
        assert breakdown.supporting_weight == 2.0
        assert breakdown.total_active_weight == 3.0
        assert abs(breakdown.agreement_ratio - 2.0 / 3.0) < 1e-6
        assert breakdown.is_unanimous is False
        assert breakdown.disagreeing_models == ("m3",)

    def test_single_active_model_confidence_one(self) -> None:
        """Single active model voting produces confidence 1.0."""
        ts = (_ts(0),)
        comp_preds = {"m1": (2,)}
        aligned_preds = {"m1": (2,)}
        weights = {"m1": 1.0}
        config = EnsembleModelConfig(enabled_models=("m1",), minimum_required_models=1)

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (2,)
        record = records[0]
        assert record.confidence == 1.0
        assert record.is_unanimous is True
        assert record.agreement_count == 1
        assert record.total_models == 1
        assert record.disagreeing_models == ()

    def test_equal_weights_confidence_equals_agreement_ratio(self) -> None:
        """Under equal weights, confidence score matches agreement_ratio exactly."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,), "m2": (0,), "m3": (1,)}
        aligned_preds = {"m1": (0,), "m2": (0,), "m3": (1,)}
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0}
        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))

        _, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        record = records[0]
        assert abs(record.confidence - record.confidence_breakdown.agreement_ratio) < 1e-6


# ===========================================================================
# 2. Weighted Confidence Scoring Tests
# ===========================================================================


class TestWeightedConfidenceScoring:
    def test_custom_unequal_weights(self) -> None:
        """
        KMeans = 0.5 (regime 0), GMM = 0.3 (regime 0), HMM = 0.2 (regime 1).
        Consensus: regime 0. Confidence: (0.5 + 0.3) / 1.0 = 0.80.
        """
        ts = (_ts(0),)
        comp_preds = {"kmeans": (0,), "gmm": (0,), "hmm": (1,)}
        aligned_preds = {"kmeans": (0,), "gmm": (0,), "hmm": (1,)}
        weights = {"kmeans": 0.5, "gmm": 0.3, "hmm": 0.2}
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm", "hmm"),
            model_weights=weights,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (0,)
        record = records[0]
        assert abs(record.confidence - 0.80) < 1e-6
        assert record.agreement_count == 2
        assert record.total_models == 3
        assert record.disagreeing_models == ("hmm",)

        breakdown = record.confidence_breakdown
        assert abs(breakdown.score - 0.80) < 1e-6
        assert breakdown.supporting_weight == 0.80
        assert breakdown.total_active_weight == 1.0
        assert abs(breakdown.agreement_ratio - 2.0 / 3.0) < 1e-6

    def test_dominant_model_overrides_plurality(self) -> None:
        """
        Dominant model (weight 0.70) voting for regime 2 overrides two models
        (weights 0.15, 0.15) voting for regime 0.
        Consensus is regime 2 with confidence 0.70.
        """
        ts = (_ts(0),)
        comp_preds = {"m1": (2,), "m2": (0,), "m3": (0,)}
        aligned_preds = {"m1": (2,), "m2": (0,), "m3": (0,)}
        weights = {"m1": 0.70, "m2": 0.15, "m3": 0.15}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            model_weights=weights,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (2,)
        record = records[0]
        assert abs(record.confidence - 0.70) < 1e-6
        assert record.agreement_count == 1
        assert record.disagreeing_models == ("m2", "m3")

        breakdown = record.confidence_breakdown
        assert abs(breakdown.score - 0.70) < 1e-6
        assert abs(breakdown.agreement_ratio - 1.0 / 3.0) < 1e-6

    def test_low_weight_disagreement_discounts_confidence(self) -> None:
        """
        KMeans (0.45) and GMM (0.45) vote 1, HMM (0.10) votes 0.
        Confidence is 0.90.
        """
        ts = (_ts(0),)
        comp_preds = {"kmeans": (1,), "gmm": (1,), "hmm": (0,)}
        aligned_preds = {"kmeans": (1,), "gmm": (1,), "hmm": (0,)}
        weights = {"kmeans": 0.45, "gmm": 0.45, "hmm": 0.10}
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm", "hmm"),
            model_weights=weights,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (1,)
        record = records[0]
        assert abs(record.confidence - 0.90) < 1e-6
        assert record.disagreeing_models == ("hmm",)

    def test_skipped_model_weight_excluded_from_denominator(self) -> None:
        """
        Config has 3 models (weights 0.5, 0.3, 0.2).
        If m3 is skipped, active weights are over m1 and m2 only.
        If m1 votes 0 and m2 votes 1, confidence is 0.5 / (0.5 + 0.3) = 0.625.
        m3's weight (0.2) is NOT in denominator.
        """
        ts = (_ts(0),)
        comp_preds = {"m1": (0,), "m2": (1,)}
        aligned_preds = {"m1": (0,), "m2": (1,)}
        weights = {"m1": 0.5, "m2": 0.3}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            minimum_required_models=2,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (0,)
        record = records[0]
        expected_conf = 0.5 / (0.5 + 0.3)
        assert abs(record.confidence - expected_conf) < 1e-6
        assert record.confidence_breakdown.active_model_count == 2
        assert record.confidence_breakdown.total_active_weight == 0.8


# ===========================================================================
# 3. Tie Handling Tests
# ===========================================================================


class TestConfidenceTieHandling:
    def test_exact_50_50_tie_retains_50_percent_confidence(self) -> None:
        """
        Exact 50/50 tie: m1 votes 1 (weight 0.5), m2 votes 0 (weight 0.5).
        Tie-breaker selects regime 0, but confidence MUST remain exactly 0.50.
        It must NEVER be inflated to 1.0.
        """
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (0,)}
        aligned_preds = {"m1": (1,), "m2": (0,)}
        weights = {"m1": 0.5, "m2": 0.5}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            tie_breaker=EnsembleTieBreaker.LOWEST_REGIME_ID,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (0,)
        record = records[0]
        assert record.confidence == 0.50
        assert record.is_unanimous is False
        assert record.agreement_count == 1
        assert record.total_models == 2

        breakdown = record.confidence_breakdown
        assert breakdown.score == 0.50
        assert breakdown.supporting_weight == 0.50
        assert breakdown.total_active_weight == 1.0
        assert breakdown.agreement_ratio == 0.50

    def test_exact_50_50_tie_with_model_precedence(self) -> None:
        """With MODEL_PRECEDENCE selecting m1's regime 1, confidence remains 0.50."""
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (0,)}
        aligned_preds = {"m1": (1,), "m2": (0,)}
        weights = {"m1": 0.5, "m2": 0.5}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            tie_breaker=EnsembleTieBreaker.MODEL_PRECEDENCE,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (1,)
        record = records[0]
        assert record.confidence == 0.50

    def test_three_way_tie_retains_one_third_confidence(self) -> None:
        """3 models vote 0, 1, 2 with equal weights -> confidence is exactly 1/3."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,), "m2": (1,), "m3": (2,)}
        aligned_preds = {"m1": (0,), "m2": (1,), "m3": (2,)}
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            tie_breaker=EnsembleTieBreaker.LOWEST_REGIME_ID,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )

        assert regimes == (0,)
        record = records[0]
        assert abs(record.confidence - 1.0 / 3.0) < 1e-6
        assert record.confidence_breakdown.supporting_model_count == 1
        assert record.confidence_breakdown.active_model_count == 3


# ===========================================================================
# 4. Failure Policies and Availability
# ===========================================================================


class TestFailurePoliciesAndAvailability:
    def test_fail_fast_raises_without_partial_confidence(self) -> None:
        """FAIL_FAST immediately raises error when a model fails; no confidence computed."""
        matrix = _make_feature_matrix()
        m1 = MockDetector("m1")
        m2 = MockDetector("m2", fail_predict=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            minimum_required_models=1,
            failure_policy=FailurePolicy.FAIL_FAST,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2}).fit(matrix)

        with pytest.raises(EnsembleModelUnavailableError):
            ensemble.predict_ensemble(matrix)

    def test_skip_unavailable_computes_confidence_on_surviving_models(self) -> None:
        """SKIP_UNAVAILABLE computes confidence strictly over surviving models."""
        matrix = _make_feature_matrix(n_rows=4)
        m1 = MockDetector("m1", predictions=(0, 0, 0, 0))
        m2 = MockDetector("m2", predictions=(0, 0, 1, 1))
        m3 = MockDetector("m3", fail_predict=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            model_weights={"m1": 1.0, "m2": 1.0, "m3": 1.0},
            minimum_required_models=2,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )
        ensemble = RegimeModelEnsemble(
            config=config,
            models={"m1": m1, "m2": m2, "m3": m3},
        ).fit(matrix)

        result = ensemble.predict_ensemble(matrix)
        assert result.models_used == ("m1", "m2")
        assert "m3" in result.models_unavailable

        # Row 0: m1=0, m2=0 -> unanimous among active models -> confidence = 1.0
        assert result.records[0].confidence == 1.0
        assert result.records[0].confidence_breakdown.active_model_count == 2

        # Row 2: m1=0, m2=1 -> 50/50 tie -> confidence = 0.50
        assert result.records[2].confidence == 0.50
        assert result.records[2].confidence_breakdown.active_model_count == 2

    def test_insufficient_usable_models_raises_error(self) -> None:
        """If active models < minimum_required_models, raises InsufficientUsableModelsError."""
        matrix = _make_feature_matrix(n_rows=4)
        m1 = MockDetector("m1", fail_predict=True)
        m2 = MockDetector("m2", fail_predict=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            minimum_required_models=2,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2}).fit(matrix)

        with pytest.raises(InsufficientUsableModelsError):
            ensemble.predict_ensemble(matrix)


# ===========================================================================
# 5. Validation and Safety Tests
# ===========================================================================


class TestConfidenceValidationAndSafety:
    def test_confidence_domain_model_valid(self) -> None:
        """Valid EnsembleConfidence passes validation."""
        conf = EnsembleConfidence(
            score=0.75,
            supporting_model_count=3,
            active_model_count=4,
            supporting_weight=3.0,
            total_active_weight=4.0,
            agreement_ratio=0.75,
            is_unanimous=False,
            disagreeing_models=("m4",),
        )
        assert conf.score == 0.75
        assert conf.confidence == 0.75
        assert conf.unanimous is False

    def test_confidence_validation_rejects_supporting_greater_than_active(self) -> None:
        """Validation rejects supporting_model_count > active_model_count."""
        with pytest.raises(ValueError, match="supporting_model_count"):
            EnsembleConfidence(
                score=1.0,
                supporting_model_count=5,
                active_model_count=3,
                supporting_weight=3.0,
                total_active_weight=3.0,
                agreement_ratio=1.0,
                is_unanimous=True,
            )

    def test_confidence_validation_rejects_supporting_weight_greater_than_total(self) -> None:
        """Validation rejects supporting_weight > total_active_weight."""
        with pytest.raises(ValueError, match="supporting_weight"):
            EnsembleConfidence(
                score=1.0,
                supporting_model_count=2,
                active_model_count=2,
                supporting_weight=3.5,
                total_active_weight=3.0,
                agreement_ratio=1.0,
                is_unanimous=True,
            )

    def test_confidence_validation_rejects_inconsistent_agreement_ratio(self) -> None:
        """Validation rejects agreement_ratio that does not match supporting / active."""
        with pytest.raises(ValueError, match="agreement_ratio"):
            EnsembleConfidence(
                score=0.5,
                supporting_model_count=1,
                active_model_count=2,
                supporting_weight=1.0,
                total_active_weight=2.0,
                agreement_ratio=0.99,  # Inconsistent with 1/2 = 0.5
                is_unanimous=False,
            )

    def test_zero_total_active_weight_raises_error(self) -> None:
        """If active model weights sum to zero, raises EnsembleExecutionError."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,)}
        aligned_preds = {"m1": (0,)}
        weights = {"m1": 0.0}
        config = EnsembleModelConfig(
            enabled_models=("m1",),
            model_weights={"m1": 0.001},  # config check passes
            minimum_required_models=1,
        )

        with pytest.raises(EnsembleExecutionError, match="strictly positive"):
            EnsembleAggregator.aggregate(
                timestamps=ts,
                component_predictions=comp_preds,
                aligned_predictions=aligned_preds,
                weights=weights,
                config=config,
            )

    def test_nan_active_weight_raises_error(self) -> None:
        """NaN weight raises EnsembleExecutionError."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,)}
        aligned_preds = {"m1": (0,)}
        weights = {"m1": float("nan")}
        config = EnsembleModelConfig(
            enabled_models=("m1",),
            minimum_required_models=1,
        )

        with pytest.raises(EnsembleExecutionError, match="Invalid active weight"):
            EnsembleAggregator.aggregate(
                timestamps=ts,
                component_predictions=comp_preds,
                aligned_predictions=aligned_preds,
                weights=weights,
                config=config,
            )

    def test_infinite_active_weight_raises_error(self) -> None:
        """Infinite weight raises EnsembleExecutionError."""
        ts = (_ts(0),)
        comp_preds = {"m1": (0,)}
        aligned_preds = {"m1": (0,)}
        weights = {"m1": float("inf")}
        config = EnsembleModelConfig(
            enabled_models=("m1",),
            minimum_required_models=1,
        )

        with pytest.raises(EnsembleExecutionError, match="Invalid active weight"):
            EnsembleAggregator.aggregate(
                timestamps=ts,
                component_predictions=comp_preds,
                aligned_predictions=aligned_preds,
                weights=weights,
                config=config,
            )

    def test_predict_proba_simplex_and_support_invariants(self) -> None:
        """predict_proba() row vectors sum to 1.0 and consensus regime has max prob."""
        matrix = _make_feature_matrix(n_rows=6)
        m1 = MockDetector("m1", predictions=(0, 1, 0, 1, 0, 1))
        m2 = MockDetector("m2", predictions=(0, 1, 1, 1, 0, 0))
        m3 = MockDetector("m3", predictions=(0, 0, 0, 1, 2, 1))
        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))
        ensemble = RegimeModelEnsemble(
            config=config,
            models={"m1": m1, "m2": m2, "m3": m3},
        ).fit(matrix)

        probs = ensemble.predict_proba(matrix)
        assert probs is not None
        assert len(probs) == matrix.sample_count

        result = ensemble.predict_ensemble(matrix)

        for i, row in enumerate(probs):
            assert abs(sum(row) - 1.0) < 1e-6
            for val in row:
                assert 0.0 <= val <= 1.0
            # Consensus regime probability equals ensemble confidence for that observation
            consensus_id = result.ensemble_regimes[i]
            assert abs(row[consensus_id] - result.records[i].confidence) < 1e-6


# ===========================================================================
# 6. Anti-Leakage and Determinism Tests
# ===========================================================================


class TestConfidenceAntiLeakageAndDeterminism:
    def test_confidence_strictly_deterministic(self) -> None:
        """Identical inputs produce identical confidence scores across runs."""
        matrix = _make_feature_matrix(n_rows=8)
        m1 = MockDetector("m1", predictions=(0, 1, 0, 1, 0, 1, 0, 1))
        m2 = MockDetector("m2", predictions=(0, 0, 0, 1, 1, 1, 0, 1))
        m3 = MockDetector("m3", predictions=(1, 1, 0, 0, 0, 1, 0, 0))

        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            model_weights={"m1": 0.5, "m2": 0.3, "m3": 0.2},
        )

        models_dict = {"m1": m1, "m2": m2, "m3": m3}
        ens_a = RegimeModelEnsemble(config=config, models=models_dict).fit(matrix)
        ens_b = RegimeModelEnsemble(config=config, models=models_dict).fit(matrix)

        res_a = ens_a.predict_ensemble(matrix)
        res_b = ens_b.predict_ensemble(matrix)

        assert res_a.get_confidence_series() == res_b.get_confidence_series()
        assert res_a.get_average_confidence() == res_b.get_average_confidence()

    def test_anti_leakage_future_data_does_not_alter_past_confidence(self) -> None:
        """
        Confidence scores for observations 0..T-1 are identical whether evaluated
        on the first T samples or an expanded series of T+N samples.
        """
        full_matrix = _make_feature_matrix(n_rows=10)
        sub_matrix = FeatureMatrix(
            timestamps=full_matrix.timestamps[:5],
            feature_names=full_matrix.feature_names,
            values=full_matrix.values[:5],
        )

        m1 = MockDetector("m1")
        m2 = MockDetector("m2")
        m3 = MockDetector("m3")

        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))
        ensemble = RegimeModelEnsemble(
            config=config,
            models={"m1": m1, "m2": m2, "m3": m3},
        ).fit(sub_matrix)

        res_sub = ensemble.predict_ensemble(sub_matrix)
        res_full = ensemble.predict_ensemble(full_matrix)

        # First 5 confidence scores must be bitwise identical
        sub_conf = res_sub.get_confidence_series()
        full_conf_prefix = res_full.get_confidence_series()[:5]
        assert sub_conf == full_conf_prefix


# ===========================================================================
# 7. Domain Model Convenience Methods Tests
# ===========================================================================


class TestConfidenceConvenienceMethods:
    def test_result_convenience_methods(self) -> None:
        """Verify get_confidence_series, get_average_confidence, and get_confidence_records."""
        matrix = _make_feature_matrix(n_rows=4)
        m1 = MockDetector("m1", predictions=(0, 0, 0, 0))
        m2 = MockDetector("m2", predictions=(0, 1, 0, 1))
        config = EnsembleModelConfig(enabled_models=("m1", "m2"))
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2}).fit(matrix)

        result = ensemble.predict_ensemble(matrix)
        series = result.get_confidence_series()
        assert len(series) == 4
        assert series[0] == 1.0
        assert series[1] == 0.5
        assert series[2] == 1.0
        assert series[3] == 0.5

        avg = result.get_average_confidence()
        assert abs(avg - 0.75) < 1e-6

        records = result.get_confidence_records()
        assert len(records) == 4
        assert all(isinstance(r, EnsembleConfidence) for r in records)
