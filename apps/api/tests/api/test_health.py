"""
RegimeX API — Health Endpoint Tests
====================================
Verifies:
- GET /health process liveness check returns HTTP 200 and ok status
- Lightweight execution without calling external services
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthLivenessProbe:
    def test_health_returns_200(self, client: TestClient) -> None:
        """GET /health must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_shape(self, client: TestClient) -> None:
        """GET /health must return the standard liveness payload."""
        response = client.get("/health")
        body = response.json()
        assert body == {"status": "ok"}
