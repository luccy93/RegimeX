"""
RegimeX Identity & Access — Domain Exceptions
=============================================
Defines domain and application exceptions for authentication, password policies,
token verification, and user identity management.

All exceptions inherit from RegimeXError to adhere to the standard ApiError contract
without importing web framework or HTTP constructs.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class IdentityAccessError(RegimeXError):
    """Base exception for all identity, access, and authentication domain errors."""

    http_status = 500
    error_code = "IDENTITY_ACCESS_ERROR"


class AuthenticationRequiredError(IdentityAccessError):
    """Raised when authentication credentials are required, missing, or invalid."""

    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"

    def __init__(
        self,
        message: str = "Authentication is required.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class InvalidCredentialsError(IdentityAccessError):
    """Raised when provided credentials (email/password) do not match."""

    http_status = 401
    error_code = "INVALID_CREDENTIALS"

    def __init__(
        self,
        message: str = "Invalid email or password.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class InactiveUserError(IdentityAccessError):
    """Raised when attempting to authenticate an inactive or deactivated user account."""

    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"

    def __init__(
        self,
        message: str = "User account is inactive.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class DuplicateEmailError(IdentityAccessError):
    """Raised when attempting to register an email address that already exists."""

    http_status = 409
    error_code = "CONFLICT"

    def __init__(
        self,
        message: str = "An account with this email address already exists.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class InvalidEmailError(IdentityAccessError):
    """Raised when an email address is malformed or invalid."""

    http_status = 422
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Invalid email address format.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class InvalidPasswordError(IdentityAccessError):
    """Raised when a password violates security policy (e.g., minimum length)."""

    http_status = 422
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Password must be at least 12 characters in length.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class InvalidTokenError(IdentityAccessError):
    """Raised when an authentication token is malformed, invalid, or forged."""

    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"

    def __init__(
        self,
        message: str = "Invalid or malformed authentication token.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class ExpiredTokenError(IdentityAccessError):
    """Raised when an authentication token has expired."""

    http_status = 401
    error_code = "AUTHENTICATION_REQUIRED"

    def __init__(
        self,
        message: str = "Authentication token has expired.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
