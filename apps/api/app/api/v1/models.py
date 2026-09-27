"""
RegimeX API v1 — Response & Request Models
==========================================
Canonical typed presentation schemas for API v1 endpoints.

Design Principles:
- Pydantic v2 BaseModel subclasses with frozen immutability.
- No internal domain object or ORM instance leakage.
- Explicit schemas supporting clean OpenAPI documentation generation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ApiError, ApiErrorDetail

# =============================================================================
# Root & Health Responses
# =============================================================================


class RootResponse(BaseModel):
    """API Root metadata response."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Platform API name")
    version: str = Field(description="Semantic platform release version")
    api_version: str = Field(description="Active API namespace version")
    status: str = Field(default="ok", description="Overall service status")


class HealthResponse(BaseModel):
    """Lightweight process liveness response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="ok", description="Process liveness state")


class ReadinessResponse(BaseModel):
    """Detailed operational readiness response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Readiness status ('ready' or 'not_ready')")
    checks: dict[str, str] = Field(description="Status of individual infrastructure checks")
    timestamp: str | None = Field(default=None, description="ISO 8601 evaluation timestamp")


# =============================================================================
# Market Intelligence Responses
# =============================================================================


class MarketItemResponse(BaseModel):
    """Summary representation of a tradeable instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Canonical instrument symbol")
    asset_class: str = Field(description="Asset classification")
    exchange: str = Field(description="Exchange or marketplace")
    currency: str = Field(description="Trading or quote currency")
    description: str = Field(default="", description="Descriptive instrument name")


class MarketListResponse(BaseModel):
    """Paginated collection of discoverable market instruments."""

    model_config = ConfigDict(frozen=True)

    items: list[MarketItemResponse] = Field(description="List of market instruments")
    total: int = Field(ge=0, description="Total number of items in list")
    limit: int = Field(default=100, ge=1, description="Pagination limit")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class OHLCVBarResponse(BaseModel):
    """Single discrete historical price and volume observation bar."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(description="Bar opening/observation timestamp in UTC")
    open: float = Field(gt=0.0, description="Opening price")
    high: float = Field(gt=0.0, description="Highest price")
    low: float = Field(gt=0.0, description="Lowest price")
    close: float = Field(gt=0.0, description="Closing price")
    volume: float = Field(ge=0.0, description="Traded volume")


