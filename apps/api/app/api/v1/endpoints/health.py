"""
RegimeX API — Health Endpoint
================================
Provides liveness and readiness probes for orchestration health checks.

Architecture note:
  - Health endpoints belong to the API transport layer.
  - They must NOT contain business logic.
  - Liveness (/health/live) — is the process running?
  - Readiness (/health/ready) — are all dependencies reachable?
    (Readiness with real dependency checks is implemented in V05+
     when the database and Redis are wired up.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


# =============================================================================
# Response Schemas
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
# Endpoints
# =============================================================================


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description=(
        "Returns HTTP 200 if the RegimeX API process is alive. "
        "Used by Docker, Kubernetes, and load balancers to determine "
        "whether to restart or route traffic to this instance."
    ),
)
async def liveness() -> LivenessResponse:
    """
    Liveness probe — always returns 200 if the process is running.

    This endpoint intentionally contains no external dependency checks.
    """
    from app.core.config import get_settings

    settings = get_settings()
    return LivenessResponse(
        status="ok",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Returns HTTP 200 when all required dependencies are reachable. "
        "Returns HTTP 503 if any critical dependency is unavailable. "
        "Note: Real dependency checks (database, Redis) are implemented "
        "in V05 when infrastructure is wired. This endpoint currently "
        "returns a stub readiness response."
    ),
)
async def readiness() -> ReadinessResponse:
    """
    Readiness probe.

    V04: Returns stub 'ready' status — no real dependency checks yet.
    V05+: Will perform live PostgreSQL and Redis connectivity checks.
    """
    return ReadinessResponse(
        status="ready",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        checks={
            "api": "ok",
            # "database": "pending_v05",  # uncomment in V05
            # "redis": "pending_v05",     # uncomment in V05
        },
    )
