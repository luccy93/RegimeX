"""
RegimeX Backtesting — Pairwise Comparison & Deltas Tests
========================================================
Validates pairwise comparisons:
- Strict directionality: Delta = Metric_A - Metric_B
- Arithmetic consistency of absolute differences
- Relative differences with non-zero denominators
- Safe handling of zero denominators (None, never NaN or Inf)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_backtest_result(
    initial_cash: float,
    equity_values: list[float],
    total_fees: float = 0.0,
) -> BacktestResult:
    start_dt = _ts(0)
    end_dt = _ts(len(equity_values) - 1)
    curve = [
        EquitySnapshot(
            timestamp=_ts(i),
            cash=eq,
            market_value=0.0,
            equity=eq,
            fees=total_fees,
            realized_pnl=eq - initial_cash,
            unrealized_pnl=0.0,
        )
        for i, eq in enumerate(equity_values)
    ]
    return BacktestResult(
        start_timestamp=start_dt,
        end_timestamp=end_dt,
        initial_cash=initial_cash,
        final_cash=equity_values[-1],
        final_equity=equity_values[-1],
        orders=(),
        fills=(),
        positions={},
        equity_curve=tuple(curve),
        total_fees=total_fees,
        trade_count=0,
        metadata={},
    )


class TestPairwiseComparisonDeltas:
    def test_pairwise_deltas_directionality(self) -> None:
        """Verify strict delta directionality: Metric_A - Metric_B."""
        res_a = _make_backtest_result(100_000.0, [100_000.0, 105_000.0, 110_000.0], total_fees=50.0)
        res_b = _make_backtest_result(100_000.0, [100_000.0, 102_000.0, 104_000.0], total_fees=20.0)

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        pair = result.get_pairwise_comparison("A", "B")
        summary_a = result.get_strategy_summary("A")
        summary_b = result.get_strategy_summary("B")

        assert pair.final_equity_delta == summary_a.final_equity - summary_b.final_equity
        assert pair.pnl_delta == summary_a.absolute_pnl - summary_b.absolute_pnl
        assert abs(pair.return_delta - (summary_a.total_return - summary_b.total_return)) < 1e-12
        assert pair.fees_delta == summary_a.total_fees - summary_b.total_fees
        assert pair.volatility_delta == summary_a.volatility - summary_b.volatility
        assert pair.drawdown_delta == summary_a.maximum_drawdown - summary_b.maximum_drawdown

    def test_relative_differences_valid_denominators(self) -> None:
        """Verify relative differences when denominator != 0: (A - B) / |B|."""
        # A: 10% return, 50 fees
        res_a = _make_backtest_result(100_000.0, [100_000.0, 105_000.0, 110_000.0], total_fees=50.0)
        # B: 5% return, 25 fees
        res_b = _make_backtest_result(100_000.0, [100_000.0, 102_500.0, 105_000.0], total_fees=25.0)

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        pair = result.get_pairwise_comparison("A", "B")

        # return_delta = 0.10 - 0.05 = 0.05
        # rel_return_diff = 0.05 / 0.05 = 1.0 (100% higher return than B)
        assert pair.relative_return_difference is not None
        assert abs(pair.relative_return_difference - 1.0) < 1e-9

        # fees_delta = 50 - 25 = 25
        # rel_fee_diff = 25 / 25 = 1.0 (100% higher fees than B)
        assert pair.relative_fee_difference is not None
        assert abs(pair.relative_fee_difference - 1.0) < 1e-9

    def test_relative_differences_zero_denominators_safety(self) -> None:
        """Verify relative difference returns None when denominator is zero (never NaN or Inf)."""
        # A: return = 5%, fees = 10.0
        res_a = _make_backtest_result(100_000.0, [100_000.0, 102_500.0, 105_000.0], total_fees=10.0)
        # B: return = 0% (flat: 100k -> 100k), fees = 0.0, drawdown = 0.0
        res_b = _make_backtest_result(100_000.0, [100_000.0, 100_000.0, 100_000.0], total_fees=0.0)

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        pair = result.get_pairwise_comparison("A", "B")

        # B total return is 0 -> rel diff must be None
        assert pair.relative_return_difference is None

        # B fees is 0 -> rel fee diff must be None
        assert pair.relative_fee_difference is None

        # B drawdown magnitude is 0 -> rel dd diff must be None
        assert pair.relative_drawdown_difference is None

        # Absolute deltas must still be computed accurately
        assert abs(pair.return_delta - 0.05) < 1e-9
        assert pair.fees_delta == 10.0
