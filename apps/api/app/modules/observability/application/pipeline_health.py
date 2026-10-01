"""
RegimeX Observability — Data Pipeline Health Monitor
===================================================
Tracks operational health across all stages of the data processing pipeline:
Provider -> Ingestion -> Validation -> Normalization -> Storage -> Features.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.modules.observability.domain.enums import HealthStatus, PipelineStage
from app.modules.observability.domain.models import PipelineHealthSnapshot, PipelineStageHealth


class PipelineHealthMonitor:
    """
    Monitors operational health of data pipeline stages.
    """

    def __init__(self) -> None:
        self._stages: dict[str, PipelineStageHealth] = {
            s.value: PipelineStageHealth(
                stage=s, status=HealthStatus.HEALTHY, last_run=datetime.now(tz=UTC)
            )
            for s in PipelineStage
        }

    def record_stage_status(
        self,
        stage: PipelineStage | str,
        status: HealthStatus | str,
        last_run: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Update operational status for a specific pipeline stage."""
        stage_enum = PipelineStage(stage) if isinstance(stage, str) else stage
        status_enum = HealthStatus(status) if isinstance(status, str) else status
        now = last_run or datetime.now(tz=UTC)

        self._stages[stage_enum.value] = PipelineStageHealth(
            stage=stage_enum,
            status=status_enum,
            last_run=now,
            details=details or {},
        )

    def get_pipeline_snapshot(self) -> PipelineHealthSnapshot:
        """Produce consolidated pipeline health snapshot."""
        stage_statuses = [sh.status for sh in self._stages.values()]

        if HealthStatus.UNHEALTHY in stage_statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in stage_statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in stage_statuses):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        return PipelineHealthSnapshot(
            stages=dict(self._stages),
            overall_status=overall,
        )
