"""
Unit and integration tests for RegimeX API error handling and translation boundaries.
===================================================================================
Verifies:
1. Standard error envelope structure { "error": { "code", "message", "request_id", "details" } }
2. HTTP 400, 404, 409, 422, 500, 503 error handling.
3. Domain exception translation (market_data, backtesting, portfolio_risk).
4. Validation error sanitization (no internal leaking).
5. 500 Internal Server Error sanitization (no traceback or sensitive leakage).
"""

from __future__ import annotations

import pytest
from app.core.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.main import create_app
from app.modules.backtesting.domain.errors import (
    InsufficientFundsError,
    InvalidMarketDataError,
)
from app.modules.market_data.domain.errors import (
    ProviderRateLimitError,
    ProviderSymbolNotFoundError,
    ProviderUnavailableError,
)
from app.modules.portfolio_risk.domain.errors import InvalidConfidenceLevelError
from fastapi import APIRouter
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_error_routes() -> TestClient:
    """Create test application instance with dedicated fault injection routes."""
    app = create_app()
    router = APIRouter(prefix="/api/v1/test-faults", tags=["Fault Testing"])

    @router.get("/bad-request")
    def trigger_bad_request() -> None:
        raise BadRequestError("Invalid query syntax.")

    @router.get("/not-found")
    def trigger_not_found() -> None:
        raise NotFoundError("Resource item 'xyz-123' does not exist.")

    @router.get("/conflict")
    def trigger_conflict() -> None:
        raise ConflictError("Resource item 'xyz-123' already exists.")

    @router.get("/service-unavailable")
    def trigger_service_unavailable() -> None:
        raise ServiceUnavailableError("Upstream engine is under maintenance.")

    @router.get("/provider-symbol-not-found")
    def trigger_symbol_not_found() -> None:
        raise ProviderSymbolNotFoundError(
            message="Ticker UNKNOWN not recognized by data provider.",
            symbol="UNKNOWN",
            provider_id="polygon",
        )

    @router.get("/provider-rate-limit")
    def trigger_provider_rate_limit() -> None:
        raise ProviderRateLimitError(
            message="Provider rate limit exceeded. Retry later.",
            provider_id="polygon",
            retry_after_seconds=60,
        )

    @router.get("/provider-unavailable")
    def trigger_provider_unavailable() -> None:
        raise ProviderUnavailableError(
            message="Connection timeout connecting to provider API.",
            provider_id="polygon",
        )

    @router.get("/backtesting-insufficient-funds")
    def trigger_insufficient_funds() -> None:
        raise InsufficientFundsError(
            required=15000.0,
            available=10000.0,
        )

    @router.get("/backtesting-invalid-data")
    def trigger_invalid_market_data() -> None:
        raise InvalidMarketDataError("OHLCV prices must be strictly positive.")

    @router.get("/risk-invalid-confidence")
    def trigger_invalid_confidence() -> None:
        raise InvalidConfidenceLevelError("Confidence level must be strictly between 0 and 1.")

    @router.get("/validate-query")
    def trigger_validation_query(limit: int) -> dict[str, int]:
        return {"limit": limit}

    @router.get("/unhandled-server-error")
    def trigger_unhandled() -> None:
        raise RuntimeError("Unexpected failure: db_conn://user:super_secret_pw@db.local:5432")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_standard_error_envelope_404(client_with_error_routes: TestClient) -> None:
    """Non-existent endpoints return 404 in standard ApiError envelope."""
    response = client_with_error_routes.get("/api/v1/non-existent-path")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == "NOT_FOUND"
    assert "message" in error
    assert "request_id" in error
    assert response.headers.get("X-Request-ID") == error["request_id"]


def test_platform_bad_request_error(client_with_error_routes: TestClient) -> None:
    """BadRequestError translates to HTTP 400 with BAD_REQUEST code."""
    response = client_with_error_routes.get("/api/v1/test-faults/bad-request")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert "Invalid query syntax" in data["error"]["message"]
    assert "request_id" in data["error"]


