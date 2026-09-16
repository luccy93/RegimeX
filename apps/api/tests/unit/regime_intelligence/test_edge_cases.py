"""
Unit Tests — Regime Intelligence Edge Cases & Invariants
=========================================================
Tests boundary conditions, extreme numerical values, long sequences,
and mathematical property invariants.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


class TestRegimeIntelligenceEdgeCases:
    """Comprehensive edge case and invariant tests."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_extremely_small_and_large_float_values(self) -> None:
        """Statistics handle extreme magnitudes without overflow or underflow precision bugs."""
        small_val = 1e-12
        large_val = 1e12

        assignments = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
                features={"small": small_val, "large": large_val},
            ),
            RegimeAssignment(
                timestamp=_ts(1),
                regime_id=0,
                regime_label="REGIME_0",
                features={"small": small_val * 2.0, "large": large_val * 2.0},
            ),
        ]

        summary = self.service.summarize_history(assignments)
        p0 = summary.regime_profiles[0]

        stat_small = p0.feature_statistics["small"]
        assert stat_small.mean is not None
        assert math.isclose(stat_small.mean, 1.5e-12, rel_tol=1e-6)

        stat_large = p0.feature_statistics["large"]
        assert stat_large.mean is not None
        assert math.isclose(stat_large.mean, 1.5e12, rel_tol=1e-6)

    def test_long_contiguous_regime_run(self) -> None:
        """A single regime persisting for 2,000 observations."""
        n_obs = 2000
        assignments = [
            RegimeAssignment(
                timestamp=_ts(i),
                regime_id=0,
                regime_label="REGIME_0",
                features={"constant": 42.0},
            )
            for i in range(n_obs)
        ]

        summary = self.service.summarize_history(assignments)
        assert summary.total_observations == n_obs
        assert len(summary.regime_profiles) == 1

        p0 = summary.regime_profiles[0]
        assert p0.run_count == 1
        assert p0.observation_count == n_obs
        assert p0.average_duration == float(n_obs)
        assert p0.min_duration == n_obs
        assert p0.max_duration == n_obs
        assert p0.feature_statistics["constant"].std == 0.0

        ctx = summary.current_regime
        assert ctx is not None
        assert ctx.observations_in_current_run == n_obs
        assert ctx.historical_average_duration == float(n_obs)

    def test_many_distinct_regimes(self) -> None:
        """10 distinct regimes in non-trivial pattern."""
        n_regimes = 10
        pattern = [i % n_regimes for i in range(100)]
        assignments = [
            RegimeAssignment(
                timestamp=_ts(i),
                regime_id=r,
                regime_label=f"REGIME_{r}",
                features={"idx": float(i)},
            )
            for i, r in enumerate(pattern)
        ]

        summary = self.service.summarize_history(assignments)
        assert len(summary.regimes_observed) == n_regimes
        assert summary.total_observations == 100

        # Frequency invariant: sum == 1.0 within tolerance
        total_freq = sum(p.frequency for p in summary.regime_profiles.values())
        assert math.isclose(total_freq, 1.0, abs_tol=1e-6)

        # Count invariant: sum == total observations
        total_cnt = sum(p.observation_count for p in summary.regime_profiles.values())
        assert total_cnt == 100

    def test_property_invariants_across_complex_sequence(self) -> None:
        """
        Invariants across irregular regimes and feature values:
        - min <= median <= max
        - min <= mean <= max
        - current_run >= 1
        - 0 <= frequency <= 1
        """
        regimes = [0, 0, 1, 2, 2, 2, 1, 0, 3, 3, 1, 1, 1, 2]
        assignments = [
            RegimeAssignment(
                timestamp=_ts(i),
                regime_id=r,
                regime_label=f"REGIME_{r}",
                features={"ret": float(i * 2 - 10) if i % 4 != 0 else None},
            )
            for i, r in enumerate(regimes)
        ]

        summary = self.service.summarize_history(assignments)

        for p in summary.regime_profiles.values():
            # Duration invariants
            assert p.min_duration <= p.median_duration <= p.max_duration
            assert p.min_duration <= p.average_duration <= p.max_duration
            assert 0.0 <= p.frequency <= 1.0

            # Feature statistics invariants
            stat = p.feature_statistics.get("ret")
            if stat and stat.observation_count > 0:
                assert stat.min is not None and stat.max is not None
                assert stat.min <= stat.max
                if stat.mean is not None:
                    assert stat.min <= stat.mean <= stat.max
                if stat.median is not None:
                    assert stat.min <= stat.median <= stat.max

        assert summary.current_regime is not None
        assert summary.current_regime.observations_in_current_run >= 1
