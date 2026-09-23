"""
RegimeX API — Request Correlation ID Tests
==========================================
Verifies:
- Auto-generation of unique X-Request-ID when client provides none
- Preservation and echoing of client-provided X-Request-ID
- Request ID availability inside exception handlers and standard error envelopes
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestRequestIdMiddleware:
    def test_auto_generated_request_id(self, client: TestClient) -> None:
        """Every response must include an X-Request-ID header when omitted by client."""
        response = client.get("/health")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_client_provided_request_id_is_echoed(self, client: TestClient) -> None:
        """Client-provided X-Request-ID must be preserved and returned verbatim."""
        custom_id = "test-corr-id-987654"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers.get("x-request-id") == custom_id

    def test_error_response_contains_matching_request_id(self, client: TestClient) -> None:
        """Error responses must include the same request_id in headers and JSON payload."""
        custom_id = "error-trace-id-abc"
        response = client.get("/nonexistent-endpoint", headers={"X-Request-ID": custom_id})
        assert response.headers.get("x-request-id") == custom_id
        body = response.json()
        assert "error" in body
        assert body["error"]["request_id"] == custom_id
