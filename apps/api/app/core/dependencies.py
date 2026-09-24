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
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.modules.identity_access.application.dto import UserDTO
from app.modules.identity_access.application.service import AuthenticationService
from app.modules.identity_access.domain.password import PasswordHasher
from app.modules.identity_access.domain.repository import UserRepository
from app.modules.identity_access.domain.token import TokenService
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


# =============================================================================
# Authentication & Identity Dependencies (V17 Commit 01)
# =============================================================================

http_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT Bearer token authorization header: 'Authorization: Bearer <token>'",
)


def password_hasher_dep() -> PasswordHasher:
    """Provide the Argon2id password hasher implementation."""
    from app.modules.identity_access.infrastructure.security.hasher import (
        Argon2PasswordHasher,
    )

    return Argon2PasswordHasher()


PasswordHasherDep = Annotated[PasswordHasher, Depends(password_hasher_dep)]


def token_service_dep(settings: SettingsDep) -> TokenService:
    """Provide the JWT token signing and decoding service."""
    from app.modules.identity_access.infrastructure.security.token import (
        JwtTokenService,
    )

    return JwtTokenService(
        secret=settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm,
        expire_minutes=settings.auth_access_token_expire_minutes,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
    )


TokenServiceDep = Annotated[TokenService, Depends(token_service_dep)]


def user_repository_dep(session: DatabaseSessionDep) -> UserRepository:
    """Provide the User persistence repository bound to the current database session."""
    from app.modules.identity_access.infrastructure.persistence.repository import (
        SQLAlchemyUserRepository,
    )

    return SQLAlchemyUserRepository(session=session)


UserRepositoryDep = Annotated[UserRepository, Depends(user_repository_dep)]


def auth_service_dep(
    user_repository: UserRepositoryDep,
    password_hasher: PasswordHasherDep,
    token_service: TokenServiceDep,
    settings: SettingsDep,
) -> AuthenticationService:
    """Provide the AuthenticationService application orchestration facade."""
    from app.modules.identity_access.application.service import (
        AuthenticationService,
    )

    return AuthenticationService(
        user_repository=user_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        access_token_expire_minutes=settings.auth_access_token_expire_minutes,
    )


AuthServiceDep = Annotated[AuthenticationService, Depends(auth_service_dep)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer_scheme)],
    auth_service: AuthServiceDep,
) -> UserDTO:
    """
    FastAPI authentication dependency.

    Extracts Bearer token from the standard Authorization header, validates signature
    and claims, and returns the authenticated User identity.

    Raises:
        AuthenticationRequiredError (HTTP 401): If the header is missing, malformed,
            or if the token is invalid or expired.
    """
    from app.modules.identity_access.domain.errors import (
        AuthenticationRequiredError,
    )

    if credentials is None:
        raise AuthenticationRequiredError("Authentication is required.")

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationRequiredError("Invalid authentication scheme. Bearer scheme required.")

    token = credentials.credentials.strip() if credentials.credentials else ""
    if not token:
        raise AuthenticationRequiredError("Authentication token cannot be empty.")

    user = await auth_service.get_current_user_from_token(token)
    return user


def authorization_checker_dep() -> object:
    """Provide the authorization checker enforcing active account policies."""
    from app.modules.identity_access.domain.authorization import (
        AuthorizationChecker,
    )

    return AuthorizationChecker()


AuthorizationCheckerDep = Annotated[object, Depends(authorization_checker_dep)]


async def require_authenticated_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
    authorizer: AuthorizationCheckerDep,
) -> UserDTO:
    """
    FastAPI authorization dependency.

    Enforces the complete authorization boundary:
      1. Authentication: Validates token and resolves identity.
      2. Authorization: Verifies account is active and satisfies configured policies.

    Returns:
        UserDTO: The authenticated and authorized user principal.

    Raises:
        IdentityAccessError / AuthorizationError: If authorization check fails.
    """
    from app.modules.identity_access.domain.authorization import (
        AuthorizationChecker,
    )

    if isinstance(authorizer, AuthorizationChecker):
        authorizer.authorize(current_user)
    return current_user


RequireAuthenticatedUser = Annotated[UserDTO, Depends(require_authenticated_user)]
CurrentUserDep = RequireAuthenticatedUser
CurrentUser = RequireAuthenticatedUser
