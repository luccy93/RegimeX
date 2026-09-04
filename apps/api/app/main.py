"""
RegimeX API — Application Factory
=====================================
This module is the single entry point for constructing the FastAPI application.

Pattern: Application Factory
  - ``create_app()`` builds and configures the FastAPI instance.
  - All wiring (routers, middleware, exception handlers, lifespan events)
    happens here — not inside individual domain modules.
  - Uvicorn / ASGI servers point to ``main:app`` or ``main:create_app``.

Usage:
  Development:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  Production (via Docker):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.config import get_settings
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
      - (V05+) Initialize database connection pool.
      - (V05+) Initialize Redis client.
      - (V05+) Initialize Celery application.

    Shutdown:
      - (V05+) Close database connection pool.
      - (V05+) Close Redis client.
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

    # V05+: await db_pool.initialize()
    # V05+: await redis_client.initialize()

    yield  # Application is running

    # V05+: await db_pool.close()
    # V05+: await redis_client.close()

    logger.info("RegimeX API shut down cleanly")


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> FastAPI:
    """
    Construct and configure the RegimeX FastAPI application.

    Returns a fully configured FastAPI instance. This factory function
    is used directly for testing (instantiate a fresh app per test session)
    and for production startup.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RegimeX Open-Source Market Intelligence Platform — REST API.\n\n"
            "Provides programmatic access to market regime detection, risk analytics, "
            "backtesting, and quantitative research infrastructure.\n\n"
            "**This API does not provide financial advice.** All outputs are for "
            "informational and research purposes only."
        ),
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # Middleware
    # -------------------------------------------------------------------------

    # CORS — configure allowed origins from settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID middleware — attach a unique ID to every request for tracing
    @app.middleware("http")
    async def attach_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # -------------------------------------------------------------------------
    # Exception handlers
    # -------------------------------------------------------------------------
    register_error_handlers(app)

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    app.include_router(v1_router)

    return app


# =============================================================================
# Application instance
# =============================================================================

# ASGI app — used by uvicorn and test clients
app: FastAPI = create_app()
