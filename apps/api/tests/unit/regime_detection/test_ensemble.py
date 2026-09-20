"""
RegimeX Regime Detection — Regime Model Ensemble Test Suite
===========================================================
Comprehensive unit and integration tests for the Regime Model Ensemble (V11 Commit 01).

Guarantees:
- Configuration validation and constraints.
- Deterministic regime identity alignment across heterogeneous models.
- Deterministic consensus voting aggregation and tie-breaking.
- Availability, failure policies (FAIL_FAST, SKIP_UNAVAILABLE, BEST_EFFORT),
  and minimum required model enforcement.
- Output contract completeness: component predictions, aligned predictions, agreement metrics.
- Explicit non-confidence contract: predict_proba() returns None; no confidence fields.
- Anti-leakage, immutability, and deterministic repeatability.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest
from app.modules.regime_detection.domain.errors import (
    EnsembleModelUnavailableError,
    InsufficientTrainingDataError,
    InsufficientUsableModelsError,
    InvalidEnsembleConfigurationError,
    InvalidFeatureMatrixError,
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    AggregationStrategy,
    AlignmentPolicy,
    ClusterProfile,
    DetectorMetadata,
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
from app.modules.regime_detection.infrastructure.ensemble.alignment import (
    RegimeAlignmentEngine,
)
from app.modules.regime_detection.infrastructure.ensemble.registry import (
    RegimeModelRegistry,
)
from app.modules.regime_detection.infrastructure.models.ensemble import (
    RegimeModelEnsemble,
)
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.hmm import (
    GaussianHMMRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Synthetic Dataset Generators
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TIME + timedelta(days=i)


def _make_separable_three_cluster_matrix(
    n_per_cluster: int = 40,
    seed: int = 42,
) -> FeatureMatrix:
    """Three well-separated 2D clusters: low, medium, high return."""
    rng = np.random.default_rng(seed)
    n_total = n_per_cluster * 3

    timestamps = tuple(_ts(i) for i in range(n_total))
    feature_names = ("feat_return", "feat_volatility")

    data_a = rng.normal(loc=[-0.05, 0.25], scale=0.01, size=(n_per_cluster, 2))
    data_b = rng.normal(loc=[0.00, 0.15], scale=0.01, size=(n_per_cluster, 2))
    data_c = rng.normal(loc=[0.05, 0.08], scale=0.01, size=(n_per_cluster, 2))

    stacked = np.vstack([data_a, data_b, data_c])
    values = tuple(tuple(float(v) for v in row) for row in stacked)

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=values,
    )


# ---------------------------------------------------------------------------
# Mock Detector Helpers for Isolation Testing
# ---------------------------------------------------------------------------


class MockRegimeDetector(RegimeDetector):
    """Controllable mock detector for deterministic alignment and failure testing."""

    def __init__(
        self,
        algorithm_id: str = "mock_model",
        predictions: tuple[int, ...] = (0, 1, 0),
        profiles: tuple[ClusterProfile, ...] = (),
        fail_fit: bool = False,
        fail_predict: bool = False,
    ) -> None:
        self._alg_id = algorithm_id
        self._predictions = predictions
        self._profiles = profiles
        self._fail_fit = fail_fit
        self._fail_predict = fail_predict
        self._state = ModelState.UNFITTED
        self._fit_result: FitResult | None = None

    @property
    def algorithm_id(self) -> str:
        return self._alg_id

    @property
    def algorithm_version(self) -> str:
        return "1.0.0"

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    def fit(self, feature_matrix: FeatureMatrix) -> MockRegimeDetector:
        if self._fail_fit:
            raise RuntimeError(f"Simulated fit failure for {self._alg_id}")
        self._state = ModelState.FITTED
        self._fit_result = FitResult(
            model_name=self._alg_id,
            model_version="1.0.0",
            algorithm="Mock",
            n_clusters=len(self._profiles) or 2,
            random_state=42,
            feature_names=feature_matrix.feature_names,
            training_sample_count=feature_matrix.sample_count,
            training_start=feature_matrix.timestamps[0],
            training_end=feature_matrix.timestamps[-1],
            inertia=0.0,
            iterations=1,
            cluster_profiles=self._profiles,
        )
        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._alg_id)
        if self._fail_predict:
            raise RuntimeError(f"Simulated prediction failure for {self._alg_id}")
        # Repeat or slice predictions to match feature_matrix sample count
        n = feature_matrix.sample_count
        if len(self._predictions) >= n:
            return self._predictions[:n]
        reps = (n // len(self._predictions)) + 1
        return (self._predictions * reps)[:n]

    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...] | None:
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._alg_id)
        return None

    def get_params(self) -> dict[str, Any]:
        return {"algorithm_id": self._alg_id}

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            algorithm_id=self._alg_id,
            algorithm_version="1.0.0",
            algorithm_family="Mock",
            description="Mock detector",
        )


def _make_dummy_profile(
    cluster_id: int,
    canonical_id: int,
    feat_means: dict[str, float],
) -> ClusterProfile:
    return ClusterProfile(
        cluster_id=cluster_id,
        canonical_regime_id=canonical_id,
        canonical_regime_label=f"REGIME_{canonical_id}",
        center=tuple(feat_means.values()),
        sample_count=50,
        feature_means=feat_means,
        feature_stds=dict.fromkeys(feat_means, 0.01),
    )


# ===========================================================================
# 1. Configuration Validation Tests
# ===========================================================================


class TestEnsembleConfiguration:
    def test_default_config(self) -> None:
        config = EnsembleModelConfig()
        assert config.model_name == "regime-ensemble"
        assert config.enabled_models == ("kmeans", "gmm", "hmm")
        assert config.model_weights == {"kmeans": 1.0, "gmm": 1.0, "hmm": 1.0}
        assert config.aggregation_strategy == AggregationStrategy.WEIGHTED_VOTING
        assert config.minimum_required_models == 2
        assert config.failure_policy == FailurePolicy.SKIP_UNAVAILABLE
        assert config.alignment_policy == AlignmentPolicy.FEATURE_SIMILARITY
        assert config.tie_breaker == EnsembleTieBreaker.LOWEST_REGIME_ID

    def test_custom_valid_config(self) -> None:
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm"),
            model_weights={"kmeans": 2.0, "gmm": 1.0},
            minimum_required_models=1,
            aggregation_strategy=AggregationStrategy.MAJORITY_VOTING,
            failure_policy=FailurePolicy.FAIL_FAST,
            alignment_policy=AlignmentPolicy.CANONICAL_LABEL,
            tie_breaker=EnsembleTieBreaker.MODEL_PRECEDENCE,
            reference_model="kmeans",
        )
        assert config.enabled_models == ("kmeans", "gmm")
        assert config.minimum_required_models == 1
        assert config.reference_model == "kmeans"

    def test_empty_enabled_models_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must enable at least one model"):
            EnsembleModelConfig(enabled_models=())

    def test_duplicate_enabled_models_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate model identifier"):
            EnsembleModelConfig(enabled_models=("kmeans", "kmeans"))

    def test_negative_weight_rejected(self) -> None:
        with pytest.raises(ValidationError, match="cannot be negative"):
            EnsembleModelConfig(
                enabled_models=("kmeans", "gmm"),
                model_weights={"kmeans": -1.0, "gmm": 1.0},
            )

    def test_zero_total_weight_rejected(self) -> None:
        with pytest.raises(ValidationError, match="strictly greater than 0.0"):
            EnsembleModelConfig(
                enabled_models=("kmeans", "gmm"),
                model_weights={"kmeans": 0.0, "gmm": 0.0},
            )

    def test_unknown_model_in_weights_rejected(self) -> None:
        with pytest.raises(ValidationError, match="keys not present in enabled_models"):
            EnsembleModelConfig(
                enabled_models=("kmeans", "gmm"),
                model_weights={"kmeans": 1.0, "unknown_model": 1.0},
            )

    def test_minimum_required_models_exceeds_enabled_rejected(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed the number of enabled models"):
            EnsembleModelConfig(
                enabled_models=("kmeans", "gmm"),
                minimum_required_models=3,
            )

    def test_minimum_required_models_less_than_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EnsembleModelConfig(minimum_required_models=0)

    def test_reference_model_not_in_enabled_rejected(self) -> None:
        with pytest.raises(ValidationError, match="reference_model .* is not in enabled_models"):
            EnsembleModelConfig(
                enabled_models=("kmeans", "gmm"),
                reference_model="hmm",
            )

    def test_explicit_mapping_policy_requires_mapping(self) -> None:
        with pytest.raises(ValidationError, match="explicit_mapping must be provided"):
            EnsembleModelConfig(
                alignment_policy=AlignmentPolicy.EXPLICIT_MAPPING,
                explicit_mapping=None,
            )

    def test_duplicate_feature_names_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate feature name"):
            EnsembleModelConfig(feature_names=("feat_a", "feat_a"))


# ===========================================================================
# 2. Registry Tests
# ===========================================================================


class TestRegimeModelRegistry:
    def test_standard_models_registered(self) -> None:
        available = RegimeModelRegistry.list_available()
        assert "kmeans" in available
        assert "gmm" in available
        assert "hmm" in available

    def test_instantiate_standard_models(self) -> None:
        km = RegimeModelRegistry.create("kmeans")
        assert isinstance(km, KMeansRegimeDetector)
        gmm = RegimeModelRegistry.create("gmm")
        assert isinstance(gmm, GaussianMixtureRegimeDetector)
        hmm = RegimeModelRegistry.create("hmm")
        assert isinstance(hmm, GaussianHMMRegimeDetector)

    def test_custom_model_registration(self) -> None:
        RegimeModelRegistry.register(
            "custom_mock",
            lambda: MockRegimeDetector(algorithm_id="custom_mock"),
        )
        assert "custom_mock" in RegimeModelRegistry.list_available()
        custom = RegimeModelRegistry.create("custom_mock")
        assert custom.algorithm_id == "custom_mock"

    def test_unknown_model_raises_error(self) -> None:
        with pytest.raises(InvalidEnsembleConfigurationError, match="Unknown model identifier"):
            RegimeModelRegistry.create("nonexistent_model")

    def test_invalid_model_id_raises_error(self) -> None:
        with pytest.raises(InvalidEnsembleConfigurationError, match="non-empty string"):
            RegimeModelRegistry.register("", lambda: MockRegimeDetector())


# ===========================================================================
# 3. Regime Identity Alignment Tests
# ===========================================================================


class TestRegimeAlignmentEngine:
    def test_canonical_label_alignment(self) -> None:
        """CANONICAL_LABEL produces direct identity mapping for models."""
        matrix = _make_separable_three_cluster_matrix()
        prof_0 = _make_dummy_profile(0, 0, {"feat_return": -0.05, "feat_volatility": 0.25})
        prof_1 = _make_dummy_profile(1, 1, {"feat_return": 0.05, "feat_volatility": 0.08})

        m1 = MockRegimeDetector(algorithm_id="m1", profiles=(prof_0, prof_1)).fit(matrix)
        m2 = MockRegimeDetector(algorithm_id="m2", profiles=(prof_0, prof_1)).fit(matrix)

        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            alignment_policy=AlignmentPolicy.CANONICAL_LABEL,
        )
        mapping = RegimeAlignmentEngine.build_alignment({"m1": m1, "m2": m2}, config)
        assert mapping["m1"] == {0: 0, 1: 1}
        assert mapping["m2"] == {0: 0, 1: 1}

    def test_permuted_labels_alignment_via_feature_similarity(self) -> None:
        """
        When Model A defines:
          Regime 0: Low return (-0.05)
          Regime 1: High return (+0.05)
        And Model B defines permuted labels:
          Regime 0: High return (+0.05) -> should map to Reference Regime 1
          Regime 1: Low return (-0.05)  -> should map to Reference Regime 0
        """
        matrix = _make_separable_three_cluster_matrix()

        # Model A: canonical reference
        prof_a0 = _make_dummy_profile(0, 0, {"feat_return": -0.05, "feat_volatility": 0.25})
        prof_a1 = _make_dummy_profile(1, 1, {"feat_return": 0.05, "feat_volatility": 0.08})
        m_a = MockRegimeDetector(algorithm_id="m_a", profiles=(prof_a0, prof_a1)).fit(matrix)

        # Model B: inverted labels
        prof_b0 = _make_dummy_profile(0, 0, {"feat_return": 0.05, "feat_volatility": 0.08})
        prof_b1 = _make_dummy_profile(1, 1, {"feat_return": -0.05, "feat_volatility": 0.25})
        m_b = MockRegimeDetector(algorithm_id="m_b", profiles=(prof_b0, prof_b1)).fit(matrix)

        config = EnsembleModelConfig(
            enabled_models=("m_a", "m_b"),
            reference_model="m_a",
            alignment_policy=AlignmentPolicy.FEATURE_SIMILARITY,
        )
        mapping = RegimeAlignmentEngine.build_alignment({"m_a": m_a, "m_b": m_b}, config)

        assert mapping["m_a"] == {0: 0, 1: 1}
        # Model B: source 0 maps to canonical 1, source 1 maps to canonical 0
        assert mapping["m_b"][0] == 1
        assert mapping["m_b"][1] == 0

    def test_explicit_mapping_policy(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        prof_0 = _make_dummy_profile(0, 0, {"feat_return": 0.0, "feat_volatility": 0.1})
        m1 = MockRegimeDetector(algorithm_id="m1", profiles=(prof_0,)).fit(matrix)

        config = EnsembleModelConfig(
            enabled_models=("m1",),
            minimum_required_models=1,
            alignment_policy=AlignmentPolicy.EXPLICIT_MAPPING,
            explicit_mapping={"m1": {0: 42}},
        )
        mapping = RegimeAlignmentEngine.build_alignment({"m1": m1}, config)
        assert mapping["m1"] == {0: 42}

    def test_alignment_fails_on_unfitted_model(self) -> None:
        m1 = MockRegimeDetector(algorithm_id="m1")
        config = EnsembleModelConfig(enabled_models=("m1",), minimum_required_models=1)
        with pytest.raises(ModelNotFittedError):
            RegimeAlignmentEngine.build_alignment({"m1": m1}, config)

    def test_align_predictions_transformation(self) -> None:
        raw_preds = {"m1": (0, 1, 0), "m2": (0, 0, 1)}
        alignment_maps = {"m1": {0: 0, 1: 1}, "m2": {0: 1, 1: 0}}
        aligned = RegimeAlignmentEngine.align_predictions(raw_preds, alignment_maps)
        assert aligned["m1"] == (0, 1, 0)
        assert aligned["m2"] == (1, 1, 0)


# ===========================================================================
# 4. Aggregation & Voting Tests
# ===========================================================================


class TestEnsembleAggregator:
    def test_unanimous_models(self) -> None:
        ts = (_ts(0), _ts(1))
        comp_preds = {"m1": (0, 1), "m2": (0, 1), "m3": (0, 1)}
        aligned_preds = {"m1": (0, 1), "m2": (0, 1), "m3": (0, 1)}
        weights = {"m1": 0.33, "m2": 0.33, "m3": 0.34}
        config = EnsembleModelConfig(enabled_models=("m1", "m2", "m3"))

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )
        assert regimes == (0, 1)
        assert records[0].is_unanimous is True
        assert records[0].agreement_count == 3
        assert records[0].disagreeing_models == ()

    def test_majority_voting_agreement(self) -> None:
        """2 models vote regime 1, 1 model votes regime 0 -> consensus is regime 1."""
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (1,), "m3": (0,)}
        aligned_preds = {"m1": (1,), "m2": (1,), "m3": (0,)}
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            aggregation_strategy=AggregationStrategy.MAJORITY_VOTING,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )
        assert regimes == (1,)
        assert records[0].agreement_count == 2
        assert records[0].is_unanimous is False
        assert records[0].disagreeing_models == ("m3",)

    def test_weighted_majority_overrides_unweighted_plurality(self) -> None:
        """
        m1 has weight 3.0 and votes 0.
        m2 and m3 each have weight 1.0 and vote 1.
        Weighted voting: 0 gets 3.0, 1 gets 2.0 -> consensus is 0.
        """
        ts = (_ts(0),)
        comp_preds = {"m1": (0,), "m2": (1,), "m3": (1,)}
        aligned_preds = {"m1": (0,), "m2": (1,), "m3": (1,)}
        weights = {"m1": 0.6, "m2": 0.2, "m3": 0.2}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2", "m3"),
            aggregation_strategy=AggregationStrategy.WEIGHTED_VOTING,
        )

        regimes, records = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )
        assert regimes == (0,)
        assert records[0].agreement_count == 1
        assert records[0].disagreeing_models == ("m2", "m3")

    def test_exact_tie_broken_by_lowest_regime_id(self) -> None:
        """m1 votes 1 (weight 1.0), m2 votes 0 (weight 1.0) -> tie broken to 0."""
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (0,)}
        aligned_preds = {"m1": (1,), "m2": (0,)}
        weights = {"m1": 0.5, "m2": 0.5}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            tie_breaker=EnsembleTieBreaker.LOWEST_REGIME_ID,
        )

        regimes, _ = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )
        assert regimes == (0,)

    def test_exact_tie_broken_by_model_precedence(self) -> None:
        """
        m1 votes 1 (weight 1.0), m2 votes 0 (weight 1.0).
        With MODEL_PRECEDENCE and enabled_models=("m1", "m2"), m1's vote (1) wins.
        """
        ts = (_ts(0),)
        comp_preds = {"m1": (1,), "m2": (0,)}
        aligned_preds = {"m1": (1,), "m2": (0,)}
        weights = {"m1": 0.5, "m2": 0.5}
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            tie_breaker=EnsembleTieBreaker.MODEL_PRECEDENCE,
        )

        regimes, _ = EnsembleAggregator.aggregate(
            timestamps=ts,
            component_predictions=comp_preds,
            aligned_predictions=aligned_preds,
            weights=weights,
            config=config,
        )
        assert regimes == (1,)


# ===========================================================================
# 5. Availability & Failure Policy Tests
# ===========================================================================


class TestEnsembleAvailabilityAndFailure:
    def test_all_models_available(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1", predictions=(0, 1, 2))
        m2 = MockRegimeDetector(algorithm_id="m2", predictions=(0, 1, 2))
        config = EnsembleModelConfig(enabled_models=("m1", "m2"))

        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        ensemble.fit(matrix)
        preds = ensemble.predict(matrix)
        assert len(preds) == matrix.sample_count

    def test_fail_fast_policy_raises_on_fit_failure(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1")
        m2 = MockRegimeDetector(algorithm_id="m2", fail_fit=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            failure_policy=FailurePolicy.FAIL_FAST,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        with pytest.raises(EnsembleModelUnavailableError, match="Fit failed for model 'm2'"):
            ensemble.fit(matrix)

    def test_skip_unavailable_policy_tolerates_failed_model(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1", predictions=(0,))
        m2 = MockRegimeDetector(algorithm_id="m2", fail_fit=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            minimum_required_models=1,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        ensemble.fit(matrix)
        assert ensemble.state == ModelState.FITTED

        result = ensemble.predict_ensemble(matrix)
        assert "m1" in result.models_used
        assert "m2" in result.models_unavailable

    def test_insufficient_usable_models_raises_error(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1", fail_fit=True)
        m2 = MockRegimeDetector(algorithm_id="m2", fail_fit=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            minimum_required_models=1,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        with pytest.raises(InsufficientUsableModelsError, match="requires at least 1 models"):
            ensemble.fit(matrix)

    def test_fail_fast_on_predict_failure(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1")
        m2 = MockRegimeDetector(algorithm_id="m2", fail_predict=True)
        config = EnsembleModelConfig(
            enabled_models=("m1", "m2"),
            minimum_required_models=1,
            failure_policy=FailurePolicy.FAIL_FAST,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        ensemble.fit(matrix)

        with pytest.raises(EnsembleModelUnavailableError, match="Prediction failed for model 'm2'"):
            ensemble.predict(matrix)


# ===========================================================================
# 6. Output Contract & Non-Confidence Guard Tests
# ===========================================================================


class TestEnsembleOutputContract:
    def test_predict_proba_returns_normalized_support_distribution(self) -> None:
        """V11 Commit 02 contract: predict_proba() returns support vectors summing to 1.0."""
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1")
        config = EnsembleModelConfig(enabled_models=("m1",), minimum_required_models=1)
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1}).fit(matrix)

        proba = ensemble.predict_proba(matrix)
        assert proba is not None
        assert len(proba) == matrix.sample_count
        for row in proba:
            assert abs(sum(row) - 1.0) < 1e-6
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_output_contains_validated_confidence_fields(self) -> None:
        """Ensures confidence fields and breakdown records are present and valid."""
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1")
        config = EnsembleModelConfig(enabled_models=("m1",), minimum_required_models=1)
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1}).fit(matrix)
        result = ensemble.predict_ensemble(matrix)

        assert hasattr(result, "confidence_scores")
        assert len(result.confidence_scores) == matrix.sample_count
        assert len(result.get_confidence_series()) == matrix.sample_count
        assert 0.0 <= result.get_average_confidence() <= 1.0

        for record in result.records:
            assert hasattr(record, "confidence")
            assert hasattr(record, "confidence_breakdown")
            assert 0.0 <= record.confidence <= 1.0
            assert record.confidence_breakdown.score == record.confidence

    def test_provenance_and_predictions_preserved(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1", predictions=(0, 1, 0))
        m2 = MockRegimeDetector(algorithm_id="m2", predictions=(0, 0, 1))
        config = EnsembleModelConfig(enabled_models=("m1", "m2"))
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2}).fit(matrix)
        result = ensemble.predict_ensemble(matrix)

        assert result.models_used == ("m1", "m2")
        assert "m1" in result.component_predictions
        assert "m2" in result.component_predictions
        assert "m1" in result.aligned_predictions
        assert "m2" in result.aligned_predictions
        assert len(result.ensemble_regimes) == matrix.sample_count
        assert len(result.records) == matrix.sample_count
        assert result.get_agreement_rate() >= 0.0

    def test_metadata_and_params(self) -> None:
        config = EnsembleModelConfig()
        ensemble = RegimeModelEnsemble(config=config)
        meta = ensemble.metadata()
        assert meta.algorithm_id == "regime_ensemble"
        assert meta.algorithm_family == "Ensemble Consensus"
        assert "predict_proba" not in meta.hyperparameters  # cleanly documented


# ===========================================================================
# 7. Leakage, Immutability & Determinism Tests
# ===========================================================================


class TestEnsembleLeakageAndDeterminism:
    def test_feature_matrix_unmutated(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        orig_timestamps = list(matrix.timestamps)
        orig_values = list(matrix.values)

        m1 = MockRegimeDetector(algorithm_id="m1")
        config = EnsembleModelConfig(enabled_models=("m1",), minimum_required_models=1)
        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1})
        ensemble.fit(matrix)
        _ = ensemble.predict(matrix)

        assert list(matrix.timestamps) == orig_timestamps
        assert list(matrix.values) == orig_values

    def test_repeatable_inference_determinism(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        m1 = MockRegimeDetector(algorithm_id="m1", predictions=(0, 1, 2))
        m2 = MockRegimeDetector(algorithm_id="m2", predictions=(0, 1, 1))
        config = EnsembleModelConfig(enabled_models=("m1", "m2"))

        ensemble = RegimeModelEnsemble(config=config, models={"m1": m1, "m2": m2})
        ensemble.fit(matrix)

        preds_a = ensemble.predict(matrix)
        preds_b = ensemble.predict(matrix)
        assert preds_a == preds_b

    def test_empty_matrix_raises_error(self) -> None:
        empty_matrix = FeatureMatrix(
            timestamps=(),
            feature_names=("feat_a",),
            values=(),
        )
        ensemble = RegimeModelEnsemble()
        with pytest.raises(InvalidFeatureMatrixError):
            ensemble.fit(empty_matrix)

    def test_insufficient_samples_raises_error(self) -> None:
        single_row_matrix = FeatureMatrix(
            timestamps=(_ts(0),),
            feature_names=("feat_a",),
            values=((1.0,),),
        )
        ensemble = RegimeModelEnsemble()
        with pytest.raises(InsufficientTrainingDataError):
            ensemble.fit(single_row_matrix)

    def test_feature_name_mismatch_raises_error(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        config = EnsembleModelConfig(
            enabled_models=("m1",),
            minimum_required_models=1,
            feature_names=("feat_different_1", "feat_different_2"),
        )
        ensemble = RegimeModelEnsemble(
            config=config,
            models={"m1": MockRegimeDetector(algorithm_id="m1")},
        )
        with pytest.raises(
            InvalidFeatureMatrixError,
            match="do not match configured ensemble features",
        ):
            ensemble.fit(matrix)


# ===========================================================================
# 8. End-to-End Multi-Model Integration (KMeans + GMM + HMM)
# ===========================================================================


class TestEnsembleMultiModelIntegration:
    def test_kmeans_gmm_hmm_end_to_end_consensus(self) -> None:
        """
        Fit all three real models (KMeans, GMM, HMM) on synthetic 3-cluster data,
        align regimes, and execute ensemble consensus inference.
        """
        matrix = _make_separable_three_cluster_matrix(n_per_cluster=40, seed=101)

        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm", "hmm"),
            minimum_required_models=3,
            aggregation_strategy=AggregationStrategy.WEIGHTED_VOTING,
            alignment_policy=AlignmentPolicy.FEATURE_SIMILARITY,
        )

        ensemble = RegimeModelEnsemble(config=config)
        ensemble.fit(matrix)
        assert ensemble.state == ModelState.FITTED
        assert ensemble.fit_result is not None

        result = ensemble.predict_ensemble(matrix)

        # Basic contract assertions
        assert len(result.records) == matrix.sample_count
        assert set(result.models_used) == {"kmeans", "gmm", "hmm"}
        assert len(result.models_unavailable) == 0

        # On well-separated synthetic data, all 3 models should achieve high consensus
        agreement_rate = result.get_agreement_rate()
        msg = f"Expected high agreement on separated data, got {agreement_rate}"
        assert agreement_rate >= 0.80, msg

        # Verify predictions series helper
        regime_series = result.get_regime_series()
        assert len(regime_series) == matrix.sample_count
        assert all(isinstance(r, int) for r in regime_series)

        # Verify predict() matches get_regime_series()
        direct_preds = ensemble.predict(matrix)
        assert direct_preds == regime_series
