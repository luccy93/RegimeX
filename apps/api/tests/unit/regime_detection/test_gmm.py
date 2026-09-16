"""
RegimeX Regime Detection — Gaussian Mixture Model (GMM) Unit Tests
==================================================================
Comprehensive test suite for GaussianMixtureRegimeDetector covering:
1. Hyperparameter configuration and domain validation.
2. Input validation and typed exception handling.
3. Lifecycle state machine and provenance tracking.
4. Probabilistic output contracts (normalization, bounds, shape).
5. Hard regime prediction / posterior probability argmax consistency.
6. Deterministic component canonicalization and column remapping.
7. Algorithmic determinism and random seed control.
8. Anti-leakage preprocessing and lookahead immunity.
9. Serialization-safe parameters and metadata disclosure.
10. Synthetic multi-modal cluster separation benchmark.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.modules.regime_detection.domain.errors import (
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.models import (
    DetectorMetadata,
    FeatureMatrix,
    GMMModelConfig,
    ModelState,
)
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Synthetic Dataset Fixtures & Generators
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TIME + timedelta(days=i)


def _make_separable_three_cluster_matrix(
    n_per_cluster: int = 30,
    seed: int = 42,
) -> FeatureMatrix:
    """
    Synthetic dataset with three well-separated 2D clusters:
    - Cluster A: center (-4.0, -4.0)
    - Cluster B: center (0.0, 0.0)
    - Cluster C: center (4.0, 4.0)
    """
    rng = np.random.default_rng(seed)
    n_total = n_per_cluster * 3

    timestamps = tuple(_ts(i) for i in range(n_total))
    feature_names = ("feat_alpha", "feat_beta")

    data_a = rng.normal(loc=[-4.0, -4.0], scale=0.3, size=(n_per_cluster, 2))
    data_b = rng.normal(loc=[0.0, 0.0], scale=0.3, size=(n_per_cluster, 2))
    data_c = rng.normal(loc=[4.0, 4.0], scale=0.3, size=(n_per_cluster, 2))

    stacked = np.vstack([data_a, data_b, data_c])
    values = tuple(tuple(float(v) for v in row) for row in stacked)

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=values,
    )


def _make_simple_matrix(n_samples: int = 30, n_features: int = 2) -> FeatureMatrix:
    timestamps = tuple(_ts(i) for i in range(n_samples))
    feature_names = tuple(f"feature_{j}" for j in range(n_features))
    values = tuple(tuple(float(i + j * 0.5) for j in range(n_features)) for i in range(n_samples))
    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=values,
    )


# ===========================================================================
# 1. Configuration Tests
# ===========================================================================


class TestGMMConfiguration:
    def test_default_configuration(self) -> None:
        cfg = GMMModelConfig()
        assert cfg.model_name == "gmm"
        assert cfg.model_version == "1.0.0"
        assert cfg.n_components == 4
        assert cfg.covariance_type == "full"
        assert cfg.random_state == 42
        assert cfg.max_iter == 100
        assert cfg.tol == 1e-3
        assert cfg.reg_covar == 1e-6
        assert cfg.init_params == "kmeans"
        assert cfg.feature_names == ()

    def test_valid_custom_configuration(self) -> None:
        cfg = GMMModelConfig(
            n_components=3,
            covariance_type="diag",
            random_state=123,
            max_iter=200,
            tol=1e-4,
            reg_covar=1e-5,
            init_params="random",
            feature_names=("volatility", "momentum"),
        )
        assert cfg.n_components == 3
        assert cfg.covariance_type == "diag"
        assert cfg.random_state == 123
        assert cfg.feature_names == ("volatility", "momentum")

    @pytest.mark.parametrize("cov_type", ["full", "tied", "diag", "spherical"])
    def test_all_supported_covariance_types(self, cov_type: str) -> None:
        cfg = GMMModelConfig(covariance_type=cov_type)
        assert cfg.covariance_type == cov_type

    def test_invalid_covariance_type_raises(self) -> None:
        with pytest.raises(ValidationError, match="covariance_type"):
            GMMModelConfig(covariance_type="unsupported_cov")

    @pytest.mark.parametrize("invalid_n", [0, -1, 51])
    def test_invalid_n_components_raises(self, invalid_n: int) -> None:
        with pytest.raises(ValidationError):
            GMMModelConfig(n_components=invalid_n)

    def test_invalid_max_iter_raises(self) -> None:
        with pytest.raises(ValidationError):
            GMMModelConfig(max_iter=0)

    def test_invalid_tol_raises(self) -> None:
        with pytest.raises(ValidationError):
            GMMModelConfig(tol=0.0)

    def test_invalid_reg_covar_raises(self) -> None:
        with pytest.raises(ValidationError):
            GMMModelConfig(reg_covar=-1e-6)

    def test_invalid_init_params_raises(self) -> None:
        with pytest.raises(ValidationError, match="init_params"):
            GMMModelConfig(init_params="invalid_init")

    def test_duplicate_feature_names_raises(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate feature name"):
            GMMModelConfig(feature_names=("feat_a", "feat_a"))

    def test_empty_feature_name_string_raises(self) -> None:
        with pytest.raises(ValidationError, match="non-empty strings"):
            GMMModelConfig(feature_names=("",))


# ===========================================================================
# 2. Input Validation Tests
# ===========================================================================


class TestGMMInputValidation:
    def test_sample_count_less_than_components_raises(self) -> None:
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=4))
        matrix = _make_simple_matrix(n_samples=3, n_features=2)

        with pytest.raises(InsufficientTrainingDataError) as exc_info:
            detector.fit(matrix)

        err = exc_info.value
        assert err.required_samples == 4
        assert err.available_samples == 3
        assert err.requested_clusters == 4

    def test_feature_matrix_dimension_mismatch_with_config(self) -> None:
        cfg = GMMModelConfig(
            n_components=2,
            feature_names=("feat_a", "feat_b"),
        )
        detector = GaussianMixtureRegimeDetector(cfg)
        matrix = _make_simple_matrix(n_samples=20, n_features=2)  # has feature_0, feature_1

        with pytest.raises(InvalidFeatureMatrixError, match="do not match configured"):
            detector.fit(matrix)

    def test_predict_feature_mismatch_raises_error(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3))
        detector.fit(matrix)

        mismatched_matrix = FeatureMatrix(
            timestamps=matrix.timestamps[:5],
            feature_names=("feat_x", "feat_y"),
            values=matrix.values[:5],
        )
        with pytest.raises(InvalidFeatureMatrixError, match="Feature mismatch"):
            detector.predict(mismatched_matrix)

    def test_predict_proba_feature_mismatch_raises_error(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3))
        detector.fit(matrix)

        mismatched_matrix = FeatureMatrix(
            timestamps=matrix.timestamps[:5],
            feature_names=("wrong_1", "wrong_2"),
            values=matrix.values[:5],
        )
        with pytest.raises(InvalidFeatureMatrixError, match="Feature mismatch"):
            detector.predict_proba(mismatched_matrix)


# ===========================================================================
# 3. Model Lifecycle Tests
# ===========================================================================


class TestGMMLifecycle:
    def test_initial_unfitted_state(self) -> None:
        detector = GaussianMixtureRegimeDetector()
        assert detector.state == ModelState.UNFITTED
        assert detector.fit_result is None
        assert detector.cluster_profiles == ()
        assert detector.algorithm_id == "gaussian_mixture"
        assert detector.algorithm_version == "1.0.0"

    def test_predict_before_fit_raises_model_not_fitted(self) -> None:
        detector = GaussianMixtureRegimeDetector()
        matrix = _make_simple_matrix()
        with pytest.raises(ModelNotFittedError, match="has not been fitted"):
            detector.predict(matrix)

    def test_predict_proba_before_fit_raises_model_not_fitted(self) -> None:
        detector = GaussianMixtureRegimeDetector()
        matrix = _make_simple_matrix()
        with pytest.raises(ModelNotFittedError, match="has not been fitted"):
            detector.predict_proba(matrix)

    def test_fit_returns_self_and_transitions_to_fitted(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3))
        res = detector.fit(matrix)

        assert res is detector
        assert detector.state == ModelState.FITTED
        assert detector.fit_result is not None

    def test_fit_result_provenance_and_diagnostics(self) -> None:
        matrix = _make_separable_three_cluster_matrix(n_per_cluster=25)
        config = GMMModelConfig(n_components=3, random_state=42)
        detector = GaussianMixtureRegimeDetector(config)
        detector.fit(matrix)

        res = detector.fit_result
        assert res is not None
        assert res.algorithm == "GaussianMixture"
        assert res.n_clusters == 3
        assert res.random_state == 42
        assert res.feature_names == ("feat_alpha", "feat_beta")
        assert res.training_sample_count == 75
        assert res.training_start == matrix.timestamps[0]
        assert res.training_end == matrix.timestamps[-1]
        assert res.iterations >= 1
        assert res.lower_bound is not None
        assert isinstance(res.lower_bound, float)
        assert res.converged is True
        assert len(res.cluster_profiles) == 3


# ===========================================================================
# 4. Probabilistic Output Contracts
# ===========================================================================


class TestGMMProbabilisticProperties:
    @pytest.fixture
    def fitted_detector(self) -> tuple[GaussianMixtureRegimeDetector, FeatureMatrix]:
        matrix = _make_separable_three_cluster_matrix(n_per_cluster=20)
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)
        return detector, matrix

    def test_predict_proba_shape(
        self,
        fitted_detector: tuple[GaussianMixtureRegimeDetector, FeatureMatrix],
    ) -> None:
        detector, matrix = fitted_detector
        probs = detector.predict_proba(matrix)

        assert len(probs) == matrix.sample_count
        for row in probs:
            assert len(row) == 3

    def test_predict_proba_row_sum_strictly_normalized(
        self,
        fitted_detector: tuple[GaussianMixtureRegimeDetector, FeatureMatrix],
    ) -> None:
        detector, matrix = fitted_detector
        probs = detector.predict_proba(matrix)

        for row_idx, row in enumerate(probs):
            row_sum = sum(row)
            assert math.isclose(row_sum, 1.0, rel_tol=1e-6, abs_tol=1e-6), (
                f"Row {row_idx} probability sum {row_sum} != 1.0"
            )

    def test_predict_proba_probability_bounds(
        self,
        fitted_detector: tuple[GaussianMixtureRegimeDetector, FeatureMatrix],
    ) -> None:
        detector, matrix = fitted_detector
        probs = detector.predict_proba(matrix)

        for row in probs:
            for p in row:
                assert 0.0 <= p <= 1.0
                assert not math.isnan(p)
                assert not math.isinf(p)

    def test_predict_argmax_consistency(
        self,
        fitted_detector: tuple[GaussianMixtureRegimeDetector, FeatureMatrix],
    ) -> None:
        """Mandatory invariant: predict(X)[i] == argmax(predict_proba(X)[i])."""
        detector, matrix = fitted_detector
        preds = detector.predict(matrix)
        probs = detector.predict_proba(matrix)

        assert len(preds) == len(probs)
        for i, (pred, prob_row) in enumerate(zip(preds, probs, strict=True)):
            max_idx = int(np.argmax(prob_row))
            assert pred == max_idx, (
                f"Discrepancy at row {i}: predict={pred}, argmax(predict_proba)={max_idx}"
            )


# ===========================================================================
# 5. Canonicalization & Probability Remapping Tests
# ===========================================================================


class TestGMMCanonicalization:
    def test_canonical_profiles_have_standard_labels(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        profiles = detector.cluster_profiles
        assert len(profiles) == 3
        for i, prof in enumerate(profiles):
            assert prof.canonical_regime_id == i
            assert prof.canonical_regime_label == f"REGIME_{i}"
            assert prof.sample_count > 0

    def test_canonical_ordering_is_lexicographical_by_signature(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        profiles = detector.cluster_profiles
        # Check that signatures are strictly increasing
        signatures = [
            tuple(prof.feature_means[f] for f in sorted(matrix.feature_names)) for prof in profiles
        ]
        for i in range(1, len(signatures)):
            assert signatures[i] >= signatures[i - 1], (
                f"Signatures out of canonical order: {signatures[i - 1]} vs {signatures[i]}"
            )

    def test_probability_columns_match_canonical_profiles(self) -> None:
        """
        Cluster A is around (-4, -4), B at (0, 0), C at (4, 4).
        By lexicographical sorting, Cluster A will have the smallest mean vector -> REGIME_0.
        Cluster B -> REGIME_1.
        Cluster C -> REGIME_2.
        Therefore, test query point (-4.0, -4.0) must have highest probability at column 0.
        Test query point (4.0, 4.0) must have highest probability at column 2.
        """
        matrix = _make_separable_three_cluster_matrix(n_per_cluster=30, seed=42)
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix)

        query_matrix = FeatureMatrix(
            timestamps=(_ts(0), _ts(1), _ts(2)),
            feature_names=("feat_alpha", "feat_beta"),
            values=(
                (-4.0, -4.0),  # near cluster A
                (0.0, 0.0),  # near cluster B
                (4.0, 4.0),  # near cluster C
            ),
        )

        probs = detector.predict_proba(query_matrix)
        preds = detector.predict(query_matrix)

        # Row 0: near A -> column 0 has maximum probability
        assert np.argmax(probs[0]) == 0
        assert preds[0] == 0
        assert probs[0][0] > 0.90

        # Row 1: near B -> column 1 has maximum probability
        assert np.argmax(probs[1]) == 1
        assert preds[1] == 1
        assert probs[1][1] > 0.90

        # Row 2: near C -> column 2 has maximum probability
        assert np.argmax(probs[2]) == 2
        assert preds[2] == 2
        assert probs[2][2] > 0.90


# ===========================================================================
# 6. Determinism & Random State Tests
# ===========================================================================


class TestGMMDeterminism:
    def test_exact_determinism_with_same_seed(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        config = GMMModelConfig(n_components=3, random_state=42)

        det1 = GaussianMixtureRegimeDetector(config).fit(matrix)
        det2 = GaussianMixtureRegimeDetector(config).fit(matrix)

        preds1 = det1.predict(matrix)
        preds2 = det2.predict(matrix)
        assert preds1 == preds2

        probs1 = det1.predict_proba(matrix)
        probs2 = det2.predict_proba(matrix)
        for r1, r2 in zip(probs1, probs2, strict=True):
            for p1, p2 in zip(r1, r2, strict=True):
                assert math.isclose(p1, p2, rel_tol=1e-7, abs_tol=1e-7)

        # Profiles must match exactly
        for prof1, prof2 in zip(det1.cluster_profiles, det2.cluster_profiles, strict=True):
            assert prof1.canonical_regime_id == prof2.canonical_regime_id
            assert prof1.canonical_regime_label == prof2.canonical_regime_label
            assert prof1.sample_count == prof2.sample_count

    def test_different_seeds_produce_valid_normalized_outputs(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        det1 = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42)).fit(
            matrix
        )
        det2 = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=999)).fit(
            matrix
        )

        assert det1.get_params()["random_state"] == 42
        assert det2.get_params()["random_state"] == 999

        probs1 = det1.predict_proba(matrix)
        probs2 = det2.predict_proba(matrix)

        for probs in [probs1, probs2]:
            for row in probs:
                assert math.isclose(sum(row), 1.0, rel_tol=1e-6, abs_tol=1e-6)


# ===========================================================================
# 7. Anti-Leakage & Lookahead Prevention Tests
# ===========================================================================


class TestGMMAntiLeakage:
    def test_scaler_parameters_frozen_after_fit(self) -> None:
        matrix_train = _make_separable_three_cluster_matrix(n_per_cluster=20)
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix_train)

        # Inspect scaler parameters
        scaler = detector._scaler
        assert scaler is not None
        mean_before = np.copy(scaler.mean_)
        var_before = np.copy(scaler.var_)

        # Create extreme out-of-sample data
        matrix_extreme = FeatureMatrix(
            timestamps=(_ts(500), _ts(501)),
            feature_names=matrix_train.feature_names,
            values=((10000.0, 10000.0), (-10000.0, -10000.0)),
        )

        detector.predict(matrix_extreme)
        detector.predict_proba(matrix_extreme)

        # Scaler parameters must remain completely unmodified
        np.testing.assert_array_equal(scaler.mean_, mean_before)
        np.testing.assert_array_equal(scaler.var_, var_before)

    def test_future_data_does_not_affect_past_predictions(self) -> None:
        """
        Verify that predicting on prefix data [t0..tk] yields identical results
        regardless of whether future points [tk+1..tn] are appended or changed.
        """
        matrix_train = _make_separable_three_cluster_matrix(n_per_cluster=30, seed=42)
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        detector.fit(matrix_train)

        # Prefix matrix (first 20 rows)
        prefix_matrix = FeatureMatrix(
            timestamps=matrix_train.timestamps[:20],
            feature_names=matrix_train.feature_names,
            values=matrix_train.values[:20],
        )

        prefix_preds = detector.predict(prefix_matrix)
        prefix_probs = detector.predict_proba(prefix_matrix)

        # Full matrix prediction
        full_preds = detector.predict(matrix_train)
        full_probs = detector.predict_proba(matrix_train)

        assert full_preds[:20] == prefix_preds

        for p_prob, f_prob in zip(prefix_probs, full_probs[:20], strict=True):
            for p1, p2 in zip(p_prob, f_prob, strict=True):
                assert math.isclose(p1, p2, rel_tol=1e-7, abs_tol=1e-7)


# ===========================================================================
# 8. Serialization, Parameters & Metadata Tests
# ===========================================================================


class TestGMMMetadataAndParams:
    def test_get_params_returns_json_serializable_primitives(self) -> None:
        cfg = GMMModelConfig(
            n_components=3,
            covariance_type="tied",
            random_state=42,
            max_iter=150,
            tol=1e-4,
            reg_covar=1e-5,
            init_params="kmeans",
            feature_names=("feat_1", "feat_2"),
        )
        detector = GaussianMixtureRegimeDetector(cfg)
        params = detector.get_params()

        # Must serialize cleanly to JSON
        json_str = json.dumps(params)
        decoded = json.loads(json_str)

        assert decoded["n_components"] == 3
        assert decoded["covariance_type"] == "tied"
        assert decoded["max_iter"] == 150
        assert decoded["feature_names"] == ["feat_1", "feat_2"]

    def test_metadata_returns_valid_detector_metadata(self) -> None:
        matrix = _make_separable_three_cluster_matrix()
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3))
        detector.fit(matrix)

        meta = detector.metadata()
        assert isinstance(meta, DetectorMetadata)
        assert meta.algorithm_id == "gaussian_mixture"
        assert meta.algorithm_version == "1.0.0"
        assert meta.algorithm_family == "Probabilistic / Mixture Models"
        assert len(meta.assumptions) >= 1
        assert len(meta.known_limitations) >= 1

        # Must serialize to JSON
        json_meta = meta.model_dump_json()
        assert "gaussian_mixture" in json_meta
        assert "Probabilistic / Mixture Models" in json_meta


# ===========================================================================
# 9. Service Integration & Convergence Edge Cases
# ===========================================================================


class TestGMMServiceIntegration:
    def test_service_with_gmm_detector(self) -> None:
        from app.modules.regime_detection.application.services import (
            RegimeDetectionService,
        )

        matrix = _make_separable_three_cluster_matrix(n_per_cluster=20)
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_components=3, random_state=42))
        service = RegimeDetectionService(detector=detector)

        # Detect before fit raises ModelNotFittedError
        with pytest.raises(ModelNotFittedError):
            service.detect_from_matrix(matrix)

        # Fit detector
        detector.fit(matrix)
        result = service.detect_from_matrix(matrix)

        assert result.algorithm == "gaussian_mixture"
        assert result.model_version == "1.0.0"
        assert result.record_count == 60
        assert not result.is_empty
        assert len(result.records) == 60

        for r in result.records:
            assert r.probabilities is not None
            assert len(r.probabilities) == 3
            assert math.isclose(sum(r.probabilities), 1.0, rel_tol=1e-6, abs_tol=1e-6)
            assert r.canonical_regime_id == int(np.argmax(r.probabilities))


class TestGMMConvergenceEdgeCases:
    def test_max_iter_one_records_iteration_count(self) -> None:
        """When max_iter=1, model fits 1 iteration and preserves diagnostic status."""
        matrix = _make_separable_three_cluster_matrix()
        config = GMMModelConfig(n_components=3, max_iter=1, random_state=42)
        detector = GaussianMixtureRegimeDetector(config)
        detector.fit(matrix)

        fit_res = detector.fit_result
        assert fit_res is not None
        assert fit_res.iterations == 1
        # converged is a boolean flag (True or False)
        assert isinstance(fit_res.converged, bool)
        assert fit_res.lower_bound is not None
