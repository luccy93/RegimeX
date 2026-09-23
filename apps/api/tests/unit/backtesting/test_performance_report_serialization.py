"""
RegimeX Backtesting — Performance Report Serialization Tests
============================================================
Validates serialization and deserialization of PerformanceReport:
- Full JSON serialization round-trip: model_dump_json() -> model_validate_json()
- Dictionary serialization round-trip: model_dump() -> model_validate()
- Verification of ISO 8601 timestamps and finite numerical values
- Deserialized object equivalence
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    PerformanceReport,
    StrategyComparisonInput,
)
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


class TestPerformanceReportSerialization:
    def test_json_roundtrip_serialization(self) -> None:
        """Verify report serializes to JSON and round-trips with bit-for-bit equivalence."""

        res_a = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 103_000.0, 107_000.0])
        res_b = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 101_000.0, 104_000.0])

        inputs = [
            StrategyComparisonInput(
                strategy_id="strat_a", display_name="Alpha", backtest_result=res_a
            ),
            StrategyComparisonInput(
                strategy_id="strat_b", display_name="Beta", backtest_result=res_b
            ),
        ]

        fixed_time = datetime(2026, 4, 15, 8, 30, 0, tzinfo=UTC)
        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(
            inputs=inputs,
            periods_per_year=252.0,
            generated_at=fixed_time,
            report_id="test-json-roundtrip",
        )

        # Serialize to JSON string
        json_str = report.model_dump_json()

        # Validate that JSON is valid standard JSON
        parsed_dict = json.loads(json_str)
        assert parsed_dict["report_id"] == "test-json-roundtrip"
        assert parsed_dict["report_version"] == "1.0"
        assert parsed_dict["generated_at"] == "2026-04-15T08:30:00Z"
        assert len(parsed_dict["strategies"]) == 2
        assert len(parsed_dict["pairwise_comparisons"]) == 1

        # Deserialize back to PerformanceReport
        restored_report = PerformanceReport.model_validate_json(json_str)

        assert restored_report == report
        assert restored_report.report_id == report.report_id
        assert restored_report.generated_at == report.generated_at
        assert restored_report.strategies == report.strategies
        assert restored_report.pairwise_comparisons == report.pairwise_comparisons
        assert restored_report.metadata == report.metadata

    def test_dict_roundtrip_serialization(self) -> None:
        """Verify performance report serializes to dict and round-trips with model_validate."""
        res = _make_backtest_result(_ts(0), _ts(5), 100_000.0, [100_000.0, 102_000.0, 105_000.0])
        inputs = [StrategyComparisonInput(strategy_id="SOLO", backtest_result=res)]

        builder = PerformanceReportBuilder()
        report = builder.build_from_inputs(inputs=inputs, report_id="test-dict-roundtrip")

        report_dict = report.model_dump()
        assert isinstance(report_dict, dict)
        assert report_dict["report_id"] == "test-dict-roundtrip"
        assert report_dict["generated_at"] is None

        restored_report = PerformanceReport.model_validate(report_dict)
        assert restored_report == report
