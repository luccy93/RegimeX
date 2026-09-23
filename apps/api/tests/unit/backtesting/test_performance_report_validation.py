"""
RegimeX Backtesting — Performance Report Validation Tests
=========================================================
Validates rejection of malformed or invalid inputs:
- Empty strategies in PerformanceReport
- Duplicate strategy IDs in PerformanceReport
- Empty or whitespace report versions
- Non-StrategyComparisonResult passed to build()
- Invalid generated_at timestamp types
- Empty or invalid MetricDefinition fields
- Naive datetime rejection
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.errors import InvalidReportError
from app.modules.backtesting.domain.models import (
    REPORT_SCHEMA_VERSION,
    BacktestResult,
    ComparisonPeriod,
    EquitySnapshot,
    MetricDefinition,
    PerformanceReport,
    ReportMetadata,
    StrategyComparisonInput,
    StrategySummary,
    TradeStatistics,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.backtesting.infrastructure.reporting import (
    DEFAULT_LIMITATIONS,
    DEFAULT_METHODOLOGY,
    DEFAULT_METRIC_DEFINITIONS,
    PerformanceReportBuilder,
)
from pydantic import ValidationError


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_dummy_strategy_summary(strategy_id: str) -> StrategySummary:
    period = ComparisonPeriod(start_timestamp=_ts(0), end_timestamp=_ts(5))
    trades = TradeStatistics(
        order_count=0,
        fill_count=0,
        completed_trade_count=0,
        winning_trades=0,
        losing_trades=0,
    )
    return StrategySummary(
        strategy_id=strategy_id,
        display_name=f"Strategy {strategy_id}",
        evaluation_period=period,
        initial_equity=100_000.0,
        final_equity=105_000.0,
        absolute_pnl=5_000.0,
        total_return=0.05,
        realized_pnl=5_000.0,
        unrealized_pnl=0.0,
        total_fees=10.0,
        trades=trades,
        volatility=0.01,
        maximum_drawdown=-0.02,
        drawdown_magnitude=0.02,
    )


class TestPerformanceReportValidation:
    def test_reject_empty_strategies_in_report(self) -> None:
        """Verify PerformanceReport cannot be instantiated with empty strategies tuple."""
        period = ComparisonPeriod(start_timestamp=_ts(0), end_timestamp=_ts(5))
        metadata = ReportMetadata(
            report_version=REPORT_SCHEMA_VERSION,
            comparison_start=_ts(0),
            comparison_end=_ts(5),
            strategy_count=1,
            pairwise_comparison_count=0,
            is_truncated=False,
        )

        with pytest.raises(ValidationError, match="requires at least one strategy summary"):
            PerformanceReport(
                metadata=metadata,
                comparison_period=period,
                strategies=(),
                pairwise_comparisons=(),
                metric_definitions=DEFAULT_METRIC_DEFINITIONS,
                methodology=DEFAULT_METHODOLOGY,
                limitations=DEFAULT_LIMITATIONS,
            )

    def test_reject_duplicate_strategy_ids_in_report(self) -> None:
        """Verify PerformanceReport rejects duplicate strategy IDs in its strategies tuple."""
        period = ComparisonPeriod(start_timestamp=_ts(0), end_timestamp=_ts(5))
        metadata = ReportMetadata(
            report_version=REPORT_SCHEMA_VERSION,
            comparison_start=_ts(0),
            comparison_end=_ts(5),
            strategy_count=2,
            pairwise_comparison_count=0,
            is_truncated=False,
        )

        strat1 = _make_dummy_strategy_summary("ALPHA")
        strat2 = _make_dummy_strategy_summary("ALPHA")  # Duplicate

        with pytest.raises(ValidationError, match="Duplicate strategy ID in report: 'ALPHA'"):
            PerformanceReport(
                metadata=metadata,
                comparison_period=period,
                strategies=(strat1, strat2),
                pairwise_comparisons=(),
                metric_definitions=DEFAULT_METRIC_DEFINITIONS,
                methodology=DEFAULT_METHODOLOGY,
                limitations=DEFAULT_LIMITATIONS,
            )

    def test_reject_empty_or_whitespace_report_version(self) -> None:
        """Verify report_version cannot be empty or whitespace."""
        with pytest.raises(ValidationError, match="report_version cannot be empty"):
            ReportMetadata(
                report_version="   ",
                comparison_start=_ts(0),
                comparison_end=_ts(5),
                strategy_count=1,
                pairwise_comparison_count=0,
                is_truncated=False,
            )

    def test_reject_non_strategy_comparison_result(self) -> None:
        """Verify builder.build() rejects non-StrategyComparisonResult objects."""
        builder = PerformanceReportBuilder()
        with pytest.raises(InvalidReportError, match="must be a valid StrategyComparisonResult"):
            builder.build(comparison_result="invalid_string")  # type: ignore[arg-type]

        with pytest.raises(InvalidReportError, match="must be a valid StrategyComparisonResult"):
            builder.build(comparison_result=None)  # type: ignore[arg-type]

    def test_reject_invalid_generated_at_type(self) -> None:
        """Verify builder.build() rejects non-datetime generated_at parameter."""
        res_a = BacktestResult(
            start_timestamp=_ts(0),
            end_timestamp=_ts(5),
            initial_cash=100_000.0,
            final_cash=105_000.0,
            final_equity=105_000.0,
            orders=(),
            fills=(),
            positions={},
            equity_curve=(
                EquitySnapshot(
                    timestamp=_ts(0),
                    cash=100_000.0,
                    market_value=0.0,
                    equity=100_000.0,
                    fees=0.0,
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                ),
                EquitySnapshot(
                    timestamp=_ts(2),
                    cash=102_000.0,
                    market_value=0.0,
                    equity=102_000.0,
                    fees=0.0,
                    realized_pnl=2_000.0,
                    unrealized_pnl=0.0,
                ),
                EquitySnapshot(
                    timestamp=_ts(5),
                    cash=105_000.0,
                    market_value=0.0,
                    equity=105_000.0,
                    fees=0.0,
                    realized_pnl=5_000.0,
                    unrealized_pnl=0.0,
                ),
            ),
            total_fees=0.0,
            trade_count=0,
            metadata={},
        )
        engine = StrategyComparisonEngine()
        comparison_res = engine.compare(
            [StrategyComparisonInput(strategy_id="strat_1", backtest_result=res_a)]
        )

        builder = PerformanceReportBuilder()
        with pytest.raises(InvalidReportError, match="generated_at must be a datetime"):
            builder.build(
                comparison_result=comparison_res,
                generated_at="2026-01-01T00:00:00Z",  # type: ignore[arg-type]
            )

    def test_metric_definition_field_validation(self) -> None:
        """Verify MetricDefinition requires non-empty strings for all fields."""
        with pytest.raises(ValidationError):
            MetricDefinition(
                metric_name="",
                description="desc",
                unit="unit",
                direction_semantics="sem",
                source="src",
            )

        with pytest.raises(ValidationError):
            MetricDefinition(
                metric_name="name",
                description="",
                unit="unit",
                direction_semantics="sem",
                source="src",
            )

    def test_timezone_naive_rejection(self) -> None:
        """Verify naive timestamps in ReportMetadata are rejected."""
        naive_dt = datetime(2026, 1, 1, 10, 0, 0)
        with pytest.raises(ValidationError, match="must be UTC-aware"):
            ReportMetadata(
                comparison_start=naive_dt,
                comparison_end=_ts(5),
                strategy_count=1,
                pairwise_comparison_count=0,
                is_truncated=False,
            )