class MarketDataResponse(BaseModel):
    """Time-series market data response."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    interval: str = Field(description="Bar observation interval (e.g. 1d, 1h)")
    start: datetime = Field(description="Start query bound (UTC)")
    end: datetime = Field(description="End query bound (UTC)")
    count: int = Field(ge=0, description="Number of bars returned in this page")
    total: int = Field(ge=0, description="Total matching observations")
    items: list[OHLCVBarResponse] = Field(description="Chronologically sorted OHLCV records")


# =============================================================================
# Regime Intelligence Responses (V16 Commit 02)
# =============================================================================


class FeatureStatisticDTO(BaseModel):
    """Descriptive statistics for a single feature within a regime."""

    model_config = ConfigDict(frozen=True)

    feature_name: str = Field(description="Feature variable identifier")
    observation_count: int = Field(ge=0, description="Count of observations")
    mean: float | None = Field(default=None, description="Arithmetic mean")
    median: float | None = Field(default=None, description="Median value")
    std: float | None = Field(default=None, description="Sample standard deviation (ddof=1)")
    min: float | None = Field(default=None, description="Minimum observed value")
    max: float | None = Field(default=None, description="Maximum observed value")


class RegimeProfileDTO(BaseModel):
    """Descriptive profile for a single canonical market regime."""

    model_config = ConfigDict(frozen=True)

    regime_id: int = Field(ge=0, description="Canonical regime identifier")
    regime_label: str = Field(description="Canonical regime label")
    observation_count: int = Field(ge=0, description="Number of observations in this regime")
    frequency: float = Field(ge=0.0, le=1.0, description="Empirical occurrence frequency")
    percentage: float = Field(ge=0.0, le=100.0, description="Occurrence percentage")
    first_seen: datetime | None = Field(default=None, description="Earliest UTC timestamp observed")
    last_seen: datetime | None = Field(default=None, description="Latest UTC timestamp observed")
    run_count: int = Field(ge=0, description="Contiguous runs / spells in this regime")
    average_duration: float = Field(ge=0.0, description="Mean duration in observation bars")
    median_duration: float = Field(ge=0.0, description="Median duration in observation bars")
    min_duration: int = Field(ge=0, description="Minimum duration in observation bars")
    max_duration: int = Field(ge=0, description="Maximum duration in observation bars")
    feature_statistics: dict[str, FeatureStatisticDTO] = Field(
        default_factory=dict, description="Feature distribution statistics"
    )


class CurrentRegimeContextDTO(BaseModel):
    """Point-in-time context for the active/current market regime."""

    model_config = ConfigDict(frozen=True)

    current_regime_id: int = Field(ge=0, description="Active regime identifier")
    current_regime_label: str = Field(description="Active regime label")
    current_timestamp: datetime = Field(description="UTC timestamp of the latest observation")
    observations_in_current_run: int = Field(
        ge=1, description="Consecutive bars in active trailing spell"
    )
    historical_frequency: float = Field(
        ge=0.0, le=1.0, description="Historical empirical frequency"
    )
    historical_average_duration: float = Field(ge=0.0, description="Historical mean spell duration")
    historical_max_duration: int = Field(ge=0, description="Historical maximum spell duration")
    historical_min_duration: int = Field(ge=0, description="Historical minimum spell duration")
    historical_run_count: int = Field(ge=0, description="Total historical runs of this regime")
    current_features: dict[str, float | None] | None = Field(
        default=None, description="Feature values at current observation"
    )


class MarketRegimeResponse(BaseModel):
    """Regime intelligence summary response for an instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    current_regime: int = Field(ge=0, description="Active canonical regime index")
    current_regime_label: str = Field(description="Active canonical regime label")
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Regime classification confidence"
    )
    current_context: CurrentRegimeContextDTO = Field(
        description="Active regime point-in-time context"
    )
    profile: RegimeProfileDTO | None = Field(
        default=None, description="Profile of the currently active regime"
    )
    profiles: dict[int, RegimeProfileDTO] = Field(
        default_factory=dict, description="Profiles for all identified regimes"
    )
    statistics: dict[str, FeatureStatisticDTO] = Field(
        default_factory=dict, description="Feature statistics of the currently active regime"
    )
    regimes_observed: list[int] = Field(
        default_factory=list, description="Sorted list of observed canonical regime IDs"
    )
    total_observations: int = Field(ge=0, description="Total observations analyzed")
    model_name: str | None = Field(default=None, description="Name of the detecting model")
    model_version: str | None = Field(default=None, description="Version of the detecting model")
    algorithm: str | None = Field(default=None, description="Algorithm identifier")
    analysis_start: datetime | None = Field(
        default=None, description="Earliest timestamp in analysis window"
    )
    analysis_end: datetime | None = Field(
        default=None, description="Latest timestamp in analysis window"
    )


# =============================================================================
# Transition Analytics Responses (V16 Commit 02)
# =============================================================================


class RankedDestinationDTO(BaseModel):
    """Destination regime ranking by empirical transition probability."""

    model_config = ConfigDict(frozen=True)

    target_regime: int = Field(ge=0, description="Destination canonical regime ID")
    target_label: str = Field(description="Destination canonical regime label")
    probability: float = Field(
        ge=0.0, le=1.0, description="Empirical transition probability P(source -> target)"
    )
    count: int = Field(ge=0, description="Observed transition count")
    rank: int = Field(ge=1, description="Deterministic 1-indexed destination rank")


