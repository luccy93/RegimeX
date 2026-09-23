"""
RegimeX API — Readiness Endpoint Tests
======================================
Verifies:
- GET /ready returns HTTP 200 and 'ready' when dependencies pass
- GET /ready returns HTTP 503 and 'not_ready' when a dependency check fails
- Dependency injection allows overriding the readiness checker
"""

from __future__ import annotations

from app.core.dependencies import ReadinessChecker, readiness_checker_dep
from app.main import create_app
from fastapi.testclient import TestClient


class TestReadinessProbe:
    def test_readiness_default_ready(self, client: TestClient) -> None:
        """GET /ready must return HTTP 200 with status ready."""
        response = client.get("/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["checks"]["application"] == "ok"
        assert "timestamp" in body

    def test_readiness_not_ready_state_via_dependency_override(self) -> None:
        """GET /ready must return HTTP 503 when an infrastructure check reports a failure."""
        app = create_app()

        class FailingReadinessChecker(ReadinessChecker):
            async def check(self) -> dict[str, str]:
                return {"application": "ok", "database": "connection_failed"}

        app.dependency_overrides[readiness_checker_dep] = lambda: FailingReadinessChecker()

        with TestClient(app) as test_client:
            response = test_client.get("/ready")
            assert response.status_code == 503
            body = response.json()
            assert body["status"] == "not_ready"
            assert body["checks"]["database"] == "connection_failed"
