"""
RegimeX Regime Detection — Determinism & Reproducibility Tests
=============================================================
Verifies bit-for-bit reproducibility across repeated runs and
deterministic handling of column ordering.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.models import FeatureRecord
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


def _make_deterministic_matrix() -> FeatureMatrix:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=i) for i in range(40))
    feature_names = ("momentum_10", "volatility_20", "return_5")

    values = []
    for i in range(40):
        m = 0.05 * math.sin(i * 0.3)
        v = 0.15 + 0.05 * math.cos(i * 0.2)
        r = 0.02 * math.sin(i * 0.5)
        values.append((m, v, r))

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=feature_names,
        values=tuple(values),
    )


class TestDeterminismAndReproducibility:
    def test_identical_runs_produce_identical_model_and_predictions(self) -> None:
        """Repeated fits on separate detector instances must be bit-for-bit identical."""
        matrix = _make_deterministic_matrix()
        config = RegimeModelConfig(n_clusters=3, random_state=42)

        det_1 = KMeansRegimeDetector(config=config)
        det_1.fit(matrix)
        preds_1 = det_1.predict(matrix)
        probs_1 = det_1.predict_proba(matrix)
        res_1 = det_1.fit_result
        assert res_1 is not None

        det_2 = KMeansRegimeDetector(config=config)
        det_2.fit(matrix)
        preds_2 = det_2.predict(matrix)
        probs_2 = det_2.predict_proba(matrix)
        res_2 = det_2.fit_result
        assert res_2 is not None

        assert preds_1 == preds_2
        assert probs_1 == probs_2
        assert math.isclose(res_1.inertia, res_2.inertia, rel_tol=1e-9)
        assert res_1.iterations == res_2.iterations

        for p1, p2 in zip(res_1.cluster_profiles, res_2.cluster_profiles, strict=True):
            assert p1.canonical_regime_id == p2.canonical_regime_id
            assert p1.sample_count == p2.sample_count
            assert p1.feature_means == p2.feature_means

    def test_feature_matrix_builder_canonical_column_normalization(self) -> None:
        """
        When feature_names is omitted, FeatureMatrixBuilder sorts features alphabetically.
        Even if the underlying FeatureSet lists features in different orders,
        the resulting FeatureMatrix column order is identical.
        """
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        records = (
            FeatureRecord(
                timestamp=base_time,
                values={"volatility_20": 0.12, "return_1": 0.01, "momentum_10": 0.03},
            ),
        )

        # FeatureSet with order [volatility_20, return_1, momentum_10]
        fset_1 = FeatureSet(
            symbol="TEST",
            interval=DataInterval.ONE_DAY,
            feature_names=("volatility_20", "return_1", "momentum_10"),
            records=records,
        )
        # FeatureSet with order [return_1, momentum_10, volatility_20]
        fset_2 = FeatureSet(
            symbol="TEST",
            interval=DataInterval.ONE_DAY,
            feature_names=("return_1", "momentum_10", "volatility_20"),
            records=records,
        )

        matrix_1 = FeatureMatrixBuilder.build(fset_1)
        matrix_2 = FeatureMatrixBuilder.build(fset_2)

        # Both normalize to alphabetical order
        assert matrix_1.feature_names == ("momentum_10", "return_1", "volatility_20")
        assert matrix_2.feature_names == ("momentum_10", "return_1", "volatility_20")
        assert matrix_1.values == matrix_2.values