class TransitionRegimeAnalyticsDTO(BaseModel):
    """Detailed transition analytics for a single market regime."""

    model_config = ConfigDict(frozen=True)

    regime_id: int = Field(ge=0, description="Canonical regime identifier")
    regime_label: str = Field(description="Canonical regime label")
    outgoing_transition_count: int = Field(ge=0, description="Total outgoing transitions")
    incoming_transition_count: int = Field(ge=0, description="Total incoming transitions")
    self_transition_count: int = Field(ge=0, description="Persistence self-transitions (i -> i)")
    regime_change_count: int = Field(ge=0, description="Regime changes (i -> j, j != i)")
    persistence_probability: float = Field(
        ge=0.0, le=1.0, description="Empirical persistence probability"
    )
    change_rate: float = Field(
        ge=0.0, le=1.0, description="Proportion of transitions that are changes"
    )
    most_likely_destination: int | None = Field(
        default=None, description="Most probable destination regime ID"
    )
    most_likely_destination_probability: float = Field(
        ge=0.0, le=1.0, description="Probability of most likely destination"
    )
    destination_count: int = Field(ge=0, description="Distinct target regimes reached")
    source_count: int = Field(ge=0, description="Distinct source regimes entering this regime")
    transition_entropy: float = Field(ge=0.0, description="Shannon transition entropy (nats)")
    rankings: list[RankedDestinationDTO] = Field(
        default_factory=list, description="Deterministically ranked destination regimes"
    )


class GlobalTransitionAnalyticsDTO(BaseModel):
    """Aggregate global transition statistics across the analyzed sequence."""

    model_config = ConfigDict(frozen=True)

    total_observations: int = Field(ge=0, description="Total observations analyzed")
    total_consecutive_transitions: int = Field(ge=0, description="Total step transitions evaluated")
    total_regime_changes: int = Field(ge=0, description="Total regime shift transitions")
    total_self_transitions: int = Field(ge=0, description="Total regime persistence transitions")
    global_change_rate: float = Field(ge=0.0, le=1.0, description="Sequence-wide change rate")
    global_persistence_rate: float = Field(
        ge=0.0, le=1.0, description="Sequence-wide persistence rate"
    )
    number_of_regimes: int = Field(ge=1, description="Number of regimes in universe")
    number_of_observed_transition_edges: int = Field(
        ge=0, description="Count of distinct directed transition edges observed"
    )


class TransitionProbabilityDTO(BaseModel):
    """Pairwise empirical transition probability and sample count."""

    model_config = ConfigDict(frozen=True)

    source_regime: int = Field(ge=0, description="Source regime identifier")
    target_regime: int = Field(ge=0, description="Target regime identifier")
    count: int = Field(ge=0, description="Observed transition count")
    total_transitions_from_source: int = Field(ge=0, description="Sample size from source")
    probability: float = Field(
        ge=0.0, le=1.0, description="Transition probability P(source -> target)"
    )


