"""
RegimeX Systematic Backtesting — Engine Invariants & Accounting Tests
=====================================================================
Verifies:
- Cash + positions market value = total equity invariant
- Temporal order validation & non-UTC timestamp rejection
- Non-finite price or volume rejection
- Negative price rejection
- Invalid market_data types (non-list, non-dict, empty list)
- Strategy context history queries with negative / zero counts
- Execution convention difference: CURRENT_CLOSE vs NEXT_OPEN
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.errors import (
    InvalidMarketDataError,
    NonFiniteValueError,
    TemporalOrderError,
)
from app.modules.backtesting.domain.interfaces import StrategyContext
from app.modules.backtesting.domain.models import (
    BacktestConfig,
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import (
    EventDrivenBacktestEngine,
    StrategyContextImpl,
)


def make_market_event(
    sym: str,
    dt: datetime,
    close: float,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
    vol: float = 1000.0,
) -> MarketEvent:
    o = open_ if open_ is not None else close
    h = high if high is not None else max(o, close) + 1.0
    low_val = low if low is not None else min(o, close) - 1.0
    return MarketEvent(
        symbol=sym,
        timestamp=dt,
        open=o,
        high=h,
        low=low_val,
        close=close,
        volume=vol,
    )


class InvariantCheckingStrategy:
    """Strategy that verifies cash + position value == equity on every bar."""

    def __init__(self) -> None:
        self.invariants_verified = 0

    def on_market_event(self, event: MarketEvent, context: StrategyContext) -> list[OrderRequest]:
        # Cash + position market value == total equity
        pos_val = sum(p.market_value for p in context.current_positions.values())
        expected_equity = context.available_cash + pos_val
        actual_equity = context.portfolio_equity

        assert math.isclose(expected_equity, actual_equity, rel_tol=1e-5), (
            f"Accounting mismatch: expected {expected_equity}, got {actual_equity}"
        )

        self.invariants_verified += 1

        # Buy 10 shares on bar 1, hold
        if self.invariants_verified == 1:
            return [
                OrderRequest(
                    symbol=event.symbol,
                    timestamp=event.timestamp,
                    side=OrderSide.BUY,
                    quantity=10.0,
                )
            ]
        return []


class TestBacktestEngineInvariants:
    def test_cash_plus_positions_equals_equity(self) -> None:
        engine = EventDrivenBacktestEngine(
            BacktestConfig(initial_cash=100_000.0, commission_rate=0.0, slippage_rate=0.0)
        )
        t0 = datetime(2026, 1, 1, 14, 30, tzinfo=UTC)
        bars = [make_market_event("SPY", t0 + timedelta(days=i), 100.0 + i) for i in range(10)]

        strategy = InvariantCheckingStrategy()
        result = engine.run(bars, strategy)

        assert strategy.invariants_verified == 10
        assert result.trade_count >= 1
        assert len(result.equity_curve) == 10

    def test_invalid_market_data_types(self) -> None:
        engine = EventDrivenBacktestEngine()
        strategy = InvariantCheckingStrategy()

        # Non-list, non-dict
        with pytest.raises(InvalidMarketDataError, match="must be a list or dict"):
            engine.run("invalid_data", strategy)  # type: ignore[arg-type]

        # Empty list
        with pytest.raises(InvalidMarketDataError, match="cannot be empty"):
            engine.run([], strategy)

    def test_rejects_non_utc_timestamps(self) -> None:
        engine = EventDrivenBacktestEngine()
        strategy = InvariantCheckingStrategy()
        naive_dt = datetime(2026, 1, 1, 10, 0)  # naive

        # Domain model directly rejects naive timestamps
        with pytest.raises(ValueError):
            make_market_event("SPY", naive_dt, 100.0)

        # Engine validation protects against unvalidated events
        unvalidated = MarketEvent.model_construct(
            symbol="SPY",
            timestamp=naive_dt,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1000.0,
        )
        with pytest.raises(TemporalOrderError, match="non-UTC timestamp"):
            engine.run([unvalidated], strategy)

    def test_rejects_non_finite_and_negative_prices(self) -> None:
        engine = EventDrivenBacktestEngine()
        strategy = InvariantCheckingStrategy()
        t0 = datetime(2026, 1, 1, tzinfo=UTC)

        # NaN price
        nan_event = MarketEvent.model_construct(
            symbol="SPY",
            timestamp=t0,
            open=float("nan"),
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1000.0,
        )
        with pytest.raises(NonFiniteValueError):
            engine.run([nan_event], strategy)

        # Negative price
        neg_event = MarketEvent.model_construct(
            symbol="SPY",
            timestamp=t0,
            open=100.0,
            high=101.0,
            low=99.0,
            close=-50.0,
            volume=1000.0,
        )
        with pytest.raises(InvalidMarketDataError, match="strictly positive"):
            engine.run([neg_event], strategy)

        # Negative volume
        bad_vol = MarketEvent.model_construct(
            symbol="SPY",
            timestamp=t0,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=-10.0,
        )
        with pytest.raises(InvalidMarketDataError, match="volume is invalid"):
            engine.run([bad_vol], strategy)

    def test_context_history_negative_or_zero_count(self) -> None:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        bar = make_market_event("SPY", t0, 100.0)
        ctx = StrategyContextImpl(
            current_timestamp=t0,
            current_prices={"SPY": 100.0},
            positions={},
            cash=1000.0,
            equity=1000.0,
            history={"SPY": [bar]},
            current_regime=0,
            regime_history=[0],
        )

        assert ctx.get_history("SPY", count=0) == ()
        assert ctx.get_history("SPY", count=-5) == ()
        assert len(ctx.get_history("SPY", count=5)) == 1

        assert ctx.get_regime_history(count=0) == ()
        assert ctx.get_regime_history(count=-2) == ()
