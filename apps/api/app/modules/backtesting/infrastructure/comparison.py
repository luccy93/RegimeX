"""
RegimeX Backtesting — Strategy Comparison Analytics Engine
==========================================================
Deterministic calculation engine for comparing multiple completed backtest results.

Architectural position: ``infrastructure/comparison.py``
- Pure Python and Pydantic v2 domain models.
- Reuses V13 Portfolio Risk Engine (analyze_risk, return series, drawdown, VaR/ES).
- Enforces strict input validation, non-empty IDs, and positive initial equity.
- Determines common evaluation period via overlapping intersection.
- Produces immutable, deterministic strategy summaries and pairwise deltas.
- No strategy ranking, scoring, winner declaration, or recommendation logic.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from app.modules.backtesting.domain.errors import (
    DuplicateStrategyIdError,
    EmptyComparisonError,
    IncompatibleEvaluationPeriodError,
    InsufficientComparisonDataError,
    InvalidEquityError,
    InvalidStrategyIdError,
    NonFiniteValueError,
)
from app.modules.backtesting.domain.interfaces import (
    StrategyComparisonEngineProtocol,
)
from app.modules.backtesting.domain.models import (
    ComparisonPeriod,
    EquitySnapshot,
    FillEvent,
    OrderRequest,
    OrderSide,
    PairwiseComparison,
    StrategyComparisonInput,
    StrategyComparisonResult,
    StrategySummary,
    TradeStatistics,
)
from app.modules.portfolio_risk.domain.interfaces import PortfolioRiskEngineProtocol
from app.modules.portfolio_risk.domain.models import PriceSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class StrategyComparisonEngine(StrategyComparisonEngineProtocol):
    """
    Deterministic comparison engine analyzing and contrasting completed backtests.
    """

    def compare(
        self,
        inputs: Sequence[StrategyComparisonInput],
        periods_per_year: float | None = None,
        risk_engine: PortfolioRiskEngineProtocol | None = None,
    ) -> StrategyComparisonResult:
        """
        Compare two or more strategy backtest results across their common evaluation window.

        Parameters
        ----------
        inputs : Sequence[StrategyComparisonInput]
            Sequence of strategy inputs containing strategy_id, display_name, and BacktestResult.
        periods_per_year : float | None
            Annualization factor for volatility and return calculations (e.g., 252.0 for daily).
        risk_engine : PortfolioRiskEngineProtocol | None
            Optional portfolio risk engine for V13 analytics delegation.

        Returns
        -------
        StrategyComparisonResult
            Immutable comparison result containing strategy summaries and pairwise deltas.
        """
        self._validate_inputs(inputs)

        # Determine common evaluation period
        common_period = self._resolve_common_period(inputs)

        # Instantiate or reuse risk engine
        active_risk_engine = risk_engine or PortfolioRiskEngine()

        # Extract metrics and build summary for each strategy
        summaries: list[StrategySummary] = []
        for strat_input in inputs:
            summary = self._build_strategy_summary(
                strat_input=strat_input,
                common_period=common_period,
                periods_per_year=periods_per_year,
                risk_engine=active_risk_engine,
            )
            summaries.append(summary)

        # Generate deterministic pairwise comparisons
        pairwise = self._build_pairwise_comparisons(summaries)

        return StrategyComparisonResult(
            common_evaluation_period=common_period,
            strategies=tuple(summaries),
            pairwise_comparisons=tuple(pairwise),
            metadata={
                "strategy_count": len(summaries),
                "pairwise_count": len(pairwise),
                "periods_per_year": periods_per_year,
                "is_truncated": common_period.is_truncated,
            },
        )

    # =========================================================================
    # Validation & Period Alignment
    # =========================================================================

    def _validate_inputs(self, inputs: Sequence[StrategyComparisonInput]) -> None:
        """Validate input collection structure, uniqueness, and metric sanity."""
        if not inputs or len(inputs) == 0:
            raise EmptyComparisonError(
                "Comparison requires at least one strategy input; received empty collection."
            )

        seen_ids: set[str] = set()
        for idx, item in enumerate(inputs):
            if not isinstance(item, StrategyComparisonInput):
                raise InvalidStrategyIdError(
                    f"Expected StrategyComparisonInput at index {idx}, got {type(item)}."
                )

            clean_id = item.strategy_id.strip()
            if not clean_id:
                raise InvalidStrategyIdError(
                    f"Strategy ID at index {idx} cannot be empty or whitespace-only."
                )

            if clean_id in seen_ids:
                raise DuplicateStrategyIdError(
                    f"Duplicate strategy ID found in comparison: {clean_id!r}."
                )
            seen_ids.add(clean_id)

            res = item.backtest_result
            if res.initial_cash <= 0.0:
                raise InvalidEquityError(
                    f"Strategy {clean_id!r} has invalid initial cash: {res.initial_cash}. "
                    "Must be strictly positive."
                )
            if math.isnan(res.initial_cash) or math.isinf(res.initial_cash):
                raise NonFiniteValueError(
                    f"Strategy {clean_id!r} has non-finite initial cash: {res.initial_cash}."
                )
            if math.isnan(res.final_equity) or math.isinf(res.final_equity):
                raise NonFiniteValueError(
                    f"Strategy {clean_id!r} has non-finite final equity: {res.final_equity}."
                )

    def _resolve_common_period(self, inputs: Sequence[StrategyComparisonInput]) -> ComparisonPeriod:
        """
        Determine common evaluation period: [max(all starts), min(all ends)].
        """
        starts: list[datetime] = [item.backtest_result.start_timestamp for item in inputs]
        ends: list[datetime] = [item.backtest_result.end_timestamp for item in inputs]

        comparison_start = max(starts)
        comparison_end = min(ends)

        if comparison_start > comparison_end:
            raise IncompatibleEvaluationPeriodError(
                f"No overlapping evaluation period found: max start "
                f"({comparison_start.isoformat()}) exceeds min end ({comparison_end.isoformat()})."
            )

        if comparison_start == comparison_end:
            raise IncompatibleEvaluationPeriodError(
                f"Evaluation period is instantaneous ({comparison_start.isoformat()}); "
                "return and risk metrics require at least two observations."
            )

        is_truncated = any(
            s != comparison_start or e != comparison_end for s, e in zip(starts, ends, strict=True)
        )

        return ComparisonPeriod(
            start_timestamp=comparison_start,
            end_timestamp=comparison_end,
            is_truncated=is_truncated,
        )

    # =========================================================================
    # Strategy Summary & Metric Extraction
    # =========================================================================

    def _build_strategy_summary(
        self,
        strat_input: StrategyComparisonInput,
        common_period: ComparisonPeriod,
        periods_per_year: float | None,
        risk_engine: PortfolioRiskEngineProtocol,
    ) -> StrategySummary:
        """Extract performance and risk metrics over the common evaluation period."""
        b_res = strat_input.backtest_result
        strat_id = strat_input.strategy_id
        display_name = strat_input.display_name or strat_id

        # Slice equity curve to common period
        sliced_snapshots: tuple[EquitySnapshot, ...] = tuple(
            s
            for s in b_res.equity_curve
            if common_period.start_timestamp <= s.timestamp <= common_period.end_timestamp
        )

        if len(sliced_snapshots) < 3:
            raise InsufficientComparisonDataError(
                f"Strategy {strat_id!r} has fewer than 3 equity observations in the common "
                f"evaluation period ({len(sliced_snapshots)} found). Risk analytics require at "
                "least 2 return observations."
            )

        initial_equity = sliced_snapshots[0].equity
        final_equity = sliced_snapshots[-1].equity

        if initial_equity <= 0.0:
            raise InvalidEquityError(
                f"Strategy {strat_id!r} initial equity in common period is "
                f"non-positive: {initial_equity}."
            )
        if math.isnan(initial_equity) or math.isinf(initial_equity):
            raise NonFiniteValueError(
                f"Strategy {strat_id!r} initial equity in common period is "
                f"non-finite: {initial_equity}."
            )
        if math.isnan(final_equity) or math.isinf(final_equity):
            raise NonFiniteValueError(
                f"Strategy {strat_id!r} final equity in common period is "
                f"non-finite: {final_equity}."
            )

        absolute_pnl = final_equity - initial_equity
        total_return = (final_equity / initial_equity) - 1.0

        # Annualized return calculation
        duration_sec = common_period.duration.total_seconds()
        annualized_return: float | None = None
        if duration_sec >= 86400.0:  # At least 1 day
            years = duration_sec / (365.25 * 86400.0)
            if years > 0.0 and (1.0 + total_return) > 0.0:
                annualized_return = math.pow(1.0 + total_return, 1.0 / years) - 1.0
        elif periods_per_year is not None and periods_per_year > 0.0:
            obs = len(sliced_snapshots) - 1
            if obs > 0 and (1.0 + total_return) > 0.0:
                annualized_return = math.pow(1.0 + total_return, periods_per_year / obs) - 1.0

        # PnL accounting components
        unrealized_pnl = sliced_snapshots[-1].unrealized_pnl
        realized_pnl = (
            sliced_snapshots[-1].realized_pnl - sliced_snapshots[0].realized_pnl
            if common_period.is_truncated
            else sliced_snapshots[-1].realized_pnl
        )

        # Fills and trade statistics within the common evaluation window
        period_orders = tuple(
            o
            for o in b_res.orders
            if common_period.start_timestamp <= o.timestamp <= common_period.end_timestamp
        )
        period_fills = tuple(
            f
            for f in b_res.fills
            if common_period.start_timestamp <= f.timestamp <= common_period.end_timestamp
        )

        if common_period.is_truncated:
            fees_from_snapshots = sliced_snapshots[-1].fees - sliced_snapshots[0].fees
            fees_from_fills = sum(f.commission for f in period_fills)
            total_fees = max(fees_from_snapshots, fees_from_fills)
        else:
            total_fees = b_res.total_fees
        trade_stats = self._extract_trade_statistics(period_orders, period_fills)

        # V13 Portfolio Risk Engine integration
        price_series = PriceSeries(
            timestamps=tuple(s.timestamp for s in sliced_snapshots),
            prices=tuple(s.equity for s in sliced_snapshots),
            symbol=f"{strat_id}_EQUITY",
        )

        risk_result = risk_engine.analyze_risk(
            data=price_series,
            periods_per_year=periods_per_year,
            series_id=strat_id,
        )

        # Extract risk metrics from V13 result
        var_95: float | None = None
        for conf, var_m in risk_result.var_metrics.items():
            if abs(conf - 0.95) < 1e-4:
                var_95 = var_m.var_loss
                break

        es_95: float | None = None
        for conf, es_m in risk_result.expected_shortfall_metrics.items():
            if abs(conf - 0.95) < 1e-4:
                es_95 = es_m.expected_shortfall
                break

        return StrategySummary(
            strategy_id=strat_id,
            display_name=display_name,
            evaluation_period=common_period,
            initial_equity=initial_equity,
            final_equity=final_equity,
            absolute_pnl=absolute_pnl,
            total_return=total_return,
            annualized_return=annualized_return,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_fees=total_fees,
            trades=trade_stats,
            volatility=risk_result.volatility.period_volatility,
            annualized_volatility=risk_result.volatility.annualized_volatility,
            maximum_drawdown=risk_result.drawdown.max_drawdown,
            drawdown_magnitude=risk_result.drawdown.drawdown_magnitude,
            peak_timestamp=risk_result.drawdown.peak_timestamp,
            trough_timestamp=risk_result.drawdown.trough_timestamp,
            recovery_timestamp=risk_result.drawdown.recovery_timestamp,
            is_recovered=risk_result.drawdown.is_recovered,
            var_95=var_95,
            expected_shortfall_95=es_95,
            return_mean=risk_result.return_statistics.mean_return,
            return_median=risk_result.return_statistics.median_return,
            return_min=risk_result.return_statistics.minimum_return,
            return_max=risk_result.return_statistics.maximum_return,
        )

    def _extract_trade_statistics(
        self,
        orders: Sequence[OrderRequest],
        fills: Sequence[FillEvent],
    ) -> TradeStatistics:
        """
        Extract trade statistics matching SimulatedPortfolio's weighted average cost basis.

        A completed trade is defined as an execution fill that reduces or closes
        an open position (an exit fill), realizing gross PnL.
        """
        order_count = len(orders)
        fill_count = len(fills)

        # Track positions per symbol to determine trade realizations
        positions: dict[str, dict[str, float]] = defaultdict(lambda: {"qty": 0.0, "avg_price": 0.0})
        completed_pnls: list[float] = []

        for fill in fills:
            sym = fill.symbol.strip().upper()
            pos = positions[sym]

            if fill.side == OrderSide.BUY:
                old_qty = pos["qty"]
                new_qty = old_qty + fill.quantity
                new_avg = (old_qty * pos["avg_price"] + fill.quantity * fill.price) / new_qty
                pos["qty"] = new_qty
                pos["avg_price"] = new_avg

            elif fill.side == OrderSide.SELL:
                # Realized gross PnL on position exit
                trade_pnl = (fill.price - pos["avg_price"]) * fill.quantity
                completed_pnls.append(trade_pnl)

                new_qty = max(0.0, pos["qty"] - fill.quantity)
                pos["avg_price"] = pos["avg_price"] if new_qty > 1e-9 else 0.0
                pos["qty"] = new_qty

        completed_trade_count = len(completed_pnls)
        winning_pnls = [p for p in completed_pnls if p > 0.0]
        losing_pnls = [p for p in completed_pnls if p < 0.0]

        winning_count = len(winning_pnls)
        losing_count = len(losing_pnls)
        win_rate = (winning_count / completed_trade_count) if completed_trade_count > 0 else None
        total_realized_pnl = sum(completed_pnls)
        average_trade_pnl = (
            (total_realized_pnl / completed_trade_count) if completed_trade_count > 0 else None
        )
        largest_win = max(winning_pnls) if winning_pnls else None
        largest_loss = min(losing_pnls) if losing_pnls else None

        return TradeStatistics(
            order_count=order_count,
            fill_count=fill_count,
            completed_trade_count=completed_trade_count,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate=win_rate,
            total_realized_pnl=total_realized_pnl,
            average_trade_pnl=average_trade_pnl,
            largest_winning_trade=largest_win,
            largest_losing_trade=largest_loss,
        )

    # =========================================================================
    # Pairwise Comparison & Deltas
    # =========================================================================

    def _build_pairwise_comparisons(
        self, summaries: Sequence[StrategySummary]
    ) -> list[PairwiseComparison]:
        """
        Generate deterministic pairwise comparisons in canonical order:
        (S_0 vs S_1), (S_0 vs S_2), ..., (S_1 vs S_2), etc.
        Formula: Delta = Metric_A - Metric_B.
        """
        pairwise: list[PairwiseComparison] = []
        n = len(summaries)

        for i in range(n):
            for j in range(i + 1, n):
                strat_a = summaries[i]
                strat_b = summaries[j]

                # Absolute deltas: A - B
                final_equity_delta = strat_a.final_equity - strat_b.final_equity
                pnl_delta = strat_a.absolute_pnl - strat_b.absolute_pnl
                return_delta = strat_a.total_return - strat_b.total_return

                annualized_ret_delta: float | None = None
                if strat_a.annualized_return is not None and strat_b.annualized_return is not None:
                    annualized_ret_delta = strat_a.annualized_return - strat_b.annualized_return

                volatility_delta = strat_a.volatility - strat_b.volatility

                annualized_vol_delta: float | None = None
                if (
                    strat_a.annualized_volatility is not None
                    and strat_b.annualized_volatility is not None
                ):
                    annualized_vol_delta = (
                        strat_a.annualized_volatility - strat_b.annualized_volatility
                    )

                drawdown_delta = strat_a.maximum_drawdown - strat_b.maximum_drawdown
                drawdown_mag_delta = strat_a.drawdown_magnitude - strat_b.drawdown_magnitude

                var_delta: float | None = None
                if strat_a.var_95 is not None and strat_b.var_95 is not None:
                    var_delta = strat_a.var_95 - strat_b.var_95

                es_delta: float | None = None
                if (
                    strat_a.expected_shortfall_95 is not None
                    and strat_b.expected_shortfall_95 is not None
                ):
                    es_delta = strat_a.expected_shortfall_95 - strat_b.expected_shortfall_95

                fees_delta = strat_a.total_fees - strat_b.total_fees
                trade_count_delta = (
                    strat_a.trades.completed_trade_count - strat_b.trades.completed_trade_count
                )

                win_rate_delta: float | None = None
                if strat_a.trades.win_rate is not None and strat_b.trades.win_rate is not None:
                    win_rate_delta = strat_a.trades.win_rate - strat_b.trades.win_rate

                # Safe relative differences: (A - B) / |B| (None if B == 0)
                rel_ret_diff = (
                    (return_delta / abs(strat_b.total_return))
                    if abs(strat_b.total_return) > 1e-12
                    else None
                )

                rel_fee_diff = (
                    (fees_delta / abs(strat_b.total_fees))
                    if abs(strat_b.total_fees) > 1e-12
                    else None
                )

                rel_dd_diff = (
                    (drawdown_mag_delta / abs(strat_b.drawdown_magnitude))
                    if abs(strat_b.drawdown_magnitude) > 1e-12
                    else None
                )

                rel_eq_diff = (
                    (final_equity_delta / abs(strat_b.final_equity))
                    if abs(strat_b.final_equity) > 1e-12
                    else None
                )

                pairwise.append(
                    PairwiseComparison(
                        base_strategy_id=strat_a.strategy_id,
                        target_strategy_id=strat_b.strategy_id,
                        final_equity_delta=final_equity_delta,
                        pnl_delta=pnl_delta,
                        return_delta=return_delta,
                        annualized_return_delta=annualized_ret_delta,
                        volatility_delta=volatility_delta,
                        annualized_volatility_delta=annualized_vol_delta,
                        drawdown_delta=drawdown_delta,
                        drawdown_magnitude_delta=drawdown_mag_delta,
                        var_delta=var_delta,
                        es_delta=es_delta,
                        fees_delta=fees_delta,
                        trade_count_delta=trade_count_delta,
                        win_rate_delta=win_rate_delta,
                        relative_return_difference=rel_ret_diff,
                        relative_fee_difference=rel_fee_diff,
                        relative_drawdown_difference=rel_dd_diff,
                        relative_equity_difference=rel_eq_diff,
                    )
                )

        return pairwise