class MarketTransitionResponse(BaseModel):
    """Empirical transition analytics response for an instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    regimes: list[int] = Field(description="Canonical regime identifiers in matrix")
    probability_matrix: list[list[float]] = Field(
        description="2D empirical transition probability matrix"
    )
    count_matrix: list[list[int]] = Field(description="2D transition observation count matrix")
    regime_change_counts: list[list[int]] = Field(
        description="Transition count matrix with diagonal zeroed out (shifts only)"
    )
    regime_change_probabilities: list[list[float]] = Field(
        description="Conditional shift probabilities excluding self-transitions"
    )
    regime_analytics: dict[int, TransitionRegimeAnalyticsDTO] = Field(
        description="Per-regime transition metrics"
    )
    global_analytics: GlobalTransitionAnalyticsDTO = Field(
        description="Sequence-wide global transition statistics"
    )
    probabilities: list[TransitionProbabilityDTO] = Field(
        default_factory=list, description="Flat list of pairwise transition probabilities"
    )


# =============================================================================
# Portfolio Risk Analytics Responses (V13 / V20)
# =============================================================================


class ReturnStatisticsDTO(BaseModel):
    """Descriptive summary statistics of discrete returns."""

    model_config = ConfigDict(frozen=True)

    mean_return: float = Field(description="Sample arithmetic mean of returns")
    median_return: float = Field(description="Sample median of returns")
    standard_deviation: float = Field(description="Sample standard deviation (ddof=1)")
    minimum_return: float = Field(description="Minimum return observed")
    maximum_return: float = Field(description="Maximum return observed")
    observation_count: int = Field(description="Total observations analyzed")


class VolatilityMetricsDTO(BaseModel):
    """Realized and annualized volatility metrics."""

    model_config = ConfigDict(frozen=True)

    period_volatility: float = Field(
        description="Realized sample standard deviation of period returns"
    )
    annualized_volatility: float | None = Field(
        default=None, description="Annualized volatility scaled by sqrt(periods_per_year)"
    )
    periods_per_year: float | None = Field(
        default=None, description="Explicit annualization factor disclosed"
    )


class DownsideRiskMetricsDTO(BaseModel):
    """Downside deviation and semi-variance relative to target return."""

    model_config = ConfigDict(frozen=True)

    downside_deviation: float = Field(
        description="Root-mean-square downside deviation below target"
    )
    semi_variance: float = Field(description="Mean squared downside deviation below target")
    target_return: float = Field(default=0.0, description="Minimum acceptable return benchmark")
    observation_count: int = Field(description="Total returns evaluated")
    downside_observation_count: int = Field(
        description="Observations falling strictly below target"
    )


class DrawdownMetricsDTO(BaseModel):
    """Historical peak-to-trough maximum drawdown dynamics."""

    model_config = ConfigDict(frozen=True)

    max_drawdown: float = Field(
        description="Maximum drawdown value as a signed non-positive float (e.g. -0.176)"
    )
    drawdown_magnitude: float = Field(description="Absolute magnitude |max_drawdown| >= 0")
    peak_value: float = Field(description="Peak asset price preceding max drawdown")
    trough_value: float = Field(description="Trough price at lowest point of max drawdown")
    peak_timestamp: datetime | None = Field(default=None, description="Timestamp of the peak")
    trough_timestamp: datetime | None = Field(default=None, description="Timestamp of the trough")
    recovery_timestamp: datetime | None = Field(
        default=None, description="Timestamp of recovery to peak"
    )
    is_recovered: bool = Field(
        default=False, description="True if price recovered above prior peak"
    )


class VaRMetricsDTO(BaseModel):
    """Loss-oriented Value at Risk (VaR) metric."""

    model_config = ConfigDict(frozen=True)

    confidence_level: float = Field(description="Evaluated confidence level e.g. 0.95")
    var_loss: float = Field(description="Loss threshold expressed as positive loss e.g. 0.048")
    return_quantile: float = Field(
        description="Empirical return quantile (signed negative e.g. -0.048)"
    )
    method: str = Field(default="historical", description="Calculation method")
    tail_observations: int = Field(description="Number of observations at or below quantile")
    total_observations: int = Field(description="Total observations in sample")


class ExpectedShortfallMetricsDTO(BaseModel):
    """Loss-oriented Expected Shortfall (CVaR) conditional on exceeding VaR."""

    model_config = ConfigDict(frozen=True)

    confidence_level: float = Field(description="Evaluated confidence level e.g. 0.95")
    expected_shortfall: float = Field(
        description="Conditional expected loss expressed as positive float"
    )
    tail_mean_return: float = Field(
        description="Mean return of tail observations (signed negative)"
    )
    var_loss: float = Field(description="Corresponding VaR threshold")
    tail_observations: int = Field(description="Number of tail observations")
    total_observations: int = Field(description="Total observations in sample")


class RiskPricePointDTO(BaseModel):
    """Point-in-time price and drawdown observation for visualization."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(description="Observation timestamp (UTC)")
    price: float = Field(description="Historical asset price")
    period_return: float | None = Field(default=None, description="Period arithmetic return")
    running_peak: float = Field(description="Historical running peak up to this timestamp")
    drawdown: float = Field(description="Signed drawdown relative to running peak")


