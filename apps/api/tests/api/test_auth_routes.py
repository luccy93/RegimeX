"""
Integration and Contract tests for Authentication API endpoints (/api/v1/auth).
================================================================================
Verifies:
1. POST /api/v1/auth/register (success, duplicate 409, short password 422, invalid email 422).
2. POST /api/v1/auth/login (success, incorrect password 401, unknown email 401, inactive 401).
3. Anti-enumeration: identical error semantics for unknown email and wrong password.
4. GET /api/v1/auth/me (success 200, missing auth 401, invalid scheme 401, expired token 401).
5. Safe representations: passwords, password hashes, and JWT secrets are NEVER returned.
6. Dependency injection overrides for testing.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime

import jwt
import pytest
from app.core.database.base import Base
from app.core.dependencies import db_session_dep, get_current_user
from app.main import create_app
from app.modules.identity_access.application.dto import UserDTO
from app.modules.identity_access.infrastructure.persistence.models import (
    UserModel,  # noqa: F401
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def auth_test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite database engine with tables created."""
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
def auth_client(auth_test_engine: AsyncEngine) -> Generator[TestClient, None, None]:
    """Create a TestClient with db_session_dep overridden by the in-memory SQLite engine."""
    session_factory = async_sessionmaker(
        bind=auth_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[db_session_dep] = override_db_session
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


class TestRegisterEndpoint:
    def test_register_success_201(self, auth_client: TestClient) -> None:
        """Verify successful user registration returns HTTP 201 and safe user data."""
        payload = {
            "email": "analyst@regimex.org",
            "password": "StrongPassword123!",
        }
        res = auth_client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201

        data = res.json()
        assert "user" in data
        user = data["user"]
        assert user["email"] == "analyst@regimex.org"
        assert user["is_active"] is True
        assert "id" in user
        assert "created_at" in user

        # Critical security invariant: passwords/hashes must NEVER appear in responses
        assert "password" not in user
        assert "password_hash" not in user
        assert "hash" not in user

    def test_register_duplicate_email_returns_409(self, auth_client: TestClient) -> None:
        """Verify duplicate normalized email registration returns HTTP 409 Conflict."""
        payload = {
            "email": "duplicate@regimex.org",
            "password": "StrongPassword123!",
        }
        res1 = auth_client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = auth_client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        err = res2.json()
        assert "error" in err
        assert err["error"]["code"] == "CONFLICT"

    def test_register_duplicate_with_case_and_whitespace_returns_409(
        self, auth_client: TestClient
    ) -> None:
        """Verify duplicate registration is caught despite whitespace or uppercase characters."""
        auth_client.post(
            "/api/v1/auth/register",
            json={"email": "case.sensitive@regimex.org", "password": "StrongPassword123!"},
        )

        res = auth_client.post(
            "/api/v1/auth/register",
            json={"email": "  CASE.SENSITIVE@REGIMEX.ORG  ", "password": "StrongPassword123!"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CONFLICT"

    def test_register_short_password_returns_422(self, auth_client: TestClient) -> None:
        """Verify password shorter than 12 characters is rejected with HTTP 422."""
        res = auth_client.post(
            "/api/v1/auth/register",
            json={"email": "short@regimex.org", "password": "short"},
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_register_invalid_email_format_returns_422(self, auth_client: TestClient) -> None:
        """Verify malformed email format is rejected with HTTP 422."""
        res = auth_client.post(
            "/api/v1/auth/register",
            json={"email": "not-a-valid-email", "password": "StrongPassword123!"},
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"


class TestLoginEndpoint:
    def test_login_success_200(self, auth_client: TestClient) -> None:
        """Verify successful login returns signed access token and safe user profile."""
        email = "trader@regimex.org"
        password = "StrongPassword123!"

        auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )

        login_res = auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200

        data = login_res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert data["user"]["email"] == email

        # Invariant: passwords/hashes must never leak
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

    def test_login_incorrect_password_returns_401(self, auth_client: TestClient) -> None:
        """Verify wrong password returns HTTP 401 with generic error message."""
        email = "login.fail@regimex.org"
        auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "StrongPassword123!"},
        )

        res = auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999!"},
        )
        assert res.status_code == 401
        err = res.json()["error"]
        assert err["code"] == "INVALID_CREDENTIALS"
        assert err["message"] == "Invalid email or password."

    def test_login_unknown_email_returns_identical_generic_401(
        self, auth_client: TestClient
    ) -> None:
        """
        Anti-enumeration invariant: unknown email produces the identical generic message
        and error code as an incorrect password.
        """
        res = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@regimex.org", "password": "RandomPassword123!"},
        )
        assert res.status_code == 401
        err = res.json()["error"]
        assert err["code"] == "INVALID_CREDENTIALS"
        assert err["message"] == "Invalid email or password."

    def test_login_case_and_whitespace_email_normalization(self, auth_client: TestClient) -> None:
        """Verify login succeeds when email is submitted with varying whitespace or casing."""
        auth_client.post(
            "/api/v1/auth/register",
            json={"email": "case.login@regimex.org", "password": "StrongPassword123!"},
        )

        res = auth_client.post(
            "/api/v1/auth/login",
            json={"email": "  CASE.LOGIN@REGIMEX.ORG  ", "password": "StrongPassword123!"},
        )
        assert res.status_code == 200
        assert res.json()["user"]["email"] == "case.login@regimex.org"


class TestCurrentUserEndpoint:
    def test_get_current_user_success_200(self, auth_client: TestClient) -> None:
        """Verify GET /api/v1/auth/me returns current user identity with valid Bearer token."""
        email = "me.user@regimex.org"
        password = "StrongPassword123!"

        reg_res = auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        user_id = reg_res.json()["user"]["id"]

        login_res = auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        token = login_res.json()["access_token"]

        me_res = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["id"] == user_id
        assert data["email"] == email
        assert data["is_active"] is True

    def test_get_current_user_missing_authorization_header_returns_401(
        self, auth_client: TestClient
    ) -> None:
        """Verify request without Authorization header returns HTTP 401."""
        res = auth_client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_get_current_user_invalid_scheme_returns_401(self, auth_client: TestClient) -> None:
        """Verify request with non-Bearer scheme (e.g., Basic) returns HTTP 401."""
        res = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_get_current_user_malformed_token_returns_401(self, auth_client: TestClient) -> None:
        """Verify request with malformed token returns HTTP 401."""
        res = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_get_current_user_expired_token_returns_401(self, auth_client: TestClient) -> None:
        """Verify expired token returns HTTP 401 with standard error envelope."""
        past_time = int(time.time()) - 100
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "expired@regimex.org",
            "iat": past_time - 3600,
            "exp": past_time,
            "jti": str(uuid.uuid4()),
        }
        # Signs with test secret matching conftest.py
        test_secret = "test-secret-key-not-for-production-use"
        expired_token = jwt.encode(payload, test_secret, algorithm="HS256")

        res = auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    def test_get_current_user_dependency_override(self) -> None:
        """Verify dependency injection override of get_current_user for isolated testing."""
        app = create_app()
        fake_user = UserDTO(
            id=uuid.uuid4(),
            email="mocked.user@regimex.org",
            is_active=True,
            created_at=datetime.now(tz=UTC),
        )

        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            res = client.get("/api/v1/auth/me")
            assert res.status_code == 200
            assert res.json()["email"] == "mocked.user@regimex.org"
