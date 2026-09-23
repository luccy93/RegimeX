"""
RegimeX Backtesting — Strategy Comparison Validation Tests
==========================================================
Validates rejection of malformed or invalid inputs:
- Empty comparison collection
- Duplicate strategy identifiers
- Empty or whitespace strategy identifiers
- Incompatible/non-overlapping evaluation periods
- Instantaneous evaluation periods
- Non-positive or non-finite initial equity
- Insufficient observations in common window
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.errors import (
    DuplicateStrategyIdError,
    EmptyComparisonError,
    IncompatibleEvaluationPeriodError,
    InsufficientComparisonDataError,
)
from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from pydantic import ValidationError


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_backtest_result(
    start_dt: datetime,
    end_dt: datetime,
    initial_cash: float = 100_000.0,
    equity_values: list[float] | None = None,
) -> BacktestResult:
    eqs = equity_values or [100_000.0, 105_000.0]
    n = len(eqs)
    step = (end_dt - start_dt) / max(1, n - 1)
    curve = [
        EquitySnapshot(
            timestamp=start_dt + i * step,
            cash=eq,
            market_value=0.0,
            equity=eq,
            fees=0.0,
            realized_pnl=eq - initial_cash,
            unrealized_pnl=0.0,
        )
        for i, eq in enumerate(eqs)
    ]
    return BacktestResult(
        start_timestamp=start_dt,
        end_timestamp=end_dt,
        initial_cash=initial_cash,
        final_cash=eqs[-1],
        final_equity=eqs[-1],
        orders=(),
        fills=(),
        positions={},
        equity_curve=tuple(curve),
        total_fees=0.0,
        trade_count=0,
        metadata={},
    )


class TestStrategyComparisonValidation:
    def test_reject_empty_inputs(self) -> None:
        """Reject empty comparison input collection."""
        engine = StrategyComparisonEngine()
        with pytest.raises(EmptyComparisonError, match="requires at least one strategy input"):
            engine.compare([])

    def test_reject_duplicate_strategy_ids(self) -> None:
        """Reject duplicate strategy identifiers within the same comparison."""
        res_a = _make_backtest_result(_ts(0), _ts(5))
        res_b = _make_backtest_result(_ts(0), _ts(5))

        engine = StrategyComparisonEngine()
        with pytest.raises(DuplicateStrategyIdError, match="Duplicate strategy ID found"):
            engine.compare(
                [
                    StrategyComparisonInput(strategy_id="SAME_ID", backtest_result=res_a),
                    StrategyComparisonInput(strategy_id="SAME_ID", backtest_result=res_b),
                ]
            )

    def test_reject_empty_or_whitespace_strategy_id(self) -> None:
        """Reject empty or whitespace-only strategy identifiers."""
        res = _make_backtest_result(_ts(0), _ts(5))

        with pytest.raises(ValidationError):
            StrategyComparisonInput(strategy_id="", backtest_result=res)

        with pytest.raises(ValidationError):
            StrategyComparisonInput(strategy_id="   ", backtest_result=res)

    def test_reject_non_overlapping_periods(self) -> None:
        """Reject strategies with completely disjoint time periods."""
        # Strat A: Day 0 to Day 5
        res_a = _make_backtest_result(_ts(0), _ts(5))
        # Strat B: Day 10 to Day 15
        res_b = _make_backtest_result(_ts(10), _ts(15))

        engine = StrategyComparisonEngine()
        with pytest.raises(
            IncompatibleEvaluationPeriodError, match="No overlapping evaluation period found"
        ):
            engine.compare(
                [
                    StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                    StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
                ]
            )

    def test_reject_instantaneous_overlapping_period(self) -> None:
        """Reject strategies whose overlap is a single instantaneous point."""
        # Strat A: Day 0 to Day 5
        res_a = _make_backtest_result(_ts(0), _ts(5))
        # Strat B: Day 5 to Day 10
        res_b = _make_backtest_result(_ts(5), _ts(10))

        engine = StrategyComparisonEngine()
        with pytest.raises(
            IncompatibleEvaluationPeriodError, match="Evaluation period is instantaneous"
        ):
            engine.compare(
                [
                    StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                    StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
                ]
            )

    def test_reject_non_positive_initial_equity(self) -> None:
        """Reject strategy inputs with zero or negative initial equity."""
        res_zero = _make_backtest_result(_ts(0), _ts(5), initial_cash=0.0)
        with pytest.raises(ValidationError, match="initial_cash must be strictly positive"):
            StrategyComparisonInput(strategy_id="ZERO_CASH", backtest_result=res_zero)

        res_neg = _make_backtest_result(_ts(0), _ts(5), initial_cash=-500.0)
        with pytest.raises(ValidationError, match="initial_cash must be strictly positive"):
            StrategyComparisonInput(strategy_id="NEG_CASH", backtest_result=res_neg)

    def test_reject_non_finite_values(self) -> None:
        """Reject non-finite values in equity snapshots or inputs."""
        with pytest.raises(ValidationError, match="equity snapshot metric must be finite"):
            EquitySnapshot(
                timestamp=_ts(0),
                cash=float("nan"),
                market_value=0.0,
                equity=100_000.0,
            )

        with pytest.raises(ValidationError, match="equity snapshot metric must be finite"):
            EquitySnapshot(
                timestamp=_ts(0),
                cash=100_000.0,
                market_value=0.0,
                equity=float("inf"),
            )

    def test_reject_insufficient_data_points_in_window(self) -> None:
        """Reject if fewer than 2 snapshots exist in the common overlapping window."""
        # Create result where only 1 snapshot falls in the common window
        res_a = _make_backtest_result(_ts(0), _ts(10), equity_values=[100_000.0, 105_000.0])
        # Strat B only has observations at day 8 and 10, but day 9 and 10 are common
        curve_b = [
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
                timestamp=_ts(10),
                cash=102_000.0,
                market_value=0.0,
                equity=102_000.0,
                fees=0.0,
                realized_pnl=2000.0,
                unrealized_pnl=0.0,
            ),
        ]
        res_b = BacktestResult(
            start_timestamp=_ts(9),  # Starts at day 9, but curve only has day 10 in [9, 10]
            end_timestamp=_ts(10),
            initial_cash=100_000.0,
            final_cash=102_000.0,
            final_equity=102_000.0,
            orders=(),
            fills=(),
            positions={},
            equity_curve=tuple(curve_b),
            total_fees=0.0,
            trade_count=0,
            metadata={},
        )

        engine = StrategyComparisonEngine()
        with pytest.raises(
            InsufficientComparisonDataError, match="fewer than 3 equity observations"
        ):
            engine.compare(
                [
                    StrategyComparisonInput(strategy_id="A", backtest_result=res_a),
                    StrategyComparisonInput(strategy_id="B", backtest_result=res_b),
                ]
            )