class MarketRiskResponse(BaseModel):
    """Complete portfolio risk intelligence response for a queried instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    series_id: str = Field(description="Risk evaluation series identifier")
    observation_count: int = Field(description="Total return observations analyzed")
    start_timestamp: datetime | None = Field(
        default=None, description="Start timestamp of risk sample"
    )
    end_timestamp: datetime | None = Field(default=None, description="End timestamp of risk sample")
    computed_at: datetime = Field(description="UTC timestamp when analytics were evaluated")
    return_statistics: ReturnStatisticsDTO = Field(description="Return descriptive statistics")
    volatility: VolatilityMetricsDTO = Field(description="Volatility analytics")
    downside_risk: DownsideRiskMetricsDTO = Field(
        description="Downside deviation and semi-variance"
    )
    drawdown: DrawdownMetricsDTO = Field(description="Peak-to-trough maximum drawdown metrics")
    var_metrics: dict[str, VaRMetricsDTO] = Field(
        description="Value at Risk mapped by confidence level string e.g. '0.90', '0.95', '0.99'"
    )
    expected_shortfall_metrics: dict[str, ExpectedShortfallMetricsDTO] = Field(
        description="Expected Shortfall mapped by confidence level string"
    )
    price_points: list[RiskPricePointDTO] = Field(
        default_factory=list, description="Historical price and drawdown series for chart rendering"
    )


# =============================================================================
# Systematic Backtesting Responses (V14 / V15 / V20)
# =============================================================================


class EquitySnapshotDTO(BaseModel):
    """Point-in-time snapshot of backtest equity curve."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(description="Snapshot timestamp (UTC)")
    cash: float = Field(description="Cash balance")
    market_value: float = Field(description="Marked-to-market position value")
    equity: float = Field(description="Total portfolio equity (cash + market_value)")
    fees: float = Field(default=0.0, description="Cumulative execution commissions and fees")
    realized_pnl: float = Field(default=0.0, description="Cumulative realized profit/loss")
    unrealized_pnl: float = Field(default=0.0, description="Open mark-to-market profit/loss")
    drawdown: float = Field(
        default=0.0, description="Signed point-in-time drawdown from running peak"
    )


class TradeStatisticsDTO(BaseModel):
    """Descriptive trade execution statistics."""

    model_config = ConfigDict(frozen=True)

    order_count: int = Field(description="Total orders requested")
    fill_count: int = Field(description="Total order fills executed")
    completed_trade_count: int = Field(description="Total position exits realizing PnL")
    winning_trades: int = Field(description="Number of profitable closed trades")
    losing_trades: int = Field(description="Number of loss-making closed trades")
    win_rate: float | None = Field(default=None, description="Winning trades / completed trades")
    total_realized_pnl: float = Field(default=0.0, description="Cumulative realized PnL")
    average_trade_pnl: float | None = Field(
        default=None, description="Average PnL per completed trade"
    )
    largest_winning_trade: float | None = Field(
        default=None, description="Largest single winning trade"
    )
    largest_losing_trade: float | None = Field(
        default=None, description="Largest single losing trade"
    )


class BacktestTradeDTO(BaseModel):
    """Executed trade fill record."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(description="Execution fill timestamp (UTC)")
    symbol: str = Field(description="Instrument symbol")
    side: str = Field(description="Order side: BUY or SELL")
    quantity: float = Field(description="Filled share quantity")
    price: float = Field(description="Execution price")
    commission: float = Field(description="Commission paid")
    slippage: float = Field(description="Slippage cost applied")


class BacktestRiskMetricsDTO(BaseModel):
    """Risk analytics evaluated on the backtest equity curve."""

    model_config = ConfigDict(frozen=True)

    volatility: float = Field(description="Sample standard deviation of equity curve returns")
    annualized_volatility: float | None = Field(
        default=None, description="Annualized equity volatility"
    )
    maximum_drawdown: float = Field(description="Maximum peak-to-trough drawdown (signed <= 0)")
    drawdown_magnitude: float = Field(description="Drawdown magnitude |max_drawdown|")
    var_95: float | None = Field(default=None, description="Loss-oriented VaR at 95% confidence")
    expected_shortfall_95: float | None = Field(
        default=None, description="Loss-oriented ES at 95% confidence"
    )


class MethodologyDTO(BaseModel):
    """Documentation of quantitative assumptions and rules."""

    model_config = ConfigDict(frozen=True)

    common_period_policy: str = Field(description="Policy for evaluation window")
    trade_definition: str = Field(description="Definition of completed trade")
    risk_engine_source: str = Field(description="Risk calculation engine")
    return_type: str = Field(description="Return compounding convention")
    execution_engine_source: str = Field(description="Execution simulator")


class MetricDefinitionDTO(BaseModel):
    """Machine-readable definition of a reported performance metric."""

    model_config = ConfigDict(frozen=True)

    metric_name: str = Field(description="Canonical metric key")
    description: str = Field(description="Functional definition")
    unit: str = Field(description="Unit of measurement")
    direction_semantics: str = Field(description="Directional interpretation guidance")
    source: str = Field(description="Originating engine or component")


class PerformanceReportDTO(BaseModel):
    """Self-contained reproducible performance report metadata."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(description="Deterministic report unique identifier")
    report_version: str = Field(description="Report schema version")
    generated_at: datetime | None = Field(default=None, description="UTC generation timestamp")
    methodology: MethodologyDTO = Field(description="Quantitative methodology")
    limitations: list[str] = Field(
        default_factory=list, description="Explicit caveats and analytical scope"
    )
    metric_definitions: list[MetricDefinitionDTO] = Field(
        default_factory=list, description="Canonical metric definitions"
    )


