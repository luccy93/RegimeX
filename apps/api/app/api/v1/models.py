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


__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "CurrentRegimeContextDTO",
    "FeatureStatisticDTO",
    "GlobalTransitionAnalyticsDTO",
    "HealthResponse",
    "MarketDataResponse",
    "MarketItemResponse",
    "MarketListResponse",
    "MarketRegimeResponse",
    "MarketTransitionResponse",
    "OHLCVBarResponse",
    "RankedDestinationDTO",
    "ReadinessResponse",
    "RegimeProfileDTO",
    "RootResponse",
    "TransitionProbabilityDTO",
    "TransitionRegimeAnalyticsDTO",
]
