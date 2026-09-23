"""
RegimeX Backtesting — Strategy Comparison Determinism Tests
===========================================================
Validates determinism guarantees:
- 100% bit-for-bit identical outputs across repeated executions
- Strict deterministic ordering of strategy summaries and pairwise pairs
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
) -> BacktestResult:
    start_dt = _ts(0)
    end_dt = _ts(len(equity_values) - 1)
    curve = [
        EquitySnapshot(
            timestamp=_ts(i),
            cash=eq,
            market_value=0.0,
            equity=eq,
            fees=10.0,
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
        total_fees=10.0,
        trade_count=0,
        metadata={},
    )


class TestComparisonDeterminism:
    def test_repeated_comparison_reproducibility(self) -> None:
        """Verify repeated comparison invocations produce bit-for-bit identical results."""
        res_a = _make_backtest_result(100_000.0, [100_000.0, 103_000.0, 108_000.0])
        res_b = _make_backtest_result(100_000.0, [100_000.0, 99_000.0, 104_000.0])
        res_c = _make_backtest_result(100_000.0, [100_000.0, 101_000.0, 106_000.0])

        inputs = [
            StrategyComparisonInput(strategy_id="ALPHA", backtest_result=res_a),
            StrategyComparisonInput(strategy_id="BETA", backtest_result=res_b),
            StrategyComparisonInput(strategy_id="GAMMA", backtest_result=res_c),
        ]

        engine = StrategyComparisonEngine()
        baseline = engine.compare(inputs, periods_per_year=252.0)

        for _ in range(5):
            repeated = engine.compare(inputs, periods_per_year=252.0)

            # Strategies order and values match
            assert len(repeated.strategies) == len(baseline.strategies)
            for s1, s2 in zip(baseline.strategies, repeated.strategies, strict=True):
                assert s1.strategy_id == s2.strategy_id
                assert s1.total_return == s2.total_return
                assert s1.volatility == s2.volatility
                assert s1.maximum_drawdown == s2.maximum_drawdown
                assert s1.var_95 == s2.var_95
                assert s1.expected_shortfall_95 == s2.expected_shortfall_95

            # Pairwise ordering and values match
            assert len(repeated.pairwise_comparisons) == len(baseline.pairwise_comparisons)
            for p1, p2 in zip(
                baseline.pairwise_comparisons, repeated.pairwise_comparisons, strict=True
            ):
                assert p1.base_strategy_id == p2.base_strategy_id
                assert p1.target_strategy_id == p2.target_strategy_id
                assert p1.return_delta == p2.return_delta
                assert p1.final_equity_delta == p2.final_equity_delta
                assert p1.volatility_delta == p2.volatility_delta

    def test_canonical_pairwise_ordering_rule(self) -> None:
        """
        Verify pairwise ordering is deterministic and follows the input order:
        [S0, S1, S2, S3] -> (S0, S1), (S0, S2), (S0, S3), (S1, S2), (S1, S3), (S2, S3).
        """
        res = _make_backtest_result(100_000.0, [100_000.0, 102_000.0, 105_000.0])
        inputs = [
            StrategyComparisonInput(strategy_id="S0", backtest_result=res),
            StrategyComparisonInput(strategy_id="S1", backtest_result=res),
            StrategyComparisonInput(strategy_id="S2", backtest_result=res),
            StrategyComparisonInput(strategy_id="S3", backtest_result=res),
        ]

        engine = StrategyComparisonEngine()
        result = engine.compare(inputs)

        pairs = [(p.base_strategy_id, p.target_strategy_id) for p in result.pairwise_comparisons]
        expected = [
            ("S0", "S1"),
            ("S0", "S2"),
            ("S0", "S3"),
            ("S1", "S2"),
            ("S1", "S3"),
            ("S2", "S3"),
        ]
        assert pairs == expected
