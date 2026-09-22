"""
RegimeX Backtesting — Event-Driven Engine Integration Tests
===========================================================
Tests end-to-end simulation runs, strategy protocols, execution conventions, and determinism.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestConfig,
    ExecutionPriceConvention,
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine


def _make_bars(
    prices: list[float],
    symbol: str = "AAPL",
    start_dt: datetime | None = None,
) -> list[MarketEvent]:
    base_dt = start_dt or datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    events: list[MarketEvent] = []
    for i, p in enumerate(prices):
        events.append(
            MarketEvent(
                timestamp=base_dt + timedelta(days=i),
                symbol=symbol,
                open=p,
                high=p * 1.02,
                low=p * 0.98,
                close=p,
                volume=10_000.0,
            )
        )
    return events


class BuyAndHoldStrategy:
    def __init__(self, quantity: float = 100.0) -> None:
        self.quantity = quantity
        self.bought = False

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        if not self.bought:
            self.bought = True
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.BUY,
                    quantity=self.quantity,
                )
            ]
        return []


class MovingAverageCrossStrategy:
    def __init__(self, window: int = 3, quantity: float = 50.0) -> None:
        self.window = window
        self.quantity = quantity

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        history = context.get_history(event.symbol, count=self.window)
        if len(history) < self.window:
            return []

        ma = sum(bar.close for bar in history) / len(history)
        pos = context.current_positions.get(event.symbol)
        curr_qty = pos.quantity if pos else 0.0

        # If close > ma and flat -> BUY
        if event.close > ma and curr_qty == 0.0:
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.BUY,
                    quantity=self.quantity,
                )
            ]
        # If close < ma and holding -> SELL
        elif event.close < ma and curr_qty > 0.0:
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.SELL,
                    quantity=curr_qty,
                )
            ]
        return []


class TestEventDrivenBacktestEngine:
    def test_buy_and_hold_end_to_end(self) -> None:
        prices = [100.0, 105.0, 110.0, 120.0, 130.0]
        bars = _make_bars(prices, symbol="AAPL")

        config = BacktestConfig(
            initial_cash=50_000.0,
            commission_rate=0.001,
            slippage_rate=0.0,
            execution_convention=ExecutionPriceConvention.CURRENT_CLOSE,
        )
        engine = EventDrivenBacktestEngine(config=config)
        strategy = BuyAndHoldStrategy(quantity=100.0)

        result = engine.run(bars, strategy)

        # Total trades = 1 buy
        assert result.trade_count == 1
        assert len(result.fills) == 1
        fill = result.fills[0]
        assert fill.price == 100.0
        assert fill.quantity == 100.0
        assert fill.commission == 10.0  # 100 * 100 * 0.001

        # Final equity = cash (50000 - 10000 - 10) + 100 shares * 130.0 = 39990 + 13000 = 52990.0
        assert abs(result.final_equity - 52_990.0) < 1e-9
        assert len(result.equity_curve) == 5
        assert result.positions["AAPL"].quantity == 100.0

    def test_moving_average_cross_strategy(self) -> None:
        prices = [100.0, 102.0, 105.0, 108.0, 95.0, 90.0, 110.0, 115.0]
        bars = _make_bars(prices, symbol="AAPL")

        config = BacktestConfig(
            initial_cash=50_000.0,
            commission_rate=0.0,
            slippage_rate=0.0,
        )
        engine = EventDrivenBacktestEngine(config=config)
        strategy = MovingAverageCrossStrategy(window=3, quantity=50.0)

        result = engine.run(bars, strategy)

        assert result.trade_count >= 2  # multiple buys and sells
        assert len(result.equity_curve) == len(bars)
        assert result.start_timestamp == bars[0].timestamp
        assert result.end_timestamp == bars[-1].timestamp

    def test_next_open_execution_convention(self) -> None:
        # Day 0: 100 close, Day 1: 102 open / 105 close
        bars = [
            MarketEvent(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                symbol="XYZ",
                open=99.0,
                high=101.0,
                low=98.0,
                close=100.0,
                volume=1000.0,
            ),
            MarketEvent(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                symbol="XYZ",
                open=103.0,
                high=106.0,
                low=102.0,
                close=105.0,
                volume=1000.0,
            ),
        ]

        config = BacktestConfig(
            initial_cash=20_000.0,
            execution_convention=ExecutionPriceConvention.NEXT_OPEN,
        )
        engine = EventDrivenBacktestEngine(config=config)
        strategy = BuyAndHoldStrategy(quantity=10.0)

        result = engine.run(bars, strategy)

        # Order emitted on Day 0, executed on Day 1 at open (103.0)!
        assert len(result.fills) == 1
        fill = result.fills[0]
        assert fill.timestamp == datetime(2026, 1, 2, tzinfo=UTC)
        assert fill.price == 103.0

    def test_determinism_across_repeated_runs(self) -> None:
        prices = [50.0, 52.0, 55.0, 48.0, 53.0, 60.0]
        bars = _make_bars(prices, symbol="DET")

        config = BacktestConfig(initial_cash=100_000.0, commission_rate=0.001, slippage_rate=0.0005)
        engine1 = EventDrivenBacktestEngine(config=config)
        engine2 = EventDrivenBacktestEngine(config=config)

        res1 = engine1.run(bars, MovingAverageCrossStrategy(window=2, quantity=20.0))
        res2 = engine2.run(bars, MovingAverageCrossStrategy(window=2, quantity=20.0))

        assert res1.final_cash == res2.final_cash
        assert res1.final_equity == res2.final_equity
        assert res1.trade_count == res2.trade_count
        assert len(res1.fills) == len(res2.fills)
        for f1, f2 in zip(res1.fills, res2.fills, strict=True):
            assert f1.price == f2.price
            assert f1.quantity == f2.quantity
            assert f1.commission == f2.commission
            assert f1.slippage == f2.slippage

    def test_regime_aware_strategy(self) -> None:
        prices = [100.0, 110.0, 120.0, 130.0]
        bars = _make_bars(prices)
        regimes = [0, 1, 1, 0]

        class RegimeTrader:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                # Only buy in regime 1
                pos = context.current_positions.get(event.symbol)
                qty = pos.quantity if pos else 0.0
                if context.current_regime == 1 and qty == 0.0:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=10.0,
                        )
                    ]
                return []

        engine = EventDrivenBacktestEngine()
        result = engine.run(bars, RegimeTrader(), regimes=regimes)

        assert result.trade_count == 1
        # Bought on bar index 1 (timestamp day 1)
        assert result.fills[0].timestamp == bars[1].timestamp
