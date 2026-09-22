"""
RegimeX Backtesting — Anti-Lookahead Protection & Adversarial Strategy Tests
===========================================================================
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
    Position,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine
from pydantic import ValidationError


def _make_bars(
    prices: list[float],
    symbol: str = "SAFE",
    start_dt: datetime | None = None,
) -> list[MarketEvent]:
    base_dt = start_dt or datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
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


class AdversarialLookaheadStrategy:
    """
    Adversarial strategy attempting to exploit every potential vector of lookahead bias:
    1. Future timestamps in history
    2. Future regime states in regime history
    3. Mutating history tuple
    4. Mutating positions dict or object
    5. Mutating prices dict
    6. Mutating frozen event fields
    """

    def __init__(self) -> None:
        self.observed_timestamps: list[datetime] = []
        self.history_mutation_blocked = False
        self.event_mutation_blocked = False
        self.position_mutation_blocked = False

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        self.observed_timestamps.append(event.timestamp)

        # 1. Assert no future timestamp exists in history
        history = context.get_history(event.symbol)
        for past_bar in history:
            assert past_bar.timestamp <= event.timestamp, (
                f"History contains future timestamp: {past_bar.timestamp} > {event.timestamp}"
            )

        # 2. Assert no future regime states in regime history
        regime_history = context.get_regime_history()
        assert len(regime_history) == len(self.observed_timestamps)

        # 3. Assert current_timestamp equals event.timestamp
        assert context.current_timestamp == event.timestamp

        # 4. Attempt to mutate history tuple
        if history:
            try:
                tuple_obj: Any = history
                tuple_obj[0] = event
            except (TypeError, Exception):
                self.history_mutation_blocked = True

        # 5. Attempt to mutate frozen event
        try:
            event_any: Any = event
            event_any.close = 999999.0
        except (ValidationError, TypeError, Exception):
            self.event_mutation_blocked = True

        # 6. Attempt to mutate positions dictionary
        pos_dict = context.current_positions
        pos_dict["HACK"] = Position(symbol="HACK", quantity=1000.0)
        # Verify mutating the returned positions dict does NOT affect context
        assert "HACK" not in context.current_positions
        self.position_mutation_blocked = True

        # 7. Attempt to mutate prices dictionary
        prices_dict = context.current_prices
        prices_dict[event.symbol] = 0.0001
        assert context.current_prices[event.symbol] == event.close

        return []


class TestLookaheadProtection:
    def test_adversarial_strategy_cannot_breach_isolation(self) -> None:
        prices = [100.0, 105.0, 110.0, 115.0, 120.0]
        bars = _make_bars(prices)
        regimes = [0, 1, 1, 0, 2]

        strategy = AdversarialLookaheadStrategy()
        engine = EventDrivenBacktestEngine()
        engine.run(bars, strategy, regimes=regimes)

        assert len(strategy.observed_timestamps) == 5
        assert strategy.history_mutation_blocked is True
        assert strategy.event_mutation_blocked is True
        assert strategy.position_mutation_blocked is True

    def test_future_data_independence_extreme_crash_and_rally(self) -> None:
        """
        Verify that running a backtest on [t0..t3] yields exact same initial orders, fills,
        and equity snapshots as running on [t0..t5] with extreme future rally (+1000%)
        or crash (-90%).
        """
        base_prices = [100.0, 102.0, 101.0, 104.0]
        # Injected extreme future movements: crash to 10.0 (-90%) then rally to 1100.0 (+1000%)
        extended_prices = base_prices + [10.0, 1100.0]

        bars_base = _make_bars(base_prices, symbol="LEAK")
        bars_extended = _make_bars(extended_prices, symbol="LEAK")

        class StaticTrader:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                # Buy on day 0 (t=0), Sell on day 2 (t=2)
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
            assert s_base.unrealized_pnl == s_ext.unrealized_pnl
            assert s_base.fees == s_ext.fees

    def test_multi_symbol_chronological_isolation(self) -> None:
        """
        Ensure multi-symbol streams do not leak future bars across different symbols.
        """
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)

        bars = [
            MarketEvent(
                timestamp=t0, symbol="A", open=10.0, high=11.0, low=9.0, close=10.0, volume=100.0
            ),
            MarketEvent(
                timestamp=t0, symbol="B", open=20.0, high=21.0, low=19.0, close=20.0, volume=100.0
            ),
            MarketEvent(
                timestamp=t1, symbol="A", open=12.0, high=13.0, low=11.0, close=12.0, volume=100.0
            ),
            MarketEvent(
                timestamp=t1, symbol="B", open=22.0, high=23.0, low=21.0, close=22.0, volume=100.0
            ),
        ]

        class CrossSymbolChecker:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                if event.timestamp == t0:
                    # At t0, history of A and B can only contain t0 bars
                    hist_a = context.get_history("A")
                    hist_b = context.get_history("B")
                    for b in hist_a:
                        assert b.timestamp <= t0
                    for b in hist_b:
                        assert b.timestamp <= t0
                return []

        engine = EventDrivenBacktestEngine()
        res = engine.run(bars, CrossSymbolChecker())
        assert res.metadata["event_count"] == 4
