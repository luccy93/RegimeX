"""
RegimeX Backtesting — Strategy Comparison Core Tests
====================================================
Validates end-to-end strategy comparison analytics:
- Basic two-strategy comparison
- Multi-strategy pairwise combinations
- Single-strategy comparison (N=1)
- Golden arithmetic verification
- Immutability guarantees
- Metric lookup methods and absence of ranking
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    FillEvent,
    OrderRequest,
    StrategyComparisonInput,
    StrategyComparisonResult,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from pydantic import ValidationError


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_backtest_result(
    start_dt: datetime,
    end_dt: datetime,
    initial_cash: float,
    equity_values: list[float],
    orders: list[OrderRequest] | None = None,
    fills: list[FillEvent] | None = None,
    total_fees: float = 0.0,
) -> BacktestResult:
    n = len(equity_values)
    step = (end_dt - start_dt) / max(1, n - 1)
    curve: list[EquitySnapshot] = []
    for i, eq in enumerate(equity_values):
        t = start_dt + i * step
        curve.append(
            EquitySnapshot(
                timestamp=t,
                cash=eq,
                market_value=0.0,
                equity=eq,
                fees=total_fees,
                realized_pnl=eq - initial_cash,
                unrealized_pnl=0.0,
            )
        )
    return BacktestResult(
        start_timestamp=start_dt,
        end_timestamp=end_dt,
        initial_cash=initial_cash,
        final_cash=equity_values[-1],
        final_equity=equity_values[-1],
        orders=tuple(orders or []),
        fills=tuple(fills or []),
        positions={},
        equity_curve=tuple(curve),
        total_fees=total_fees,
        trade_count=len(fills or []),
        metadata={},
    )


class TestStrategyComparisonCore:
    def test_basic_two_strategy_comparison(self) -> None:
        """Verify standard comparison between two strategies."""
        res_a = _make_backtest_result(
            start_dt=_ts(0),
            end_dt=_ts(10),
            initial_cash=100_000.0,
            equity_values=[100_000.0, 102_000.0, 105_000.0, 110_000.0],
            total_fees=50.0,
        )
        res_b = _make_backtest_result(
            start_dt=_ts(0),
            end_dt=_ts(10),
            initial_cash=100_000.0,
            equity_values=[100_000.0, 99_000.0, 101_000.0, 104_000.0],
            total_fees=30.0,
        )

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(
                    strategy_id="strat_a",
                    display_name="Strategy Alpha",
                    backtest_result=res_a,
                ),
                StrategyComparisonInput(
                    strategy_id="strat_b",
                    display_name="Strategy Beta",
                    backtest_result=res_b,
                ),
            ]
        )

        assert isinstance(result, StrategyComparisonResult)
        assert len(result.strategies) == 2
        assert len(result.pairwise_comparisons) == 1

        summary_a = result.get_strategy_summary("strat_a")
        summary_b = result.get_strategy_summary("strat_b")

        assert summary_a.strategy_id == "strat_a"
        assert summary_a.display_name == "Strategy Alpha"
        assert summary_a.initial_equity == 100_000.0
        assert summary_a.final_equity == 110_000.0
        assert summary_a.absolute_pnl == 10_000.0
        assert abs(summary_a.total_return - 0.10) < 1e-9
        assert summary_a.total_fees == 50.0

        assert summary_b.strategy_id == "strat_b"
        assert summary_b.final_equity == 104_000.0
        assert summary_b.absolute_pnl == 4_000.0
        assert abs(summary_b.total_return - 0.04) < 1e-9

        pair = result.get_pairwise_comparison("strat_a", "strat_b")
        assert pair.base_strategy_id == "strat_a"
        assert pair.target_strategy_id == "strat_b"
        assert pair.final_equity_delta == 6_000.0
        assert pair.pnl_delta == 6_000.0
        assert abs(pair.return_delta - 0.06) < 1e-9
        assert pair.fees_delta == 20.0

    def test_multi_strategy_pairwise_combinations(self) -> None:
        """Verify N=3 produces exactly N*(N-1)/2 = 3 pairwise comparisons in order."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 103_000.0])
        res_c = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 100_500.0, 101_000.0])

        inputs = [
            StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
            StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            StrategyComparisonInput(strategy_id="C", backtest_result=res_c),
        ]

        engine = StrategyComparisonEngine()
        result = engine.compare(inputs)

        assert len(result.strategies) == 3
        assert len(result.pairwise_comparisons) == 3

        pairs = [(p.base_strategy_id, p.target_strategy_id) for p in result.pairwise_comparisons]
        assert pairs == [("A", "B"), ("A", "C"), ("B", "C")]

    def test_single_strategy_comparison(self) -> None:
        """Verify N=1 produces a summary and empty pairwise tuple."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 104_000.0, 108_000.0])
        engine = StrategyComparisonEngine()
        result = engine.compare([StrategyComparisonInput(strategy_id="SOLO", backtest_result=res)])

        assert len(result.strategies) == 1
        assert len(result.pairwise_comparisons) == 0
        summary = result.get_strategy_summary("SOLO")
        assert summary.strategy_id == "SOLO"
        assert abs(summary.total_return - 0.08) < 1e-9

    def test_golden_arithmetic_scenario(self) -> None:
        """
        Verify exact arithmetic on golden scenario:
        Strategy A: 100,000 -> 110,000 (10%)
        Strategy B: 100,000 -> 105,000 (5%)
        A - B return delta = 5 percentage points (0.05).
        """
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 105_000.0, 110_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="StratA", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="StratB", backtest_result=res_b),
            ]
        )

        s_a = result.get_strategy_summary("StratA")
        s_b = result.get_strategy_summary("StratB")
        pair = result.get_pairwise_comparison("StratA", "StratB")

        assert abs(s_a.total_return - 0.10) < 1e-12
        assert abs(s_b.total_return - 0.05) < 1e-12
        assert abs(pair.return_delta - 0.05) < 1e-12
        assert abs(pair.pnl_delta - 5_000.0) < 1e-12

    def test_immutability_enforcement(self) -> None:
        """Verify frozen models reject mutation attempts."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 103_000.0])

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        with pytest.raises(ValidationError):
            setattr(result, "version", "2.0.0")  # noqa: B010

        with pytest.raises(ValidationError):
            setattr(result.strategies[0], "initial_equity", 999.0)  # noqa: B010

        with pytest.raises(ValidationError):
            setattr(result.pairwise_comparisons[0], "return_delta", 0.50)  # noqa: B010

    def test_lookup_exceptions_for_missing_ids(self) -> None:
        """Verify KeyError is raised when looking up non-existent strategies or pairs."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 103_000.0])

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        with pytest.raises(KeyError, match="Strategy 'NON_EXISTENT' not found"):
            result.get_strategy_summary("NON_EXISTENT")

        with pytest.raises(KeyError, match="Pairwise comparison for \\('B', 'A'\\) not found"):
            result.get_pairwise_comparison("B", "A")

    def test_metric_direction_semantics_presence(self) -> None:
        """Verify descriptive direction semantics are exposed without scores/ranks."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 103_000.0])

        engine = StrategyComparisonEngine()
        result = engine.compare(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        assert "total_return" in result.metric_semantics
        assert "volatility" in result.metric_semantics
        assert "maximum_drawdown" in result.metric_semantics
        assert not hasattr(result, "best_strategy")
        assert not hasattr(result, "winner")
        assert not hasattr(result, "rank")
