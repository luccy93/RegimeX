"""
RegimeX API — Dependency Injection Foundation
===============================================
Defines FastAPI dependency functions that provide shared resources to
route handlers via ``Depends()``.

Architecture boundary:
  - This module provides infrastructure resources (settings, database
    sessions, cache clients) to the API layer.
  - Domain modules must NOT import from here. Domain logic is pure Python,
    independent of FastAPI and web frameworks.

Future dependencies (database sessions, Redis clients, Celery app) will
be added in their respective volumes (V05+) once infrastructure is
established. Stubs are documented below to communicate the intended pattern.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.market_data.application.registry import ProviderRegistry
from app.modules.market_data.application.service import MarketDataService
from app.modules.market_data.domain.provider import MarketDataProvider
from app.modules.market_data.domain.repository import MarketDataRepository
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade

# =============================================================================
# Settings Dependency
# =============================================================================


def settings_dep() -> Settings:
    """
    Provide the application settings to route handlers.

    Example usage in a route:
        @router.get("/example")
        async def example(settings: SettingsDep) -> ...:
            return {"env": settings.env}
    """
    return get_settings()


# Type alias for annotated dependency injection
SettingsDep = Annotated[Settings, Depends(settings_dep)]


# =============================================================================
# Market Data Dependencies (V05 Commit 02)
# =============================================================================


def market_data_registry_dep() -> ProviderRegistry:
    """Provide the market data provider registry."""
    from app.modules.market_data.application.registry import default_registry

    return default_registry


MarketDataRegistryDep = Annotated[ProviderRegistry, Depends(market_data_registry_dep)]


def market_data_provider_dep(
    registry: MarketDataRegistryDep,
) -> MarketDataProvider:
    """
    Provide the default market data provider abstraction.

    The application layer depends on MarketDataProvider, not concrete adapters.
    """
    return registry.get("yahoo_finance")


MarketDataProviderDep = Annotated[MarketDataProvider, Depends(market_data_provider_dep)]


# =============================================================================
# Database Session & Repository Dependencies (V06 Commit 02)
# =============================================================================


async def db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session with transaction management."""
    from app.core.database import get_db_session

    async for session in get_db_session():
        yield session


DatabaseSessionDep = Annotated[AsyncSession, Depends(db_session_dep)]


def market_data_repository_dep(
    session: DatabaseSessionDep,
) -> MarketDataRepository:
    """Provide the market data repository abstraction backed by SQLAlchemy."""
    from app.modules.market_data.infrastructure.persistence import (
        SQLAlchemyMarketDataRepository,
    )

    return SQLAlchemyMarketDataRepository(session)


MarketDataRepositoryDep = Annotated[MarketDataRepository, Depends(market_data_repository_dep)]


# =============================================================================
# Market Data Service Dependency
# =============================================================================


def market_service_dep(
    provider: MarketDataProviderDep,
) -> MarketDataService:
    """Provide the application MarketDataService facade."""
    from app.modules.market_data.application.service import MarketDataService

    return MarketDataService(provider=provider)


MarketServiceDep = Annotated[MarketDataService, Depends(market_service_dep)]


# =============================================================================
# Market Intelligence Facade Dependency (V16 Commit 02)
# =============================================================================


def market_intelligence_dep(
    market_service: MarketServiceDep,
) -> MarketIntelligenceFacade:
    """Provide the application MarketIntelligenceFacade."""
    from app.modules.regime_intelligence.application.facade import (
        MarketIntelligenceFacade,
    )

    return MarketIntelligenceFacade(market_service=market_service)


MarketIntelligenceDep = Annotated[MarketIntelligenceFacade, Depends(market_intelligence_dep)]


# =============================================================================
# Readiness Dependency
# =============================================================================


class ReadinessChecker:
    """
    Evaluates application and infrastructure dependency readiness.

    Supports test overrides to simulate ready and not-ready states.
    """

    async def check(self) -> dict[str, str]:
        """Perform readiness checks and return status mapping."""
        return {"application": "ok"}


def readiness_checker_dep() -> ReadinessChecker:
    """Provide the default ReadinessChecker."""
    return ReadinessChecker()


ReadinessCheckerDep = Annotated[ReadinessChecker, Depends(readiness_checker_dep)]

# The following stubs document the intended dependency pattern for resources
# that will be implemented in later volumes. They are intentionally not
# implemented here to respect volume scope boundaries.

# REDIS CLIENT (V05 — Market Data Engine)
# ----------------------------------------
# async def get_redis_client() -> AsyncGenerator[Redis, None]:
#     """Provide a Redis client for caching and rate limiting."""
#     client = Redis.from_url(get_settings().redis_url)
#     try:
#         yield client
#     finally:
#         await client.aclose()
#
# RedisClient = Annotated[Redis, Depends(get_redis_client)]

# CURRENT USER PRINCIPAL (V15 — Identity & Access)
# --------------------------------------------------
# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: DatabaseSession = None,
# ) -> UserPrincipal:
#     """Authenticate and return the current user principal."""
#     ...
#
# CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]