class MarketBacktestResponse(BaseModel):
    """Complete systematic backtesting simulation response."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    strategy_id: str = Field(description="Evaluated strategy identifier")
    strategy_name: str = Field(description="Human-readable strategy name")
    execution_convention: str = Field(
        description="Execution timing convention: CURRENT_CLOSE or NEXT_OPEN"
    )
    initial_cash: float = Field(description="Starting capital")
    final_cash: float = Field(description="Ending unallocated cash balance")
    final_equity: float = Field(description="Ending total portfolio equity")
    total_return: float = Field(description="Cumulative return over simulation")
    annualized_return: float | None = Field(
        default=None, description="Compound annual growth rate (CAGR)"
    )
    absolute_pnl: float = Field(description="Net wealth change: final_equity - initial_cash")
    realized_pnl: float = Field(description="Gross realized profit or loss from completed exits")
    unrealized_pnl: float = Field(description="Open position marked-to-market profit or loss")
    total_fees: float = Field(description="Total execution fees and commissions incurred")
    slippage_rate: float = Field(description="Configured slippage rate")
    commission_rate: float = Field(description="Configured commission rate")
    trades: TradeStatisticsDTO = Field(description="Execution trade statistics")
    risk_metrics: BacktestRiskMetricsDTO = Field(
        description="Risk metrics evaluated on equity curve"
    )
    equity_curve: list[EquitySnapshotDTO] = Field(description="Sequential equity curve snapshots")
    executed_trades: list[BacktestTradeDTO] = Field(
        default_factory=list, description="Executed trade fills"
    )
    report: PerformanceReportDTO = Field(description="Deterministic performance report metadata")


# =============================================================================
# Authentication Request & Response Models (V17 Commit 01)
# =============================================================================


class UserResponse(BaseModel):
    """Public representation of an authenticated user identity."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(description="Unique user primary identifier")
    email: str = Field(description="Canonical normalized user email")
    is_active: bool = Field(description="Account active status")
    created_at: datetime = Field(description="Account creation timestamp (UTC)")


class RegisterRequest(BaseModel):
    """User account registration payload."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(description="User email address")
    password: str = Field(min_length=12, description="User password (minimum 12 characters)")


class RegisterResponse(BaseModel):
    """Response returned upon successful user account registration."""

    model_config = ConfigDict(frozen=True)

    user: UserResponse = Field(description="Newly created user account identity")


class LoginRequest(BaseModel):
    """User login credential payload."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(description="User email address")
    password: str = Field(description="User password")


