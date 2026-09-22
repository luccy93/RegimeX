"""
RegimeX Backtesting — Execution Timing Integrity Tests
======================================================
Verifies execution timing correctness across CURRENT_CLOSE and NEXT_OPEN conventions,
guaranteeing no same-bar lookahead or accidental price substitution, and validating
end-of-series pending order handling.
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


def _ts(day: int) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=day)


class TestExecutionTimingIntegrity:
    def test_current_close_timing_uses_exact_bar_close(self) -> None:
        """
        In CURRENT_CLOSE mode:
        Order emitted on Bar 0 must execute at Bar 0 close (not open, not high, not Bar 1).
        """
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="TIMING",
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=1000.0,
            ),
            MarketEvent(
                timestamp=_ts(1),
                symbol="TIMING",
                open=120.0,
                high=130.0,
                low=115.0,
                close=125.0,
                volume=1000.0,
            ),
        ]

        class SingleOrderStrategy:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                if event.timestamp == bars[0].timestamp:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=10.0,
                        )
                    ]
                return []

        config = BacktestConfig(
            initial_cash=50_000.0,
            slippage_rate=0.01,  # 1% slippage
            commission_rate=0.0,
            execution_convention=ExecutionPriceConvention.CURRENT_CLOSE,
        )
        engine = EventDrivenBacktestEngine(config=config)
        result = engine.run(bars, SingleOrderStrategy())

        assert len(result.fills) == 1
        fill = result.fills[0]
        # Bar 0 close = 105.0. 105.0 * 1.01 = 106.05
        assert abs(fill.price - 106.05) < 1e-9
        assert fill.timestamp == bars[0].timestamp

    def test_next_open_timing_executes_at_subsequent_bar_open(self) -> None:
        """
        In NEXT_OPEN mode:
        Order emitted on Bar 0 must execute at Bar 1 open (not Bar 0 close, not Bar 1 close).
        """
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="TIMING",
                open=100.0,
                high=110.0,
                low=95.0,
                close=105.0,
                volume=1000.0,
            ),
            MarketEvent(
                timestamp=_ts(1),
                symbol="TIMING",
                open=120.0,
                high=130.0,
                low=115.0,
                close=125.0,
                volume=1000.0,
            ),
            MarketEvent(
                timestamp=_ts(2),
                symbol="TIMING",
                open=140.0,
                high=150.0,
                low=135.0,
                close=145.0,
                volume=1000.0,
            ),
        ]

        class NextOpenTrader:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                if event.timestamp == bars[0].timestamp:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=10.0,
                        )
                    ]
                return []

        config = BacktestConfig(
            initial_cash=50_000.0,
            slippage_rate=0.005,  # 0.5% slippage
            commission_rate=0.0,
            execution_convention=ExecutionPriceConvention.NEXT_OPEN,
        )
        engine = EventDrivenBacktestEngine(config=config)
        result = engine.run(bars, NextOpenTrader())

        assert len(result.fills) == 1
        fill = result.fills[0]
        # Must execute on Bar 1 at open: 120.0 * 1.005 = 120.60
        assert fill.timestamp == bars[1].timestamp
        assert abs(fill.price - 120.60) < 1e-9

    def test_end_of_series_pending_orders_remain_unfilled_safely(self) -> None:
        """
        In NEXT_OPEN mode:
        An order emitted on the final bar T_last cannot be filled because there is no T_last+1.
        Verify that order is recorded in result.orders, but NOT in result.fills, and portfolio
        cash remains uncorrupted.
        """
        bars = [
            MarketEvent(
                timestamp=_ts(0),
                symbol="FINAL",
                open=50.0,
                high=52.0,
                low=48.0,
                close=50.0,
                volume=100.0,
            ),
            MarketEvent(
                timestamp=_ts(1),
                symbol="FINAL",
                open=55.0,
                high=57.0,
                low=54.0,
                close=56.0,
                volume=100.0,
            ),
        ]

        class LastBarBuyer:
            def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
                # Place order on final bar (Bar 1)
                if event.timestamp == bars[1].timestamp:
                    return [
                        OrderRequest(
                            timestamp=event.timestamp,
                            symbol=event.symbol,
                            side=OrderSide.BUY,
                            quantity=50.0,
                        )
                    ]
                return []

        config = BacktestConfig(
            initial_cash=10_000.0,
            execution_convention=ExecutionPriceConvention.NEXT_OPEN,
        )
        engine = EventDrivenBacktestEngine(config=config)
        result = engine.run(bars, LastBarBuyer())

        # Order was emitted
        assert len(result.orders) == 1
        assert result.orders[0].symbol == "FINAL"
        # But zero fills occurred because no subsequent bar exists
        assert len(result.fills) == 0
        assert result.trade_count == 0
        # Cash remains completely uncharged
        assert result.final_cash == 10_000.0
        assert result.final_equity == 10_000.0
