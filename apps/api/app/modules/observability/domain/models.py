"""
RegimeX Observability — Canonical Domain Models
================================================
Immutable snapshot representations for data health, provider health, pipeline
stages, model health, stability, and distribution drift.

Architectural Position:
- Pure domain layer: standard library and Pydantic v2 only.
- Immutable, frozen domain models with strict validation.
- All timestamps are timezone-aware (UTC).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.observability.domain.enums import (
    DriftMethod,
    HealthStatus,
    PipelineStage,
    ProviderStatus,
)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


# =============================================================================
# Data Health Snapshots
# =============================================================================


class DataFreshnessSnapshot(BaseModel):
    """
    Point-in-time observation freshness assessment accounting for exchange calendar.
    """

    model_config = {"frozen": True}

    latest_observation_time: datetime | None = Field(
        default=None,
        description="UTC timestamp of the latest available observation bar",
    )
    freshness_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Elapsed seconds between current time and latest observation",
    )
    market_open: bool = Field(
        default=False,
        description="Whether the market is currently in an open trading session",
    )
    calendar_id: str = Field(
        default="nyse",
        description="Exchange or trading calendar identifier used for evaluation",
    )
    status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Freshness health classification",
    )
    reason: str | None = Field(
        default=None,
        description="Human-readable explanation of freshness determination",
    )

    @field_validator("latest_observation_time", mode="before")
    @classmethod
    def require_tz_aware_observation(cls, v: datetime | None) -> datetime | None:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"latest_observation_time must be timezone-aware (got {v!r})")
        return v


class DataCompletenessSnapshot(BaseModel):
    """
    Assessment of expected versus received observations.
    """

    model_config = {"frozen": True}

    expected_rows: int = Field(ge=0, description="Expected observation count according to calendar")
    received_rows: int = Field(ge=0, description="Actual observation count received")
    missing_rows: int = Field(ge=0, description="Count of missing observation bars")
    duplicate_rows: int = Field(
        default=0, ge=0, description="Count of duplicate observation timestamps"
    )
    completeness_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of received valid rows to expected rows (clamped to [0.0, 1.0])",
    )
    status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Completeness health status",
    )


class DataValiditySnapshot(BaseModel):
    """
    Integrates results from the authoritative V06 data validation layer.
    """

    model_config = {"frozen": True}

    is_valid: bool = Field(description="True if data passed validation gates (PASS or WARN)")
    critical_issues_count: int = Field(ge=0, description="Count of critical validation violations")
    warning_issues_count: int = Field(ge=0, description="Count of non-fatal warnings")
    failed_rule_ids: tuple[str, ...] = Field(
        default=(),
        description="Distinct rule IDs triggering critical validation failures",
    )
    violations_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Histogram of detected issues across validation categories",
    )
    status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Validity health status",
    )


class ProviderHealthSnapshot(BaseModel):
    """
    Operational health of an upstream market data provider adapter.
    """

    model_config = {"frozen": True}

    provider_id: str = Field(description="Bounded snake_case provider identifier")
    status: ProviderStatus = Field(description="Provider operational availability status")
    request_count: int = Field(ge=0, description="Total requests issued to provider")
    success_count: int = Field(ge=0, description="Total successful provider responses")
    failure_count: int = Field(ge=0, description="Total failed provider responses")
    consecutive_failures: int = Field(ge=0, description="Consecutive failure streak")
    failure_rate: float = Field(ge=0.0, le=1.0, description="Fraction of failed requests")
    avg_latency_ms: float = Field(ge=0.0, description="Average request latency in milliseconds")
    last_successful_request: datetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent successful operation",
    )
    last_failure: datetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent failure",
    )
    last_error_category: str | None = Field(
        default=None,
        description="Bounded classification of the last failure error",
    )


class PipelineStageHealth(BaseModel):
    """
    Operational health for a discrete pipeline stage.
    """

    model_config = {"frozen": True}

    stage: PipelineStage = Field(description="Pipeline stage identifier")
    status: HealthStatus = Field(description="Operational health status of this stage")
    last_run: datetime | None = Field(
        default=None, description="UTC timestamp of last stage execution"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic stage metadata")


class PipelineHealthSnapshot(BaseModel):
    """
    Aggregate operational status across all pipeline stages.
    """

    model_config = {"frozen": True}

    stages: dict[str, PipelineStageHealth] = Field(
        default_factory=dict,
        description="Health by pipeline stage identifier",
    )
    overall_status: HealthStatus = Field(
        default=HealthStatus.HEALTHY,
        description="Consolidated pipeline health status",
    )


class DataHealthSnapshot(BaseModel):
    """
    Comprehensive immutable snapshot of market data health for an instrument or feed.
    """

    model_config = {"frozen": True}

    symbol: str = Field(description="Market instrument symbol (e.g. 'SPY')")
    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when this health snapshot was evaluated",
    )
    status: HealthStatus = Field(description="Overall consolidated data health status")
    freshness: DataFreshnessSnapshot
    completeness: DataCompletenessSnapshot
    validity: DataValiditySnapshot
    provider: ProviderHealthSnapshot | None = None
    pipeline: PipelineHealthSnapshot | None = None
    summary: str = Field(default="", description="Descriptive human-readable summary")


# =============================================================================
# Model Health Snapshots
# =============================================================================


class PredictionValiditySnapshot(BaseModel):
    """
    Mathematical validity check of regime model predictions.
    """

    model_config = {"frozen": True}

    total_predictions: int = Field(ge=0, description="Number of prediction points evaluated")
    valid_predictions: int = Field(
        ge=0, description="Number of valid predictions meeting all invariants"
    )
    invalid_predictions: int = Field(ge=0, description="Count of invalid predictions")
    invalid_regime_ids: int = Field(
        ge=0, description="Predictions with invalid or out-of-range regime IDs"
    )
    non_finite_values: int = Field(ge=0, description="Occurrences of NaN or Inf in outputs")
    invalid_probability_vectors: int = Field(
        ge=0,
        description="Probability vectors violating [0, 1] range or unity sum",
    )
    status: HealthStatus = Field(description="Prediction validity health status")
    violations: tuple[str, ...] = Field(default=(), description="Explanatory violation notices")


class ModelExecutionSnapshot(BaseModel):
    """
    Model execution telemetry and failure tracking.
    """

    model_config = {"frozen": True}

    prediction_count: int = Field(ge=0, description="Total prediction invocations")
    failure_count: int = Field(ge=0, description="Failed model execution attempts")
    failure_rate: float = Field(ge=0.0, le=1.0, description="Model execution failure rate")
    avg_latency_ms: float = Field(ge=0.0, description="Average execution latency in milliseconds")
    status: HealthStatus = Field(description="Execution health status")


class ModelConfidenceSnapshot(BaseModel):
    """
    Operational health of model confidence and consensus metrics.
    """

    model_config = {"frozen": True}

    mean_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean confidence across evaluated window",
    )
    min_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence observation",
    )
    max_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum confidence observation",
    )
    std_confidence: float | None = Field(
        default=None,
        ge=0.0,
        description="Sample standard deviation of confidence",
    )
    low_confidence_count: int = Field(
        default=0,
        ge=0,
        description="Count of predictions below low-confidence threshold",
    )
    low_confidence_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of low-confidence predictions to total predictions",
    )
    missing_confidence_count: int = Field(
        default=0,
        ge=0,
        description="Count of predictions lacking confidence scores",
    )
    status: HealthStatus = Field(description="Confidence health status")


class ModelStabilitySnapshot(BaseModel):
    """
    Operational stability metrics for regime sequence persistence.
    """

    model_config = {"frozen": True}

    regime_switching_frequency: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction of bar-to-bar observations where regime state changed",
    )
    consecutive_stable_bars: int = Field(
        ge=0,
        description="Length of longest consecutive run without a regime switch",
    )
    confidence_variability: float = Field(
        ge=0.0,
        description="Variability / standard deviation of confidence over window",
    )
    status: HealthStatus = Field(description="Stability health status")


class RegimeDistributionSnapshot(BaseModel):
    """
    Descriptive empirical regime distribution over an observation window.
    """

    model_config = {"frozen": True}

    sample_count: int = Field(ge=0, description="Total observations in the evaluated distribution")
    regime_counts: dict[int, int] = Field(
        default_factory=dict,
        description="Frequency count per canonical regime ID",
    )
    regime_percentages: dict[int, float] = Field(
        default_factory=dict,
        description="Percentage of observations per canonical regime ID",
    )
    entropy: float = Field(
        default=0.0,
        ge=0.0,
        description="Shannon entropy of the empirical regime distribution in nats",
    )


class DistributionDriftSnapshot(BaseModel):
    """
    Quantifies statistical divergence between comparison and reference distributions.
    """

    model_config = {"frozen": True}

    metric_name: str = Field(description="Distribution evaluated ('regime_output' or feature name)")
    method: DriftMethod = Field(description="Statistical divergence metric employed")
    drift_score: float = Field(ge=0.0, description="Computed divergence statistic")
    threshold: float = Field(ge=0.0, description="Configured drift detection threshold")
    is_drift_detected: bool = Field(description="True if drift_score exceeds threshold")
    reference_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Reference population probabilities or binned frequencies",
    )
    comparison_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Comparison population probabilities or binned frequencies",
    )
    status: HealthStatus = Field(description="Drift classification status")


class ModelHealthSnapshot(BaseModel):
    """
    Comprehensive immutable snapshot of model health for a regime detector or ensemble.
    """

    model_config = {"frozen": True}

    model_id: str = Field(description="Model or algorithm identifier (e.g. 'kmeans', 'ensemble')")
    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when health was evaluated",
    )
    status: HealthStatus = Field(description="Overall consolidated model health status")
    validity: PredictionValiditySnapshot
    execution: ModelExecutionSnapshot
    confidence: ModelConfidenceSnapshot
    stability: ModelStabilitySnapshot
    regime_distribution: RegimeDistributionSnapshot
    drift: DistributionDriftSnapshot | None = None
    summary: str = Field(default="", description="Descriptive operational summary")


# =============================================================================
# System-Level Summary Snapshot
# =============================================================================


class SystemHealthSummarySnapshot(BaseModel):
    """
    High-level platform operational health summary uniting data, models, and providers.
    """

    model_config = {"frozen": True}

    status: HealthStatus = Field(description="Consolidated system health status")
    timestamp: datetime = Field(default_factory=_utc_now, description="Evaluation UTC timestamp")
    data_health_status: HealthStatus = Field(description="Consolidated market data health")
    model_health_status: HealthStatus = Field(description="Consolidated regime model health")
    provider_status: ProviderStatus = Field(description="Consolidated upstream provider status")
    pipeline_status: HealthStatus = Field(description="Consolidated pipeline status")
    active_models: tuple[str, ...] = Field(default=(), description="Monitored model identifiers")
    active_providers: tuple[str, ...] = Field(
        default=(), description="Monitored provider identifiers"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Summary details and highlights"
    )
