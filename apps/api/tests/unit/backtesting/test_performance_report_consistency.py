"""
RegimeX Backtesting — Performance Report Consistency Tests
==========================================================
Validates that PerformanceReport strictly reflects StrategyComparisonResult:
- Zero metric drift or recomputation between comparison and report
- All strategy summaries and pairwise deltas are preserved verbatim
- Metric definitions cover all primary reported metrics
- Metadata accurately reflects comparison parameters
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.backtesting.infrastructure.reporting import PerformanceReportBuilder


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_backtest_result(
    start_dt: datetime,
    end_dt: datetime,
    initial_cash: float,
    equity_values: list[float],
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
        orders=(),
        fills=(),
        positions={},
        equity_curve=tuple(curve),
        total_fees=total_fees,
        trade_count=0,
        metadata={},
    )


class TestPerformanceReportConsistency:
    def test_zero_metric_drift_between_comparison_and_report(self) -> None:
        """Verify that every metric in comparison result is bit-for-bit preserved in report."""
        res_a = _make_backtest_result(
            _ts(0),
            _ts(10),
            100_000.0,
            [100_000.0, 102_000.0, 105_000.0, 110_000.0],
            total_fees=45.0,
        )
        res_b = _make_backtest_result(
            _ts(0), _ts(10), 100_000.0, [100_000.0, 99_000.0, 101_000.0, 104_000.0], total_fees=25.0
        )

        inputs = [
            StrategyComparisonInput(
                strategy_id="strat_a", display_name="Alpha", backtest_result=res_a
            ),
            StrategyComparisonInput(
                strategy_id="strat_b", display_name="Beta", backtest_result=res_b
            ),
        ]

        engine = StrategyComparisonEngine()
        comparison = engine.compare(inputs=inputs, periods_per_year=252.0)

        builder = PerformanceReportBuilder()
        report = builder.build(comparison_result=comparison)

        # Exact equality of strategy tuples
        assert report.strategies == comparison.strategies

        # Exact equality of pairwise comparison tuples
        assert report.pairwise_comparisons == comparison.pairwise_comparisons

        # Exact equality of comparison period
        assert report.comparison_period == comparison.common_evaluation_period

        # Metadata fidelity
        assert (
            report.metadata.comparison_start == comparison.common_evaluation_period.start_timestamp
        )
        assert report.metadata.comparison_end == comparison.common_evaluation_period.end_timestamp
        assert report.metadata.strategy_count == len(comparison.strategies)
        assert report.metadata.pairwise_comparison_count == len(comparison.pairwise_comparisons)
        assert report.metadata.is_truncated == comparison.common_evaluation_period.is_truncated

    def test_metric_definitions_cover_core_metrics(self) -> None:
        """Verify report provides documentation for all core performance and risk metrics."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            inputs=[StrategyComparisonInput(strategy_id="A", backtest_result=res)]
        )

        reported_metric_names = {m.metric_name for m in report.metric_definitions}

        core_required_metrics = [
            "total_return",
            "annualized_return",
            "absolute_pnl",
            "realized_pnl",
            "unrealized_pnl",
            "volatility",
            "annualized_volatility",
            "maximum_drawdown",
            "drawdown_magnitude",
            "var_95",
            "expected_shortfall_95",
            "total_fees",
            "order_count",
            "fill_count",
            "completed_trade_count",
            "win_rate",
            "initial_equity",
            "final_equity",
            "final_equity_delta",
            "return_delta",
            "volatility_delta",
            "drawdown_delta",
            "fees_delta",
        ]

        for metric in core_required_metrics:
            assert metric in reported_metric_names, f"Missing definition for core metric: {metric}"
            definition = report.get_metric_definition(metric)
            assert definition.description
            assert definition.unit
            assert definition.direction_semantics
            assert definition.source
