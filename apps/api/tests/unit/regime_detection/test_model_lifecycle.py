"""
RegimeX Regime Detection — Model Lifecycle Hardening Tests
==========================================================
Comprehensive lifecycle validation for the KMeansRegimeDetector:

1. UNFITTED state on construction — predict/predict_proba raise typed errors.
2. UNFITTED → FITTED transition upon successful fit().
3. fit() returns self (fluent interface).
4. Repeated prediction after fit() is deterministic.
5. Refit on second dataset completely replaces model state.
6. No stale scaler or KMeans model survives from previous fit.
7. Metadata completeness validation.
8. Full model configuration edge-case tests.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.errors import (
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    ModelState,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TIME + timedelta(days=i)


def _make_simple_matrix(n: int = 20, n_features: int = 2) -> FeatureMatrix:
    """Creates a minimal separable matrix for lifecycle tests."""
    rows = [(float(i % 2) * 2.0 - 1.0, float(i % 2) * 3.0) for i in range(n)]
    feat_names = tuple(f"feat_{j}" for j in range(n_features))
    return FeatureMatrix(
        timestamps=tuple(_ts(i) for i in range(n)),
        feature_names=feat_names,
        values=tuple(rows),
    )


# ---------------------------------------------------------------------------
# Class 1: UNFITTED → FITTED lifecycle
# ---------------------------------------------------------------------------


class TestModelLifecycleTransitions:
    """Tests the UNFITTED → FITTED state machine."""

    def test_new_detector_is_unfitted(self) -> None:
        """A freshly constructed detector must be in UNFITTED state."""
        detector = KMeansRegimeDetector()
        assert detector.state == ModelState.UNFITTED

    def test_new_detector_fit_result_is_none(self) -> None:
        """A freshly constructed detector must have fit_result = None."""
        detector = KMeansRegimeDetector()
        assert detector.fit_result is None

    def test_predict_before_fit_raises_model_not_fitted_error(self) -> None:
        """predict() on an unfitted model must raise ModelNotFittedError."""
        detector = KMeansRegimeDetector()
        matrix = _make_simple_matrix()
        with pytest.raises(ModelNotFittedError):
            detector.predict(matrix)

    def test_predict_proba_before_fit_raises_model_not_fitted_error(self) -> None:
        """predict_proba() on an unfitted model must raise ModelNotFittedError."""
        detector = KMeansRegimeDetector()
        matrix = _make_simple_matrix()
        with pytest.raises(ModelNotFittedError):
            detector.predict_proba(matrix)

    def test_model_not_fitted_error_carries_model_name(self) -> None:
        """ModelNotFittedError must include the model name in its message."""
        config = RegimeModelConfig(model_name="test-kmeans")
        detector = KMeansRegimeDetector(config=config)
        matrix = _make_simple_matrix()
        with pytest.raises(ModelNotFittedError, match="test-kmeans"):
            detector.predict(matrix)

    def test_fit_transitions_to_fitted_state(self) -> None:
        """After successful fit(), detector.state must be FITTED."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=20)
        detector.fit(matrix)
        assert detector.state == ModelState.FITTED

    def test_fit_returns_self(self) -> None:
        """fit() must return the same detector instance (fluent builder pattern)."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=20)
        result = detector.fit(matrix)
        assert result is detector

    def test_predict_succeeds_after_fit(self) -> None:
        """predict() must succeed after fit() and return one value per row."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=20)
        detector.fit(matrix)
        preds = detector.predict(matrix)
        assert len(preds) == 20

    def test_predict_proba_succeeds_after_fit(self) -> None:
        """predict_proba() must succeed after fit() and return normalized distributions."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=20)
        detector.fit(matrix)
        probs = detector.predict_proba(matrix)
        assert len(probs) == 20
        for row in probs:
            assert math.isclose(sum(row), 1.0, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Class 2: Repeated prediction determinism
# ---------------------------------------------------------------------------


class TestRepeatedPredictionDeterminism:
    """Validates deterministic behavior across multiple sequential calls."""

    def test_three_repeated_predictions_are_identical(self) -> None:
        """Three sequential predict() calls on the same matrix must be identical."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=30)
        detector.fit(matrix)

        preds_1 = detector.predict(matrix)
        preds_2 = detector.predict(matrix)
        preds_3 = detector.predict(matrix)

        assert preds_1 == preds_2 == preds_3

    def test_three_repeated_predict_proba_are_identical(self) -> None:
        """Three sequential predict_proba() calls must produce identical results."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        matrix = _make_simple_matrix(n=30)
        detector.fit(matrix)

        probs_1 = detector.predict_proba(matrix)
        probs_2 = detector.predict_proba(matrix)
        probs_3 = detector.predict_proba(matrix)

        assert probs_1 == probs_2 == probs_3

    def test_predict_deterministic_across_two_independent_detectors(self) -> None:
        """Two detectors with the same config on the same data must produce
        identical predictions."""
        config = RegimeModelConfig(n_clusters=3, random_state=42)
        matrix = _make_simple_matrix(n=30)

        det_a = KMeansRegimeDetector(config=config)
        det_a.fit(matrix)

        det_b = KMeansRegimeDetector(config=config)
        det_b.fit(matrix)

        assert det_a.predict(matrix) == det_b.predict(matrix)
        assert det_a.predict_proba(matrix) == det_b.predict_proba(matrix)


# ---------------------------------------------------------------------------
# Class 3: Refit lifecycle
# ---------------------------------------------------------------------------


class TestRefitLifecycle:
    """Validates that refitting correctly replaces all model state."""

    def test_refit_updates_sample_count(self) -> None:
        """After refit on a larger dataset, training_sample_count must update."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))

        matrix_20 = _make_simple_matrix(n=20)
        detector.fit(matrix_20)
        assert detector.fit_result is not None
        assert detector.fit_result.training_sample_count == 20

        matrix_40 = _make_simple_matrix(n=40)
        detector.fit(matrix_40)
        assert detector.fit_result is not None
        assert detector.fit_result.training_sample_count == 40

    def test_refit_updates_training_timestamps(self) -> None:
        """After refit, training_start and training_end must reflect the new data."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))

        matrix_1 = _make_simple_matrix(n=10)
        detector.fit(matrix_1)
        end_1 = detector.fit_result.training_end  # type: ignore[union-attr]

        # Second dataset starts much later
        later_base = datetime(2030, 1, 1, 0, 0, tzinfo=UTC)
        rows = [(float(i % 2) * 2.0 - 1.0, float(i % 2) * 3.0) for i in range(10)]
        matrix_2 = FeatureMatrix(
            timestamps=tuple(later_base + timedelta(days=i) for i in range(10)),
            feature_names=("feat_0", "feat_1"),
            values=tuple(rows),
        )
        detector.fit(matrix_2)
        start_2 = detector.fit_result.training_start  # type: ignore[union-attr]

        assert start_2 > end_1, (
            "training_start after refit must be after training_end of original fit."
        )

    def test_refit_replaces_scaler_not_accumulates(self) -> None:
        """After refit, scaler must be entirely replaced — no parameter accumulation."""
        import numpy as np
        from sklearn.preprocessing import StandardScaler

        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))

        matrix_1 = _make_simple_matrix(n=20)
        detector.fit(matrix_1)

        mean_after_fit1 = np.copy(detector._scaler.mean_)  # type: ignore[union-attr]

        # New dataset with different statistics
        rows = [(float(100.0 + i), float(200.0 + i)) for i in range(20)]
        matrix_2 = FeatureMatrix(
            timestamps=tuple(_ts(i + 500) for i in range(20)),
            feature_names=("feat_0", "feat_1"),
            values=tuple(rows),
        )
        detector.fit(matrix_2)

        # Verify new scaler reflects new data
        ref = StandardScaler()
        import numpy as np

        ref.fit(np.array(matrix_2.values, dtype=np.float64))

        assert detector._scaler is not None
        assert np.allclose(detector._scaler.mean_, ref.mean_, rtol=1e-10)
        # Must differ substantially from old fit
        assert not np.allclose(detector._scaler.mean_, mean_after_fit1, atol=1.0)

    def test_state_remains_fitted_after_refit(self) -> None:
        """State must be FITTED (not UNFITTED) after refit on second dataset."""
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(_make_simple_matrix(n=20))
        detector.fit(_make_simple_matrix(n=30))
        assert detector.state == ModelState.FITTED

    def test_predict_uses_new_model_after_refit(self) -> None:
        """After refit, predict() must produce predictions consistent with the new training data."""

        # First fit: two clusters at ±1
        rows_a = [(-1.0, -1.0)] * 10 + [(1.0, 1.0)] * 10
        matrix_a = FeatureMatrix(
            timestamps=tuple(_ts(i) for i in range(20)),
            feature_names=("feat_0", "feat_1"),
            values=tuple(rows_a),
        )
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix_a)
        preds_a = detector.predict(matrix_a)

        # Second fit: two clusters at ±100 (completely different feature space)
        rows_b = [(-100.0, -100.0)] * 10 + [(100.0, 100.0)] * 10
        matrix_b = FeatureMatrix(
            timestamps=tuple(_ts(i + 100) for i in range(20)),
            feature_names=("feat_0", "feat_1"),
            values=tuple(rows_b),
        )
        detector.fit(matrix_b)
        preds_b = detector.predict(matrix_b)

        # Both should cleanly separate their respective clusters
        assert len(set(preds_a)) == 2
        assert len(set(preds_b)) == 2


# ---------------------------------------------------------------------------
# Class 4: Metadata completeness
# ---------------------------------------------------------------------------


class TestMetadataCompleteness:
    """
    Validates that model metadata includes all fields required for research reproducibility.
    """

    def test_metadata_algorithm_id_present(self) -> None:
        """metadata().algorithm_id must be present and non-empty."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert meta.algorithm_id
        assert meta.algorithm_id == "kmeans_baseline"

    def test_metadata_algorithm_version_present(self) -> None:
        """metadata().algorithm_version must be present."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert meta.algorithm_version
        assert meta.algorithm_version == "1.0.0"

    def test_metadata_algorithm_family_present(self) -> None:
        """metadata().algorithm_family must describe the model family."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert meta.algorithm_family
        # Should reference geometric clustering
        assert (
            "cluster" in meta.algorithm_family.lower()
            or "partition" in meta.algorithm_family.lower()
        )

    def test_metadata_description_present(self) -> None:
        """metadata().description must be a non-empty human-readable text."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert meta.description
        assert len(meta.description) > 20

    def test_metadata_assumptions_non_empty(self) -> None:
        """metadata().assumptions must list at least one modeling assumption."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert len(meta.assumptions) >= 1

    def test_metadata_known_limitations_non_empty(self) -> None:
        """metadata().known_limitations must list at least one limitation."""
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        assert len(meta.known_limitations) >= 1

    def test_metadata_hyperparameters_include_required_fields(self) -> None:
        """metadata().hyperparameters must include n_clusters, random_state, init, and tol."""
        config = RegimeModelConfig(n_clusters=3, random_state=77)
        detector = KMeansRegimeDetector(config=config)
        meta = detector.metadata()
        params = meta.hyperparameters
        assert "n_clusters" in params
        assert params["n_clusters"] == 3
        assert "random_state" in params
        assert params["random_state"] == 77
        assert "init" in params
        assert "tol" in params
        assert "max_iter" in params

    def test_metadata_does_not_contain_machine_credentials_or_paths(self) -> None:
        """Metadata must not expose local paths, usernames, or environment secrets."""
        import os

        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        meta_str = meta.model_dump_json()

        # Must not contain common credential exposure patterns
        assert "password" not in meta_str.lower()
        assert "secret" not in meta_str.lower()
        assert "api_key" not in meta_str.lower()
        # Must not contain the user's home directory path
        home = os.path.expanduser("~").replace("\\", "/")
        assert home not in meta_str


