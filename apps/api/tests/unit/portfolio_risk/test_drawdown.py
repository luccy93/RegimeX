"""
RegimeX Portfolio Risk — Maximum Drawdown Unit Tests
====================================================
Tests peak-to-trough historical drawdown, recovery detection, and anti-lookahead.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.portfolio_risk.domain.errors import (
    InvalidReturnSeriesError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestDrawdown:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_monotonic_growth_has_zero_drawdown(self) -> None:
        prices = [100.0, 105.0, 110.0, 120.0]
        timestamps = [_ts(0), _ts(1), _ts(2), _ts(3)]
        dd = self.engine.compute_drawdown_from_prices(prices, timestamps)

        assert dd.max_drawdown == 0.0
        assert dd.drawdown_magnitude == 0.0
        assert dd.peak_value == 100.0
        assert dd.trough_value == 100.0
        assert dd.is_recovered is True

    def test_monotonic_decline_drawdown(self) -> None:
        prices = [100.0, 90.0, 80.0, 70.0]
        timestamps = [_ts(0), _ts(1), _ts(2), _ts(3)]
        dd = self.engine.compute_drawdown_from_prices(prices, timestamps)

        assert abs(dd.max_drawdown - (-0.30)) < 1e-12
        assert abs(dd.drawdown_magnitude - 0.30) < 1e-12
        assert dd.peak_value == 100.0
        assert dd.trough_value == 70.0
        assert dd.peak_timestamp == _ts(0)
        assert dd.trough_timestamp == _ts(3)
        assert dd.is_recovered is False
        assert dd.recovery_timestamp is None

    def test_single_drawdown_with_recovery(self) -> None:
        # Prices: 100 -> 120 (peak) -> 96 (trough, -20%) -> 120 (recovered)
        prices = [100.0, 120.0, 96.0, 125.0]
        timestamps = [_ts(0), _ts(1), _ts(2), _ts(3)]
        dd = self.engine.compute_drawdown_from_prices(prices, timestamps)

        assert abs(dd.max_drawdown - (-0.20)) < 1e-12
        assert abs(dd.drawdown_magnitude - 0.20) < 1e-12
        assert dd.peak_value == 120.0
        assert dd.trough_value == 96.0
        assert dd.peak_timestamp == _ts(1)
        assert dd.trough_timestamp == _ts(2)
        assert dd.is_recovered is True
        assert dd.recovery_timestamp == _ts(3)

    def test_drawdown_from_returns(self) -> None:
        # Returns: +0.20 (W=1.20), -0.20 (W=0.96 -> DD = (0.96-1.20)/1.20 = -0.20), +0.30 (W=1.248)
        rets = [0.20, -0.20, 0.30]
        timestamps = [_ts(1), _ts(2), _ts(3)]
        dd = self.engine.compute_drawdown_from_returns(rets, timestamps)

        assert abs(dd.max_drawdown - (-0.20)) < 1e-12
        assert abs(dd.drawdown_magnitude - 0.20) < 1e-12
        assert abs(dd.peak_value - 1.20) < 1e-12
        assert abs(dd.trough_value - 0.96) < 1e-12
        assert dd.peak_timestamp == _ts(1)
        assert dd.trough_timestamp == _ts(2)
        assert dd.is_recovered is True
        assert dd.recovery_timestamp == _ts(3)

    def test_return_below_minus_one_rejected(self) -> None:
        rets = [0.10, -1.05]
        with pytest.raises(InvalidReturnSeriesError):
            self.engine.compute_drawdown_from_returns(rets)

    def test_no_future_lookahead_in_running_peak(self) -> None:
        # Check that a giant future peak does not alter past running peak
        prices_early = [100.0, 80.0]  # DD = -20%
        # Even with 500 at t=2, running peak at t=1 is still 100
        prices_later = [100.0, 80.0, 500.0]

        dd_early = self.engine.compute_drawdown_from_prices(prices_early)
        dd_later = self.engine.compute_drawdown_from_prices(prices_later)

        # The maximum drawdown was 20% in both cases
        assert abs(dd_early.max_drawdown - (-0.20)) < 1e-12
        assert abs(dd_later.max_drawdown - (-0.20)) < 1e-12
        assert dd_later.is_recovered is True
