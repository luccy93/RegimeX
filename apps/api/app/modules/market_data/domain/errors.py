"""
RegimeX Market Data — Domain Exception Hierarchy
=================================================
All provider-level errors that may propagate through the application layer
are defined here.  Provider adapters (infrastructure/) MUST catch
vendor-specific exceptions at the adapter boundary and translate them into
one of these types.

Why here, not in ``core/errors.py``?
  ``core/errors.py`` holds platform-wide HTTP-aware exceptions (mapped to
  HTTP status codes).  These provider exceptions are domain/application-level
  errors that carry richer context about *what went wrong at the data layer*
  before they are optionally mapped to HTTP responses at the API boundary.

Hierarchy:
  RegimeXError                    (core platform base)
  └── ProviderError               (all market data provider errors)
      ├── ProviderConfigurationError   (adapter mis-configured)
      ├── ProviderUnavailableError     (endpoint unreachable / timeout)
      ├── ProviderRateLimitError       (429 / quota exceeded)
      ├── ProviderAuthenticationError  (401 / invalid credentials)
      ├── ProviderDataError            (malformed / unexpected response)
      └── ProviderSymbolNotFoundError  (instrument not found)

Vendor isolation rule:
  NEVER include vendor SDK exception types in these classes.
  Adapters must strip all vendor-specific attributes before raising.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class ProviderError(RegimeXError):
    """
    Base class for all market data provider errors.

    All errors that originate from provider adapters must inherit from this
    class.  Downstream modules (application services, API handlers) can catch
    this base class to handle any provider failure generically.

    Attributes:
        provider_id: Identifier of the provider that raised this error.
                     May be empty string if the error occurred before the
                     provider identity was resolved.
    """

    error_code = "PROVIDER_ERROR"

    def __init__(
        self,
        message: str,
        provider_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.provider_id = provider_id

    def __str__(self) -> str:
        prefix = f"[provider={self.provider_id}] " if self.provider_id else ""
        return f"{prefix}{self.message}"


class ProviderConfigurationError(ProviderError):
    """
    The provider adapter is misconfigured.

    Raised when required configuration (API key, base URL, credentials) is
    absent or structurally invalid *before* any network call is attempted.

    Adapters should raise this during initialisation or the first call if
    the environment lacks required variables.
    """

    error_code = "PROVIDER_CONFIGURATION_ERROR"


class ProviderUnavailableError(ProviderError):
    """
    The provider endpoint is temporarily unreachable.

    Raised when network-level connectivity fails (connection refused,
    DNS resolution failure, timeout) or when the provider returns a 5xx
    server error.

    Adapters must catch vendor-specific connection exceptions and
    re-raise as this type.  Do NOT propagate raw ``httpx``, ``requests``,
    or vendor SDK connection errors.
    """

    error_code = "PROVIDER_UNAVAILABLE"


class ProviderRateLimitError(ProviderError):
    """
    The provider's rate limit or API quota has been exceeded.

    Raised when the provider returns a 429 Too Many Requests response or
    equivalent quota-exhaustion signal.

    Optional ``retry_after_seconds`` attribute may be set by adapters when
    the provider includes a ``Retry-After`` header or equivalent.
    """

    error_code = "PROVIDER_RATE_LIMIT"

    def __init__(
        self,
        message: str,
        provider_id: str = "",
        retry_after_seconds: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, provider_id=provider_id, details=details)
        self.retry_after_seconds = retry_after_seconds


class ProviderAuthenticationError(ProviderError):
    """
    Provider rejected the adapter's credentials.

    Raised when the provider returns a 401 Unauthorized or 403 Forbidden
    response due to missing, expired, or invalid API keys.

    Adapters must NOT include the raw API key or credential value in the
    exception message or details — log-safe error messages only.
    """

    error_code = "PROVIDER_AUTHENTICATION_ERROR"


class ProviderDataError(ProviderError):
    """
    The provider returned data that is structurally invalid or unexpected.

    Raised when:
    - Response JSON is malformed.
    - Required fields are missing from the vendor payload.
    - Data types do not match expected format (e.g. non-numeric price).
    - Normalization into ``OHLCVRecord`` fails due to unexpected vendor schema.

    Adapters must not include raw vendor response bodies in public exception
    attributes; only include sanitised diagnostic messages.
    """

    error_code = "PROVIDER_DATA_ERROR"


class ProviderSymbolNotFoundError(ProviderError):
    """
    The requested instrument/symbol was not found in the provider's catalogue.

    Raised when the provider explicitly responds that the ticker or instrument
    does not exist (as distinct from a general availability or auth failure).

    Attributes:
        symbol: The symbol that was not found.
    """

    error_code = "PROVIDER_SYMBOL_NOT_FOUND"

    def __init__(
        self,
        message: str,
        symbol: str,
        provider_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, provider_id=provider_id, details=details)
        self.symbol = symbol

    def __str__(self) -> str:
        prefix = f"[provider={self.provider_id}] " if self.provider_id else ""
        return f"{prefix}Symbol not found: {self.symbol!r} — {self.message}"


# =============================================================================
# Storage / Persistence Exception Hierarchy
# =============================================================================


class StorageError(RegimeXError):
    """
    Base exception for all market data persistence and repository errors.

    Translates lower-level SQLAlchemy, database, or connection failures into
    clean platform errors without leaking credentials or raw SQL strings.
    """

    error_code = "STORAGE_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class StorageConnectionError(StorageError):
    """Database connectivity failure or pool exhaustion."""

    error_code = "STORAGE_CONNECTION_ERROR"


class StorageIntegrityError(StorageError):
    """Database constraint or data integrity violation."""

    error_code = "STORAGE_INTEGRITY_ERROR"


class StorageNotFoundError(StorageError):
    """Requested record was not found in the persistence store."""

    error_code = "STORAGE_NOT_FOUND"
