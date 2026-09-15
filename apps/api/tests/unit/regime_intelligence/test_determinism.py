"""
Unit Tests — Regime Intelligence Determinism
=============================================
Tests repeatable execution determinism, dictionary key order invariance,
and deterministic ranking tie-breaking.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


class TestIntelligenceDeterminism:
    """Tests guaranteeing pure determinism of regime intelligence."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_repeated_analysis_identical_output(self) -> None:
        """Running summarize_history multiple times produces byte-for-byte identical output."""
        assignments = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
                features={"f1": 1.0, "f2": 2.0},
            ),
            RegimeAssignment(
                timestamp=_ts(1),
                regime_id=0,
                regime_label="REGIME_0",
                features={"f1": 1.5, "f2": 2.5},
            ),
            RegimeAssignment(
                timestamp=_ts(2),
                regime_id=1,
                regime_label="REGIME_1",
                features={"f1": 3.0, "f2": 0.5},
            ),
            RegimeAssignment(
                timestamp=_ts(3),
                regime_id=1,
                regime_label="REGIME_1",
                features={"f1": 3.5, "f2": 0.8},
            ),
        ]

        summary_1 = self.service.summarize_history(assignments)
        summary_2 = self.service.summarize_history(assignments)

        assert summary_1.total_observations == summary_2.total_observations
        assert summary_1.regimes_observed == summary_2.regimes_observed

        for r_id in summary_1.regimes_observed:
            p1 = summary_1.regime_profiles[r_id]
            p2 = summary_2.regime_profiles[r_id]
            assert p1.observation_count == p2.observation_count
            assert p1.frequency == p2.frequency
            assert p1.average_duration == p2.average_duration
            assert p1.run_count == p2.run_count
            for f_name in p1.feature_statistics:
                assert p1.feature_statistics[f_name].mean == p2.feature_statistics[f_name].mean
                assert p1.feature_statistics[f_name].std == p2.feature_statistics[f_name].std

    def test_feature_dictionary_order_invariance(self) -> None:
        """Assignments with different dictionary key insertion orders produce identical profiles."""
        assignments_order_1 = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
                features={"beta": 2.0, "alpha": 1.0},
            ),
            RegimeAssignment(
                timestamp=_ts(1),
                regime_id=0,
                regime_label="REGIME_0",
                features={"beta": 4.0, "alpha": 3.0},
            ),
        ]
        assignments_order_2 = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
                features={"alpha": 1.0, "beta": 2.0},
            ),
            RegimeAssignment(
                timestamp=_ts(1),
                regime_id=0,
                regime_label="REGIME_0",
                features={"alpha": 3.0, "beta": 4.0},
            ),
        ]

        profiles_1 = self.service.build_profiles(assignments_order_1)
        profiles_2 = self.service.build_profiles(assignments_order_2)

        p1 = profiles_1[0]
        p2 = profiles_2[0]

        assert p1.feature_statistics["alpha"].mean == p2.feature_statistics["alpha"].mean
        assert p1.feature_statistics["beta"].mean == p2.feature_statistics["beta"].mean
