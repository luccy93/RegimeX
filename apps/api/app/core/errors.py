"""
RegimeX API — Error Handling Foundation
=========================================
Defines the platform exception hierarchy and FastAPI exception handlers.

All error responses follow the standard RegimeX JSON envelope:
  {
    "success": false,
    "data": null,
    "meta": { "request_id": "...", "timestamp": "..." },
    "error": {
      "code": "ERROR_CODE",
      "message": "Human-readable description",
      "details": {}
    }
  }
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Platform Exception Hierarchy
# =============================================================================


class RegimeXError(Exception):
    """
    Base exception for all RegimeX application errors.

    All domain and infrastructure errors should inherit from this class
    to ensure consistent error serialization and HTTP response mapping.
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class NotFoundError(RegimeXError):
    """Resource not found."""

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationError(RegimeXError):
    """Business-level validation failure (distinct from request schema validation)."""

    http_status = 422  # HTTP 422 Unprocessable Content
    error_code = "VALIDATION_ERROR"


class ConflictError(RegimeXError):
    """Resource conflict (e.g., duplicate record)."""

    http_status = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class AuthenticationError(RegimeXError):
    """Authentication required or credentials invalid."""

    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_REQUIRED"


class AuthorizationError(RegimeXError):
    """Authenticated user lacks required permission."""

    http_status = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"


class RateLimitError(RegimeXError):
    """Request rate limit exceeded."""

    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


class ServiceUnavailableError(RegimeXError):
    """External dependency or internal service temporarily unavailable."""

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"


# =============================================================================
# Response Envelope Builder
# =============================================================================


def _error_envelope(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a standard RegimeX error response envelope."""
    return {
        "success": False,
        "data": None,
        "meta": {
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(tz=UTC).isoformat(),
        },
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
        },
    }


# =============================================================================
# Exception Handlers
# =============================================================================


async def regimex_error_handler(request: Request, exc: RegimeXError) -> JSONResponse:
    """Handle all RegimeX application exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    if exc.http_status >= 500:
        logger.exception(
            "Unhandled application error",
            extra={
                "error_code": exc.error_code,
                "request_id": request_id,
                "path": request.url.path,
            },
        )
    else:
        logger.warning(
            "Application error",
            extra={
                "error_code": exc.error_code,
                "message": exc.message,
                "request_id": request_id,
                "path": request.url.path,
            },
        )

    return JSONResponse(
        status_code=exc.http_status,
        content=_error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        ),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    details = {"validation_errors": exc.errors()}
    logger.warning(
        "Request validation failed",
        extra={"request_id": request_id, "path": request.url.path},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_envelope(
            error_code="REQUEST_VALIDATION_ERROR",
            message="The request payload failed schema validation.",
            details=details,
            request_id=request_id,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors. Never leak stack traces to clients."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "traceback": traceback.format_exc(),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_envelope(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id,
        ),
    )


# =============================================================================
# Handler Registration
# =============================================================================


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application instance.

    Call this from the application factory (main.py) during startup.
    """
    app.add_exception_handler(RegimeXError, regimex_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
