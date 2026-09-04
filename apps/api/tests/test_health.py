"""
RegimeX API — Health Endpoint Tests
======================================
Baseline tests proving:
  1. The FastAPI application can initialize correctly.
  2. The health liveness endpoint returns HTTP 200.
  3. The health readiness endpoint returns HTTP 200.
  4. Configuration can load in test mode without external dependencies.

These tests must:
  - Pass without a running database or Redis.
  - Pass without any production credentials.
  - Serve as the CI green-gate for the API foundation.
"""

from __future__ import annotations

import pytest


class TestApplicationStartup:
    """Verify the application can initialize without errors."""

    def test_app_can_be_created(self) -> None:
        """Application factory must produce a valid FastAPI instance."""
        from fastapi import FastAPI

        from app.main import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_settings_load_in_test_environment(self) -> None:
        """Settings must load cleanly in the test environment."""
        from app.core.config import Environment, get_settings

        get_settings.cache_clear()
        settings = get_settings()
        assert settings.env == Environment.TEST
        assert settings.debug is False
        assert settings.app_name == "RegimeX API"
        assert settings.api_v1_prefix == "/api/v1"

    def test_v1_router_is_registered(self, test_app) -> None:
        """The /api/v1 router must be registered on the application."""
        # Use openapi routes for a version-agnostic check that works across FastAPI versions
        openapi = test_app.openapi()
        paths = list(openapi.get("paths", {}).keys())
        assert any("/api/v1" in path for path in paths), (
            f"No /api/v1 paths found in OpenAPI spec. Got: {paths}. "
            "Check that v1_router is included in create_app()."
        )


class TestHealthLiveness:
    """Tests for the /api/v1/health/live liveness probe."""

    def test_liveness_returns_200(self, client) -> None:
        """Liveness probe must return HTTP 200."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    def test_liveness_response_shape(self, client) -> None:
        """Liveness response must include required fields."""
        response = client.get("/api/v1/health/live")
        body = response.json()
        assert body["status"] == "ok"
        assert "timestamp" in body
        assert "service" in body
        assert "version" in body

    def test_liveness_service_name(self, client) -> None:
        """Liveness response must report the correct service name."""
        response = client.get("/api/v1/health/live")
        body = response.json()
        assert body["service"] == "RegimeX API"

    def test_liveness_version_format(self, client) -> None:
        """Liveness response must report a semver-style version."""
        response = client.get("/api/v1/health/live")
        body = response.json()
        parts = body["version"].split(".")
        assert len(parts) == 3, f"Expected semver, got: {body['version']}"


class TestHealthReadiness:
    """Tests for the /api/v1/health/ready readiness probe."""

    def test_readiness_returns_200(self, client) -> None:
        """Readiness probe must return HTTP 200 in the V04 stub state."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_readiness_response_shape(self, client) -> None:
        """Readiness response must include required fields."""
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert body["status"] == "ready"
        assert "timestamp" in body
        assert "checks" in body
        assert isinstance(body["checks"], dict)

    def test_readiness_api_check_present(self, client) -> None:
        """Readiness checks dict must include the api check."""
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert "api" in body["checks"]
        assert body["checks"]["api"] == "ok"


class TestModuleImports:
    """Verify all domain module packages can be imported without errors."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "app.modules.market_discovery",
            "app.modules.market_data",
            "app.modules.data_quality",
            "app.modules.feature_engineering",
            "app.modules.regime_detection",
            "app.modules.regime_intelligence",
            "app.modules.risk_analytics",
            "app.modules.backtesting",
            "app.modules.research_workspace",
            "app.modules.ai_research",
            "app.modules.identity_access",
            "app.modules.administration",
            "app.modules.observability",
        ],
    )
    def test_domain_module_imports(self, module_path: str) -> None:
        """Each domain module package must be importable without errors."""
        import importlib

        module = importlib.import_module(module_path)
        assert module is not None, f"Failed to import: {module_path}"

    @pytest.mark.parametrize(
        "subpackage_path",
        [
            "app.modules.market_discovery.domain",
            "app.modules.market_data.domain",
            "app.modules.regime_detection.domain",
            "app.modules.observability.domain",
        ],
    )
    def test_domain_subpackage_imports(self, subpackage_path: str) -> None:
        """Domain sub-packages must be importable."""
        import importlib

        pkg = importlib.import_module(subpackage_path)
        assert pkg is not None


class TestRequestIDMiddleware:
    """Verify the request ID middleware is working."""

    def test_response_includes_request_id_header(self, client) -> None:
        """Every response must include an X-Request-ID header."""
        response = client.get("/api/v1/health/live")
        assert "x-request-id" in response.headers

    def test_custom_request_id_is_echoed(self, client) -> None:
        """A client-provided X-Request-ID must be echoed back."""
        custom_id = "test-request-id-12345"
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers.get("x-request-id") == custom_id
