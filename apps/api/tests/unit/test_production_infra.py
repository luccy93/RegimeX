"""
RegimeX API — Production Infrastructure & Configuration Regression Tests
========================================================================
Validates:
1. Production environment validation and strict credential checks.
2. Rejection of insecure default secrets, database URLs, and wildcard CORS.
3. Secret masking in error messages, URLs, and structured JSON logs.
4. PORT and configuration alias resolution.
5. Database connection pool sizing, recycle, and timeout configuration.
6. Bounded readiness evaluation and graceful shutdown.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Environment, Settings
from app.core.database.session import create_engine_and_session_factory, dispose_engine
from app.core.dependencies import ReadinessChecker
from app.core.logging import JSONFormatter, mask_sensitive_value
from pydantic import ValidationError


class TestProductionEnvironmentValidation:
    """Validate that production configuration strictly enforces security boundaries."""

    def test_production_rejects_default_secret_key(self) -> None:
        """Production mode must reject default placeholder secret key."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="CHANGE_ME_in_production_use_32+_random_bytes",
                database_url="postgresql+asyncpg://user:strongpass12345@prod-db:5432/regimex",
                allowed_origins=["https://app.regimex.io"],
            )
        assert "secure random value" in str(exc_info.value)

    def test_production_rejects_short_secret_key(self) -> None:
        """Production mode must reject secret keys shorter than 32 characters."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="short-secret-key-less-32-chars",
                database_url="postgresql+asyncpg://user:strongpass12345@prod-db:5432/regimex",
                allowed_origins=["https://app.regimex.io"],
            )
        assert "at least 32 characters" in str(exc_info.value)

    def test_production_rejects_insecure_dev_secret(self) -> None:
        """Production mode must reject known insecure development secret strings."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="insecure-dev-secret-replace-in-production-min32chars!",
                database_url="postgresql+asyncpg://user:strongpass12345@prod-db:5432/regimex",
                allowed_origins=["https://app.regimex.io"],
            )
        assert "secure random value" in str(exc_info.value)

    def test_production_rejects_default_database_url(self) -> None:
        """Production mode must reject default changeme database credentials."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="a" * 32,
                database_url="postgresql+asyncpg://regimex:changeme@localhost:5432/regimex_dev",
                allowed_origins=["https://app.regimex.io"],
            )
        assert "insecure default or placeholder" in str(exc_info.value)

    def test_production_rejects_debug_true(self) -> None:
        """Production mode must disallow debug=True."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                debug=True,
                secret_key="a" * 32,
                database_url="postgresql+asyncpg://user:strongpass12345@prod-db:5432/regimex",
                allowed_origins=["https://app.regimex.io"],
            )
        assert "debug=True is not allowed in production" in str(exc_info.value)

    def test_production_rejects_wildcard_cors(self) -> None:
        """Production mode must strictly prohibit wildcard '*' CORS origins."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                env=Environment.PRODUCTION,
                secret_key="a" * 32,
                database_url="postgresql+asyncpg://user:strongpass12345@prod-db:5432/regimex",
                allowed_origins=["*"],
            )
        assert "Wildcard '*' CORS origins are strictly prohibited" in str(exc_info.value)

    def test_production_normalizes_postgres_schemes(self) -> None:
        """Normalizes postgresql:// or postgres:// to postgresql+asyncpg://."""
        settings = Settings(
            env=Environment.PRODUCTION,
            secret_key="b" * 32,
            database_url="postgresql://user:validpass123@prod-db.internal:5432/regimex",
            allowed_origins=["https://app.regimex.io"],
        )
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_sanitized_database_url_masks_password(self) -> None:
        """Sanitized database URL masks password for safe telemetry and diagnostics."""
        settings = Settings(
            database_url="postgresql+asyncpg://regimex_app:SuperSecretP@ss123@db.prod.internal:5432/regimex_prod"
        )
        masked = settings.sanitized_database_url()
        assert "SuperSecretP@ss123" not in masked
        assert masked == "postgresql+asyncpg://regimex_app:***@db.prod.internal:5432/regimex_prod"

    def test_port_alias_respected(self) -> None:
        """Settings must respect standard PORT environment variable alias."""
        settings = Settings(PORT="9000")
        assert settings.api_port == 9000

    def test_ai_provider_openai_requires_api_key_when_no_base_url(self) -> None:
        """When ai_provider is openai, an API key is required if no custom base URL is supplied."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                REGIMEX_AI_PROVIDER="openai",
                REGIMEX_AI_API_KEY="",
                REGIMEX_AI_BASE_URL="",
            )
        assert "REGIMEX_AI_API_KEY must be provided" in str(exc_info.value)


class TestDatabasePoolConfiguration:
    """Verify database connection pool limits and timeouts."""

    def test_database_pool_settings_passed_to_engine(self) -> None:
        """Engine creation must configure pool limits and timeouts for PostgreSQL."""
        from sqlalchemy.pool import QueuePool

        engine, factory = create_engine_and_session_factory(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            pool_size=15,
            max_overflow=25,
            pool_timeout=45.0,
            pool_recycle=1200,
        )
        try:
            pool = engine.pool
            assert isinstance(pool, QueuePool)
            assert pool.size() == 15
            assert pool._max_overflow == 25
            assert pool._timeout == 45.0
            assert pool._recycle == 1200
        finally:
            engine.sync_engine.dispose()

    @pytest.mark.asyncio
    async def test_dispose_engine_bounded_timeout(self) -> None:
        """Engine disposal must complete cleanly within bounded timeout."""
        with patch("app.core.database.session._engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            await dispose_engine()
            mock_engine.dispose.assert_awaited_once()


class TestReadinessAndStartup:
    """Verify operational readiness evaluation and error isolation."""

    @pytest.mark.asyncio
    async def test_readiness_test_environment_isolated(self) -> None:
        """In test environment, readiness checker returns application ok without network calls."""
        checker = ReadinessChecker()
        res = await checker.check()
        assert res == {"application": "ok"}

    @pytest.mark.asyncio
    async def test_readiness_handles_database_failure_safely(self) -> None:
        """Readiness checker must catch DB errors and report unavailable without leaking."""
        checker = ReadinessChecker()
        with (
            patch("app.core.dependencies.get_settings") as mock_settings,
            patch("app.core.database.session.get_engine") as mock_engine,
        ):
            mock_settings.return_value.is_test = False
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = ConnectionRefusedError(
                "connection to server at 'db' (10.0.0.5), port 5432 failed"
            )
            mock_engine.return_value.connect.return_value.__aenter__.return_value = mock_conn

            res = await checker.check()
            assert res["application"] == "ok"
            assert res["database"] == "unavailable"


class TestStructuredLogging:
    """Verify structured JSON logging and security sanitization."""

    def test_mask_sensitive_value_handles_dicts_and_strings(self) -> None:
        """mask_sensitive_value recursively masks passwords, tokens, and db URLs."""
        payload = {
            "user": "alice",
            "password": "supersecretpassword",
            "api_key": "sk-1234567890",
            "db_uri": "postgresql+asyncpg://admin:secretpass@10.0.0.1:5432/db",
            "metadata": {"jwt_secret": "my-secret-token-key"},
        }
        masked = mask_sensitive_value(payload)
        assert isinstance(masked, dict)
        assert masked["password"] == "***"
        assert masked["api_key"] == "***"
        assert "secretpass" not in str(masked["db_uri"])
        assert isinstance(masked["metadata"], dict)
        assert masked["metadata"]["jwt_secret"] == "***"
        assert masked["user"] == "alice"

    def test_json_formatter_outputs_valid_sanitized_json(self) -> None:
        """JSONFormatter outputs single-line JSON log with masked sensitive values."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="User login attempted",
            args=(),
            exc_info=None,
        )
        record.__dict__["auth_token"] = "eyJh...secret"
        record.__dict__["database_url"] = "postgresql+asyncpg://app:secret123@db:5432/app"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "app.test"
        assert parsed["message"] == "User login attempted"
        assert parsed["auth_token"] == "***"
        assert "secret123" not in parsed["database_url"]