def test_platform_not_found_error(client_with_error_routes: TestClient) -> None:
    """NotFoundError translates to HTTP 404 with NOT_FOUND code."""
    response = client_with_error_routes.get("/api/v1/test-faults/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "xyz-123" in data["error"]["message"]


def test_platform_conflict_error(client_with_error_routes: TestClient) -> None:
    """ConflictError translates to HTTP 409 with CONFLICT code."""
    response = client_with_error_routes.get("/api/v1/test-faults/conflict")
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CONFLICT"


def test_platform_service_unavailable_error(client_with_error_routes: TestClient) -> None:
    """ServiceUnavailableError translates to HTTP 503 with SERVICE_UNAVAILABLE code."""
    response = client_with_error_routes.get("/api/v1/test-faults/service-unavailable")
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_provider_symbol_not_found_translation(client_with_error_routes: TestClient) -> None:
    """ProviderSymbolNotFoundError translates to HTTP 404 with PROVIDER_SYMBOL_NOT_FOUND code."""
    response = client_with_error_routes.get("/api/v1/test-faults/provider-symbol-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_SYMBOL_NOT_FOUND"
    assert "UNKNOWN" in data["error"]["message"]


def test_provider_rate_limit_translation(client_with_error_routes: TestClient) -> None:
    """ProviderRateLimitError translates to HTTP 429 with PROVIDER_RATE_LIMIT code."""
    response = client_with_error_routes.get("/api/v1/test-faults/provider-rate-limit")
    assert response.status_code == 429
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_RATE_LIMIT"


def test_provider_unavailable_translation(client_with_error_routes: TestClient) -> None:
    """ProviderUnavailableError translates to HTTP 503 with PROVIDER_UNAVAILABLE code."""
    response = client_with_error_routes.get("/api/v1/test-faults/provider-unavailable")
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_UNAVAILABLE"


def test_backtesting_insufficient_funds_translation(client_with_error_routes: TestClient) -> None:
    """InsufficientFundsError translates to HTTP 422 with INSUFFICIENT_FUNDS code and details."""
    response = client_with_error_routes.get("/api/v1/test-faults/backtesting-insufficient-funds")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_FUNDS"
    assert "details" in data["error"]
    details = data["error"]["details"]
    assert details["required_cash"] == 15000.0
    assert details["available_cash"] == 10000.0


def test_backtesting_invalid_data_translation(client_with_error_routes: TestClient) -> None:
    """InvalidMarketDataError translates to HTTP 422 with INVALID_MARKET_DATA code."""
    response = client_with_error_routes.get("/api/v1/test-faults/backtesting-invalid-data")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_MARKET_DATA"


def test_risk_invalid_confidence_translation(client_with_error_routes: TestClient) -> None:
    """InvalidConfidenceLevelError translates to HTTP 422 with INVALID_CONFIDENCE_LEVEL code."""
    response = client_with_error_routes.get("/api/v1/test-faults/risk-invalid-confidence")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_CONFIDENCE_LEVEL"


def test_validation_error_structure(client_with_error_routes: TestClient) -> None:
    """Schema validation error returns 422 with sanitized detail items."""
    # Query validation route with invalid parameter (limit is string not integer)
    response = client_with_error_routes.get("/api/v1/test-faults/validate-query?limit=not-an-int")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0
    err = data["error"]["details"][0]
    assert "loc" in err
    assert "msg" in err
    assert "type" in err


def test_unhandled_server_error_sanitization(client_with_error_routes: TestClient) -> None:
    """500 error never leaks exception messages, credentials, or stack traces."""
    response = client_with_error_routes.get("/api/v1/test-faults/unhandled-server-error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Verify sensitive string is NOT leaked
    assert "super_secret_pw" not in response.text
    assert "db_conn" not in response.text
    assert "Traceback" not in response.text
    # Generic safe message
    assert "unexpected internal server error" in data["error"]["message"].lower()
    # Request ID is preserved
    assert "request_id" in data["error"]
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]
