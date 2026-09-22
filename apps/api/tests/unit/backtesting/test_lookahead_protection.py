"""
RegimeX Backtesting — Anti-Lookahead Protection & Timing Tests
==============================================================
Proves that strategies cannot access future observations, future regime states, or future portfolio
values, and that adding future observations does not contaminate historical execution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.backtesting.domain.models import (
    BacktestConfig,
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine


def _make_bars(prices: list[float], symbol: str = "SAFE") -> list[MarketEvent]:
    base_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    return [
        MarketEvent(
            timestamp=base_dt + timedelta(days=i),
            symbol=symbol,
            open=p,
            high=p * 1.01,
            low=p * 0.99,
            close=p,
            volume=1000.0,
        )
        for i, p in enumerate(prices)
    ]


class MaliciousLookaheadStrategy:
    """
    Attempts to read future timestamps, future bars, or mutate past data.
    """

    def __init__(self) -> None:
        self.observed_timestamps: list[datetime] = []
        self.highest_history_timestamp: datetime | None = None
        self.attempted_mutation_failed = False

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        self.observed_timestamps.append(event.timestamp)

        # 1. Attempt to see if history contains future timestamps
        history = context.get_history(event.symbol)
        for past_bar in history:
            assert past_bar.timestamp <= event.timestamp, "History contains future timestamp!"

        # 2. Verify current_timestamp matches event.timestamp
        assert context.current_timestamp == event.timestamp

        # 3. Attempt to mutate the returned history tuple or bar
        if history:
            try:
                # History is returned as an immutable tuple and MarketEvent is frozen
                tuple_obj: Any = history
                tuple_obj[0] = event
            except TypeError:
                self.attempted_mutation_failed = True

        return []


class TestLookaheadProtection:
    def test_malicious_strategy_cannot_access_future_data(self) -> None:
        prices = [100.0, 105.0, 110.0, 115.0, 120.0]
        bars = _make_bars(prices)

        strategy = MaliciousLookaheadStrategy()
        engine = EventDrivenBacktestEngine()
        engine.run(bars, strategy)

        # Proves every bar had only past bars in context
        assert len(strategy.observed_timestamps) == 5
        assert strategy.attempted_mutation_failed is True

    def test_future_observations_do_not_alter_past_results(self) -> None:
        """
        Verify that running a backtest on [t0..t3] yields exact same initial orders, fills,
        and equity snapshots as running on [t0..t5] with extreme future rally or crash.
        """
        base_prices = [100.0, 102.0, 101.0, 104.0]
        extended_prices = base_prices + [500.0, 1000.0]

        bars_base = _make_bars(base_prices, symbol="LEAK")
        bars_extended = _make_bars(extended_prices, symbol="LEAK")

        class StaticTrader:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                # Buy on day 1 (t=0), Sell on day 3 (t=2)
                if event.timestamp == bars_base[0].timestamp:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=10.0,
                        )
                    ]
                elif event.timestamp == bars_base[2].timestamp:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.SELL,
                            quantity=10.0,
                        )
                    ]
                return []

        config = BacktestConfig(initial_cash=20_000.0, commission_rate=0.001)
        res_base = EventDrivenBacktestEngine(config=config).run(bars_base, StaticTrader())
        res_extended = EventDrivenBacktestEngine(config=config).run(bars_extended, StaticTrader())

        # The 2 trades executed during [t0..t3] must be bit-for-bit identical
        assert len(res_base.fills) == 2
        assert len(res_extended.fills) == 2
        for f_base, f_ext in zip(res_base.fills, res_extended.fills, strict=True):
            assert f_base.price == f_ext.price
            assert f_base.timestamp == f_ext.timestamp
            assert f_base.commission == f_ext.commission
            assert f_base.quantity == f_ext.quantity

        # The first 4 snapshots of the equity curve must be identical
        for s_base, s_ext in zip(res_base.equity_curve, res_extended.equity_curve[:4], strict=True):
            assert s_base.timestamp == s_ext.timestamp
            assert s_base.cash == s_ext.cash
            assert s_base.equity == s_ext.equity
            assert s_base.realized_pnl == s_ext.realized_pnl

    def test_execution_timing_convention_no_same_bar_leakage(self) -> None:
        """
        Verify the execution timing convention:
        - In CURRENT_CLOSE mode, strategy generates decision from Bar t.
        - Execution occurs at Bar t close price.
        - Future bar t+1 prices are completely unknown at time of order creation.
        """
        bars = _make_bars([100.0, 150.0])

        class TimingChecker:
            def __init__(self) -> None:
                self.checked = False

            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                if event.timestamp == bars[0].timestamp:
                    # Strategy cannot see bar 1 price (150.0)
                    assert context.current_prices[event.symbol] == 100.0
                    assert len(context.get_history(event.symbol)) == 1
                    self.checked = True
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=5.0,
                        )
                    ]
                return []

        checker = TimingChecker()
        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=10_000.0))
        result = engine.run(bars, checker)

        assert checker.checked is True
        assert len(result.fills) == 1
        assert result.fills[0].price == 100.0  # Settled at Bar 0 close, not Bar 1
