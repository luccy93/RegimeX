"""
RegimeX Backtesting — Performance Report Determinism Tests
==========================================================
Validates that performance reporting produces bit-for-bit identical outputs:
- Repeated builds with explicit timestamp and report_id produce identical reports
- Equality comparisons report_1 == report_2
- Dictionary and JSON serialization determinism
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


class TestPerformanceReportDeterminism:
    def test_deterministic_identical_reports_across_runs(self) -> None:
        """Verify repeated calls with explicit timestamp produce bit-for-bit equality."""
        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 103_000.0, 108_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 104_000.0])

        inputs = [
            StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
            StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
        ]

        engine = StrategyComparisonEngine()
        comparison_res = engine.compare(inputs)

        fixed_time = datetime(2026, 6, 1, 9, 30, 0, tzinfo=UTC)
        fixed_id = "test-deterministic-report-id"

        builder = PerformanceReportBuilder()
        report_1 = builder.build(
            comparison_result=comparison_res,
            generated_at=fixed_time,
            report_id=fixed_id,
        )
        report_2 = builder.build(
            comparison_result=comparison_res,
            generated_at=fixed_time,
            report_id=fixed_id,
        )

        assert report_1 == report_2
        assert report_1.model_dump() == report_2.model_dump()
        assert report_1.model_dump_json() == report_2.model_dump_json()

    def test_deterministic_build_from_inputs(self) -> None:
        """Verify build_from_inputs with explicit arguments produces identical reports."""

        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 103_000.0, 108_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 104_000.0])

        inputs = [
            StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
            StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
        ]

        fixed_time = datetime(2026, 6, 1, 9, 30, 0, tzinfo=UTC)
        fixed_id = "test-deterministic-from-inputs"

        builder = PerformanceReportBuilder()
        report_1 = builder.build_from_inputs(
            inputs=inputs,
            periods_per_year=252.0,
            generated_at=fixed_time,
            report_id=fixed_id,
        )
        report_2 = builder.build_from_inputs(
            inputs=inputs,
            periods_per_year=252.0,
            generated_at=fixed_time,
            report_id=fixed_id,
        )

        assert report_1 == report_2
        assert report_1.model_dump() == report_2.model_dump()
        assert report_1.model_dump_json() == report_2.model_dump_json()

    def test_deterministic_none_generated_at(self) -> None:
        """Verify when generated_at is None, report does not auto-inject dynamic time."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        inputs = [StrategyComparisonInput(strategy_id="A", backtest_result=res)]

        builder = PerformanceReportBuilder()
        report_1 = builder.build_from_inputs(inputs=inputs, report_id="id-static")
        report_2 = builder.build_from_inputs(inputs=inputs, report_id="id-static")

        assert report_1.generated_at is None
        assert report_2.generated_at is None
        assert report_1 == report_2
