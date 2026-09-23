"""
RegimeX Backtesting — Strategy Comparison Metric Analytics Tests
================================================================
Validates exact metric extraction and accounting across:
- Equity curves and return calculations
- Trade statistics (orders, fills, completed trades, win rate, PnL extrema)
- Transaction cost and commission tracking
- Dynamic common-period slicing with partial windows
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    FillEvent,
    OrderRequest,
    OrderSide,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


class TestComparisonMetricExtraction:
    def test_equity_and_return_metrics(self) -> None:
        """Validate accurate computation of initial equity, final equity, PnL, and returns."""
        curve = [
            EquitySnapshot(
                timestamp=_ts(0),
                cash=50_000.0,
                market_value=0.0,
                equity=50_000.0,
                fees=0.0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
            ),
            EquitySnapshot(
                timestamp=_ts(5),
                cash=55_000.0,
                market_value=0.0,
                equity=55_000.0,
                fees=10.0,
                realized_pnl=5000.0,
                unrealized_pnl=0.0,
            ),
            EquitySnapshot(
                timestamp=_ts(10),
                cash=65_000.0,
                market_value=0.0,
                equity=65_000.0,
                fees=25.0,
                realized_pnl=15000.0,
                unrealized_pnl=0.0,
            ),
        ]
        res = BacktestResult(
            start_timestamp=_ts(0),
            end_timestamp=_ts(10),
            initial_cash=50_000.0,
            final_cash=65_000.0,
            final_equity=65_000.0,
            orders=(),
            fills=(),
            positions={},
            equity_curve=tuple(curve),
            total_fees=25.0,
            trade_count=0,
            metadata={},
        )

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [StrategyComparisonInput(strategy_id="GROWTH", backtest_result=res)]
        )

        summary = result.get_strategy_summary("GROWTH")
        assert summary.initial_equity == 50_000.0
        assert summary.final_equity == 65_000.0
        assert summary.absolute_pnl == 15_000.0
        assert abs(summary.total_return - 0.30) < 1e-12  # 30% gain

    def test_trade_statistics_accounting(self) -> None:
        """
        Validate trade statistics on simulated fills:
        1. BUY 100 @ 50 (entry)
        2. SELL 40 @ 60 (win: +400)
        3. SELL 30 @ 40 (loss: -300)
        4. SELL 30 @ 50 (breakeven: 0)
        Result: 3 completed trades (1 win, 1 loss, 0 breakeven win/loss), win_rate = 1/3 ~ 0.3333,
        total realized = 100.
        """
        fills = [
            FillEvent(
                order_id="o1",
                timestamp=_ts(1),
                symbol="XYZ",
                side=OrderSide.BUY,
                quantity=100.0,
                price=50.0,
                commission=2.0,
            ),
            FillEvent(
                order_id="o2",
                timestamp=_ts(2),
                symbol="XYZ",
                side=OrderSide.SELL,
                quantity=40.0,
                price=60.0,
                commission=1.5,
            ),
            FillEvent(
                order_id="o3",
                timestamp=_ts(3),
                symbol="XYZ",
                side=OrderSide.SELL,
                quantity=30.0,
                price=40.0,
                commission=1.5,
            ),
            FillEvent(
                order_id="o4",
                timestamp=_ts(4),
                symbol="XYZ",
                side=OrderSide.SELL,
                quantity=30.0,
                price=50.0,
                commission=1.5,
            ),
        ]
        orders = [
            OrderRequest(
                order_id=f"o{i}",
                timestamp=_ts(i),
                symbol="XYZ",
                side=OrderSide.BUY if i == 1 else OrderSide.SELL,
                quantity=100.0 if i == 1 else 30.0,
            )
            for i in range(1, 5)
        ]
        curve = [
            EquitySnapshot(
                timestamp=_ts(i),
                cash=100_000.0 + i * 50.0,
                market_value=0.0,
                equity=100_000.0 + i * 50.0,
                fees=6.5,
                realized_pnl=100.0,
                unrealized_pnl=0.0,
            )
            for i in range(5)
        ]
        res = BacktestResult(
            start_timestamp=_ts(0),
            end_timestamp=_ts(4),
            initial_cash=100_000.0,
            final_cash=100_200.0,
            final_equity=100_200.0,
            orders=tuple(orders),
            fills=tuple(fills),
            positions={},
            equity_curve=tuple(curve),
            total_fees=6.5,
            trade_count=4,
            metadata={},
        )

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [StrategyComparisonInput(strategy_id="TRADER", backtest_result=res)]
        )

        summary = result.get_strategy_summary("TRADER")
        trades = summary.trades

        assert trades.order_count == 4
        assert trades.fill_count == 4
        assert trades.completed_trade_count == 3
        assert trades.winning_trades == 1
        assert trades.losing_trades == 1
        assert trades.win_rate is not None
        assert abs(trades.win_rate - (1.0 / 3.0)) < 1e-6
        assert trades.total_realized_pnl == 100.0
        assert trades.average_trade_pnl is not None
        assert abs(trades.average_trade_pnl - (100.0 / 3.0)) < 1e-6
        assert trades.largest_winning_trade == 400.0
        assert trades.largest_losing_trade == -300.0
        assert summary.total_fees == 6.5

    def test_common_period_slicing_behavior(self) -> None:
        """
        Verify that overlapping but mismatched date ranges are sliced to common period:
        Strat A: Day 0 to Day 10 (snapshots at 0, 2, 4, 6, 8, 10)
        Strat B: Day 2 to Day 8  (snapshots at 2, 4, 6, 8)
        Common Window: Day 2 to Day 8
        """
        curve_a = [
            EquitySnapshot(
                timestamp=_ts(d),
                cash=100_000.0 + d * 1000.0,
                market_value=0.0,
                equity=100_000.0 + d * 1000.0,
                fees=10.0,
                realized_pnl=d * 1000.0,
                unrealized_pnl=0.0,
            )
            for d in [0, 2, 4, 6, 8, 10]
        ]
        res_a = BacktestResult(
            start_timestamp=_ts(0),
            end_timestamp=_ts(10),
            initial_cash=100_000.0,
            final_cash=110_000.0,
            final_equity=110_000.0,
            orders=(),
            fills=(),
            positions={},
            equity_curve=tuple(curve_a),
            total_fees=10.0,
            trade_count=0,
            metadata={},
        )

        curve_b = [
            EquitySnapshot(
                timestamp=_ts(d),
                cash=100_000.0 + d * 500.0,
                market_value=0.0,
                equity=100_000.0 + d * 500.0,
                fees=5.0,
                realized_pnl=d * 500.0,
                unrealized_pnl=0.0,
            )
            for d in [2, 4, 6, 8]
        ]
        res_b = BacktestResult(
            start_timestamp=_ts(2),
            end_timestamp=_ts(8),
            initial_cash=100_000.0,
            final_cash=104_000.0,
            final_equity=104_000.0,
            orders=(),
            fills=(),
            positions={},
            equity_curve=tuple(curve_b),
            total_fees=5.0,
            trade_count=0,
            metadata={},
        )

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        # Common period must be [Day 2, Day 8]
        period = result.common_evaluation_period
        assert period.start_timestamp == _ts(2)
        assert period.end_timestamp == _ts(8)
        assert period.is_truncated is True

        summary_a = result.get_strategy_summary("A")
        # In [Day 2, Day 8], A started at 102,000 and ended at 108,000
        assert summary_a.initial_equity == 102_000.0
        assert summary_a.final_equity == 108_000.0
        assert summary_a.absolute_pnl == 6_000.0
        assert abs(summary_a.total_return - (6_000.0 / 102_000.0)) < 1e-12

        summary_b = result.get_strategy_summary("B")
        # In [Day 2, Day 8], B started at 101,000 and ended at 104,000
        assert summary_b.initial_equity == 101_000.0
        assert summary_b.final_equity == 104_000.0
        assert summary_b.absolute_pnl == 3_000.0
        assert abs(summary_b.total_return - (3_000.0 / 101_000.0)) < 1e-12
