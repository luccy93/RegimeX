"""
RegimeX Backtesting — Comprehensive Input Validation Tests
==========================================================
Verifies strict domain rejection for timestamps, prices, quantities, symbols, and market data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.modules.backtesting.domain.errors import (
    InvalidMarketDataError,
    InvalidOrderError,
    TemporalOrderError,
)
from app.modules.backtesting.domain.models import (
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine
from pydantic import ValidationError


def _ts(delta: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=delta)


class DummyStrategy:
    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        return []


class TestInputValidation:
    def test_timezone_naive_market_event_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=datetime(2026, 1, 1, 10, 0, 0),  # naive
                symbol="VALID",
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0,
                volume=100.0,
            )

    def test_non_utc_timezone_market_event_rejected(self) -> None:
        ist = timezone(timedelta(hours=5, minutes=30))
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=datetime(2026, 1, 1, 10, 0, 0, tzinfo=ist),
                symbol="VALID",
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0,
                volume=100.0,
            )

    def test_empty_market_data_sequence_rejected(self) -> None:
        engine = EventDrivenBacktestEngine()
        with pytest.raises(InvalidMarketDataError):
            engine.run([], DummyStrategy())

    def test_duplicate_timestamps_for_same_symbol_rejected(self) -> None:
        engine = EventDrivenBacktestEngine()
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="DUP",
                open=10.0,
                high=11.0,
                low=9.0,
                close=10.0,
                volume=10.0,
            ),
            MarketEvent(
                timestamp=_ts(0),
                symbol="DUP",
                open=10.0,
                high=11.0,
                low=9.0,
                close=10.0,
                volume=10.0,
            ),
        ]
        with pytest.raises(TemporalOrderError, match="Duplicate or decreasing timestamp"):
            engine.run(bars, DummyStrategy())

    def test_non_positive_and_non_finite_prices_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="BAD",
                open=-10.0,
                high=10.0,
                low=-15.0,
                close=5.0,
                volume=10.0,
            )

        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(), symbol="BAD", open=0.0, high=10.0, low=0.0, close=5.0, volume=10.0
            )

        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="BAD",
                open=float("nan"),
                high=10.0,
                low=5.0,
                close=5.0,
                volume=10.0,
            )

        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="BAD",
                open=10.0,
                high=float("inf"),
                low=5.0,
                close=5.0,
                volume=10.0,
            )

    def test_order_quantity_validation(self) -> None:
        with pytest.raises(ValidationError):
            OrderRequest(timestamp=_ts(), symbol="TEST", side=OrderSide.BUY, quantity=0.0)

        with pytest.raises(ValidationError):
            OrderRequest(timestamp=_ts(), symbol="TEST", side=OrderSide.BUY, quantity=-5.0)

        with pytest.raises(ValidationError):
            OrderRequest(timestamp=_ts(), symbol="TEST", side=OrderSide.BUY, quantity=float("nan"))

        with pytest.raises(ValidationError):
            OrderRequest(timestamp=_ts(), symbol="TEST", side=OrderSide.BUY, quantity=float("inf"))

    def test_empty_or_invalid_symbol_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(), symbol="", open=10.0, high=11.0, low=9.0, close=10.0, volume=10.0
            )

        with pytest.raises(ValidationError):
            OrderRequest(timestamp=_ts(), symbol="", side=OrderSide.BUY, quantity=10.0)

    def test_strategy_emitting_unobserved_symbol_rejected(self) -> None:
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="AAPL",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            )
        ]

        class RogueTrader:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                return [
                    OrderRequest(
                        timestamp=event.timestamp,
                        symbol="UNKNOWN_SYM",
                        side=OrderSide.BUY,
                        quantity=10.0,
                    )
                ]

        engine = EventDrivenBacktestEngine()
        with pytest.raises(InvalidOrderError, match="has not been observed"):
            engine.run(bars, RogueTrader())
