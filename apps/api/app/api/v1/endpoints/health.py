"""
RegimeX API — Health & Observability Endpoints
==============================================
Provides liveness, readiness, and comprehensive data/model operational health probes.

Architectural Guarantees:
- Endpoints remain lightweight: zero retraining, zero backtests, zero network downloads.
- Exposes typed DTO contracts conforming to API schema standards.
- Preserves backward compatibility with existing /live and /ready endpoints.
- No internal stack traces, API keys, or infrastructure credentials leaked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Path, Response
from pydantic import BaseModel

from app.api.v1.models import (
    DataCompletenessDTO,
    DataFreshnessDTO,
    DataHealthListResponseDTO,
    DataHealthResponseDTO,
    DataValidityDTO,
    DistributionDriftDTO,
    ModelConfidenceDTO,
    ModelExecutionDTO,
    ModelHealthListResponseDTO,
    ModelHealthResponseDTO,
    ModelStabilityDTO,
    PipelineHealthDTO,
    PipelineStageHealthDTO,
    PredictionValidityDTO,
    ProviderHealthDTO,
    ProviderHealthListResponseDTO,
    RegimeDistributionDTO,
    SystemHealthSummaryResponseDTO,
)
from app.core.dependencies import HealthMonitoringServiceDep
from app.core.errors import NotFoundError
from app.modules.observability.domain.models import (
    DataHealthSnapshot,
    ModelHealthSnapshot,
    PipelineHealthSnapshot,
    ProviderHealthSnapshot,
)
from app.modules.observability.infrastructure.metrics import metrics

router = APIRouter(prefix="/health", tags=["Health"])


# =============================================================================
# Legacy Probes Response Schemas
# =============================================================================


class LivenessResponse(BaseModel):
    """Response payload for the liveness probe."""

    status: str
    timestamp: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Response payload for the readiness probe."""

    status: str
    timestamp: str
    checks: dict[str, str]


# =============================================================================
# DTO Converters
# =============================================================================


def _to_provider_dto(snap: ProviderHealthSnapshot) -> ProviderHealthDTO:
    return ProviderHealthDTO(
        provider_id=snap.provider_id,
        status=snap.status.value,
        request_count=snap.request_count,
        success_count=snap.success_count,
        failure_count=snap.failure_count,
        consecutive_failures=snap.consecutive_failures,
        failure_rate=snap.failure_rate,
        avg_latency_ms=snap.avg_latency_ms,
        last_successful_request=snap.last_successful_request.isoformat()
        if snap.last_successful_request
        else None,
        last_failure=snap.last_failure.isoformat() if snap.last_failure else None,
        last_error_category=snap.last_error_category,
    )


def _to_pipeline_dto(snap: PipelineHealthSnapshot) -> PipelineHealthDTO:
    stages_dto = {
        k: PipelineStageHealthDTO(
            stage=v.stage.value,
            status=v.status.value,
            last_run=v.last_run.isoformat() if v.last_run else None,
            details=v.details,
        )
        for k, v in snap.stages.items()
    }
    return PipelineHealthDTO(
        overall_status=snap.overall_status.value,
        stages=stages_dto,
    )


def _to_data_health_dto(snap: DataHealthSnapshot) -> DataHealthResponseDTO:
    fresh_dto = DataFreshnessDTO(
        latest_observation_time=snap.freshness.latest_observation_time.isoformat()
        if snap.freshness.latest_observation_time
        else None,
        freshness_seconds=snap.freshness.freshness_seconds,
        market_open=snap.freshness.market_open,
        calendar_id=snap.freshness.calendar_id,
        status=snap.freshness.status.value,
        reason=snap.freshness.reason,
    )
    comp_dto = DataCompletenessDTO(
        expected_rows=snap.completeness.expected_rows,
        received_rows=snap.completeness.received_rows,
        missing_rows=snap.completeness.missing_rows,
        duplicate_rows=snap.completeness.duplicate_rows,
        completeness_ratio=snap.completeness.completeness_ratio,
        status=snap.completeness.status.value,
    )
    val_dto = DataValidityDTO(
        is_valid=snap.validity.is_valid,
        critical_issues_count=snap.validity.critical_issues_count,
        warning_issues_count=snap.validity.warning_issues_count,
        failed_rule_ids=list(snap.validity.failed_rule_ids),
        violations_by_category=snap.validity.violations_by_category,
        status=snap.validity.status.value,
    )
    prov_dto = _to_provider_dto(snap.provider) if snap.provider else None
    pipe_dto = _to_pipeline_dto(snap.pipeline) if snap.pipeline else None

    return DataHealthResponseDTO(
        symbol=snap.symbol,
        timestamp=snap.timestamp.isoformat(),
        status=snap.status.value,
        freshness=fresh_dto,
        completeness=comp_dto,
        validity=val_dto,
        provider=prov_dto,
        pipeline=pipe_dto,
        summary=snap.summary,
    )


