"""
Unit tests — Provider exception hierarchy.

Tests cover:
- All provider errors inherit from ProviderError → RegimeXError.
- Error codes are set correctly on each subtype.
- provider_id and symbol attributes are stored.
- retry_after_seconds on ProviderRateLimitError.
- __str__ representations are informative.
- No vendor-specific exception types are referenced.
"""

from __future__ import annotations

import pytest
from app.core.errors import RegimeXError
from app.modules.market_data.domain.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderDataError,
    ProviderError,
    ProviderRateLimitError,
    ProviderSymbolNotFoundError,
    ProviderUnavailableError,
)

# =============================================================================
# Exception hierarchy correctness
# =============================================================================


class TestExceptionHierarchy:
    def test_provider_error_is_regimex_error(self) -> None:
        exc = ProviderError("base error")
        assert isinstance(exc, RegimeXError)

    def test_configuration_error_is_provider_error(self) -> None:
        exc = ProviderConfigurationError("bad config")
        assert isinstance(exc, ProviderError)
        assert isinstance(exc, RegimeXError)

    def test_unavailable_error_is_provider_error(self) -> None:
        exc = ProviderUnavailableError("timeout")
        assert isinstance(exc, ProviderError)

    def test_rate_limit_error_is_provider_error(self) -> None:
        exc = ProviderRateLimitError("429")
        assert isinstance(exc, ProviderError)

    def test_authentication_error_is_provider_error(self) -> None:
        exc = ProviderAuthenticationError("invalid key")
        assert isinstance(exc, ProviderError)

    def test_data_error_is_provider_error(self) -> None:
        exc = ProviderDataError("malformed response")
        assert isinstance(exc, ProviderError)

    def test_symbol_not_found_is_provider_error(self) -> None:
        exc = ProviderSymbolNotFoundError("not found", symbol="BOGUS")
        assert isinstance(exc, ProviderError)


# =============================================================================
# Error codes
# =============================================================================


class TestErrorCodes:
    def test_provider_error_code(self) -> None:
        assert ProviderError.error_code == "PROVIDER_ERROR"

    def test_configuration_error_code(self) -> None:
        assert ProviderConfigurationError.error_code == "PROVIDER_CONFIGURATION_ERROR"

    def test_unavailable_error_code(self) -> None:
        assert ProviderUnavailableError.error_code == "PROVIDER_UNAVAILABLE"

    def test_rate_limit_error_code(self) -> None:
        assert ProviderRateLimitError.error_code == "PROVIDER_RATE_LIMIT"

    def test_authentication_error_code(self) -> None:
        assert ProviderAuthenticationError.error_code == "PROVIDER_AUTHENTICATION_ERROR"

    def test_data_error_code(self) -> None:
        assert ProviderDataError.error_code == "PROVIDER_DATA_ERROR"

    def test_symbol_not_found_error_code(self) -> None:
        assert ProviderSymbolNotFoundError.error_code == "PROVIDER_SYMBOL_NOT_FOUND"


# =============================================================================
# provider_id attribute
# =============================================================================


class TestProviderIdAttribute:
    def test_provider_id_stored(self) -> None:
        exc = ProviderError("msg", provider_id="yahoo_finance")
        assert exc.provider_id == "yahoo_finance"

    def test_provider_id_defaults_to_empty_string(self) -> None:
        exc = ProviderError("msg")
        assert exc.provider_id == ""

    def test_provider_id_in_str_representation(self) -> None:
        exc = ProviderError("something failed", provider_id="my_provider")
        assert "my_provider" in str(exc)

    def test_no_provider_id_in_str_when_empty(self) -> None:
        exc = ProviderError("something failed")
        assert str(exc) == "something failed"


# =============================================================================
# ProviderRateLimitError extras
# =============================================================================


class TestProviderRateLimitError:
    def test_retry_after_stored(self) -> None:
        exc = ProviderRateLimitError("quota exceeded", retry_after_seconds=60)
        assert exc.retry_after_seconds == 60

    def test_retry_after_defaults_to_none(self) -> None:
        exc = ProviderRateLimitError("quota exceeded")
        assert exc.retry_after_seconds is None

    def test_provider_id_stored_with_retry_after(self) -> None:
        exc = ProviderRateLimitError("429", provider_id="alpha_vantage", retry_after_seconds=30)
        assert exc.provider_id == "alpha_vantage"
        assert exc.retry_after_seconds == 30


# =============================================================================
# ProviderSymbolNotFoundError extras
# =============================================================================


class TestProviderSymbolNotFoundError:
    def test_symbol_stored(self) -> None:
        exc = ProviderSymbolNotFoundError("not found", symbol="FAKE123")
        assert exc.symbol == "FAKE123"

    def test_symbol_in_str(self) -> None:
        exc = ProviderSymbolNotFoundError("not found", symbol="FAKE123")
        assert "FAKE123" in str(exc)

    def test_provider_id_and_symbol_in_str(self) -> None:
        exc = ProviderSymbolNotFoundError(
            "not found", symbol="FAKE123", provider_id="test_provider"
        )
        s = str(exc)
        assert "test_provider" in s
        assert "FAKE123" in s


# =============================================================================
# details dict
# =============================================================================


class TestProviderErrorDetails:
    def test_details_default_empty(self) -> None:
        exc = ProviderError("msg")
        assert exc.details == {}

    def test_details_stored(self) -> None:
        exc = ProviderDataError("bad data", details={"field": "close", "value": "N/A"})
        assert exc.details["field"] == "close"

    def test_details_not_shared_between_instances(self) -> None:
        exc1 = ProviderError("a")
        exc2 = ProviderError("b")
        exc1.details["x"] = 1
        assert "x" not in exc2.details


# =============================================================================
# can_be_caught as Exception
# =============================================================================


class TestCanBeCaughtAsException:
    def test_provider_error_is_catchable_as_provider_error(self) -> None:
        """ProviderUnavailableError must be catchable as its base ProviderError type."""
        exc = ProviderUnavailableError("down")
        assert isinstance(exc, ProviderError)

    def test_provider_error_can_be_raised_and_caught(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            raise ProviderUnavailableError("down")

    def test_provider_error_catchable_as_regimex_error(self) -> None:
        with pytest.raises(RegimeXError):
            raise ProviderRateLimitError("429")

    def test_subtypes_catchable_as_provider_error(self) -> None:
        with pytest.raises(ProviderError):
            raise ProviderSymbolNotFoundError("missing", symbol="X")
