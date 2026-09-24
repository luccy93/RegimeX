"""
Pytest fixtures for identity_access unit tests.
===============================================
Provides an in-memory asynchronous SQLite database engine and session factory
for deterministic, 100% offline persistence and service testing.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from app.core.database.base import Base
from app.modules.identity_access.application.service import AuthenticationService
from app.modules.identity_access.domain.password import PasswordHasher
from app.modules.identity_access.domain.repository import UserRepository
from app.modules.identity_access.domain.token import TokenService
from app.modules.identity_access.infrastructure.persistence.models import (
    UserModel,  # noqa: F401
)
from app.modules.identity_access.infrastructure.persistence.repository import (
    SQLAlchemyUserRepository,
)
from app.modules.identity_access.infrastructure.security.hasher import (
    Argon2PasswordHasher,
)
from app.modules.identity_access.infrastructure.security.token import (
    JwtTokenService,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_JWT_SECRET = "test-secret-key-32-bytes-minimum-length-for-hmac-sha256"


@pytest.fixture
async def sqlite_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory async SQLite engine with schema initialized."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(
    sqlite_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async session for each test."""
    session_factory = async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def user_repository(db_session: AsyncSession) -> UserRepository:
    """Provide a UserRepository instance bound to the test database session."""
    return SQLAlchemyUserRepository(session=db_session)


@pytest.fixture
def password_hasher() -> PasswordHasher:
    """Provide an Argon2id password hasher."""
    return Argon2PasswordHasher()


@pytest.fixture
def token_service() -> TokenService:
    """Provide a JWT token service configured with a test secret."""
    return JwtTokenService(
        secret=TEST_JWT_SECRET,
        algorithm="HS256",
        expire_minutes=60,
    )


@pytest.fixture
def auth_service(
    user_repository: UserRepository,
    password_hasher: PasswordHasher,
    token_service: TokenService,
) -> AuthenticationService:
    """Provide a fully configured AuthenticationService."""
    return AuthenticationService(
        user_repository=user_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        access_token_expire_minutes=60,
    )