def _to_model_health_dto(snap: ModelHealthSnapshot) -> ModelHealthResponseDTO:
    val_dto = PredictionValidityDTO(
        total_predictions=snap.validity.total_predictions,
        valid_predictions=snap.validity.valid_predictions,
        invalid_predictions=snap.validity.invalid_predictions,
        invalid_regime_ids=snap.validity.invalid_regime_ids,
        non_finite_values=snap.validity.non_finite_values,
        invalid_probability_vectors=snap.validity.invalid_probability_vectors,
        status=snap.validity.status.value,
        violations=list(snap.validity.violations),
    )
    exec_dto = ModelExecutionDTO(
        prediction_count=snap.execution.prediction_count,
        failure_count=snap.execution.failure_count,
        failure_rate=snap.execution.failure_rate,
        avg_latency_ms=snap.execution.avg_latency_ms,
        status=snap.execution.status.value,
    )
    conf_dto = ModelConfidenceDTO(
        mean_confidence=snap.confidence.mean_confidence,
        min_confidence=snap.confidence.min_confidence,
        max_confidence=snap.confidence.max_confidence,
        std_confidence=snap.confidence.std_confidence,
        low_confidence_count=snap.confidence.low_confidence_count,
        low_confidence_ratio=snap.confidence.low_confidence_ratio,
        missing_confidence_count=snap.confidence.missing_confidence_count,
        status=snap.confidence.status.value,
    )
    stab_dto = ModelStabilityDTO(
        regime_switching_frequency=snap.stability.regime_switching_frequency,
        consecutive_stable_bars=snap.stability.consecutive_stable_bars,
        confidence_variability=snap.stability.confidence_variability,
        status=snap.stability.status.value,
    )
    reg_dist_dto = RegimeDistributionDTO(
        sample_count=snap.regime_distribution.sample_count,
        regime_counts={str(k): v for k, v in snap.regime_distribution.regime_counts.items()},
        regime_percentages={
            str(k): v for k, v in snap.regime_distribution.regime_percentages.items()
        },
        entropy=snap.regime_distribution.entropy,
    )
    drift_dto = None
    if snap.drift:
        drift_dto = DistributionDriftDTO(
            metric_name=snap.drift.metric_name,
            method=snap.drift.method.value,
            drift_score=snap.drift.drift_score,
            threshold=snap.drift.threshold,
            is_drift_detected=snap.drift.is_drift_detected,
            reference_distribution=snap.drift.reference_distribution,
            comparison_distribution=snap.drift.comparison_distribution,
            status=snap.drift.status.value,
        )

    return ModelHealthResponseDTO(
        model_id=snap.model_id,
        timestamp=snap.timestamp.isoformat(),
        status=snap.status.value,
        validity=val_dto,
        execution=exec_dto,
        confidence=conf_dto,
        stability=stab_dto,
        regime_distribution=reg_dist_dto,
        drift=drift_dto,
        summary=snap.summary,
    )


# =============================================================================
# Legacy Endpoints (Process Liveness & Readiness Probes)
# =============================================================================


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Returns HTTP 200 if the RegimeX API process is alive.",
)
async def liveness() -> LivenessResponse:
    from app.core.config import get_settings

    settings = get_settings()
    return LivenessResponse(
        status="ok",
        timestamp=datetime.now(tz=UTC).isoformat(),
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns HTTP 200 when all required dependencies are reachable.",
)
async def readiness() -> ReadinessResponse:
    return ReadinessResponse(
        status="ready",
        timestamp=datetime.now(tz=UTC).isoformat(),
        checks={"api": "ok"},
    )


# =============================================================================
# Operational Health Endpoints (V23 Commit 02)
# =============================================================================


