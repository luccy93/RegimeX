"""
RegimeX Regime Detection — KMeansRegimeDetector Unit Tests
=========================================================
Tests model lifecycle, fitting, prediction, probability heuristic,
and parameter/metadata disclosure.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.errors import (
    InvalidFeatureMatrixError,
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


def _make_synthetic_matrix(n_samples: int = 50, n_features: int = 2) -> FeatureMatrix:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=i) for i in range(n_samples))
    feature_names = tuple(f"feat_{j}" for j in range(n_features))

    # Synthetic separable data: half positive, half negative
    values = []
    for i in range(n_samples):
        row = []
        for _ in range(n_features):
            val = (1.0 if i < n_samples // 2 else -1.0) + 0.1 * (i % 5)
            row.append(val)
        values.append(tuple(row))

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=tuple(values),
    )


class TestKMeansRegimeDetector:
    def test_initial_state_unfitted(self) -> None:
        detector = KMeansRegimeDetector()
        assert detector.state == ModelState.UNFITTED
        assert detector.fit_result is None
        assert detector.algorithm_id == "kmeans_baseline"
        assert detector.algorithm_version == "1.0.0"

    def test_predict_before_fit_raises_typed_error(self) -> None:
        detector = KMeansRegimeDetector()
        matrix = _make_synthetic_matrix()
        with pytest.raises(ModelNotFittedError, match="has not been fitted"):
            detector.predict(matrix)

    def test_predict_proba_before_fit_raises_typed_error(self) -> None:
        detector = KMeansRegimeDetector()
        matrix = _make_synthetic_matrix()
        with pytest.raises(ModelNotFittedError, match="has not been fitted"):
            detector.predict_proba(matrix)

    def test_successful_fit_and_fit_result(self) -> None:
        matrix = _make_synthetic_matrix(n_samples=40)
        config = RegimeModelConfig(n_clusters=2, random_state=42)
        detector = KMeansRegimeDetector(config=config)

        res = detector.fit(matrix)
        assert res is detector
        assert detector.state == ModelState.FITTED

        fit_res = detector.fit_result
        assert fit_res is not None
        assert fit_res.algorithm == "KMeans"
        assert fit_res.n_clusters == 2
        assert fit_res.random_state == 42
        assert fit_res.training_sample_count == 40
        assert fit_res.inertia >= 0.0
        assert fit_res.iterations >= 1
        assert len(fit_res.cluster_profiles) == 2

    def test_predict_returns_valid_canonical_ids(self) -> None:
        matrix = _make_synthetic_matrix(n_samples=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        assert len(preds) == 30
        assert all(isinstance(p, int) for p in preds)
        assert all(0 <= p < 3 for p in preds)

    def test_predict_proba_row_sum_invariant(self) -> None:
        matrix = _make_synthetic_matrix(n_samples=25)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        assert len(probs) == 25

        for row in probs:
            assert len(row) == 3
            # All probabilities non-negative
            assert all(p >= 0.0 for p in row)
            # Row sum must equal 1.0 within 1e-6
            assert math.isclose(sum(row), 1.0, rel_tol=1e-6, abs_tol=1e-6)

    def test_predict_feature_mismatch_raises_error(self) -> None:
        matrix = _make_synthetic_matrix(n_samples=20, n_features=2)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2))
        detector.fit(matrix)

        # Create matrix with different feature names
        mismatched_matrix = FeatureMatrix(
            timestamps=matrix.timestamps,
            feature_names=("feat_different_1", "feat_different_2"),
            values=matrix.values,
        )
        with pytest.raises(InvalidFeatureMatrixError, match="Feature mismatch"):
            detector.predict(mismatched_matrix)

    def test_refitting_replaces_state(self) -> None:
        matrix_1 = _make_synthetic_matrix(n_samples=20)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix_1)
        res_1 = detector.fit_result
        assert res_1 is not None and res_1.training_sample_count == 20

        # Refit on 30 samples
        matrix_2 = _make_synthetic_matrix(n_samples=30)
        detector.fit(matrix_2)
        res_2 = detector.fit_result
        assert res_2 is not None and res_2.training_sample_count == 30

    def test_metadata_and_parameters_disclosures(self) -> None:
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=99))
        meta = detector.metadata()
        assert meta.algorithm_id == "kmeans_baseline"
        assert meta.algorithm_version == "1.0.0"
        assert len(meta.assumptions) >= 3
        assert len(meta.known_limitations) >= 3

        params = detector.get_params()
        assert params["n_clusters"] == 4
        assert params["random_state"] == 99
