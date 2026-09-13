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

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from app.modules.market_data.application.registry import ProviderRegistry
    from app.modules.market_data.domain.provider import MarketDataProvider

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
# Future Dependency Stubs
# =============================================================================
# The following stubs document the intended dependency pattern for resources
# that will be implemented in later volumes. They are intentionally not
# implemented here to respect V04 scope boundaries.

# DATABASE SESSION (V05 — Market Data Engine)
# ------------------------------------------
# async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
#     """Provide an async SQLAlchemy database session per request."""
#     async with async_session_factory() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
#
# DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]

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
