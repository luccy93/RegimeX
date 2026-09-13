"""
RegimeX Market Data — Yahoo Finance Provider Configuration
===========================================================
Defines the environment-driven configuration model for the Yahoo Finance adapter.

Rules:
- Reads from environment variables prefixed with `REGIMEX_YAHOO_FINANCE_`.
- No API key is defined (Yahoo Finance historical data retrieval requires no credentials).
- Operational controls only: timeouts, bounded retries, backoff, and optional proxy.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class YahooFinanceConfig(BaseSettings):
    """
    Configuration options for Yahoo Finance market data provider.

    Environment variables:
        REGIMEX_YAHOO_FINANCE_TIMEOUT_SECONDS: Network request timeout (seconds).
        REGIMEX_YAHOO_FINANCE_MAX_RETRIES: Max retry attempts for transient failures.
        REGIMEX_YAHOO_FINANCE_BACKOFF_FACTOR: Initial backoff delay (seconds).
        REGIMEX_YAHOO_FINANCE_USER_AGENT: Optional custom user-agent string.
        REGIMEX_YAHOO_FINANCE_PROXY: Optional proxy URL.
    """

    model_config = SettingsConfigDict(
        env_prefix="REGIMEX_YAHOO_FINANCE_",
        env_file=".env",
        extra="ignore",
    )

    timeout_seconds: int = Field(
        default=30,
        gt=0,
        le=300,
        description="HTTP request timeout in seconds.",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for transient network failures.",
    )
    backoff_factor: float = Field(
        default=0.5,
        gt=0.0,
        le=10.0,
        description="Base delay factor in seconds for exponential backoff.",
    )
    user_agent: str | None = Field(
        default=None,
        description="Optional custom User-Agent header for vendor requests.",
    )
    proxy: str | None = Field(
        default=None,
        description="Optional proxy server URL (e.g. 'http://proxy.example.com:8080').",
    )
