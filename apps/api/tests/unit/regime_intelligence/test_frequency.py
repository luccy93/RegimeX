"""
Unit Tests — Regime Frequency Analytics
========================================
Tests deterministic empirical frequency calculation and mathematical invariants
across benchmark test datasets (Datasets A–E).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment


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


class TestRegimeFrequencyAnalytics:
    """Tests for frequency calculation and property invariants."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_dataset_a_frequency_manual_verification(self) -> None:
        """
        Dataset A: R0 R0 R0, R1 R1, R0, R2 R2 R2 R2 (total 10).

        Expected:
        - R0: 4 observations -> frequency 0.4, percentage 40.0%
        - R1: 2 observations -> frequency 0.2, percentage 20.0%
        - R2: 4 observations -> frequency 0.4, percentage 40.0%
        """
        regimes = [0, 0, 0, 1, 1, 0, 2, 2, 2, 2]
        assignments = _make_assignments(regimes)

        profiles = self.service.build_profiles(assignments)

        assert len(profiles) == 3
        p0 = profiles[0]
        p1 = profiles[1]
        p2 = profiles[2]

        assert p0.observation_count == 4
        assert math.isclose(p0.frequency, 0.4, abs_tol=1e-9)
        assert math.isclose(p0.percentage, 40.0, abs_tol=1e-9)

        assert p1.observation_count == 2
        assert math.isclose(p1.frequency, 0.2, abs_tol=1e-9)
        assert math.isclose(p1.percentage, 20.0, abs_tol=1e-9)

        assert p2.observation_count == 4
        assert math.isclose(p2.frequency, 0.4, abs_tol=1e-9)
        assert math.isclose(p2.percentage, 40.0, abs_tol=1e-9)

        # Invariant: frequencies sum to 1.0 within tolerance
        total_freq = sum(p.frequency for p in profiles.values())
        assert math.isclose(total_freq, 1.0, abs_tol=1e-6)

        # Invariant: sum of observation counts equals total
        total_obs = sum(p.observation_count for p in profiles.values())
        assert total_obs == 10

    def test_dataset_b_single_regime_frequency(self) -> None:
        """Dataset B: All observations belong to a single regime."""
        regimes = [0, 0, 0, 0, 0]
        assignments = _make_assignments(regimes)

        profiles = self.service.build_profiles(assignments)

        assert len(profiles) == 1
        p0 = profiles[0]
        assert p0.observation_count == 5
        assert math.isclose(p0.frequency, 1.0, abs_tol=1e-9)
        assert math.isclose(p0.percentage, 100.0, abs_tol=1e-9)

    def test_dataset_c_alternating_regimes_frequency(self) -> None:
        """Dataset C: Alternating regimes R0, R1, R0, R1, R0, R1."""
        regimes = [0, 1, 0, 1, 0, 1]
        assignments = _make_assignments(regimes)

        profiles = self.service.build_profiles(assignments)

        assert len(profiles) == 2
        assert math.isclose(profiles[0].frequency, 0.5, abs_tol=1e-9)
        assert math.isclose(profiles[1].frequency, 0.5, abs_tol=1e-9)
        assert profiles[0].observation_count == 3
        assert profiles[1].observation_count == 3

    def test_dataset_d_single_observation_frequency(self) -> None:
        """Dataset D: Single observation."""
        assignments = _make_assignments([2])

        profiles = self.service.build_profiles(assignments)

        assert len(profiles) == 1
        p2 = profiles[2]
        assert p2.observation_count == 1
        assert math.isclose(p2.frequency, 1.0, abs_tol=1e-9)

    def test_dataset_e_empty_input_frequency(self) -> None:
        """Dataset E: Empty input returns empty profiles."""
        assignments: list[RegimeAssignment] = []
        profiles = self.service.build_profiles(assignments)
        assert profiles == {}

    def test_frequency_mathematical_bounds(self) -> None:
        """Invariant: Every regime frequency must satisfy 0 <= frequency <= 1."""
        regimes = [0, 1, 1, 2, 0, 3, 1, 2, 2, 2, 0]
        assignments = _make_assignments(regimes)

        profiles = self.service.build_profiles(assignments)

        for p in profiles.values():
            assert 0.0 <= p.frequency <= 1.0
            assert 0.0 <= p.percentage <= 100.0

        total_freq = sum(p.frequency for p in profiles.values())
        assert math.isclose(total_freq, 1.0, abs_tol=1e-6)
