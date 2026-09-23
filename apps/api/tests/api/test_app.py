"""
RegimeX API — Application Entrypoint & Root Endpoint Tests
==========================================================
Verifies:
- create_app() factory returns a configured FastAPI application
- GET / root endpoint returns expected machine-readable metadata
- OpenAPI metadata (title, version, description, versioned routes)
- Documentation and schema endpoints (/docs, /openapi.json)
"""

from __future__ import annotations

from app.core.config import get_settings
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAppFactoryAndRoot:
    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app() must return a valid FastAPI application instance."""
        app = create_app()
        assert isinstance(app, FastAPI)
        settings = get_settings()
        assert app.title == settings.app_name
        assert app.version == settings.app_version
        assert "RegimeX" in app.description

    def test_root_endpoint_metadata(self, client: TestClient) -> None:
        """GET / must return machine-readable platform metadata."""
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "RegimeX API"
        assert body["version"] == "1.0.0"
        assert body["api_version"] == "v1"
        assert body["status"] == "ok"

    def test_openapi_spec_includes_versioned_routes(self, test_app: FastAPI) -> None:
        """OpenAPI schema must include versioned /api/v1 routes."""
        schema = test_app.openapi()
        paths = schema.get("paths", {})
        assert "/" in paths
        assert "/health" in paths
        assert "/ready" in paths
        assert "/api/v1/health/live" in paths
        assert "/api/v1/health/ready" in paths
        assert "/api/v1/markets" in paths
        assert "/api/v1/markets/{symbol}/data" in paths

    def test_openapi_json_endpoint_accessible(self, client: TestClient) -> None:
        """GET /openapi.json must be accessible and return valid OpenAPI JSON."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        body = response.json()
        assert "openapi" in body
        assert body["info"]["title"] == "RegimeX API"
        assert body["info"]["version"] == "1.0.0"
