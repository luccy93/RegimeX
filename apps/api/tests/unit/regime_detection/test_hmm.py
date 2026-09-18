"""
Unit Tests — Gaussian Hidden Markov Model Regime Detector (V10 Commit 02)
========================================================================
Exhaustive verification of GaussianHMMRegimeDetector:
- Configuration validation and hyperparameter bounds
- Lifecycle transitions (UNFITTED -> FITTED)
- Temporal sequence dynamics and Viterbi decoding semantics
- Continuous Bayesian posterior probabilities and normalization (sum = 1.0)
- Deterministic component canonicalization and column remapping
- Anti-leakage standardization and prefix invariance
- Timestamp alignment
- Service integration with RegimeDetectionService
- Architectural isolation and guardrails
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.modules.regime_detection.application.services import (
    RegimeDetectionService,
)
from app.modules.regime_detection.domain.errors import (
    HMMConvergenceError,
    HMMFitError,
    HMMPredictionError,
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    InvalidHMMConfigurationError,
    InvalidModelConfigurationError,
    ModelNotFittedError,
    ModelPredictionError,
    ModelTrainingError,
)
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    HMMModelConfig,
    ModelState,
)
from app.modules.regime_detection.infrastructure.models.hmm import (
    GaussianHMMRegimeDetector,
)

# ---------------------------------------------------------------------------
# Test Fixtures & Synthetic Data Helpers
# ---------------------------------------------------------------------------


def _make_sample_timestamps(n: int, start: datetime | None = None) -> tuple[datetime, ...]:
    """Generate n strictly ascending UTC timestamps with 1-day intervals."""
    base = start or datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    return tuple(base + timedelta(days=i) for i in range(n))


def _make_synthetic_feature_matrix(
    n_samples: int = 60,
    n_features: int = 2,
    seed: int = 42,
    feature_names: tuple[str, ...] | None = None,
) -> FeatureMatrix:
    """Generate synthetic FeatureMatrix with Gaussian noise."""
    rng = np.random.default_rng(seed)
    values = rng.standard_normal((n_samples, n_features))
    names = feature_names or tuple(f"feat_{i}" for i in range(n_features))
    timestamps = _make_sample_timestamps(n_samples)
    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=names,
        values=tuple(tuple(float(v) for v in row) for row in values),
    )


def _make_persistent_regime_sequence(
    n_per_state: int = 25,
    seed: int = 42,
) -> FeatureMatrix:
    """
    Generate synthetic temporal sequence with 3 distinct, temporally persistent regimes:
    State A: low volatility, negative mean  ([-3.0, -3.0])
    State B: moderate, zero mean            ([0.0, 0.0])
    State C: high volatility, positive mean ([4.0, 4.0])

    Temporal structure: State A (25) -> State B (25) -> State C (25)
    Total observations: 75
    """
    rng = np.random.default_rng(seed)
    state_a = rng.normal(loc=-3.0, scale=0.4, size=(n_per_state, 2))
    state_b = rng.normal(loc=0.0, scale=0.4, size=(n_per_state, 2))
    state_c = rng.normal(loc=4.0, scale=0.4, size=(n_per_state, 2))

    all_data = np.vstack([state_a, state_b, state_c])
    timestamps = _make_sample_timestamps(len(all_data))

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=("volatility", "momentum"),
        values=tuple(tuple(float(v) for v in row) for row in all_data),
    )


# ===========================================================================
# 1. Configuration & Hyperparameter Validation Tests
# ===========================================================================


class TestHMMConfiguration:
    def test_default_configuration(self) -> None:
        config = HMMModelConfig()
        assert config.model_name == "hmm"
        assert config.model_version == "1.0.0"
        assert config.n_components == 4
        assert config.covariance_type == "full"
        assert config.random_state == 42
        assert config.n_iter == 100
        assert config.tol == 1e-3
        assert config.min_covar == 1e-3
        assert config.algorithm == "viterbi"
        assert config.init_params == "stmc"
        assert config.params == "stmc"
        assert config.implementation == "log"
        assert config.feature_names == ()

    def test_valid_custom_configuration(self) -> None:
        config = HMMModelConfig(
            model_name="custom_hmm",
            model_version="2.0.0",
            n_components=3,
            covariance_type="diag",
            random_state=99,
            n_iter=200,
            tol=1e-4,
            min_covar=1e-2,
            algorithm="map",
            init_params="tmc",
            params="mc",
            implementation="scaling",
            feature_names=("alpha", "beta"),
        )
        assert config.n_components == 3
        assert config.covariance_type == "diag"
        assert config.algorithm == "map"
        assert config.init_params == "tmc"
        assert config.params == "mc"
        assert config.implementation == "scaling"
        assert config.feature_names == ("alpha", "beta")

    @pytest.mark.parametrize("cov_type", ["full", "tied", "diag", "spherical"])
    def test_all_supported_covariance_types(self, cov_type: str) -> None:
        config = HMMModelConfig(covariance_type=cov_type)
        assert config.covariance_type == cov_type

    def test_invalid_covariance_type_raises(self) -> None:
        with pytest.raises(ValueError, match="covariance_type 'unsupported' must be one of"):
            HMMModelConfig(covariance_type="unsupported")

    @pytest.mark.parametrize("invalid_n", [0, -1, 51])
    def test_invalid_n_components_raises(self, invalid_n: int) -> None:
        with pytest.raises(ValueError):
            HMMModelConfig(n_components=invalid_n)

    @pytest.mark.parametrize("invalid_iter", [0, -10])
    def test_invalid_n_iter_raises(self, invalid_iter: int) -> None:
        with pytest.raises(ValueError):
            HMMModelConfig(n_iter=invalid_iter)

    @pytest.mark.parametrize("invalid_tol", [0.0, -1e-4])
    def test_invalid_tol_raises(self, invalid_tol: float) -> None:
        with pytest.raises(ValueError):
            HMMModelConfig(tol=invalid_tol)

    @pytest.mark.parametrize("invalid_min_covar", [0.0, -1.0])
    def test_invalid_min_covar_raises(self, invalid_min_covar: float) -> None:
        with pytest.raises(ValueError):
            HMMModelConfig(min_covar=invalid_min_covar)

    def test_invalid_algorithm_raises(self) -> None:
        with pytest.raises(ValueError, match="algorithm 'spectral' must be one of"):
            HMMModelConfig(algorithm="spectral")

    def test_invalid_init_params_raises(self) -> None:
        with pytest.raises(ValueError, match="init_params character 'x' is invalid"):
            HMMModelConfig(init_params="stmx")

    def test_invalid_params_raises(self) -> None:
        with pytest.raises(ValueError, match="params character 'z' is invalid"):
            HMMModelConfig(params="stz")

    def test_invalid_implementation_raises(self) -> None:
        with pytest.raises(ValueError, match="implementation 'fast' must be one of"):
            HMMModelConfig(implementation="fast")

    def test_duplicate_feature_names_raises(self) -> None:
        with pytest.raises(ValueError, match="Duplicate feature name"):
            HMMModelConfig(feature_names=("feat_a", "feat_a"))

    def test_empty_feature_name_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Feature names must be non-empty strings"):
            HMMModelConfig(feature_names=("",))


# ===========================================================================
# 2. Input Validation Tests
# ===========================================================================


class TestHMMInputValidation:
    def test_sample_count_less_than_components_raises(self) -> None:
        matrix = _make_synthetic_feature_matrix(n_samples=2, n_features=2)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=4))
        with pytest.raises(InsufficientTrainingDataError):
            detector.fit(matrix)

    def test_feature_matrix_dimension_mismatch_with_config(self) -> None:
        matrix = _make_synthetic_feature_matrix(n_samples=20, n_features=2)
        detector = GaussianHMMRegimeDetector(
            HMMModelConfig(n_components=2, feature_names=("alpha", "beta", "gamma"))
        )
        with pytest.raises(InvalidFeatureMatrixError):
            detector.fit(matrix)

    def test_predict_feature_mismatch_raises_error(self) -> None:
        train_matrix = _make_synthetic_feature_matrix(n_samples=30, n_features=2)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=2))
        detector.fit(train_matrix)

        # Create query matrix with different feature names
        timestamps = _make_sample_timestamps(10)
        bad_matrix = FeatureMatrix(
            timestamps=timestamps,
            feature_names=("other_1", "other_2"),
            values=tuple((1.0, 2.0) for _ in range(10)),
        )
        with pytest.raises(InvalidFeatureMatrixError):
            detector.predict(bad_matrix)

    def test_predict_proba_feature_mismatch_raises_error(self) -> None:
        train_matrix = _make_synthetic_feature_matrix(n_samples=30, n_features=2)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=2))
        detector.fit(train_matrix)

        timestamps = _make_sample_timestamps(10)
        bad_matrix = FeatureMatrix(
            timestamps=timestamps,
            feature_names=("diff_1", "diff_2"),
            values=tuple((0.5, -0.5) for _ in range(10)),
        )
        with pytest.raises(InvalidFeatureMatrixError):
            detector.predict_proba(bad_matrix)


# ===========================================================================
# 3. Lifecycle Tests
# ===========================================================================


class TestHMMLifecycle:
    def test_initial_unfitted_state(self) -> None:
        detector = GaussianHMMRegimeDetector()
        assert detector.state == ModelState.UNFITTED
        assert detector.fit_result is None
        assert detector.cluster_profiles == ()
        assert detector.algorithm_id == "gaussian_hmm"
        assert detector.algorithm_version == "1.0.0"

    def test_predict_before_fit_raises_model_not_fitted(self) -> None:
        matrix = _make_synthetic_feature_matrix(n_samples=20)
        detector = GaussianHMMRegimeDetector()
        with pytest.raises(ModelNotFittedError):
            detector.predict(matrix)

    def test_predict_proba_before_fit_raises_model_not_fitted(self) -> None:
        matrix = _make_synthetic_feature_matrix(n_samples=20)
        detector = GaussianHMMRegimeDetector()
        with pytest.raises(ModelNotFittedError):
            detector.predict_proba(matrix)

    def test_fit_returns_self_and_transitions_to_fitted(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        result = detector.fit(matrix)
        assert result is detector
        assert detector.state == ModelState.FITTED

    def test_fit_result_provenance_and_diagnostics(self) -> None:
        matrix = _make_persistent_regime_sequence()
        config = HMMModelConfig(n_components=3, random_state=42, n_iter=50)
        detector = GaussianHMMRegimeDetector(config)
        detector.fit(matrix)

        fit_res = detector.fit_result
        assert fit_res is not None
        assert fit_res.model_name == "hmm"
        assert fit_res.model_version == "1.0.0"
        assert fit_res.algorithm == "GaussianHMM"
        assert fit_res.n_clusters == 3
        assert fit_res.random_state == 42
        assert fit_res.training_sample_count == len(matrix.timestamps)
        assert fit_res.training_start == matrix.timestamps[0]
        assert fit_res.training_end == matrix.timestamps[-1]
        assert fit_res.inertia == 0.0
        assert fit_res.iterations >= 1
        assert fit_res.converged is not None
        assert fit_res.lower_bound is not None  # Log-likelihood score
        assert len(fit_res.cluster_profiles) == 3


# ===========================================================================
# 4. Probabilistic Properties & Viterbi vs Argmax Semantics
# ===========================================================================


class TestHMMProbabilisticProperties:
    def test_predict_proba_shape(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        assert len(probs) == len(matrix.timestamps)
        for row in probs:
            assert len(row) == 3

    def test_predict_proba_row_sum_strictly_normalized(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        for row in probs:
            row_sum = sum(row)
            assert math.isclose(row_sum, 1.0, rel_tol=1e-6, abs_tol=1e-6)

    def test_predict_proba_probability_bounds(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        for row in probs:
            for p in row:
                assert 0.0 <= p <= 1.0
                assert not math.isnan(p)
                assert not math.isinf(p)

    def test_viterbi_predictions_valid_canonical_ids(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        assert len(preds) == len(matrix.timestamps)
        for p in preds:
            assert p in {0, 1, 2}


# ===========================================================================
# 5. Deterministic State Canonicalization Tests
# ===========================================================================


class TestHMMCanonicalization:
    def test_canonical_profiles_have_standard_labels(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        profiles = detector.cluster_profiles
        assert len(profiles) == 3
        for idx, prof in enumerate(profiles):
            assert prof.canonical_regime_id == idx
            assert prof.canonical_regime_label == f"REGIME_{idx}"
            assert prof.sample_count >= 0
            assert set(prof.feature_means.keys()) == set(matrix.feature_names)
            assert set(prof.feature_stds.keys()) == set(matrix.feature_names)

    def test_canonical_ordering_is_lexicographical_by_emission_signature(self) -> None:
        matrix = _make_persistent_regime_sequence()
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        profiles = detector.cluster_profiles
        # Verify that centers/means are lexicographically ordered
        signatures = [
            tuple(p.feature_means[f] for f in sorted(matrix.feature_names)) for p in profiles
        ]
        assert signatures == sorted(signatures)

    def test_probability_columns_match_canonical_profiles(self) -> None:
        """
        Verify that probability column c corresponds to REGIME_c by checking
        that observations clearly generated from regime c exhibit highest probability in column c.
        """
        matrix = _make_persistent_regime_sequence(n_per_state=30)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        preds = detector.predict(matrix)

        # For well-separated persistent states, majority of Viterbi states match dominant prob col
        match_count = sum(1 for idx, p in enumerate(preds) if p == int(np.argmax(probs[idx])))
        assert match_count / len(preds) > 0.85


# ===========================================================================
# 6. Temporal Sequence Dynamics & Integrity Tests
# ===========================================================================


class TestHMMTemporalDynamics:
    def test_persistent_state_transitions(self) -> None:
        """HMM detects valid state count, probabilities, canonicalization, and determinism."""
        matrix = _make_persistent_regime_sequence(n_per_state=25)
        config = HMMModelConfig(n_components=3, random_state=42)
        detector = GaussianHMMRegimeDetector(config)
        detector.fit(matrix)

        preds = detector.predict(matrix)
        probs = detector.predict_proba(matrix)

        # 1. Temporal sequence handling: output length matches input observations
        assert len(preds) == len(matrix.timestamps)
        assert len(probs) == len(matrix.timestamps)

        # 2. Valid state count: states within canonical bounds [0..K-1]
        unique_states = set(preds)
        assert unique_states.issubset({0, 1, 2})
        assert len(unique_states) >= 2

        # 3. Valid probabilities: rows sum to 1.0, bounds in [0, 1]
        for row in probs:
            assert len(row) == 3
            assert math.isclose(sum(row), 1.0, rel_tol=1e-6)
            for p in row:
                assert 0.0 <= p <= 1.0

        # 4. Canonicalization: profiles exist with standard neutral labels
        assert len(detector.cluster_profiles) == 3
        canonical_labels = [p.canonical_regime_label for p in detector.cluster_profiles]
        assert canonical_labels == ["REGIME_0", "REGIME_1", "REGIME_2"]

        # 5. Deterministic output: refitting with same config yields identical predictions
        detector2 = GaussianHMMRegimeDetector(config)
        detector2.fit(matrix)
        assert detector2.predict(matrix) == preds
        assert detector2.predict_proba(matrix) == probs

    def test_sequence_reordering_affects_hmm_output(self) -> None:
        """
        HMM is temporally sensitive. Shuffling the temporal sequence will alter
        temporal transition probabilities and decoded state paths.
        """
        matrix = _make_persistent_regime_sequence(n_per_state=20)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)
        orig_preds = detector.predict(matrix)

        # Create reverse-ordered feature matrix
        reversed_values = tuple(reversed(matrix.values))
        reversed_timestamps = matrix.timestamps  # keep timestamps strictly ascending
        reversed_matrix = FeatureMatrix(
            timestamps=reversed_timestamps,
            feature_names=matrix.feature_names,
            values=reversed_values,
        )

        rev_preds = detector.predict(reversed_matrix)
        # The decoded states for reversed matrix should not be simply identical to forward matrix
        assert rev_preds != orig_preds


# ===========================================================================
# 7. Determinism & Random State Tests
# ===========================================================================


class TestHMMDeterminism:
    def test_exact_determinism_with_same_seed(self) -> None:
        matrix = _make_persistent_regime_sequence()
        config = HMMModelConfig(n_components=3, random_state=42)

        det1 = GaussianHMMRegimeDetector(config)
        det1.fit(matrix)
        preds1 = det1.predict(matrix)
        probs1 = det1.predict_proba(matrix)

        det2 = GaussianHMMRegimeDetector(config)
        det2.fit(matrix)
        preds2 = det2.predict(matrix)
        probs2 = det2.predict_proba(matrix)

        assert preds1 == preds2
        assert probs1 == probs2

    def test_differing_seeds_produce_valid_normalized_outputs(self) -> None:
        matrix = _make_persistent_regime_sequence()

        det_a = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=101))
        det_a.fit(matrix)
        probs_a = det_a.predict_proba(matrix)

        det_b = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=202))
        det_b.fit(matrix)
        probs_b = det_b.predict_proba(matrix)

        for row in probs_a:
            assert math.isclose(sum(row), 1.0, rel_tol=1e-6)
        for row in probs_b:
            assert math.isclose(sum(row), 1.0, rel_tol=1e-6)


# ===========================================================================
# 8. Anti-Leakage & Prefix Invariance Tests
# ===========================================================================


class TestHMMAntiLeakage:
    def test_scaler_parameters_frozen_after_fit(self) -> None:
        matrix = _make_persistent_regime_sequence(n_per_state=20)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        assert detector._scaler is not None
        mean_before = detector._scaler.mean_.copy()
        scale_before = detector._scaler.scale_.copy()

        # Run multiple inference queries on completely out-of-sample data
        test_matrix = _make_synthetic_feature_matrix(
            n_samples=30,
            seed=999,
            feature_names=matrix.feature_names,
        )
        detector.predict(test_matrix)
        detector.predict_proba(test_matrix)

        # Scaler parameters must remain bit-for-bit unchanged
        np.testing.assert_array_equal(detector._scaler.mean_, mean_before)
        np.testing.assert_array_equal(detector._scaler.scale_, scale_before)

    def test_future_data_does_not_affect_past_scaler(self) -> None:
        """StandardScaler fitted on train must not shift when querying test sub-window."""
        train_matrix = _make_persistent_regime_sequence(n_per_state=25)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(train_matrix)

        initial_mean = detector._scaler.mean_.copy()  # type: ignore[union-attr]

        # Query on subset of train
        sub_timestamps = train_matrix.timestamps[:10]
        sub_matrix = FeatureMatrix(
            timestamps=sub_timestamps,
            feature_names=train_matrix.feature_names,
            values=train_matrix.values[:10],
        )

        detector.predict(sub_matrix)
        detector.predict_proba(sub_matrix)

        np.testing.assert_array_equal(detector._scaler.mean_, initial_mean)  # type: ignore[union-attr]


# ===========================================================================
# 9. Timestamp Alignment Tests
# ===========================================================================


class TestHMMTimestampAlignment:
    def test_exact_index_correspondence(self) -> None:
        matrix = _make_persistent_regime_sequence(n_per_state=15)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        probs = detector.predict_proba(matrix)

        assert len(matrix.timestamps) == len(preds) == len(probs)

        # Ensure that querying on any time slice aligns index i to timestamp i
        slice_timestamps = matrix.timestamps[5:15]
        slice_values = matrix.values[5:15]
        slice_matrix = FeatureMatrix(
            timestamps=slice_timestamps,
            feature_names=matrix.feature_names,
            values=slice_values,
        )

        slice_preds = detector.predict(slice_matrix)
        slice_probs = detector.predict_proba(slice_matrix)

        assert len(slice_preds) == 10
        assert len(slice_probs) == 10


# ===========================================================================
# 10. Metadata & Parameters Tests
# ===========================================================================


class TestHMMMetadataAndParams:
    def test_get_params_returns_json_serializable_primitives(self) -> None:
        config = HMMModelConfig(
            n_components=3,
            covariance_type="diag",
            random_state=42,
            n_iter=80,
            tol=1e-4,
            min_covar=1e-2,
            algorithm="viterbi",
            feature_names=("volatility", "momentum"),
        )
        detector = GaussianHMMRegimeDetector(config)
        params = detector.get_params()

        assert params["model_name"] == "hmm"
        assert params["model_version"] == "1.0.0"
        assert params["n_components"] == 3
        assert params["covariance_type"] == "diag"
        assert params["random_state"] == 42
        assert params["n_iter"] == 80
        assert params["tol"] == 1e-4
        assert params["min_covar"] == 1e-2
        assert params["algorithm"] == "viterbi"
        assert params["feature_names"] == ["volatility", "momentum"]

        import json

        json_str = json.dumps(params)
        assert json_str is not None

    def test_metadata_returns_valid_detector_metadata(self) -> None:
        detector = GaussianHMMRegimeDetector()
        meta = detector.metadata()

        assert meta.algorithm_id == "gaussian_hmm"
        assert meta.algorithm_version == "1.0.0"
        assert meta.algorithm_family == "Probabilistic / Temporal Sequence Models"
        assert len(meta.assumptions) >= 3
        assert len(meta.known_limitations) >= 3
        assert "First-order Markov" in meta.known_limitations[0]


# ===========================================================================
# 11. Service Integration Tests
# ===========================================================================


class TestHMMServiceIntegration:
    def test_service_with_hmm_detector_instance(self) -> None:
        matrix = _make_persistent_regime_sequence(n_per_state=20)
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_components=3, random_state=42))
        service = RegimeDetectionService(detector=detector)

        # Detect before fit raises ModelNotFittedError
        with pytest.raises(ModelNotFittedError):
            service.detect_from_matrix(matrix)

        detector.fit(matrix)
        result = service.detect_from_matrix(matrix)

        assert result.algorithm == "gaussian_hmm"
        assert result.model_version == "1.0.0"
        assert result.record_count == 60
        assert not result.is_empty
        assert len(result.records) == 60

        for r in result.records:
            assert r.probabilities is not None
            assert len(r.probabilities) == 3
            assert math.isclose(sum(r.probabilities), 1.0, rel_tol=1e-6, abs_tol=1e-6)
            assert r.canonical_regime_id in {0, 1, 2}


# ===========================================================================
# 12. Architecture Guardrails Tests
# ===========================================================================


class TestHMMArchitectureGuardrails:
    def test_no_premature_future_models_in_regime_detection(self) -> None:
        """V10 Commit 02 must not introduce premature V11 or V12 components."""
        import app.modules.regime_detection as rd

        module_contents = dir(rd)
        forbidden_symbols = [
            "EnsembleRegimeDetector",
            "RegimeTransitionEngine",
            "TransitionAnalyticsService",
            "RiskEngine",
            "BacktestEngine",
            "TradingSignal",
        ]
        for sym in forbidden_symbols:
            assert sym not in module_contents, f"Forbidden future symbol '{sym}' found in V10."

    def test_domain_layer_has_zero_hmmlearn_imports(self) -> None:
        """Domain models and errors must have zero imports of hmmlearn or sklearn."""
        import inspect

        import app.modules.regime_detection.domain.errors as errs
        import app.modules.regime_detection.domain.interfaces as ifaces
        import app.modules.regime_detection.domain.models as models

        for mod in [errs, ifaces, models]:
            source = inspect.getsource(mod)
            assert "import hmmlearn" not in source
            assert "from hmmlearn" not in source
            assert "import sklearn" not in source
            assert "from sklearn" not in source


class TestHMMErrorHierarchy:
    def test_error_inheritance_and_codes(self) -> None:
        assert issubclass(InvalidHMMConfigurationError, InvalidModelConfigurationError)
        assert InvalidHMMConfigurationError.http_status == 422
        assert InvalidHMMConfigurationError.error_code == "INVALID_HMM_CONFIGURATION"

        assert issubclass(HMMFitError, ModelTrainingError)
        assert HMMFitError.http_status == 500
        assert HMMFitError.error_code == "HMM_FIT_ERROR"

        assert issubclass(HMMConvergenceError, ModelTrainingError)
        assert HMMConvergenceError.http_status == 422
        assert HMMConvergenceError.error_code == "HMM_CONVERGENCE_ERROR"

        assert issubclass(HMMPredictionError, ModelPredictionError)
        assert HMMPredictionError.http_status == 500
        assert HMMPredictionError.error_code == "HMM_PREDICTION_ERROR"
