"""
RegimeX Regime Detection — Anti-Leakage & Scaler Isolation Tests
===============================================================
Proves zero information leakage across time:
1. Scaler parameters depend strictly on in-sample training data.
2. Inference operations NEVER mutate or refit the scaler.
3. Future observation mutations or extensions do not alter earlier regime predictions.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


def _make_matrix(
    values: Sequence[tuple[float, ...]], base_time: datetime | None = None
) -> FeatureMatrix:
    if base_time is None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=i) for i in range(len(values)))
    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=("feat_x", "feat_y"),
        values=tuple(values),
    )


class TestLeakageAndScalerIsolation:
    def test_scaler_parameters_frozen_during_prediction(self) -> None:
        """
        Predicting on out-of-sample data (even with extreme outliers) must NOT
        alter the fitted scaler's mean_ or scale_ attributes.
        """
        train_data = [(float(i), float(i * 2)) for i in range(20)]
        train_matrix = _make_matrix(train_data)

        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train_matrix)

        scaler = detector._scaler
        assert scaler is not None
        mean_before = np.copy(scaler.mean_)
        scale_before = np.copy(scaler.scale_)

        # Wild extreme future out-of-sample observations
        future_data = [(1000.0, -5000.0), (9999.0, 8888.0)]
        future_matrix = _make_matrix(future_data, base_time=datetime(2026, 2, 1, 0, 0, tzinfo=UTC))

        # Run prediction on future data
        _ = detector.predict(future_matrix)
        _ = detector.predict_proba(future_matrix)

        # Scaler parameters must be completely unchanged
        assert np.array_equal(scaler.mean_, mean_before)
        assert np.array_equal(scaler.scale_, scale_before)

    def test_point_in_time_prefix_prediction_invariance(self) -> None:
        """
        For a fitted model, predicting on a sequence t_1..t_k produces the exact
        same classifications as the first k elements of predicting on t_1..t_k+n.
        Zero future information can leak backward across rows during inference.
        """
        # Train detector
        train_data = [
            (1.0, 0.1),
            (1.1, 0.12),
            (0.9, 0.08),
            (-1.0, 0.3),
            (-0.9, 0.28),
            (-1.1, 0.32),
        ]
        train_matrix = _make_matrix(train_data)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train_matrix)

        # Evaluation observations t_1..t_5
        eval_base = [(0.8, 0.09), (-0.8, 0.31), (1.05, 0.11), (-1.02, 0.29), (0.95, 0.10)]
        eval_matrix_k = _make_matrix(eval_base)
        preds_k = detector.predict(eval_matrix_k)

        # Appending future observations t_6..t_8
        future_extension = [(10.0, 1.0), (-5.0, 2.0), (0.0, 0.5)]
        eval_matrix_extended = _make_matrix(eval_base + future_extension)
        preds_extended = detector.predict(eval_matrix_extended)

        # The first 5 predictions must match preds_k identically!
        assert preds_extended[:5] == preds_k

    def test_altering_future_eval_sample_does_not_affect_past_predictions(self) -> None:
        """
        Mutating row t_2 in an evaluation batch does not alter the predicted
        regime for row t_0 or row t_1.
        """
        train_matrix = _make_matrix(
            [
                (2.0, 0.1),
                (2.1, 0.12),
                (-2.0, 0.5),
                (-2.1, 0.52),
            ]
        )
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train_matrix)

        batch_a = _make_matrix(
            [
                (1.9, 0.11),  # t_0
                (-1.9, 0.51),  # t_1
                (0.0, 0.2),  # t_2 original
            ]
        )
        preds_a = detector.predict(batch_a)

        batch_b = _make_matrix(
            [
                (1.9, 0.11),  # t_0 (identical)
                (-1.9, 0.51),  # t_1 (identical)
                (999.0, 999.0),  # t_2 (drastically changed)
            ]
        )
        preds_b = detector.predict(batch_b)

        # Predictions at t_0 and t_1 must remain identical
        assert preds_a[0] == preds_b[0]
        assert preds_a[1] == preds_b[1]
