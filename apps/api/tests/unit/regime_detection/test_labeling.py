"""
RegimeX Regime Detection — Cluster Canonicalization & Labeling Tests
===================================================================
Verifies deterministic cluster-to-regime labeling, canonical signature sorting,
and separation of distinct financial market clusters.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


def _make_two_cluster_dataset(
    seed: int = 42,
    shuffle: bool = False,
) -> FeatureMatrix:
    """
    Generate synthetic dataset with 2 clearly separated market states:
    - State A (Bull / Low Vol): return = +0.05 ± 0.005, vol = 0.10 ± 0.01
    - State B (Bear / High Vol): return = -0.05 ± 0.005, vol = 0.30 ± 0.01
    """
    rng = np.random.default_rng(seed)
    n_per_cluster = 30

    # Cluster A (Bull, low vol)
    ret_a = rng.normal(0.05, 0.005, n_per_cluster)
    vol_a = rng.normal(0.10, 0.01, n_per_cluster)

    # Cluster B (Bear, high vol)
    ret_b = rng.normal(-0.05, 0.005, n_per_cluster)
    vol_b = rng.normal(0.30, 0.01, n_per_cluster)

    all_ret = np.concatenate([ret_a, ret_b])
    all_vol = np.concatenate([vol_a, vol_b])
    indices = np.arange(len(all_ret))

    if shuffle:
        rng.shuffle(indices)
        all_ret = all_ret[indices]
        all_vol = all_vol[indices]

    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=int(i)) for i in range(len(all_ret)))
    values = tuple((float(r), float(v)) for r, v in zip(all_ret, all_vol, strict=True))

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=("return_1", "volatility_20"),
        values=values,
    )


class TestClusterCanonicalizationAndLabeling:
    def test_separates_distinct_regimes_with_100_percent_purity(self) -> None:
        """KMeans must cleanly separate the two distinct clusters."""
        matrix = _make_two_cluster_dataset(seed=123, shuffle=False)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        cluster_a_preds = preds[:30]
        cluster_b_preds = preds[30:]

        # All points in Cluster A must have the same regime ID
        assert len(set(cluster_a_preds)) == 1
        # All points in Cluster B must have the same regime ID
        assert len(set(cluster_b_preds)) == 1
        # The two regimes must be distinct
        assert cluster_a_preds[0] != cluster_b_preds[0]

    def test_canonical_regime_ordering_is_deterministic(self) -> None:
        """
        Signature rule sorts features by canonical feature means.
        Because return_1 for Bear is -0.05 < Bull (+0.05), Bear is deterministically
        mapped to canonical regime 0 (REGIME_0) and Bull to canonical regime 1 (REGIME_1).
        """
        matrix = _make_two_cluster_dataset(seed=42, shuffle=False)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix)

        profiles = detector.cluster_profiles
        assert len(profiles) == 2

        # REGIME_0 must be the Bear regime (lower signature / negative return)
        regime_0 = profiles[0]
        assert regime_0.canonical_regime_id == 0
        assert regime_0.canonical_regime_label == "REGIME_0"
        assert regime_0.feature_means["return_1"] < 0.0
        assert regime_0.feature_means["volatility_20"] > 0.20

        # REGIME_1 must be the Bull regime (higher return)
        regime_1 = profiles[1]
        assert regime_1.canonical_regime_id == 1
        assert regime_1.canonical_regime_label == "REGIME_1"
        assert regime_1.feature_means["return_1"] > 0.0
        assert regime_1.feature_means["volatility_20"] < 0.20

    def test_canonical_assignment_is_invariant_to_seed(self) -> None:
        """
        Different random seeds may alter raw scikit-learn cluster numbering,
        but canonical regime assignment must remain identical!
        """
        matrix = _make_two_cluster_dataset(seed=42, shuffle=False)

        detector_seed_1 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=1))
        detector_seed_1.fit(matrix)
        preds_seed_1 = detector_seed_1.predict(matrix)

        detector_seed_99 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=99))
        detector_seed_99.fit(matrix)
        preds_seed_99 = detector_seed_99.predict(matrix)

        # Canonical predictions must be identical regardless of internal seed
        assert preds_seed_1 == preds_seed_99
