"""
Unit Tests — Regime Intelligence Input Validation
=================================================
Tests strict temporal integrity, rejection of duplicate timestamps,
rejection of out-of-order timestamps, and regime ID validation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.errors import (
    InvalidRegimeHistoryError,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


class TestInputValidation:
    """Tests for defensive validation in RegimeIntelligenceService."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_duplicate_timestamps_raise_typed_error(self) -> None:
        """Section 34: Duplicate timestamps must raise InvalidRegimeHistoryError."""
        assignments = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
            ),
            RegimeAssignment(
                timestamp=_ts(0),  # Duplicate!
                regime_id=1,
                regime_label="REGIME_1",
            ),
        ]
        with pytest.raises(InvalidRegimeHistoryError, match="Duplicate timestamp"):
            self.service.build_profiles(assignments)

    def test_decreasing_timestamps_raise_typed_error(self) -> None:
        """Section 33: Non-monotonic timestamps must raise InvalidRegimeHistoryError."""
        assignments = [
            RegimeAssignment(
                timestamp=_ts(2),
                regime_id=0,
                regime_label="REGIME_0",
            ),
            RegimeAssignment(
                timestamp=_ts(1),  # Decreasing!
                regime_id=1,
                regime_label="REGIME_1",
            ),
        ]
        with pytest.raises(InvalidRegimeHistoryError, match="strictly ascending"):
            self.service.build_profiles(assignments)

    def test_valid_strictly_ascending_timestamps_pass(self) -> None:
        """Strictly ascending timestamps validate cleanly."""
        assignments = [
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
            ),
            RegimeAssignment(
                timestamp=_ts(1),
                regime_id=1,
                regime_label="REGIME_1",
            ),
        ]
        profiles = self.service.build_profiles(assignments)
        assert len(profiles) == 2
