"""
RegimeX API — Security & Request Boundaries Middleware
======================================================
Implements HTTP middleware for:
1. Hardened Request ID correlation tracking (sanitizing inputs, preventing CRLF/log injection).
2. API Security Headers (nosniff, clickjacking, CSP, Permissions-Policy, conditional HSTS).
3. Request Boundary Protection (Content-Length bounding to prevent unbounded payloads).
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Restrict X-Request-ID to alphanumeric characters, dashes, and underscores (max 64 chars)
# to prevent header injection, log injection, or response-splitting attacks.
REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Sanitize and attach request correlation ID.

    If the client provides a safe X-Request-ID, it is preserved and echoed.
    If the provided ID is missing, oversized (>64 chars), or contains illegal
    characters, a fresh cryptographically random UUID4 is generated.
    """
    incoming_id = request.headers.get("X-Request-ID")
    clean_id = incoming_id.strip() if incoming_id else ""

    if clean_id and REQUEST_ID_REGEX.match(clean_id):
        request_id = clean_id
    else:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def security_headers_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Attach standard API security hardening headers to all HTTP responses.

    Headers applied:
      - X-Content-Type-Options: nosniff (prevents MIME confusion attacks)
      - X-Frame-Options: DENY (clickjacking protection)
      - Referrer-Policy: strict-origin-when-cross-origin (limits referrer leakage)
      - Permissions-Policy: Disables unused browser device features
      - Content-Security-Policy: default-src 'none' for API endpoints
        (exempts /docs and /redoc to preserve OpenAPI documentation UI)
      - Strict-Transport-Security: Added ONLY over HTTPS or in production environments;
        NEVER emitted during local plain HTTP development.
    """
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )

    path = request.url.path
    if not (path.startswith("/docs") or path.startswith("/redoc")):
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    settings = get_settings()
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    is_prod_secure = settings.is_production and not settings.is_development and not settings.is_test
    if is_https or is_prod_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


async def request_boundary_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Enforce request body boundaries by checking the Content-Length header.

    Rejects oversized payloads before application-level parsing, preventing
    unbounded memory consumption attacks.
    """
    content_length_header = request.headers.get("Content-Length")
    if content_length_header:
        try:
            content_length = int(content_length_header)
        except ValueError:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Invalid Content-Length header value.",
                        "request_id": request_id,
                        "details": None,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        if content_length < 0:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Content-Length cannot be negative.",
                        "request_id": request_id,
                        "details": None,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        settings = get_settings()
        if content_length > settings.max_request_body_bytes:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": (
                            f"Request body exceeds maximum allowed size of "
                            f"{settings.max_request_body_bytes} bytes."
                        ),
                        "request_id": request_id,
                        "details": None,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

    return await call_next(request)


def register_security_middlewares(app: FastAPI) -> None:
    """Register all security and request boundary middlewares on the FastAPI app."""
    app.middleware("http")(request_id_middleware)
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(request_boundary_middleware)
