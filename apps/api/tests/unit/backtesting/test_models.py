"""
RegimeX Backtesting — Domain Model Unit Tests
=============================================
Tests construction, validation rules, UTC enforcement, and invariants across backtesting models.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.modules.backtesting.domain.models import (
    BacktestConfig,
    EquitySnapshot,
    EventType,
    ExecutionPriceConvention,
    FillEvent,
    MarketEvent,
    OrderRequest,
    OrderSide,
    OrderType,
    Position,
    SignalEvent,
)
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    OHLCVRecord,
)
from pydantic import ValidationError


def _ts(delta_seconds: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(seconds=delta_seconds)


class TestMarketEvent:
    def test_valid_market_event_creation(self) -> None:
        event = MarketEvent(
            timestamp=_ts(),
            symbol="aapl",
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1_000_000.0,
        )
        assert event.symbol == "AAPL"
        assert event.event_type == EventType.MARKET
        assert event.close == 154.0

    def test_from_ohlcv_record(self) -> None:
        record = OHLCVRecord(
            symbol="msft",
            timestamp=_ts(),
            open=300.0,
            high=305.0,
            low=298.0,
            close=302.0,
            volume=500_000.0,
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.RAW,
            source_provider_id="test_provider",
        )
        event = MarketEvent.from_ohlcv(record)
        assert event.symbol == "MSFT"
        assert event.open == 300.0
        assert event.close == 302.0

    def test_rejects_high_less_than_low(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="AAPL",
                open=150.0,
                high=140.0,
                low=145.0,
                close=142.0,
                volume=100.0,
            )

    def test_rejects_high_less_than_close(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="AAPL",
                open=150.0,
                high=152.0,
                low=149.0,
                close=155.0,
                volume=100.0,
            )

    def test_rejects_naive_timestamp(self) -> None:
        naive = datetime(2026, 1, 1, 10, 0, 0)
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=naive,
                symbol="AAPL",
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=100.0,
            )

    def test_rejects_non_utc_timestamp(self) -> None:
        est = timezone(timedelta(hours=-5))
        non_utc = datetime(2026, 1, 1, 10, 0, 0, tzinfo=est)
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=non_utc,
                symbol="AAPL",
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=100.0,
            )

    def test_rejects_non_positive_price(self) -> None:
        with pytest.raises(ValidationError):
            MarketEvent(
                timestamp=_ts(),
                symbol="AAPL",
                open=0.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=100.0,
            )


class TestOrderAndFillModels:
    def test_valid_order_request(self) -> None:
        order = OrderRequest(
            timestamp=_ts(),
            symbol="googl",
            side=OrderSide.BUY,
            quantity=50.0,
        )
        assert order.symbol == "GOOGL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 50.0
        assert order.order_type == OrderType.MARKET
        assert len(order.order_id) > 0

    def test_order_rejects_non_positive_quantity(self) -> None:
        with pytest.raises(ValidationError):
            OrderRequest(
                timestamp=_ts(),
                symbol="GOOGL",
                side=OrderSide.BUY,
                quantity=0.0,
            )

    def test_valid_fill_event(self) -> None:
        fill = FillEvent(
            order_id="test_ord_1",
            timestamp=_ts(),
            symbol="googl",
            side=OrderSide.BUY,
            quantity=50.0,
            price=120.50,
            commission=6.025,
            slippage=0.25,
        )
        assert fill.symbol == "GOOGL"
        assert fill.price == 120.50
        assert fill.commission == 6.025

    def test_fill_rejects_negative_commission(self) -> None:
        with pytest.raises(ValidationError):
            FillEvent(
                order_id="test_ord_1",
                timestamp=_ts(),
                symbol="GOOGL",
                side=OrderSide.BUY,
                quantity=50.0,
                price=120.50,
                commission=-1.0,
            )


class TestSignalEvent:
    def test_valid_signal(self) -> None:
        sig = SignalEvent(
            timestamp=_ts(),
            symbol="btc-usd",
            direction=1,
            strength=0.8,
            target_weight=0.25,
        )
        assert sig.symbol == "BTC-USD"
        assert sig.direction == 1
        assert sig.target_weight == 0.25

    def test_signal_invalid_direction(self) -> None:
        with pytest.raises(ValidationError):
            SignalEvent(
                timestamp=_ts(),
                symbol="BTC-USD",
                direction=5,
            )


class TestPosition:
    def test_position_properties(self) -> None:
        pos = Position(
            symbol="AAPL",
            quantity=100.0,
            average_entry_price=150.0,
            market_price=160.0,
            realized_pnl=50.0,
        )
        assert pos.market_value == 16_000.0
        assert pos.unrealized_pnl == 1_000.0
        assert pos.realized_pnl == 50.0

    def test_zero_position_unrealized_pnl(self) -> None:
        pos = Position(symbol="AAPL", quantity=0.0, market_price=160.0)
        assert pos.market_value == 0.0
        assert pos.unrealized_pnl == 0.0


class TestEquitySnapshot:
    def test_valid_equity_snapshot(self) -> None:
        snapshot = EquitySnapshot(
            timestamp=_ts(),
            cash=80_000.0,
            market_value=25_000.0,
            equity=105_000.0,
            fees=15.0,
            realized_pnl=200.0,
            unrealized_pnl=4_800.0,
        )
        assert snapshot.equity == 105_000.0

    def test_invalid_equity_accounting_equation(self) -> None:
        # cash (80_000) + market_value (25_000) = 105_000 != 100_000
        with pytest.raises(ValidationError):
            EquitySnapshot(
                timestamp=_ts(),
                cash=80_000.0,
                market_value=25_000.0,
                equity=100_000.0,
            )


class TestBacktestConfig:
    def test_default_config(self) -> None:
        cfg = BacktestConfig()
        assert cfg.initial_cash == 100_000.0
        assert cfg.commission_rate == 0.0
        assert cfg.slippage_rate == 0.0
        assert cfg.execution_convention == ExecutionPriceConvention.CURRENT_CLOSE
        assert cfg.allow_short is False

    def test_invalid_config_values(self) -> None:
        with pytest.raises(ValidationError):
            BacktestConfig(initial_cash=0.0)
        with pytest.raises(ValidationError):
            BacktestConfig(commission_rate=-0.01)
        with pytest.raises(ValidationError):
            BacktestConfig(slippage_rate=-0.005)
