"""
Unit Tests — Regime Ranking
============================
Tests deterministic ranking of regime profiles by frequency, duration, and feature metrics,
including tie-breaking stability and rejection of unsupported metrics.
"""

from __future__ import annotations

import pytest
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.errors import (
    UnsupportedRankingMetricError,
)
from app.modules.regime_intelligence.domain.models import (
    FeatureStatistic,
    RegimeProfile,
)


def _make_profile(
    regime_id: int,
    frequency: float,
    avg_duration: float,
    run_count: int = 1,
    feature_mean: float = 0.0,
) -> RegimeProfile:
    """Helper to create a RegimeProfile with specific ranking attributes."""
    feat_stat = FeatureStatistic(
        feature_name="return_1",
        observation_count=10,
        mean=feature_mean,
        median=feature_mean,
        std=0.01,
        min=feature_mean - 0.01,
        max=feature_mean + 0.01,
    )
    return RegimeProfile(
        regime_id=regime_id,
        regime_label=f"REGIME_{regime_id}",
        observation_count=int(frequency * 100),
        frequency=frequency,
        percentage=frequency * 100.0,
        run_count=run_count,
        average_duration=avg_duration,
        median_duration=avg_duration,
        min_duration=int(avg_duration),
        max_duration=int(avg_duration),
        feature_statistics={"return_1": feat_stat},
    )


class TestRegimeRanking:
    """Tests for RegimeIntelligenceService.rank_regimes."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_rank_by_frequency_descending(self) -> None:
        """Profiles ranked by frequency descending (default)."""
        p0 = _make_profile(regime_id=0, frequency=0.2, avg_duration=5.0)
        p1 = _make_profile(regime_id=1, frequency=0.5, avg_duration=2.0)
        p2 = _make_profile(regime_id=2, frequency=0.3, avg_duration=8.0)

        ranked = self.service.rank_regimes([p0, p1, p2], metric="frequency", ascending=False)
        assert [p.regime_id for p in ranked] == [1, 2, 0]

    def test_rank_by_average_duration(self) -> None:
        """Profiles ranked by average duration descending."""
        p0 = _make_profile(regime_id=0, frequency=0.2, avg_duration=5.0)
        p1 = _make_profile(regime_id=1, frequency=0.5, avg_duration=2.0)
        p2 = _make_profile(regime_id=2, frequency=0.3, avg_duration=8.0)

        ranked = self.service.rank_regimes([p0, p1, p2], metric="average_duration", ascending=False)
        assert [p.regime_id for p in ranked] == [2, 0, 1]

    def test_rank_by_feature_mean(self) -> None:
        """Profiles ranked by feature mean."""
        p0 = _make_profile(regime_id=0, frequency=0.3, avg_duration=5.0, feature_mean=0.01)
        p1 = _make_profile(regime_id=1, frequency=0.4, avg_duration=2.0, feature_mean=0.05)
        p2 = _make_profile(regime_id=2, frequency=0.3, avg_duration=8.0, feature_mean=-0.02)

        ranked = self.service.rank_regimes(
            [p0, p1, p2], metric="feature_mean:return_1", ascending=False
        )
        assert [p.regime_id for p in ranked] == [1, 0, 2]

    def test_deterministic_tie_breaking(self) -> None:
        """Ties broken deterministically by regime_id ascending."""
        # Both p2 and p1 have identical frequency 0.4
        p2 = _make_profile(regime_id=2, frequency=0.4, avg_duration=4.0)
        p1 = _make_profile(regime_id=1, frequency=0.4, avg_duration=4.0)
        p0 = _make_profile(regime_id=0, frequency=0.2, avg_duration=2.0)

        # In descending order, p1 should come before p2 due to regime_id 1 < 2 tie-breaking
        ranked = self.service.rank_regimes([p2, p1, p0], metric="frequency", ascending=False)
        assert [p.regime_id for p in ranked] == [1, 2, 0]

    def test_unsupported_metric_raises_typed_error(self) -> None:
        """Unsupported metric raises UnsupportedRankingMetricError."""
        p0 = _make_profile(regime_id=0, frequency=0.5, avg_duration=5.0)
        with pytest.raises(UnsupportedRankingMetricError, match="Unsupported ranking metric"):
            self.service.rank_regimes([p0], metric="invalid_metric_name")

    def test_empty_profiles_ranking(self) -> None:
        """Ranking empty profiles list returns empty list."""
        assert self.service.rank_regimes([], metric="frequency") == []

    def test_exact_user_spec_tie_breaking(self) -> None:
        """
        Example from specification:
        REGIME_0 frequency = 0.4
        REGIME_1 frequency = 0.4
        REGIME_2 frequency = 0.2
        Tied regimes R0 and R1 are ordered by regime_id ascending (0 < 1).
        Expected order: REGIME_0, REGIME_1, REGIME_2
        """
        p0 = _make_profile(regime_id=0, frequency=0.4, avg_duration=4.0)
        p1 = _make_profile(regime_id=1, frequency=0.4, avg_duration=4.0)
        p2 = _make_profile(regime_id=2, frequency=0.2, avg_duration=2.0)

        # Shuffled input order
        ranked = self.service.rank_regimes([p1, p2, p0], metric="frequency", ascending=False)
        assert [p.regime_id for p in ranked] == [0, 1, 2]

    def test_exhaustive_metrics_ranking(self) -> None:
        """Verify all supported duration, count, and feature metric ranking keys."""
        # p0: count 10, min 2, max 8, median 5.0, runs 2, feat min 0.0, max 0.02, med 0.01, std 0.01
        p0 = _make_profile(
            regime_id=0, frequency=0.1, avg_duration=5.0, run_count=2, feature_mean=0.01
        )
        # p1: count 30, min 4, max 6, median 5.0, runs 6, feat min 0.04, max 0.06
        p1 = _make_profile(
            regime_id=1, frequency=0.3, avg_duration=5.0, run_count=6, feature_mean=0.05
        )
        # p2: count 60, min 1, max 10, median 5.0, runs 12, feat min -0.03, max -0.01
        p2 = _make_profile(
            regime_id=2, frequency=0.6, avg_duration=5.0, run_count=12, feature_mean=-0.02
        )

        profiles = [p0, p1, p2]

        # 1. observation_count descending -> p2 (60), p1 (30), p0 (10)
        ranked_cnt = self.service.rank_regimes(
            profiles, metric="observation_count", ascending=False
        )
        assert [p.regime_id for p in ranked_cnt] == [2, 1, 0]

        # 2. run_count descending -> p2 (12), p1 (6), p0 (2)
        ranked_runs = self.service.rank_regimes(profiles, metric="run_count", ascending=False)
        assert [p.regime_id for p in ranked_runs] == [2, 1, 0]

        # 3. Check dynamic feature metrics ranking
        ranked_f_med = self.service.rank_regimes(
            profiles, metric="feature_median:return_1", ascending=False
        )
        assert [p.regime_id for p in ranked_f_med] == [1, 0, 2]

        ranked_f_min = self.service.rank_regimes(
            profiles, metric="feature_min:return_1", ascending=False
        )
        assert [p.regime_id for p in ranked_f_min] == [1, 0, 2]

        ranked_f_max = self.service.rank_regimes(
            profiles, metric="feature_max:return_1", ascending=False
        )
        assert [p.regime_id for p in ranked_f_max] == [1, 0, 2]

        ranked_f_std = self.service.rank_regimes(
            profiles, metric="feature_std:return_1", ascending=False
        )
        # All have std=0.01, tie break regime_id ascending: 0, 1, 2
        assert [p.regime_id for p in ranked_f_std] == [0, 1, 2]
