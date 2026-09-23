"""
RegimeX Backtesting — Performance Report Builder
================================================
Deterministic report generation layer transforming completed strategy comparison
analytics into an immutable, self-contained, machine-readable performance report.

Architectural position: ``infrastructure/reporting.py``
- Implements ``PerformanceReportBuilderProtocol``.
- Pure Python and Pydantic v2 domain models.
- Does NOT recalculate any financial metrics, drawdowns, VaR, or returns.
- Completely neutral: zero rankings, winner declaration, or recommendations.
- Deterministic output: supports explicit timestamp and report_id injection.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.modules.backtesting.domain.errors import InvalidReportError
from app.modules.backtesting.domain.interfaces import (
    PerformanceReportBuilderProtocol,
)
from app.modules.backtesting.domain.models import (
    REPORT_SCHEMA_VERSION,
    Methodology,
    MetricDefinition,
    PerformanceReport,
    ReportMetadata,
    StrategyComparisonInput,
    StrategyComparisonResult,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.portfolio_risk.domain.interfaces import PortfolioRiskEngineProtocol

# =============================================================================
# Standard Metric Definitions
# =============================================================================

DEFAULT_METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    # Return Metrics
    MetricDefinition(
        metric_name="total_return",
        description=(
            "Cumulative return over the evaluation period: (final_equity / initial_equity) - 1."
        ),
        unit="percentage",
        direction_semantics="Higher value denotes greater realized cumulative wealth gain.",
        source="BacktestEngine / StrategySummary",
    ),
    MetricDefinition(
        metric_name="annualized_return",
        description="Compound annual growth rate (CAGR) normalized by periods_per_year.",
        unit="percentage",
        direction_semantics="Higher value denotes greater annualized compound return.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="absolute_pnl",
        description="Net portfolio change in currency terms: final_equity - initial_equity.",
        unit="currency",
        direction_semantics="Higher value denotes greater net currency profit.",
        source="BacktestEngine / StrategySummary",
    ),
    MetricDefinition(
        metric_name="realized_pnl",
        description="Gross realized profit or loss from completed exit order fills.",
        unit="currency",
        direction_semantics="Higher value denotes greater closed-trade profit.",
        source="BacktestEngine / TradeStatistics",
    ),
    MetricDefinition(
        metric_name="unrealized_pnl",
        description="Mark-to-market open position profit or loss at evaluation period close.",
        unit="currency",
        direction_semantics="Higher value denotes greater unrealized mark-to-market gain.",
        source="BacktestEngine",
    ),
    MetricDefinition(
        metric_name="return_mean",
        description="Sample arithmetic mean of discrete periodic portfolio returns.",
        unit="percentage",
        direction_semantics="Higher value denotes higher average periodic return.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="return_median",
        description="Sample median of discrete periodic portfolio returns.",
        unit="percentage",
        direction_semantics="Higher value denotes higher central tendency of periodic returns.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="return_min",
        description="Minimum discrete single-period portfolio return observed.",
        unit="percentage",
        direction_semantics="Less negative value denotes smaller worst-case single-period decline.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="return_max",
        description="Maximum discrete single-period portfolio return observed.",
        unit="percentage",
        direction_semantics="Higher value denotes larger best-case single-period gain.",
        source="PortfolioRiskEngine",
    ),
    # Risk Metrics
    MetricDefinition(
        metric_name="volatility",
        description="Sample standard deviation (ddof=1) of discrete periodic returns.",
        unit="percentage",
        direction_semantics=(
            "Higher value denotes greater dispersion/variability of periodic returns."
        ),
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="annualized_volatility",
        description="Sample standard deviation annualized by sqrt(periods_per_year).",
        unit="percentage",
        direction_semantics="Higher value denotes greater annualized return dispersion.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="maximum_drawdown",
        description="Deepest signed peak-to-trough equity decline: (trough - peak) / peak <= 0.",
        unit="percentage",
        direction_semantics=(
            "More negative value denotes deeper peak-to-trough capital impairment."
        ),
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="drawdown_magnitude",
        description="Absolute magnitude of maximum peak-to-trough decline: |maximum_drawdown|.",
        unit="percentage",
        direction_semantics="Higher value denotes greater peak-to-trough decline magnitude.",
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="var_95",
        description=(
            "Historical Value at Risk at 95% confidence level (loss-oriented: positive = loss)."
        ),
        unit="percentage",
        direction_semantics=(
            "Higher value denotes larger estimated downside tail loss at 95% confidence."
        ),
        source="PortfolioRiskEngine",
    ),
    MetricDefinition(
        metric_name="expected_shortfall_95",
        description="Expected Shortfall (CVaR) at 95% confidence (loss-oriented: positive = loss).",
        unit="percentage",
        direction_semantics=(
            "Higher value denotes larger expected tail loss conditional on exceeding VaR."
        ),
        source="PortfolioRiskEngine",
    ),
    # Trade Execution & Costs
    MetricDefinition(
        metric_name="total_fees",
        description="Cumulative execution commissions and transaction fees paid.",
        unit="currency",
        direction_semantics="Higher value denotes greater cumulative transaction friction.",
        source="BacktestEngine / FillEvents",
    ),
    MetricDefinition(
        metric_name="order_count",
        description="Total discrete order requests generated by strategy during evaluation.",
        unit="count",
        direction_semantics="Higher value denotes greater strategy signaling/ordering activity.",
        source="BacktestEngine",
    ),
    MetricDefinition(
        metric_name="fill_count",
        description="Total execution order fills processed by execution model.",
        unit="count",
        direction_semantics="Higher value denotes higher execution volume.",
        source="BacktestEngine / FillEvents",
    ),
    MetricDefinition(
        metric_name="completed_trade_count",
        description="Total round-trip position exit fills realizing profit or loss.",
        unit="count",
        direction_semantics="Higher value denotes more completed trading cycles.",
        source="StrategyComparisonEngine / TradeStatistics",
    ),
    MetricDefinition(
        metric_name="win_rate",
        description="Proportion of completed round-trip trades with positive realized PnL (> 0).",
        unit="ratio",
        direction_semantics="Higher value denotes greater proportion of profitable closed trades.",
        source="StrategyComparisonEngine / TradeStatistics",
    ),
    # Equity
    MetricDefinition(
        metric_name="initial_equity",
        description="Starting portfolio capital at the beginning of the evaluation period.",
        unit="currency",
        direction_semantics="Baseline capital for return and PnL calculation.",
        source="BacktestResult / StrategyComparisonInput",
    ),
    MetricDefinition(
        metric_name="final_equity",
        description="Ending portfolio capital at the conclusion of the evaluation period.",
        unit="currency",
        direction_semantics="Higher value denotes greater final accumulated wealth.",
        source="BacktestResult / StrategySummary",
    ),
    # Pairwise Deltas
    MetricDefinition(
        metric_name="final_equity_delta",
        description="Pairwise absolute final equity difference: A.final_equity - B.final_equity.",
        unit="currency",
        direction_semantics=(
            "Positive value indicates Base strategy ended with higher capital than Target."
        ),
        source="PairwiseComparison",
    ),
    MetricDefinition(
        metric_name="return_delta",
        description="Pairwise cumulative return difference: A.total_return - B.total_return.",
        unit="percentage_points",
        direction_semantics=(
            "Positive value indicates Base strategy achieved higher cumulative return."
        ),
        source="PairwiseComparison",
    ),
    MetricDefinition(
        metric_name="volatility_delta",
        description="Pairwise sample volatility difference: A.volatility - B.volatility.",
        unit="percentage_points",
        direction_semantics=(
            "Positive value indicates Base strategy exhibited greater return variability."
        ),
        source="PairwiseComparison",
    ),
    MetricDefinition(
        metric_name="drawdown_delta",
        description="Pairwise signed drawdown difference: A.maximum_drawdown - B.maximum_drawdown.",
        unit="percentage_points",
        direction_semantics=(
            "Positive value indicates Base strategy had less severe signed drawdown."
        ),
        source="PairwiseComparison",
    ),
    MetricDefinition(
        metric_name="fees_delta",
        description="Pairwise cumulative fee difference: A.total_fees - B.total_fees.",
        unit="currency",
        direction_semantics=(
            "Positive value indicates Base strategy incurred greater transaction costs."
        ),
        source="PairwiseComparison",
    ),
)

# =============================================================================
# Standard Quantitative Methodology
# =============================================================================

DEFAULT_METHODOLOGY: Methodology = Methodology(
    common_period_policy=(
        "Intersection of overlapping equity timestamps across all evaluated strategies: "
        "max(start_timestamps) to min(end_timestamps)."
    ),
    trade_definition=(
        "Trade execution statistics are evaluated on completed position exit fills that realize "
        "profit or loss, matching buy and sell execution fills per symbol."
    ),
    pairwise_delta_definition=(
        "Deterministic difference computed as Metric(Base Strategy A) - Metric(Target Strategy B)."
    ),
    relative_difference_definition=(
        "Safe relative difference computed as (Metric_A - Metric_B) / |Metric_B|, "
        "returning None when the denominator is zero."
    ),
    risk_engine_source=(
        "V13 PortfolioRiskEngine (discrete arithmetic returns, sample standard deviation with "
        "ddof=1, historical VaR/ES at 95% confidence)."
    ),
    return_type=(
        "Discrete arithmetic returns derived from equity snapshots: "
        "(Equity_t - Equity_{t-1}) / Equity_{t-1}."
    ),
    execution_engine_source=(
        "V14 BacktestEngine event-driven execution simulation with discrete order requests, "
        "fill events, and marked-to-market positions."
    ),
)

# =============================================================================
# Standard Evaluation Limitations
# =============================================================================

DEFAULT_LIMITATIONS: tuple[str, ...] = (
    "Historical simulation results are based on simulated past market observations and "
    "do not guarantee or predict future performance.",
    "Transaction cost and slippage models are approximations of historical liquidity and "
    "may not capture extreme market stress or execution latency.",
    "Market data precision and sampling frequency (e.g. discrete close or bar intervals) "
    "influence fill timing and path-dependent metric calculations.",
    "Execution price convention (NEXT_OPEN, CURRENT_CLOSE, etc.) impacts fill simulation "
    "and entry/exit price realism.",
    "Performance metrics and pairwise comparisons are strictly descriptive and contain "
    "no strategy scoring, ranking, or investment recommendation.",
)


class PerformanceReportBuilder(PerformanceReportBuilderProtocol):
    """
    Production-grade performance report builder conforming to PerformanceReportBuilderProtocol.

    Converts completed StrategyComparisonResult analytics into an immutable,
    machine-readable PerformanceReport.
    """

    def __init__(
        self,
        metric_definitions: Sequence[MetricDefinition] | None = None,
        methodology: Methodology | None = None,
        limitations: Sequence[str] | None = None,
    ) -> None:
        self._metric_definitions: tuple[MetricDefinition, ...] = (
            tuple(metric_definitions)
            if metric_definitions is not None
            else DEFAULT_METRIC_DEFINITIONS
        )
        self._methodology: Methodology = methodology or DEFAULT_METHODOLOGY
        self._limitations: tuple[str, ...] = (
            tuple(limitations) if limitations is not None else DEFAULT_LIMITATIONS
        )

    @property
    def metric_definitions(self) -> tuple[MetricDefinition, ...]:
        """Tuple of configured metric definitions."""
        return self._metric_definitions

    @property
    def methodology(self) -> Methodology:
        """Configured quantitative methodology."""
        return self._methodology

    @property
    def limitations(self) -> tuple[str, ...]:
        """Tuple of configured report limitations."""
        return self._limitations

    def build(
        self,
        comparison_result: StrategyComparisonResult,
        generated_at: datetime | None = None,
        report_id: str | None = None,
    ) -> PerformanceReport:
        """
        Construct an immutable performance report from a completed strategy comparison result.

        Parameters
        ----------
        comparison_result : StrategyComparisonResult
            The completed, validated strategy comparison analytics result.
        generated_at : datetime | None
            Optional explicit generation timestamp for deterministic reporting.
            If None, remains None (or caller can pass explicit datetime).
        report_id : str | None
            Optional explicit report identifier. If None, a unique UUIDv4 string is assigned.

        Returns
        -------
        PerformanceReport
            Self-contained, immutable performance report.

        Raises
        ------
        InvalidReportError
            If comparison_result is missing or contains invalid structural elements.
        """
        if comparison_result is None or not isinstance(comparison_result, StrategyComparisonResult):
            raise InvalidReportError(
                "comparison_result must be a valid StrategyComparisonResult instance."
            )

        if len(comparison_result.strategies) == 0:
            raise InvalidReportError(
                "comparison_result must contain at least one evaluated strategy summary."
            )

        # Validate UTC timestamp if explicitly passed
        clean_generated_at: datetime | None = None
        if generated_at is not None:
            if not isinstance(generated_at, datetime):
                raise InvalidReportError("generated_at must be a datetime instance.")
            if generated_at.tzinfo is None or generated_at.tzinfo != UTC:
                clean_generated_at = generated_at.replace(tzinfo=UTC)
            else:
                clean_generated_at = generated_at

        # Construct structural metadata
        metadata = ReportMetadata(
            report_version=REPORT_SCHEMA_VERSION,
            comparison_start=comparison_result.common_evaluation_period.start_timestamp,
            comparison_end=comparison_result.common_evaluation_period.end_timestamp,
            strategy_count=len(comparison_result.strategies),
            pairwise_comparison_count=len(comparison_result.pairwise_comparisons),
            is_truncated=comparison_result.common_evaluation_period.is_truncated,
            source_engine_version=comparison_result.version,
            metric_schema_version="1.0.0",
        )

        final_report_id = (
            report_id.strip() if report_id and report_id.strip() else str(uuid.uuid4())
        )

        try:
            return PerformanceReport(
                report_id=final_report_id,
                report_version=REPORT_SCHEMA_VERSION,
                generated_at=clean_generated_at,
                metadata=metadata,
                comparison_period=comparison_result.common_evaluation_period,
                strategies=comparison_result.strategies,
                pairwise_comparisons=comparison_result.pairwise_comparisons,
                metric_definitions=self._metric_definitions,
                methodology=self._methodology,
                limitations=self._limitations,
            )
        except Exception as exc:
            raise InvalidReportError(f"Failed to assemble performance report: {exc}") from exc

    def build_from_inputs(
        self,
        inputs: Sequence[StrategyComparisonInput],
        periods_per_year: float | None = None,
        risk_engine: PortfolioRiskEngineProtocol | None = None,
        generated_at: datetime | None = None,
        report_id: str | None = None,
    ) -> PerformanceReport:
        """
        Convenience method executing strategy comparison analytics and assembling the
        resulting performance report in a single invocation.

        Parameters
        ----------
        inputs : Sequence[StrategyComparisonInput]
            Sequence of strategy comparison inputs.
        periods_per_year : float | None
            Annualization factor for risk and return calculations.
        risk_engine : PortfolioRiskEngineProtocol | None
            Optional portfolio risk engine instance conforming to V13 protocol.
        generated_at : datetime | None
            Optional explicit generation timestamp for deterministic reporting.
        report_id : str | None
            Optional explicit report identifier.

        Returns
        -------
        PerformanceReport
            Self-contained, immutable performance report.
        """
        comparison_engine = StrategyComparisonEngine()
        comparison_result = comparison_engine.compare(
            inputs=inputs,
            periods_per_year=periods_per_year,
            risk_engine=risk_engine,
        )
        return self.build(
            comparison_result=comparison_result,
            generated_at=generated_at,
            report_id=report_id,
        )
