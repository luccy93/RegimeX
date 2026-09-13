"""
RegimeX Regime Detection — Insufficient Data Tests
=================================================
Verifies explicit error raising and boundary behavior when sample counts
are insufficient for model training.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.errors import (
    InsufficientTrainingDataError,
)
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


def _make_matrix_with_n_samples(n: int) -> FeatureMatrix:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=i) for i in range(n))
    values = tuple((float(i), float(i * 2)) for i in range(n))
    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=("feat_1", "feat_2"),
        values=values,
    )


class TestInsufficientTrainingData:
    def test_zero_samples_raises_insufficient_training_data(self) -> None:
        matrix = _make_matrix_with_n_samples(0)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3))
        with pytest.raises(InsufficientTrainingDataError) as exc_info:
            detector.fit(matrix)

        err = exc_info.value
        assert err.available_samples == 0
        assert err.required_samples == 3
        assert err.requested_clusters == 3

    def test_single_sample_raises_insufficient_training_data(self) -> None:
        matrix = _make_matrix_with_n_samples(1)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2))
        with pytest.raises(InsufficientTrainingDataError) as exc_info:
            detector.fit(matrix)

        err = exc_info.value
        assert err.available_samples == 1
        assert err.required_samples == 2

    def test_samples_less_than_n_clusters_raises_error(self) -> None:
        # 3 samples with n_clusters = 4
        matrix = _make_matrix_with_n_samples(3)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4))
        with pytest.raises(InsufficientTrainingDataError) as exc_info:
            detector.fit(matrix)

        err = exc_info.value
        assert err.available_samples == 3
        assert err.required_samples == 4
        assert err.requested_clusters == 4

    def test_samples_equal_to_n_clusters_fits_successfully(self) -> None:
        # Exactly 3 samples with n_clusters = 3
        matrix = _make_matrix_with_n_samples(3)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        assert detector.fit_result.training_sample_count == 3
        assert len(detector.fit_result.cluster_profiles) == 3