class LoginResponse(BaseModel):
    """Response returned upon successful authentication containing access token."""

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(description="Signed JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserResponse = Field(description="Authenticated user identity")


# =============================================================================
# AI Research Assistant Models (V21)
# =============================================================================


class ResearchQueryRequest(BaseModel):
    """Query payload submitted to the AI quantitative research assistant."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language market research question",
    )
    symbol: str | None = Field(
        default=None,
        max_length=20,
        description="Optional target instrument ticker symbol",
    )
    conversation_id: str | None = Field(
        default=None,
        max_length=100,
        description="Optional client conversation tracking identifier",
    )
    context: dict[str, object] | None = Field(
        default=None,
        description="Optional contextual client state",
    )
    stream: bool = Field(
        default=False,
        description="Request response streamed via Server-Sent Events (SSE)",
    )


class CitationDTO(BaseModel):
    """Citation linking a quantitative assertion to its source EvidencePacket."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(
        ..., ge=1, description="Numeric citation marker matching in-text brackets, e.g. 1 for [1]"
    )
    source_id: str = Field(..., description="Referenced EvidencePacket source ID")
    source_type: str = Field(..., description="Domain source category")
    title: str = Field(..., description="Citation title")
    symbol: str | None = Field(default=None, description="Instrument ticker symbol")
    timestamp: str | None = Field(default=None, description="Evidence observation timestamp")
    model: str | None = Field(default=None, description="Model provenance or algorithm")
    facts_summary: str | None = Field(default=None, description="Brief summary of cited metrics")
    details: dict[str, object] = Field(
        default_factory=dict, description="Auditable metadata dictionary"
    )


class EvidencePacketDTO(BaseModel):
    """Verified factual evidence packet extracted from platform engines."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(..., description="Canonical source ID")
    source_type: str = Field(..., description="Domain source type")
    title: str = Field(..., description="Human-readable title")
    facts: dict[str, object] = Field(default_factory=dict, description="Verified factual values")
    timestamp: str | None = Field(default=None, description="Observation timestamp")
    metadata: dict[str, object] = Field(default_factory=dict, description="Technical metadata")


class ResearchResponseDTO(BaseModel):
    """Grounded AI research assistant response envelope."""

    model_config = ConfigDict(frozen=True)

    answer: str = Field(..., description="Grounded quantitative explanation")
    citations: list[CitationDTO] = Field(
        default_factory=list,
        description="Explicit citations backing factual assertions",
    )
    evidence: list[EvidencePacketDTO] = Field(
        default_factory=list,
        description="Audited evidence packets supplied for grounding",
    )
    model: str = Field(..., description="Provider or model that generated the answer")
    generated_at: str = Field(..., description="ISO 8601 UTC generation timestamp")
    request_id: str = Field(..., description="Request correlation identifier")
    intent: str = Field(..., description="Classified analytical intent")
    symbol: str | None = Field(default=None, description="Resolved instrument symbol")


__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "BacktestRiskMetricsDTO",
    "BacktestTradeDTO",
    "CitationDTO",
    "CurrentRegimeContextDTO",
    "DownsideRiskMetricsDTO",
    "DrawdownMetricsDTO",
    "EquitySnapshotDTO",
    "EvidencePacketDTO",
    "ExpectedShortfallMetricsDTO",
    "FeatureStatisticDTO",
    "GlobalTransitionAnalyticsDTO",
    "HealthResponse",
    "LoginRequest",
    "LoginResponse",
    "MarketBacktestResponse",
    "MarketDataResponse",
    "MarketItemResponse",
    "MarketListResponse",
    "MarketRegimeResponse",
    "MarketRiskResponse",
    "MarketTransitionResponse",
    "MethodologyDTO",
    "MetricDefinitionDTO",
    "OHLCVBarResponse",
    "PerformanceReportDTO",
    "RankedDestinationDTO",
    "ReadinessResponse",
    "RegimeProfileDTO",
    "RegisterRequest",
    "RegisterResponse",
    "ResearchQueryRequest",
    "ResearchResponseDTO",
    "ReturnStatisticsDTO",
    "RiskPricePointDTO",
    "RootResponse",
    "TradeStatisticsDTO",
    "TransitionProbabilityDTO",
    "TransitionRegimeAnalyticsDTO",
    "UserResponse",
    "VaRMetricsDTO",
    "VolatilityMetricsDTO",
]