# ---------------------------------------------------------------------------
# Class 5: Configuration edge cases
# ---------------------------------------------------------------------------


class TestModelConfigurationEdgeCases:
    """Tests edge-case configurations using InvalidModelConfigurationError."""

    def test_default_config_valid(self) -> None:
        """Default RegimeModelConfig must be valid and produce a working detector."""
        detector = KMeansRegimeDetector()
        assert detector._config.n_clusters == 4
        assert detector._config.random_state == 42
        assert detector._config.init == "k-means++"

    def test_custom_n_clusters_2_valid(self) -> None:
        config = RegimeModelConfig(n_clusters=2)
        detector = KMeansRegimeDetector(config=config)
        matrix = _make_simple_matrix(n=20)
        detector.fit(matrix)
        assert detector.fit_result is not None
        assert detector.fit_result.n_clusters == 2

    def test_custom_random_state_valid(self) -> None:
        config = RegimeModelConfig(n_clusters=2, random_state=123)
        detector = KMeansRegimeDetector(config=config)
        assert detector._config.random_state == 123

    def test_custom_max_iter_valid(self) -> None:
        config = RegimeModelConfig(n_clusters=2, max_iter=50)
        assert config.max_iter == 50

    def test_custom_init_random_valid(self) -> None:
        config = RegimeModelConfig(n_clusters=2, init="random")
        assert config.init == "random"

    def test_custom_tol_valid(self) -> None:
        config = RegimeModelConfig(n_clusters=2, tol=1e-6)
        assert config.tol == 1e-6

    def test_n_clusters_below_2_rejected(self) -> None:
        """n_clusters < 2 must be rejected at config construction time."""
        with pytest.raises(ValidationError):
            RegimeModelConfig(n_clusters=1)
        with pytest.raises(ValidationError):
            RegimeModelConfig(n_clusters=0)
        with pytest.raises(ValidationError):
            RegimeModelConfig(n_clusters=-5)

    def test_max_iter_zero_rejected(self) -> None:
        """max_iter = 0 must be rejected."""
        with pytest.raises(ValidationError):
            RegimeModelConfig(max_iter=0)

    def test_max_iter_negative_rejected(self) -> None:
        """max_iter < 0 must be rejected."""
        with pytest.raises(ValidationError):
            RegimeModelConfig(max_iter=-1)

    def test_tol_zero_rejected(self) -> None:
        """tol = 0.0 must be rejected (tol must be strictly positive)."""
        with pytest.raises(ValidationError):
            RegimeModelConfig(tol=0.0)

    def test_tol_negative_rejected(self) -> None:
        """tol < 0 must be rejected."""
        with pytest.raises(ValidationError):
            RegimeModelConfig(tol=-1e-5)

    def test_invalid_init_strategy_rejected(self) -> None:
        """An unsupported init strategy must be rejected."""
        with pytest.raises(ValidationError, match="init strategy"):
            RegimeModelConfig(init="spectral")
        with pytest.raises(ValidationError, match="init strategy"):
            RegimeModelConfig(init="")

    def test_empty_feature_list_allowed_in_config(self) -> None:
        """Empty feature_names in config is allowed (features inferred from matrix)."""
        config = RegimeModelConfig(feature_names=())
        assert config.feature_names == ()

    def test_duplicate_feature_names_rejected_in_config(self) -> None:
        """Duplicate feature names in config must be rejected."""
        with pytest.raises(ValidationError, match="Duplicate feature name"):
            RegimeModelConfig(feature_names=("return_1", "return_1"))

    def test_empty_string_feature_name_rejected_in_config(self) -> None:
        """Feature names that are empty strings must be rejected."""
        with pytest.raises(ValidationError, match="non-empty strings"):
            RegimeModelConfig(feature_names=("return_1", "   "))
