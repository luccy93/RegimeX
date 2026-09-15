"""
Unit Tests — Current Regime Context
====================================
Tests point-in-time extraction of the active regime, trailing run length,
comparison with historical baseline metrics, and point-in-time isolation.
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


def _make_assignments(
    regime_ids: list[int],
    features: dict[str, float] | None = None,
) -> list[RegimeAssignment]:
    """Helper to generate sequential RegimeAssignments."""
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    f_dict = features or {"volatility_20": 0.15}
    return [
        RegimeAssignment(
            timestamp=base + timedelta(hours=i),
            regime_id=r_id,
            regime_label=f"REGIME_{r_id}",
            features=f_dict,
        )
        for i, r_id in enumerate(regime_ids)
    ]


class TestCurrentRegimeContext:
    """Tests for get_current_context."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_current_context_multiple_regimes(self) -> None:
        """Trailing run correctly identified and contextualized."""
        # [0, 0, 0, 1, 1] -> active is regime 1 with trailing run of 2
        assignments = _make_assignments([0, 0, 0, 1, 1])
        ctx = self.service.get_current_context(assignments)

        assert ctx.current_regime_id == 1
        assert ctx.current_regime_label == "REGIME_1"
        assert ctx.observations_in_current_run == 2
        assert ctx.current_timestamp == assignments[-1].timestamp
        assert math.isclose(ctx.historical_frequency, 0.4, abs_tol=1e-9)
        assert ctx.historical_average_duration == 2.0
        assert ctx.historical_max_duration == 2
        assert ctx.historical_min_duration == 2
        assert ctx.historical_run_count == 1

    def test_current_regime_begins_at_final_observation(self) -> None:
        """When the latest observation marks a newly entered regime."""
        # [0, 0, 0, 0, 1] -> active is regime 1 with run length of 1
        assignments = _make_assignments([0, 0, 0, 0, 1])
        ctx = self.service.get_current_context(assignments)

        assert ctx.current_regime_id == 1
        assert ctx.observations_in_current_run == 1
        assert math.isclose(ctx.historical_frequency, 0.2, abs_tol=1e-9)

    def test_current_context_single_regime(self) -> None:
        """All observations in one regime."""
        assignments = _make_assignments([0, 0, 0])
        ctx = self.service.get_current_context(assignments)

        assert ctx.current_regime_id == 0
        assert ctx.observations_in_current_run == 3
        assert math.isclose(ctx.historical_frequency, 1.0, abs_tol=1e-9)
        assert ctx.historical_average_duration == 3.0

    def test_current_context_alternating_regimes(self) -> None:
        """Alternating regimes produce trailing run of 1."""
        assignments = _make_assignments([0, 1, 0, 1])
        ctx = self.service.get_current_context(assignments)

        assert ctx.current_regime_id == 1
        assert ctx.observations_in_current_run == 1
        assert math.isclose(ctx.historical_frequency, 0.5, abs_tol=1e-9)

    def test_empty_history_raises_insufficient_data_error(self) -> None:
        """Empty history raises typed InsufficientRegimeDataError."""
        with pytest.raises(InsufficientRegimeDataError):
            self.service.get_current_context([])

    def test_point_in_time_historical_invariance(self) -> None:
        """
        Regression: Context at time T must depend strictly on observations <= T.
        Adding observations after T does not affect the calculation for the slice up to T.
        """
        base_series = [0, 0, 1, 1, 1]
        extended_series = [0, 0, 1, 1, 1, 2, 2, 2, 0]

        assignments_base = _make_assignments(base_series)
        assignments_extended = _make_assignments(extended_series)

        # Context at T=4 (end of base_series)
        ctx_at_t = self.service.get_current_context(assignments_base)

        # Context evaluated on slice of extended series up to T=4
        ctx_from_slice = self.service.get_current_context(assignments_extended[:5])

        assert ctx_at_t.current_regime_id == ctx_from_slice.current_regime_id
        assert ctx_at_t.observations_in_current_run == ctx_from_slice.observations_in_current_run
        assert math.isclose(ctx_at_t.historical_frequency, ctx_from_slice.historical_frequency)
