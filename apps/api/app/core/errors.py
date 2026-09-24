"""
RegimeX API — Error Handling Foundation & Domain Exception Boundary
==================================================================
Defines the platform exception hierarchy, API error contracts, and FastAPI
exception handlers that map domain and infrastructure errors into standard,
typed HTTP responses.

Standard RegimeX API Error Envelope:
  {
    "error": {
      "code": "ERROR_CODE",
      "message": "Human-readable description",
      "request_id": "...",
      "details": [...]
    }
  }

Architectural Rule:
  Domain modules remain pure Python and framework-independent.
  This module acts as the translation boundary converting domain exceptions
  into appropriate HTTP status codes and machine-readable error contracts.
"""

from __future__ import annotations

import logging
import traceback
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# =============================================================================
# API Error Response Models
# =============================================================================


class ApiErrorDetail(BaseModel):
    """Structured details for standard API error response."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    request_id: str = Field(description="Unique request correlation identifier")
    details: Any | None = Field(default=None, description="Optional diagnostic details")


class ApiError(BaseModel):
    """Standard top-level API error envelope."""

    model_config = ConfigDict(frozen=True)

    error: ApiErrorDetail


# =============================================================================
# Platform Exception Hierarchy
# =============================================================================


class RegimeXError(Exception):
    """
    Base exception for all RegimeX application and platform errors.

    All domain and infrastructure errors can inherit from this class
    or follow the domain exception protocol (http_status, error_code).
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,  # noqa: ANN401
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class BadRequestError(RegimeXError):
    """Malformed or invalid request parameters."""

    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"


class NotFoundError(RegimeXError):
    """Resource not found."""

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationError(RegimeXError):
    """Business-level validation failure (distinct from request schema validation)."""

    http_status = 422
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


def _build_error_content(
    error_code: str,
    message: str,
    request_id: str,
    details: object | None = None,
) -> dict[str, Any]:
    """Build the dictionary structure for ApiError."""
    payload: dict[str, Any] = {
        "code": error_code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        payload["details"] = details
    return {"error": payload}


def _get_request_id(request: Request) -> str:
    """Safely extract or generate the request correlation identifier."""
    return getattr(request.state, "request_id", None) or str(uuid.uuid4())


# =============================================================================
# Exception Handlers
# =============================================================================


async def regimex_error_handler(request: Request, exc: RegimeXError) -> JSONResponse:
    """Handle all RegimeX platform and inherited exceptions."""
    request_id = _get_request_id(request)

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
            "Application error: %s (status %d)",
            exc.message,
            exc.http_status,
            extra={
                "error_code": exc.error_code,
                "error_message": exc.message,
                "request_id": request_id,
                "path": request.url.path,
            },
        )

    return JSONResponse(
        status_code=exc.http_status,
        content=_build_error_content(
            error_code=exc.error_code,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
        ),
        headers={"X-Request-ID": request_id},
    )


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle domain exceptions that do not directly inherit from RegimeXError.

    Extracts http_status and error_code if defined on the exception class,
    defaulting to HTTP 422 for domain validation/logic errors.
    """
    request_id = _get_request_id(request)
    http_status = getattr(exc, "http_status", 422)
    error_code = getattr(exc, "error_code", "DOMAIN_ERROR")

    message = str(exc)

    logger.warning(
        "Domain error mapped to HTTP %d: %s",
        http_status,
        message,
        extra={
            "error_code": error_code,
            "request_id": request_id,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=http_status,
        content=_build_error_content(
            error_code=error_code,
            message=message,
            request_id=request_id,
            details=getattr(exc, "details", None),
        ),
        headers={"X-Request-ID": request_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard Starlette / FastAPI HTTPExceptions in standard error format."""
    request_id = _get_request_id(request)

    code_map: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_REQUIRED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_content(
            error_code=error_code,
            message=message,
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI / Pydantic schema validation errors."""
    request_id = _get_request_id(request)

    # Sanitize validation error details to avoid leaking internal objects
    sanitized_errors: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = list(err.get("loc", ()))
        msg = err.get("msg", "Validation error")
        err_type = err.get("type", "value_error")
        sanitized_errors.append(
            {
                "loc": loc,
                "msg": msg,
                "type": err_type,
            }
        )

    logger.warning(
        "Request validation failed for %s: %d errors",
        request.url.path,
        len(sanitized_errors),
        extra={"request_id": request_id, "path": request.url.path},
    )

    return JSONResponse(
        status_code=422,
        content=_build_error_content(
            error_code="VALIDATION_ERROR",
            message="Request validation failed.",
            request_id=request_id,
            details=sanitized_errors,
        ),
        headers={"X-Request-ID": request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected internal errors.

    Never leak stack traces, database credentials, or filesystem paths to clients.
    """
    request_id = _get_request_id(request)

    logger.error(
        "Unhandled internal server exception on %s: %s",
        request.url.path,
        exc,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "traceback": traceback.format_exc(),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_content(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred. Please try again later.",
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


# =============================================================================
# Handler Registration
# =============================================================================


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application instance.

    Wires platform errors, domain errors, HTTP exceptions, and validation errors.
    """
    # 1. Platform errors
    app.add_exception_handler(RegimeXError, regimex_error_handler)  # type: ignore[arg-type]

    # 2. Domain error hierarchies (without importing FastAPI into domain layers)
    try:
        from app.modules.backtesting.domain.errors import BacktestingError

        app.add_exception_handler(BacktestingError, domain_exception_handler)
    except ImportError:
        pass

    try:
        from app.modules.portfolio_risk.domain.errors import PortfolioRiskError

        app.add_exception_handler(PortfolioRiskError, domain_exception_handler)
    except ImportError:
        pass

    try:
        from app.modules.market_data.domain.errors import ProviderError, StorageError

        app.add_exception_handler(ProviderError, regimex_error_handler)  # type: ignore[arg-type]
        app.add_exception_handler(StorageError, regimex_error_handler)  # type: ignore[arg-type]
    except ImportError:
        pass

    try:
        from app.modules.regime_detection.domain.errors import RegimeDetectionError

        app.add_exception_handler(RegimeDetectionError, regimex_error_handler)  # type: ignore[arg-type]
    except ImportError:
        pass

    try:
        from app.modules.regime_intelligence.domain.errors import RegimeIntelligenceError

        app.add_exception_handler(RegimeIntelligenceError, regimex_error_handler)  # type: ignore[arg-type]
    except ImportError:
        pass

    try:
        from app.modules.regime_transition.domain.errors import RegimeTransitionError

        app.add_exception_handler(RegimeTransitionError, regimex_error_handler)  # type: ignore[arg-type]
    except ImportError:
        pass

    try:
        from app.modules.feature_engineering.domain.errors import FeatureEngineeringError

        app.add_exception_handler(FeatureEngineeringError, regimex_error_handler)  # type: ignore[arg-type]
    except ImportError:
        pass

    # 3. HTTP and Validation errors
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    # 4. Catch-all for unexpected internal exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)
