"""
RegimeX Portfolio Risk — Return Calculation Unit Tests
======================================================
Tests arithmetic and log return calculations, validations, and edge cases.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
    InvalidPriceSeriesError,
    NonFiniteValueError,
    TemporalOrderError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestArithmeticReturns:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_basic_arithmetic_returns(self) -> None:
        prices = [100.0, 110.0, 99.0]
        timestamps = [_ts(0), _ts(1), _ts(2)]
        series = self.engine.compute_arithmetic_returns(prices, timestamps, symbol="TEST")

        assert len(series) == 2
        assert abs(series[0] - 0.10) < 1e-12  # (110 - 100) / 100
        assert abs(series[1] - (-0.10)) < 1e-12  # (99 - 110) / 110
        assert series.timestamps == (_ts(1), _ts(2))
        assert series.symbol == "TEST"

    def test_default_synthetic_timestamps_when_none_provided(self) -> None:
        prices = [10.0, 12.0, 15.0]
        series = self.engine.compute_arithmetic_returns(prices)
        assert len(series) == 2
        assert all(ts.tzinfo == UTC for ts in series.timestamps)

    def test_single_price_raises_insufficient_data(self) -> None:
        with pytest.raises(InsufficientRiskDataError):
            self.engine.compute_arithmetic_returns([100.0])

    def test_empty_prices_raises_invalid_price_series(self) -> None:
        with pytest.raises(InvalidPriceSeriesError):
            self.engine.compute_arithmetic_returns([])

    def test_zero_or_negative_price_rejected(self) -> None:
        with pytest.raises(InvalidPriceSeriesError):
            self.engine.compute_arithmetic_returns([100.0, 0.0])
        with pytest.raises(InvalidPriceSeriesError):
            self.engine.compute_arithmetic_returns([100.0, -10.0])

    def test_non_finite_price_rejected(self) -> None:
        with pytest.raises(NonFiniteValueError):
            self.engine.compute_arithmetic_returns([100.0, float("nan")])
        with pytest.raises(NonFiniteValueError):
            self.engine.compute_arithmetic_returns([100.0, float("inf")])

    def test_mismatched_timestamps_length_rejected(self) -> None:
        prices = [100.0, 105.0]
        timestamps = [_ts(0)]
        with pytest.raises(TemporalOrderError):
            self.engine.compute_arithmetic_returns(prices, timestamps)

    def test_naive_timestamps_rejected(self) -> None:
        prices = [100.0, 105.0]
        timestamps = [datetime(2025, 1, 1), datetime(2025, 1, 2)]
        with pytest.raises(TemporalOrderError):
            self.engine.compute_arithmetic_returns(prices, timestamps)

    def test_unsorted_timestamps_rejected(self) -> None:
        prices = [100.0, 105.0]
        timestamps = [_ts(1), _ts(0)]
        with pytest.raises(TemporalOrderError):
            self.engine.compute_arithmetic_returns(prices, timestamps)


class TestLogReturns:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_basic_log_returns(self) -> None:
        prices = [100.0, 110.0, 121.0]
        timestamps = [_ts(0), _ts(1), _ts(2)]
        series = self.engine.compute_log_returns(prices, timestamps)

        assert len(series) == 2
        expected_0 = math.log(110.0 / 100.0)
        expected_1 = math.log(121.0 / 110.0)
        assert abs(series[0] - expected_0) < 1e-12
        assert abs(series[1] - expected_1) < 1e-12

    def test_log_returns_zero_or_negative_price_rejected(self) -> None:
        with pytest.raises(InvalidPriceSeriesError):
            self.engine.compute_log_returns([100.0, -1.0])
        with pytest.raises(InvalidPriceSeriesError):
            self.engine.compute_log_returns([100.0, 0.0])
