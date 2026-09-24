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

from pydantic import AliasChoices, Field, field_validator
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
        populate_by_name=True,
    )

    # -------------------------------------------------------------------------
    # Application identity
    # -------------------------------------------------------------------------
    app_name: str = Field(default="RegimeX API", description="Human-readable application name")
    app_version: str = Field(default="1.0.0", description="Semantic version of this API")
    env: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    debug: bool = Field(default=False, description="Enable debug mode (never True in production)")

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0", description="API server bind host")  # noqa: S104
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server bind port")
    api_v1_prefix: str = Field(default="/api/v1", description="URL prefix for API version 1")
    allowed_origins: list[str] | str = Field(
        default=["http://localhost:3000"],
        validation_alias=AliasChoices(
            "CORS_ALLOWED_ORIGINS",
            "REGIMEX_CORS_ALLOWED_ORIGINS",
            "REGIMEX_ALLOWED_ORIGINS",
            "ALLOWED_ORIGINS",
        ),
        description="CORS allowed origins. Expand via CORS_ALLOWED_ORIGINS in production.",
    )
    max_request_body_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1024,
        validation_alias=AliasChoices(
            "MAX_REQUEST_BODY_BYTES",
            "REGIMEX_MAX_REQUEST_BODY_BYTES",
        ),
        description="Maximum permitted request body size in bytes (boundary protection)",
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
        validation_alias=AliasChoices(
            "AUTH_JWT_SECRET",
            "REGIMEX_AUTH_JWT_SECRET",
            "REGIMEX_SECRET_KEY",
            "SECRET_KEY",
        ),
        description=(
            "Application secret key for signing tokens. "
            "MUST be set via AUTH_JWT_SECRET or REGIMEX_SECRET_KEY in production. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        ),
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices(
            "AUTH_JWT_ALGORITHM",
            "REGIMEX_AUTH_JWT_ALGORITHM",
            "REGIMEX_JWT_ALGORITHM",
            "JWT_ALGORITHM",
        ),
        description="JWT signing algorithm (HS256, HS384, HS512)",
    )
    access_token_expire_minutes: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices(
            "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES",
            "REGIMEX_AUTH_ACCESS_TOKEN_EXPIRE_MINUTES",
            "REGIMEX_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
        ),
        description="JWT access token lifetime in minutes",
    )
    jwt_issuer: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUTH_JWT_ISSUER",
            "REGIMEX_AUTH_JWT_ISSUER",
            "JWT_ISSUER",
        ),
        description="Optional expected JWT issuer claim (iss)",
    )
    jwt_audience: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AUTH_JWT_AUDIENCE",
            "REGIMEX_AUTH_JWT_AUDIENCE",
            "JWT_AUDIENCE",
        ),
        description="Optional expected JWT audience claim (aud)",
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
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_allowed_origins(cls, value: object, info: object) -> list[str]:
        """Validate and normalize allowed CORS origins, rejecting wildcard origins in production."""
        origins: list[str] = []
        if isinstance(value, str):
            origins = [s.strip() for s in value.split(",") if s.strip()]
        elif isinstance(value, (list, tuple, set)):
            origins = [str(s).strip() for s in value if str(s).strip()]
        else:
            origins = ["http://localhost:3000"]

        if not origins:
            origins = ["http://localhost:3000"]

        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION:
            if "*" in origins:
                raise ValueError(
                    "Wildcard '*' CORS origins are strictly prohibited in production environments."
                )
        return origins

    @field_validator("debug")
    @classmethod
    def debug_forbidden_in_production(cls, value: bool, info: object) -> bool:
        """Prevent debug mode from being enabled in production."""
        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION and value is True:
            raise ValueError("debug=True is not allowed in production environments.")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        """Validate that the JWT signing algorithm is an approved HMAC algorithm."""
        allowed = {"HS256", "HS384", "HS512"}
        val_upper = value.upper()
        if val_upper not in allowed:
            raise ValueError(
                f"Unsupported or insecure JWT algorithm: '{value}'. "
                f"Allowed algorithms: {sorted(allowed)}"
            )
        return val_upper

    @field_validator("secret_key", mode="before")
    @classmethod
    def secret_key_must_not_be_default_in_production(cls, value: str | None, info: object) -> str:
        """Fail fast if the default placeholder secret key is used in production."""
        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION:
            if not value or not str(value).strip():
                raise ValueError("REGIMEX_SECRET_KEY / AUTH_JWT_SECRET must be set in production.")
            val_str = str(value)
            if "CHANGE_ME" in val_str or len(val_str) < 32:
                raise ValueError(
                    "REGIMEX_SECRET_KEY / AUTH_JWT_SECRET must be set to a secure random value "
                    "of at least 32 characters in production. "
                    'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
                )
        return value or "CHANGE_ME_in_production_use_32+_random_bytes"

    # -------------------------------------------------------------------------
    # Convenience properties
    # -------------------------------------------------------------------------
    @property
    def auth_jwt_secret(self) -> str:
        return self.secret_key

    @property
    def auth_jwt_algorithm(self) -> str:
        return self.jwt_algorithm

    @property
    def auth_access_token_expire_minutes(self) -> int:
        return self.access_token_expire_minutes

    @property
    def auth_jwt_issuer(self) -> str | None:
        return self.jwt_issuer

    @property
    def auth_jwt_audience(self) -> str | None:
        return self.jwt_audience

    @property
    def auth_max_request_body_bytes(self) -> int:
        return self.max_request_body_bytes

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
