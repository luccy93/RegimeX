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

import re
from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    api_host: str = Field(
        default="0.0.0.0",  # noqa: S104
        validation_alias=AliasChoices(
            "HOST",
            "REGIMEX_HOST",
            "REGIMEX_API_HOST",
            "API_HOST",
        ),
        description="API server bind host",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices(
            "PORT",
            "REGIMEX_PORT",
            "REGIMEX_API_PORT",
            "API_PORT",
        ),
        description="API server bind port",
    )
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
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "REGIMEX_DATABASE_URL",
        ),
        description=(
            "Async PostgreSQL connection URL. "
            "In production, supply REGIMEX_DATABASE_URL with real credentials."
        ),
    )
    database_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "DATABASE_POOL_SIZE",
            "REGIMEX_DATABASE_POOL_SIZE",
        ),
        description="Connection pool size",
    )
    database_max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        validation_alias=AliasChoices(
            "DATABASE_MAX_OVERFLOW",
            "REGIMEX_DATABASE_MAX_OVERFLOW",
        ),
        description="Max overflow connections",
    )
    database_pool_timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        validation_alias=AliasChoices(
            "DATABASE_POOL_TIMEOUT",
            "REGIMEX_DATABASE_POOL_TIMEOUT",
        ),
        description="Connection pool acquisition timeout in seconds",
    )
    database_pool_recycle: int = Field(
        default=1800,
        ge=60,
        le=86400,
        validation_alias=AliasChoices(
            "DATABASE_POOL_RECYCLE",
            "REGIMEX_DATABASE_POOL_RECYCLE",
        ),
        description="Connection recycling interval in seconds (prevents stale pooled connections)",
    )
    database_connect_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        validation_alias=AliasChoices(
            "DATABASE_CONNECT_TIMEOUT",
            "REGIMEX_DATABASE_CONNECT_TIMEOUT",
        ),
        description="Database connection handshake timeout in seconds",
    )
    database_statement_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        validation_alias=AliasChoices(
            "DATABASE_STATEMENT_TIMEOUT_MS",
            "REGIMEX_DATABASE_STATEMENT_TIMEOUT_MS",
        ),
        description="Database statement execution timeout in milliseconds",
    )

    # -------------------------------------------------------------------------
    # Redis — values supplied by deployment environment
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices(
            "REDIS_URL",
            "REGIMEX_REDIS_URL",
        ),
        description="Redis connection URL. Supply REGIMEX_REDIS_URL in production.",
    )
    redis_connect_timeout: float = Field(
        default=5.0,
        ge=0.5,
        le=60.0,
        validation_alias=AliasChoices(
            "REDIS_CONNECT_TIMEOUT",
            "REGIMEX_REDIS_CONNECT_TIMEOUT",
        ),
        description="Redis connection timeout in seconds",
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
        validation_alias=AliasChoices(
            "CELERY_BROKER_URL",
            "REGIMEX_CELERY_BROKER_URL",
        ),
        description="Celery message broker URL (Redis). Supply via REGIMEX_CELERY_BROKER_URL.",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        validation_alias=AliasChoices(
            "CELERY_RESULT_BACKEND",
            "REGIMEX_CELERY_RESULT_BACKEND",
        ),
        description="Celery result backend URL. Supply via REGIMEX_CELERY_RESULT_BACKEND.",
    )

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices(
            "LOG_LEVEL",
            "REGIMEX_LOG_LEVEL",
        ),
        description="Python logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    log_format: str = Field(
        default="json",
        validation_alias=AliasChoices(
            "LOG_FORMAT",
            "REGIMEX_LOG_FORMAT",
        ),
        description="Log output format: 'json' (structured) or 'text' (human-readable).",
    )

    # -------------------------------------------------------------------------
    # AI Research Assistant (V21)
    # -------------------------------------------------------------------------
    ai_provider: str = Field(
        default="mock",
        validation_alias=AliasChoices(
            "AI_PROVIDER",
            "REGIMEX_AI_PROVIDER",
        ),
        description="AI model provider: 'mock' | 'openai'",
    )
    ai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices(
            "AI_MODEL",
            "REGIMEX_AI_MODEL",
        ),
        description="AI model name for quantitative research assistant",
    )
    ai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_API_KEY",
            "REGIMEX_AI_API_KEY",
        ),
        description="Optional API key for external AI provider",
    )
    ai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_BASE_URL",
            "REGIMEX_AI_BASE_URL",
        ),
        description="Optional custom base URL for OpenAI-compatible endpoint",
    )
    ai_timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        validation_alias=AliasChoices(
            "AI_TIMEOUT",
            "REGIMEX_AI_TIMEOUT",
        ),
        description="Request timeout in seconds for AI provider calls",
    )
    ai_max_tokens: int = Field(
        default=2000,
        ge=50,
        le=8192,
        validation_alias=AliasChoices(
            "AI_MAX_TOKENS",
            "REGIMEX_AI_MAX_TOKENS",
        ),
        description="Maximum tokens generated by AI provider",
    )

    # -------------------------------------------------------------------------
    # Observability & Health Monitoring (V23 Commit 02)
    # -------------------------------------------------------------------------
    data_freshness_threshold_seconds: int = Field(
        default=86400,
        ge=60,
        validation_alias=AliasChoices(
            "DATA_FRESHNESS_THRESHOLD",
            "REGIMEX_DATA_FRESHNESS_THRESHOLD",
            "DATA_FRESHNESS_THRESHOLD_SECONDS",
            "REGIMEX_DATA_FRESHNESS_THRESHOLD_SECONDS",
        ),
        description="Freshness SLA threshold in seconds for active trading days (default 24h)",
    )
    data_stale_threshold_seconds: int = Field(
        default=259200,
        ge=300,
        validation_alias=AliasChoices(
            "DATA_STALE_THRESHOLD",
            "REGIMEX_DATA_STALE_THRESHOLD",
            "DATA_STALE_THRESHOLD_SECONDS",
            "REGIMEX_DATA_STALE_THRESHOLD_SECONDS",
        ),
        description="Threshold in seconds beyond which data is marked STALE (default 72h / 3 days)",
    )
    model_health_window: int = Field(
        default=100,
        ge=10,
        validation_alias=AliasChoices(
            "MODEL_HEALTH_WINDOW",
            "REGIMEX_MODEL_HEALTH_WINDOW",
        ),
        description="Number of observations evaluated for model health metrics and stability",
    )
    model_low_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "MODEL_LOW_CONFIDENCE_THRESHOLD",
            "REGIMEX_MODEL_LOW_CONFIDENCE_THRESHOLD",
        ),
        description="Confidence score below which a prediction is counted as low confidence",
    )
    model_drift_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "MODEL_DRIFT_THRESHOLD",
            "REGIMEX_MODEL_DRIFT_THRESHOLD",
        ),
        description="Jensen-Shannon / TV drift threshold for regime prediction distributions",
    )
    data_drift_threshold: float = Field(
        default=0.25,
        ge=0.0,
        validation_alias=AliasChoices(
            "DATA_DRIFT_THRESHOLD",
            "REGIMEX_DATA_DRIFT_THRESHOLD",
        ),
        description="PSI / distribution drift threshold for feature distributions",
    )
    observability_history_limit: int = Field(
        default=50,
        ge=5,
        le=1000,
        validation_alias=AliasChoices(
            "OBSERVABILITY_HISTORY_LIMIT",
            "REGIMEX_OBSERVABILITY_HISTORY_LIMIT",
        ),
        description="Maximum number of historical health snapshots retained in memory",
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

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: object, info: object) -> str:
        """Validate database URL and reject insecure default credentials in production."""
        val = str(value).strip() if value is not None else ""
        if not val:
            val = "postgresql+asyncpg://regimex:changeme@localhost:5432/regimex_dev"

        # Normalize postgresql:// or postgres:// to postgresql+asyncpg://
        if val.startswith("postgres://"):
            val = "postgresql+asyncpg://" + val[len("postgres://") :]
        elif val.startswith("postgresql://") and not val.startswith("postgresql+asyncpg://"):
            val = "postgresql+asyncpg://" + val[len("postgresql://") :]

        data = getattr(info, "data", {})
        env = data.get("env")
        if env == Environment.PRODUCTION:
            insecure_patterns = [
                "changeme",
                "changeme_dev_only",
                "insecure",
                "localhost:5432/regimex_dev",
            ]
            val_lower = val.lower()
            for pattern in insecure_patterns:
                if pattern in val_lower:
                    raise ValueError(
                        "REGIMEX_DATABASE_URL / DATABASE_URL must not use insecure default "
                        "or placeholder credentials in production. "
                        "Provide a valid managed database connection string."
                    )
            if not val_lower.startswith("postgresql+asyncpg://"):
                raise ValueError(
                    "Production database URL must use the postgresql+asyncpg:// scheme."
                )
        return val

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
            insecure_secret_patterns = [
                "change_me",
                "insecure-dev-secret",
                "changeme",
                "default_secret",
                "secretkey",
            ]
            if any(p in val_str.lower() for p in insecure_secret_patterns) or len(val_str) < 32:
                raise ValueError(
                    "REGIMEX_SECRET_KEY / AUTH_JWT_SECRET must be set to a secure random value "
                    "of at least 32 characters in production. "
                    'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
                )
        return value or "CHANGE_ME_in_production_use_32+_random_bytes"

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: object) -> str:
        """Validate log level string."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        val_upper = str(value).strip().upper() if value else "INFO"
        if val_upper not in allowed:
            raise ValueError(f"Invalid log_level: '{value}'. Allowed levels: {sorted(allowed)}")
        return val_upper

    @field_validator("log_format", mode="before")
    @classmethod
    def validate_log_format(cls, value: object) -> str:
        """Validate log format."""
        allowed = {"json", "text"}
        val_lower = str(value).strip().lower() if value else "json"
        if val_lower not in allowed:
            raise ValueError(f"Invalid log_format: '{value}'. Allowed formats: {sorted(allowed)}")
        return val_lower

    @model_validator(mode="after")
    def validate_ai_provider_invariants(self) -> Self:
        """Validate AI provider configuration invariants."""
        if self.ai_provider.strip().lower() == "openai":
            # If standard OpenAI endpoint without custom base URL, an API key is required
            if not self.ai_base_url and (not self.ai_api_key or not self.ai_api_key.strip()):
                raise ValueError(
                    "REGIMEX_AI_API_KEY must be provided when REGIMEX_AI_PROVIDER is 'openai' "
                    "and no custom AI_BASE_URL is configured."
                )
        return self

    # -------------------------------------------------------------------------
    # Convenience properties & methods
    # -------------------------------------------------------------------------
    def sanitized_database_url(self) -> str:
        """Return the database URL with password masked for safe logging/diagnostics."""
        try:
            from urllib.parse import urlsplit, urlunsplit

            parts = urlsplit(self.database_url)
            if parts.password:
                netloc = f"{parts.username or ''}:***@{parts.hostname or ''}"
                if parts.port:
                    netloc += f":{parts.port}"
                return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
            return self.database_url
        except Exception:
            return re.sub(r"://([^:]+):.*@", r"://\1:***@", self.database_url)

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