@router.get(
    "/summary",
    response_model=SystemHealthSummaryResponseDTO,
    summary="System Operational Health Summary",
    description=(
        "Returns the consolidated operational health summary for RegimeX, "
        "including market data health, regime model health, upstream providers, and pipelines."
    ),
)
async def get_system_health_summary(
    service: HealthMonitoringServiceDep,
) -> SystemHealthSummaryResponseDTO:
    summary_snap = service.get_system_summary()
    return SystemHealthSummaryResponseDTO(
        status=summary_snap.status.value,
        timestamp=summary_snap.timestamp.isoformat(),
        components={
            "market_data": {"status": summary_snap.data_health_status.value},
            "validation": {"status": summary_snap.data_health_status.value},
            "models": {"status": summary_snap.model_health_status.value},
            "providers": {"status": summary_snap.provider_status.value},
            "pipeline": {"status": summary_snap.pipeline_status.value},
        },
        active_models=list(summary_snap.active_models),
        active_providers=list(summary_snap.active_providers),
        details=summary_snap.details,
    )


@router.get(
    "/data",
    response_model=DataHealthListResponseDTO,
    summary="List Market Data Health Snapshots",
    description="Returns current operational health for all monitored instrument feeds.",
)
async def list_data_health(
    service: HealthMonitoringServiceDep,
) -> DataHealthListResponseDTO:
    snapshots = service.list_all_data_health()
    items = [_to_data_health_dto(s) for s in snapshots]
    return DataHealthListResponseDTO(items=items, total=len(items))


@router.get(
    "/data/{symbol}",
    response_model=DataHealthResponseDTO,
    summary="Get Market Data Health by Symbol",
    description="Returns operational data freshness, completeness, and validity for a symbol.",
)
async def get_data_health_by_symbol(
    symbol: Annotated[str, Path(description="Instrument ticker symbol, e.g. 'SPY'")],
    service: HealthMonitoringServiceDep,
) -> DataHealthResponseDTO:
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise NotFoundError("Symbol cannot be empty.")
    snapshot = service.get_data_health(clean_sym)
    return _to_data_health_dto(snapshot)


@router.get(
    "/models",
    response_model=ModelHealthListResponseDTO,
    summary="List Regime Models Health Snapshots",
    description=(
        "Returns prediction validity, execution health, confidence, stability, "
        "and drift for all models."
    ),
)
async def list_models_health(
    service: HealthMonitoringServiceDep,
) -> ModelHealthListResponseDTO:
    snapshots = service.list_all_model_health()
    items = [_to_model_health_dto(s) for s in snapshots]
    return ModelHealthListResponseDTO(items=items, total=len(items))


@router.get(
    "/models/{model_id}",
    response_model=ModelHealthResponseDTO,
    summary="Get Regime Model Health by Identifier",
    description=(
        "Returns comprehensive health metrics for a specific model (kmeans, gmm, hmm, ensemble)."
    ),
)
async def get_model_health_by_id(
    model_id: Annotated[str, Path(description="Model identifier, e.g. 'kmeans' or 'ensemble'")],
    service: HealthMonitoringServiceDep,
) -> ModelHealthResponseDTO:
    clean_id = model_id.strip().lower()
    if not clean_id:
        raise NotFoundError("model_id cannot be empty.")
    snapshot = service.get_model_health(clean_id)
    return _to_model_health_dto(snapshot)


@router.get(
    "/providers",
    response_model=ProviderHealthListResponseDTO,
    summary="List Upstream Market Data Providers Health",
    description=(
        "Returns availability status, request latency, and failure metrics for upstream providers."
    ),
)
async def list_providers_health(
    service: HealthMonitoringServiceDep,
) -> ProviderHealthListResponseDTO:
    snapshots = service.list_all_providers_health()
    items = [_to_provider_dto(s) for s in snapshots]
    return ProviderHealthListResponseDTO(items=items, total=len(items))


@router.get(
    "/pipeline",
    response_model=PipelineHealthDTO,
    summary="Get Data Pipeline Health",
    description="Returns operational status across all stages of the data processing pipeline.",
)
async def get_pipeline_health(
    service: HealthMonitoringServiceDep,
) -> PipelineHealthDTO:
    snapshot = service.get_pipeline_health()
    return _to_pipeline_dto(snapshot)


@router.get(
    "/metrics",
    summary="Expose Prometheus Telemetry Metrics",
    description="Exposes platform telemetry in standard Prometheus text format for scraping.",
)
async def get_metrics() -> Response:
    content = metrics.render_latest()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
