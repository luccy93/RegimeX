"""
Unit Tests — Regime Duration Analytics
======================================
Tests run-length encoding, duration metrics (mean, median, min, max, count),
and trailing run identification across benchmark test datasets.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.errors import InsufficientRegimeDataError
from app.modules.regime_intelligence.domain.models import RegimeAssignment
from app.modules.regime_intelligence.infrastructure.analytics.duration import (
    DurationAnalyzerImpl,
)


def _make_assignments(regime_ids: list[int]) -> list[RegimeAssignment]:
    """Helper to generate sequential RegimeAssignments from a list of regime IDs."""
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    return [
        RegimeAssignment(
            timestamp=base + timedelta(hours=i),
            regime_id=r_id,
            regime_label=f"REGIME_{r_id}",
            features={},
        )
        for i, r_id in enumerate(regime_ids)
    ]


class TestDurationAnalytics:
    """Tests for run-length encoding and duration statistics."""

    def setup_method(self) -> None:
        self.analyzer = DurationAnalyzerImpl()
        self.service = RegimeIntelligenceService(duration_analyzer=self.analyzer)

    def test_dataset_a_duration_runs_and_summary(self) -> None:
        """
        Dataset A: R0 R0 R0 (3), R1 R1 (2), R0 (1), R2 R2 R2 R2 (4).

        Expected:
        - R0: runs = [3, 1] -> run_count = 2, average = 2.0, min = 1, max = 3, median = 2.0
        - R1: runs = [2]    -> run_count = 1, average = 2.0, min = 2, max = 2, median = 2.0
        - R2: runs = [4]    -> run_count = 1, average = 4.0, min = 4, max = 4, median = 4.0
        """
        regimes = [0, 0, 0, 1, 1, 0, 2, 2, 2, 2]
        runs = self.analyzer.compute_runs(regimes)

        assert runs[0] == [3, 1]
        assert runs[1] == [2]
        assert runs[2] == [4]

        # Verify via service profiles
        assignments = _make_assignments(regimes)
        profiles = self.service.build_profiles(assignments)

        p0 = profiles[0]
        assert p0.run_count == 2
        assert math.isclose(p0.average_duration, 2.0, abs_tol=1e-9)
        assert math.isclose(p0.median_duration, 2.0, abs_tol=1e-9)
        assert p0.min_duration == 1
        assert p0.max_duration == 3

        p1 = profiles[1]
        assert p1.run_count == 1
        assert math.isclose(p1.average_duration, 2.0, abs_tol=1e-9)
        assert math.isclose(p1.median_duration, 2.0, abs_tol=1e-9)
        assert p1.min_duration == 2
        assert p1.max_duration == 2

        p2 = profiles[2]
        assert p2.run_count == 1
        assert math.isclose(p2.average_duration, 4.0, abs_tol=1e-9)
        assert math.isclose(p2.median_duration, 4.0, abs_tol=1e-9)
        assert p2.min_duration == 4
        assert p2.max_duration == 4

    def test_dataset_b_single_regime_duration(self) -> None:
        """Dataset B: All observations in single regime produce single run."""
        regimes = [1, 1, 1, 1, 1, 1]
        runs = self.analyzer.compute_runs(regimes)

        assert runs == {1: [6]}

        assignments = _make_assignments(regimes)
        profiles = self.service.build_profiles(assignments)

        p1 = profiles[1]
        assert p1.run_count == 1
        assert p1.average_duration == 6.0
        assert p1.median_duration == 6.0
        assert p1.min_duration == 6
        assert p1.max_duration == 6

    def test_dataset_c_alternating_regimes_duration(self) -> None:
        """Dataset C: Alternating regimes produce runs of length 1."""
        regimes = [0, 1, 0, 1, 0]
        runs = self.analyzer.compute_runs(regimes)

        assert runs[0] == [1, 1, 1]
        assert runs[1] == [1, 1]

        assignments = _make_assignments(regimes)
        profiles = self.service.build_profiles(assignments)

        p0 = profiles[0]
        assert p0.run_count == 3
        assert p0.average_duration == 1.0
        assert p0.median_duration == 1.0
        assert p0.min_duration == 1
        assert p0.max_duration == 1

        p1 = profiles[1]
        assert p1.run_count == 2
        assert p1.average_duration == 1.0
        assert p1.median_duration == 1.0
        assert p1.min_duration == 1
        assert p1.max_duration == 1

    def test_dataset_d_single_observation_duration(self) -> None:
        """Dataset D: Single observation produces a single run of length 1."""
        runs = self.analyzer.compute_runs([2])
        assert runs == {2: [1]}

    def test_dataset_e_empty_duration(self) -> None:
        """Dataset E: Empty series returns empty dict."""
        runs = self.analyzer.compute_runs([])
        assert runs == {}

    def test_trailing_current_run_calculation(self) -> None:
        """Compute trailing run correctly across different endings."""
        # Trailing run of length 3 for regime 2
        series_1 = [0, 0, 1, 2, 2, 2]
        r_id, length = self.analyzer.compute_current_run(series_1)
        assert r_id == 2
        assert length == 3

        # Trailing run of length 1 for regime 0
        series_2 = [0, 0, 1, 1, 0]
        r_id, length = self.analyzer.compute_current_run(series_2)
        assert r_id == 0
        assert length == 1

    def test_empty_series_raises_insufficient_data_error(self) -> None:
        """Empty series raises InsufficientRegimeDataError on current run."""
        with pytest.raises(InsufficientRegimeDataError):
            self.analyzer.compute_current_run([])

    def test_duration_property_invariants(self) -> None:
        """Duration invariant: min <= median <= max and min <= avg <= max."""
        regimes = [0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0]
        assignments = _make_assignments(regimes)
        profiles = self.service.build_profiles(assignments)

        for p in profiles.values():
            assert p.min_duration <= p.median_duration <= p.max_duration
            assert p.min_duration <= p.average_duration <= p.max_duration
