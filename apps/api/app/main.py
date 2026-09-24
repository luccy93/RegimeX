"""
RegimeX API — Application Factory & Entrypoint
==============================================
Single entry point for constructing and configuring the RegimeX FastAPI application.

Architecture:
- Application Factory: ``create_app()`` instantiates and configures the FastAPI app.
- Transport Boundary: Orchestrates routing, middleware, lifecycle, and error mapping.
- Clean Architecture: No business logic in routes or main; delegates to application/domain.
- Versioning: Public business APIs mounted under ``/api/v1``.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.models import HealthResponse, ReadinessResponse, RootResponse
from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.dependencies import ReadinessCheckerDep
from app.core.errors import register_error_handlers

logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan — startup and shutdown events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Startup:
      - Validate configuration.
      - Register default market data providers.
    Shutdown:
      - Dispose database connection pool cleanly.
    """
    settings = get_settings()

    logger.info(
        "RegimeX API starting",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "env": settings.env.value,
            "api_prefix": settings.api_v1_prefix,
        },
    )

    # Register initial market data provider
    from app.modules.market_data.application.registry import default_registry
    from app.modules.market_data.infrastructure.providers.yahoo_finance import (
        YahooFinanceProvider,
    )

    if not default_registry.is_registered("yahoo_finance"):
        default_registry.register(YahooFinanceProvider())

    yield  # Application is running

    # Dispose database engine pool cleanly
    from app.core.database import dispose_engine

    await dispose_engine()
    logger.info("RegimeX API shut down cleanly")


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> FastAPI:
    """
    Construct and configure the RegimeX FastAPI application.

    Returns a fully configured FastAPI instance with versioned routing,
    request correlation tracking, CORS protection, error contracts, and
    readiness/liveness probes.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RegimeX Open-Source Market Intelligence Platform — Versioned REST API.\n\n"
            "Provides programmatic access to market intelligence, regime detection, "
            "risk analytics, and quantitative backtesting infrastructure.\n\n"
            "### Architecture & Versioning\n"
            "- Root endpoints (``/``, ``/health``, ``/ready``) provide platform identity "
            "and operational telemetry.\n"
            "- Versioned business endpoints are segregated under ``/api/v1``.\n\n"
            "### Authentication Status\n"
            "Volume 17 Commit 01 establishes secure user authentication via Argon2id "
            "and signed JWT access tokens under /api/v1/auth. Role/permission management "
            "remains intentionally deferred.\n\n"
            "### Disclaimer\n"
            "This API does not provide financial advice. All calculations and outputs "
            "are for informational and quantitative research purposes only."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Middleware
    # -------------------------------------------------------------------------

    # CORS — safe configuration adhering to security baseline
    allow_creds = "*" not in settings.allowed_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=allow_creds,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID middleware — attach correlation ID to every request/response
    @app.middleware("http")
    async def attach_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming_id = request.headers.get("X-Request-ID")
        clean_id = incoming_id.strip() if incoming_id else ""
        request_id = clean_id if clean_id else str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    register_error_handlers(app)

    # -------------------------------------------------------------------------
    # Root & Diagnostic Endpoints
    # -------------------------------------------------------------------------

    @app.get(
        "/",
        response_model=RootResponse,
        tags=["Root"],
        summary="API Root Metadata",
        description="Machine-readable platform metadata and status.",
    )
    async def root_endpoint() -> RootResponse:
        current_settings = get_settings()
        return RootResponse(
            name=current_settings.app_name,
            version=current_settings.app_version,
            api_version="v1",
            status="ok",
        )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Process Liveness Probe",
        description="Process liveness probe returning HTTP 200 if the process is alive.",
    )
    async def health_endpoint() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/ready",
        response_model=ReadinessResponse,
        tags=["Health"],
        summary="Operational Readiness Probe",
        description="Evaluates whether the application is ready to serve traffic.",
    )
    async def readiness_endpoint(
        response: Response,
        checker: ReadinessCheckerDep,
    ) -> ReadinessResponse:
        checks = await checker.check()
        all_ok = all(v == "ok" for v in checks.values())
        if not all_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(
                status="not_ready",
                checks=checks,
                timestamp=datetime.now(tz=UTC).isoformat(),
            )
        return ReadinessResponse(
            status="ready",
            checks=checks,
            timestamp=datetime.now(tz=UTC).isoformat(),
        )

    # Alias /api/openapi.json for backward compatibility
    @app.get("/api/openapi.json", include_in_schema=False)
    async def api_openapi_alias() -> Response:
        return JSONResponse(app.openapi())

    # -------------------------------------------------------------------------
    # Versioned Routers
    # -------------------------------------------------------------------------
    app.include_router(v1_router)

    return app


# =============================================================================
# Application Instance
# =============================================================================

# ASGI app instance exposed for Uvicorn and test runners
app: FastAPI = create_app()
