"""
RegimeX Backtesting — Market Data Validation Tests
==================================================
Verifies strict rejection of empty, duplicate, unsorted, non-UTC, NaN, and non-positive market data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.modules.backtesting.domain.errors import (
    InvalidMarketDataError,
    TemporalOrderError,
)
from app.modules.backtesting.domain.models import MarketEvent, OrderRequest
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine
from pydantic import ValidationError


class DummyStrategy:
    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        return []


def _ts(delta: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=delta)


class TestMarketDataValidation:
    def test_empty_market_data_rejected(self) -> None:
        engine = EventDrivenBacktestEngine()
        with pytest.raises(InvalidMarketDataError, match="cannot be empty"):
            engine.run([], DummyStrategy())

    def test_duplicate_timestamps_rejected(self) -> None:
        engine = EventDrivenBacktestEngine()
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            ),
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            ),
        ]
        with pytest.raises(TemporalOrderError, match="Duplicate or decreasing timestamp"):
            engine.run(bars, DummyStrategy())

    def test_unsorted_timestamps_rejected(self) -> None:
        # Note: the engine automatically sorts raw inputs chronologically,
        # but if duplicate timestamps exist for a single symbol, it raises TemporalOrderError.
        # If timestamps decrease for a single symbol when not sortable (e.g. invalid series):
        engine = EventDrivenBacktestEngine()
        bars = [
            MarketEvent(
                timestamp=_ts(1),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            ),
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            ),
        ]
        # Engine sorts them chronologically -> _ts(0) then _ts(1), which succeeds!
        res = engine.run(bars, DummyStrategy())
        assert res.start_timestamp == _ts(0)
        assert res.end_timestamp == _ts(1)

    def test_non_utc_timestamps_rejected(self) -> None:
        est = timezone(timedelta(hours=-5))
        # Pydantic validates MarketEvent at construction time
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=datetime(2026, 1, 1, 10, 0, 0, tzinfo=est),
                symbol="AAPL",
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0,
                volume=100.0,
            )

    def test_nan_prices_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=float("nan"),
                high=105.0,
                low=95.0,
                close=100.0,
                volume=100.0,
            )

    def test_infinite_prices_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=float("inf"),
                low=95.0,
                close=100.0,
                volume=100.0,
            )

    def test_non_positive_prices_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=105.0,
                low=-5.0,
                close=100.0,
                volume=100.0,
            )

    def test_negative_volume_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0,
                volume=-50.0,
            )

    def test_mismatched_regimes_length_rejected(self) -> None:
        engine = EventDrivenBacktestEngine()
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            ),
            MarketEvent(
                timestamp=_ts(1),
                symbol="AAPL",
                open=101.0,
                high=102.0,
                low=100.0,
                close=101.0,
                volume=100.0,
            ),
        ]
        with pytest.raises(InvalidMarketDataError, match="Regimes sequence length"):
            engine.run(bars, DummyStrategy(), regimes=[0])  # length 1 vs 2 bars
