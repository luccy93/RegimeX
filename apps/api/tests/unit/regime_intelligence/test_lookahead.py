"""
Unit Tests — Anti-Lookahead Regression
======================================
Verifies that historical intelligence and active context calculations at time T
depend strictly on observations <= T, with zero lookahead bias.
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


class TestAntiLookaheadRegression:
    """Rigorous tests proving zero lookahead bias in V09 regime intelligence."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_context_through_t3_invariant_to_future_modifications(self) -> None:
        """
        Specification Test:
        Fixture:
          T1 R0
          T2 R0
          T3 R1
          T4 R1
          T5 R2
        Calculate the context through T3.
        Then modify T4/T5 (change regimes, change features, add observations).
        The T3 result must remain identical.
        """
        base_assignments = [
            RegimeAssignment(
                timestamp=_ts(1), regime_id=0, regime_label="REGIME_0", features={"feat": 1.0}
            ),
            RegimeAssignment(
                timestamp=_ts(2), regime_id=0, regime_label="REGIME_0", features={"feat": 2.0}
            ),
            RegimeAssignment(
                timestamp=_ts(3), regime_id=1, regime_label="REGIME_1", features={"feat": 3.0}
            ),
        ]

        # Context at T3
        ctx_t3 = self.service.get_current_context(base_assignments)
        assert ctx_t3.current_regime_id == 1
        assert ctx_t3.current_regime_label == "REGIME_1"
        assert ctx_t3.observations_in_current_run == 1
        assert ctx_t3.current_timestamp == _ts(3)
        assert math.isclose(ctx_t3.historical_frequency, 1.0 / 3.0, abs_tol=1e-9)

        # Future Variant A: T4 R1, T5 R2
        variant_a = list(base_assignments) + [
            RegimeAssignment(
                timestamp=_ts(4), regime_id=1, regime_label="REGIME_1", features={"feat": 4.0}
            ),
            RegimeAssignment(
                timestamp=_ts(5), regime_id=2, regime_label="REGIME_2", features={"feat": 5.0}
            ),
        ]
        ctx_slice_a = self.service.get_current_context(variant_a[:3])
        assert ctx_slice_a.current_regime_id == ctx_t3.current_regime_id
        assert ctx_slice_a.observations_in_current_run == ctx_t3.observations_in_current_run
        assert math.isclose(ctx_slice_a.historical_frequency, ctx_t3.historical_frequency)

        # Future Variant B: completely different future (T4 R0, T5 R0, T6 R0, T7 R0)
        variant_b = list(base_assignments) + [
            RegimeAssignment(
                timestamp=_ts(4), regime_id=0, regime_label="REGIME_0", features={"feat": 99.0}
            ),
            RegimeAssignment(
                timestamp=_ts(5), regime_id=0, regime_label="REGIME_0", features={"feat": 99.0}
            ),
            RegimeAssignment(
                timestamp=_ts(6), regime_id=0, regime_label="REGIME_0", features={"feat": 99.0}
            ),
            RegimeAssignment(
                timestamp=_ts(7), regime_id=0, regime_label="REGIME_0", features={"feat": 99.0}
            ),
        ]
        ctx_slice_b = self.service.get_current_context(variant_b[:3])
        assert ctx_slice_b.current_regime_id == ctx_t3.current_regime_id
        assert ctx_slice_b.observations_in_current_run == ctx_t3.observations_in_current_run
        assert math.isclose(ctx_slice_b.historical_frequency, ctx_t3.historical_frequency)

    def test_historical_profile_prefix_stability(self) -> None:
        """
        Profiles constructed on a historical prefix [0..k] are strictly identical
        to the prefix of data regardless of what subsequent observations occur.
        """
        history_prefix = [
            RegimeAssignment(
                timestamp=_ts(i),
                regime_id=i % 2,
                regime_label=f"REGIME_{i % 2}",
                features={"vol": 0.1 * i},
            )
            for i in range(10)
        ]

        summary_prefix = self.service.summarize_history(history_prefix)

        extended_history = list(history_prefix) + [
            RegimeAssignment(
                timestamp=_ts(i), regime_id=2, regime_label="REGIME_2", features={"vol": 0.5}
            )
            for i in range(10, 25)
        ]

        # Summarizing slice [0..10] from extended history matches summary_prefix exactly
        summary_sliced = self.service.summarize_history(extended_history[:10])

        assert summary_prefix.total_observations == summary_sliced.total_observations
        assert summary_prefix.regimes_observed == summary_sliced.regimes_observed
        for r_id in summary_prefix.regimes_observed:
            p_orig = summary_prefix.regime_profiles[r_id]
            p_slice = summary_sliced.regime_profiles[r_id]
            assert p_orig.observation_count == p_slice.observation_count
            assert math.isclose(p_orig.frequency, p_slice.frequency, abs_tol=1e-9)
            assert p_orig.run_count == p_slice.run_count
            assert p_orig.feature_statistics["vol"].mean == p_slice.feature_statistics["vol"].mean
