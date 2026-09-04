"""
RegimeX API — Test Configuration
===================================
Shared pytest fixtures, test application factory, and test client setup.

Testing conventions:
  - Tests are grouped by type: unit, integration, e2e
  - Unit tests must not require a running database or Redis
  - Integration tests use @pytest.mark.integration
  - All tests use REGIMEX_ENV=test (no production credentials needed)
  - The test settings override is applied via environment variable injection
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force test environment before any application code is imported
os.environ.setdefault("REGIMEX_ENV", "test")
os.environ.setdefault("REGIMEX_DEBUG", "false")
os.environ.setdefault("REGIMEX_SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("REGIMEX_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/regimex_test")
os.environ.setdefault("REGIMEX_REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("REGIMEX_LOG_LEVEL", "WARNING")
os.environ.setdefault("REGIMEX_LOG_FORMAT", "text")


@pytest.fixture(scope="session", autouse=True)
def _reset_settings_cache() -> None:
    """
    Clear the settings LRU cache before the test session starts.

    This ensures test environment variables are picked up cleanly
    and not polluted by any cached production/development configuration.
    """
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture(scope="session")
def test_app():
    """
    Create a fresh FastAPI application instance for the test session.

    Using session scope means the app is created once per test run,
    which is efficient for read-only endpoint tests.
    """
    from app.main import create_app

    return create_app()


@pytest.fixture(scope="session")
def client(test_app):
    """
    Provide a synchronous TestClient for the test session.

    For async endpoint testing, use httpx.AsyncClient with ASGITransport.
    """
    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c
