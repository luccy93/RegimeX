"""
RegimeX Backtesting — Performance Report Core Tests
===================================================
Validates the construction, structure, lookups, and immutability of PerformanceReport:
- Construction from StrategyComparisonResult (N=1, N=2, N=3)
- Construction via build_from_inputs
- Golden scenario verification (10% vs 5%)
- Lookups (get_strategy, get_pairwise, get_metric_definition)
- Report immutability (frozen Pydantic models)
- Neutral reporting: absence of ranking, winners, or scores
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.models import (
    REPORT_SCHEMA_VERSION,
    BacktestResult,
    EquitySnapshot,
    FillEvent,
    OrderRequest,
    PerformanceReport,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.backtesting.infrastructure.reporting import PerformanceReportBuilder
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


class TestPerformanceReportCore:
    def test_basic_report_generation_two_strategies(self) -> None:
        """Verify performance report generation from a two-strategy comparison."""
        res_a = _make_backtest_result(
            _ts(0),
            _ts(10),
            100_000.0,
            [100_000.0, 102_000.0, 105_000.0, 110_000.0],
            total_fees=50.0,
        )
        res_b = _make_backtest_result(
            _ts(0), _ts(10), 100_000.0, [100_000.0, 99_000.0, 101_000.0, 104_000.0], total_fees=30.0
        )

        comparison_engine = StrategyComparisonEngine()
        comparison_res = comparison_engine.compare(
            [
                StrategyComparisonInput(
                    strategy_id="strat_a", display_name="Alpha", backtest_result=res_a
                ),
                StrategyComparisonInput(
                    strategy_id="strat_b", display_name="Beta", backtest_result=res_b
                ),
            ]
        )

        fixed_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        builder = PerformanceReportBuilder()
        report = builder.build(
            comparison_result=comparison_res,
            generated_at=fixed_time,
            report_id="rep-12345",
        )

        assert isinstance(report, PerformanceReport)
        assert report.report_id == "rep-12345"
        assert report.report_version == REPORT_SCHEMA_VERSION
        assert report.generated_at == fixed_time

        # Metadata validation
        assert report.metadata.report_version == REPORT_SCHEMA_VERSION
        assert report.metadata.strategy_count == 2
        assert report.metadata.pairwise_comparison_count == 1
        assert report.metadata.comparison_start == _ts(0)
        assert report.metadata.comparison_end == _ts(10)
        assert not report.metadata.is_truncated

        # Strategies & Pairwise
        assert len(report.strategies) == 2
        assert len(report.pairwise_comparisons) == 1

        # Lookups
        summary_a = report.get_strategy("strat_a")
        assert summary_a.display_name == "Alpha"
        assert summary_a.final_equity == 110_000.0

        pair = report.get_pairwise("strat_a", "strat_b")
        assert pair.base_strategy_id == "strat_a"
        assert pair.target_strategy_id == "strat_b"
        assert pair.final_equity_delta == 6_000.0

    def test_single_strategy_report(self) -> None:
        """Verify performance report generation with N=1 strategy (valid, zero pairwise)."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 105_000.0, 108_000.0])
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            inputs=[
                StrategyComparisonInput(
                    strategy_id="SOLO", display_name="Solo Strategy", backtest_result=res
                )
            ],
            report_id="rep-solo",
        )

        assert report.metadata.strategy_count == 1
        assert report.metadata.pairwise_comparison_count == 0
        assert len(report.strategies) == 1
        assert len(report.pairwise_comparisons) == 0
        assert report.get_strategy("SOLO").final_equity == 108_000.0

    def test_multi_strategy_report_three_strategies(self) -> None:
        """Verify report generation with N=3 produces N*(N-1)/2 = 3 pairwise comparisons."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 106_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 104_000.0])
        res_c = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 100_500.0, 102_000.0])

        inputs = [
            StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
            StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            StrategyComparisonInput(strategy_id="C", backtest_result=res_c),
        ]

        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(inputs=inputs)

        assert report.metadata.strategy_count == 3
        assert report.metadata.pairwise_comparison_count == 3
        assert len(report.pairwise_comparisons) == 3

        # Test all pairwise lookups
        p_ab = report.get_pairwise("A", "B")
        p_ac = report.get_pairwise("A", "C")
        p_bc = report.get_pairwise("B", "C")
        assert p_ab.base_strategy_id == "A" and p_ab.target_strategy_id == "B"
        assert p_ac.base_strategy_id == "A" and p_ac.target_strategy_id == "C"
        assert p_bc.base_strategy_id == "B" and p_bc.target_strategy_id == "C"

    def test_golden_scenario_reporting(self) -> None:
        """
        Verify exact arithmetic preservation in report:
        Strategy A: 100,000 -> 110,000 (+10.0%)
        Strategy B: 100,000 -> 105,000 (+5.0%)
        Delta: +5.0 percentage points, pnl_delta = +5,000.
        """
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 105_000.0, 110_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])

        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            [
                StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
            ]
        )

        strat_a = report.get_strategy("A")
        strat_b = report.get_strategy("B")
        assert abs(strat_a.total_return - 0.10) < 1e-9
        assert abs(strat_b.total_return - 0.05) < 1e-9

        pair = report.get_pairwise("A", "B")
        assert abs(pair.return_delta - 0.05) < 1e-9
        assert pair.pnl_delta == 5_000.0
        assert pair.final_equity_delta == 5_000.0

    def test_report_lookups_and_error_handling(self) -> None:
        """Verify report lookup methods and KeyError on nonexistent keys."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 102_000.0])
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            [StrategyComparisonInput(strategy_id="STRAT1", backtest_result=res)]
        )

        # Strategy lookup
        assert report.get_strategy("STRAT1").strategy_id == "STRAT1"
        with pytest.raises(KeyError, match="Strategy 'NONEXISTENT' not found"):
            report.get_strategy("NONEXISTENT")

        # Pairwise lookup
        with pytest.raises(
            KeyError, match="Pairwise comparison \\('STRAT1', 'STRAT2'\\) not found"
        ):
            report.get_pairwise("STRAT1", "STRAT2")

        # Metric definition lookup
        metric_def = report.get_metric_definition("total_return")
        assert metric_def.metric_name == "total_return"
        assert metric_def.unit == "percentage"

        with pytest.raises(KeyError, match="Metric definition 'unknown_metric' not found"):
            report.get_metric_definition("unknown_metric")

    def test_report_immutability(self) -> None:
        """Verify that PerformanceReport and nested components are frozen against mutation."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 102_000.0])
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            [StrategyComparisonInput(strategy_id="STRAT1", backtest_result=res)]
        )

        with pytest.raises(ValidationError):
            setattr(report, "report_id", "new-id")  # noqa: B010

        with pytest.raises(ValidationError):
            setattr(report.metadata, "strategy_count", 99)  # noqa: B010

        with pytest.raises(ValidationError):
            setattr(report.methodology, "common_period_policy", "mutated")  # noqa: B010

    def test_structural_completeness_of_methodology_and_limitations(self) -> None:
        """Verify that default methodology and limitations are present and detailed."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 102_000.0])
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            [StrategyComparisonInput(strategy_id="STRAT1", backtest_result=res)]
        )

        assert report.methodology.common_period_policy
        assert report.methodology.trade_definition
        assert report.methodology.pairwise_delta_definition
        assert report.methodology.relative_difference_definition
        assert report.methodology.risk_engine_source
        assert report.methodology.return_type
        assert report.methodology.execution_engine_source

        assert len(report.limitations) >= 5
        assert any("Historical simulation" in lim for lim in report.limitations)
        assert any("no strategy scoring, ranking" in lim for lim in report.limitations)
