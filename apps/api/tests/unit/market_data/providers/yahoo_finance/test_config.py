"""
Unit tests for YahooFinanceConfig.
"""

from __future__ import annotations

import pytest
from app.modules.market_data.infrastructure.providers.yahoo_finance.config import (
    YahooFinanceConfig,
)
from pydantic import ValidationError


class TestYahooFinanceConfig:
    def test_default_values(self) -> None:
        config = YahooFinanceConfig()
        assert config.timeout_seconds == 30
        assert config.max_retries == 2
        assert config.backoff_factor == 0.5
        assert config.user_agent is None
        assert config.proxy is None

    def test_no_api_key_field(self) -> None:
        """Explicit requirement: Yahoo Finance requires no API key; do not invent one."""
        config = YahooFinanceConfig()
        assert not hasattr(config, "api_key")
        assert not hasattr(config, "apiKey")

    def test_custom_values(self) -> None:
        config = YahooFinanceConfig(
            timeout_seconds=45,
            max_retries=3,
            backoff_factor=1.0,
            user_agent="RegimeX-Bot/1.0",
            proxy="http://localhost:8080",
        )
        assert config.timeout_seconds == 45
        assert config.max_retries == 3
        assert config.backoff_factor == 1.0
        assert config.user_agent == "RegimeX-Bot/1.0"
        assert config.proxy == "http://localhost:8080"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGIMEX_YAHOO_FINANCE_TIMEOUT_SECONDS", "60")
        monkeypatch.setenv("REGIMEX_YAHOO_FINANCE_MAX_RETRIES", "4")
        monkeypatch.setenv("REGIMEX_YAHOO_FINANCE_BACKOFF_FACTOR", "2.0")
        monkeypatch.setenv("REGIMEX_YAHOO_FINANCE_PROXY", "http://proxy.local:3128")

        config = YahooFinanceConfig()
        assert config.timeout_seconds == 60
        assert config.max_retries == 4
        assert config.backoff_factor == 2.0
        assert config.proxy == "http://proxy.local:3128"

    def test_invalid_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            YahooFinanceConfig(timeout_seconds=0)

    def test_invalid_max_retries_rejected(self) -> None:
        with pytest.raises(ValidationError):
            YahooFinanceConfig(max_retries=-1)

    def test_invalid_backoff_rejected(self) -> None:
        with pytest.raises(ValidationError):
            YahooFinanceConfig(backoff_factor=0.0)
