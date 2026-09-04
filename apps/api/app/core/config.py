"""
RegimeX API — Centralized Configuration
========================================
All configuration is loaded from environment variables.
No secrets are hardcoded. See apps/api/.env.example for required variables.

Environment selection is driven by the REGIMEX_ENV variable:
  - development  (default for local development)
  - test         (used by the test suite — uses safe, non-production values)
  - production   (requires all secrets to be explicitly provided)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Allowed deployment environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    RegimeX API application settings.

    All values are loaded from environment variables (case-insensitive).
    Sensitive fields must be supplied by the deployment environment —
    they have no safe defaults and will raise a validation error if absent
    in production.
    """

    model_config = SettingsConfigDict(
        env_prefix="REGIMEX_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application identity
    # -------------------------------------------------------------------------
    app_name: str = Field(default="RegimeX API", description="Human-readable application name")
    app_version: str = Field(default="0.1.0", description="Semantic version of this API")
    env: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode (never True in production)")

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/api/v1", description="URL prefix for API version 1")
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins. Expand via REGIMEX_ALLOWED_ORIGINS in production.",
    )

    # -------------------------------------------------------------------------
    # Database — values supplied by deployment environment
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://regimex:changeme@localhost:5432/regimex_dev",
        description=(
            "Async PostgreSQL connection URL. "
            "In production, supply REGIMEX_DATABASE_URL with real credentials."
        ),
    )
    database_pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    database_max_overflow: int = Field(
        default=20, ge=0, le=100, description="Max overflow connections"
    )

    # -------------------------------------------------------------------------
    # Redis — values supplied by deployment environment
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL. Supply REGIMEX_REDIS_URL in production.",
    )

    # -------------------------------------------------------------------------
    # Security — MUST be supplied in production, no safe defaults exist
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="CHANGE_ME_in_production_use_32+_random_bytes",
        description=(
            "Application secret key for signing tokens. "
            "MUST be set via REGIMEX_SECRET_KEY in production. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        ),
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=60, ge=1, description="JWT access token lifetime in minutes"
    )

    # -------------------------------------------------------------------------
    # Background workers (Celery — validated in V05)
    # -------------------------------------------------------------------------
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery message broker URL (Redis). Supply via REGIMEX_CELERY_BROKER_URL.",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL. Supply via REGIMEX_CELERY_RESULT_BACKEND.",
    )

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        description="Python logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    log_format: str = Field(
        default="json",
        description="Log output format: 'json' (structured) or 'text' (human-readable).",
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("debug", mode="before")
    @classmethod
    def debug_forbidden_in_production(cls, value: bool, info: object) -> bool:
        """Prevent debug mode from being enabled in production."""
        # We access info.data carefully — env may not be set yet during validation
        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION and value:
            raise ValueError("debug=True is not allowed in production environments.")
        return value

    @field_validator("secret_key", mode="before")
    @classmethod
    def secret_key_must_not_be_default_in_production(cls, value: str, info: object) -> str:
        """Fail fast if the default placeholder secret key is used in production."""
        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION and "CHANGE_ME" in value:
            raise ValueError(
                "REGIMEX_SECRET_KEY must be set to a secure random value in production. "
                'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return value

    # -------------------------------------------------------------------------
    # Convenience properties
    # -------------------------------------------------------------------------
    @property
    def is_development(self) -> bool:
        return self.env == Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.env == Environment.TEST

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    The cache is populated on first call and reused for the lifetime of
    the process. Use ``get_settings.cache_clear()`` in tests to reset.
    """
    return Settings()
