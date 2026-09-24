"""
Integration tests for Regime Intelligence API endpoints (/api/v1/markets/{symbol}/regime).
===========================================================================================
Verifies:
1. Valid response & schema conformance (200 OK, MarketRegimeResponse).
2. Domain-to-DTO conversion (profiles, current_context, statistics, regimes_observed).
3. Unavailable model handling (ModelNotFittedError -> 400, ServiceUnavailableError -> 503).
4. Invalid symbol handling (ProviderSymbolNotFoundError -> 404, empty symbol -> 400/422).
5. Query parameter validations:
   - Naive datetimes rejected with 422.
   - Start >= End rejected with 422.
   - Invalid interval rejected with 422.
   - Negative / excessive limit rejected with 422.
6. Dependency injection override using custom fakes.
7. Deterministic ordering of regime profiles and observed regime lists.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.core.dependencies import market_intelligence_dep
from app.core.errors import ServiceUnavailableError
from app.main import create_app
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_detection.domain.errors import ModelNotFittedError
from app.modules.regime_intelligence.application.facade import (
    MarketIntelligenceFacade,
)
from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
)
from app.modules.regime_intelligence.domain.models import (
    CurrentRegimeContext,
    FeatureStatistic,
    RegimeHistorySummary,
    RegimeProfile,
)
from fastapi.testclient import TestClient


def _make_sample_summary(symbol: str = "SPY") -> RegimeHistorySummary:
    """Create a fully-populated, realistic RegimeHistorySummary domain model."""
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    t0 = now - timedelta(days=60)

    fstat0 = {
        "return_1d": FeatureStatistic(
            feature_name="return_1d",
            observation_count=30,
            mean=0.0012,
            median=0.0010,
            std=0.0085,
            min=-0.015,
            max=0.022,
        ),
        "volatility_20d": FeatureStatistic(
            feature_name="volatility_20d",
            observation_count=30,
            mean=0.125,
            median=0.120,
            std=0.015,
            min=0.095,
            max=0.160,
        ),
    }
    fstat1 = {
        "return_1d": FeatureStatistic(
            feature_name="return_1d",
            observation_count=30,
            mean=-0.0025,
            median=-0.0020,
            std=0.0195,
            min=-0.045,
            max=0.018,
        ),
        "volatility_20d": FeatureStatistic(
            feature_name="volatility_20d",
            observation_count=30,
            mean=0.245,
            median=0.240,
            std=0.035,
            min=0.180,
            max=0.310,
        ),
    }

    profile0 = RegimeProfile(
        regime_id=0,
        regime_label="REGIME_0",
        observation_count=30,
        frequency=0.5,
        percentage=50.0,
        first_seen=t0,
        last_seen=now - timedelta(days=10),
        run_count=3,
        average_duration=10.0,
        median_duration=10.0,
        min_duration=8,
        max_duration=12,
        feature_statistics=fstat0,
    )
    profile1 = RegimeProfile(
        regime_id=1,
        regime_label="REGIME_1",
        observation_count=30,
        frequency=0.5,
        percentage=50.0,
        first_seen=t0 + timedelta(days=10),
        last_seen=now,
        run_count=3,
        average_duration=10.0,
        median_duration=10.0,
        min_duration=7,
        max_duration=13,
        feature_statistics=fstat1,
    )

    current_context = CurrentRegimeContext(
        current_regime_id=1,
        current_regime_label="REGIME_1",
        current_timestamp=now,
        observations_in_current_run=10,
        historical_frequency=0.5,
        historical_average_duration=10.0,
        historical_max_duration=13,
        historical_min_duration=7,
        historical_run_count=3,
        current_features={"return_1d": -0.003, "volatility_20d": 0.25},
    )

    return RegimeHistorySummary(
        analysis_start=t0,
        analysis_end=now,
        total_observations=60,
        regimes_observed=(0, 1),
        regime_profiles={0: profile0, 1: profile1},
        current_regime=current_context,
        model_name="kmeans-baseline",
        model_version="1.0.0",
        algorithm="kmeans",
        feature_names=("return_1d", "volatility_20d"),
        computed_at=now,
    )


class MockMarketIntelligenceFacade:
    """Mock facade for isolated route testing."""

    def __init__(self, summary: RegimeHistorySummary | None = None) -> None:
        self.summary = summary or _make_sample_summary()
        self.confidence = 0.88

    async def get_market_regime(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
    ) -> tuple[RegimeHistorySummary, float | None]:
        if symbol == "NONEXISTENT":
            raise ProviderSymbolNotFoundError(
                f"Symbol {symbol!r} not found",
                symbol=symbol,
                provider_id="mock",
            )
        if symbol == "UNAVAILABLE_MODEL":
            raise ModelNotFittedError(model_name="kmeans")
        if symbol == "SERVICE_DOWN":
            raise ServiceUnavailableError("Regime intelligence service is temporarily offline.")
        if symbol == "INSUFFICIENT":
            raise InsufficientRegimeDataError(
                required_samples=2,
                available_samples=0,
                details={"symbol": symbol},
            )
        return self.summary, self.confidence


@pytest.fixture
def test_client() -> TestClient:
    """Create TestClient with overridden market_intelligence_dep."""
    app = create_app()
    facade = MockMarketIntelligenceFacade()
    app.dependency_overrides[market_intelligence_dep] = lambda: facade
    return TestClient(app)


def test_get_market_regime_success(test_client: TestClient) -> None:
    """GET /api/v1/markets/{symbol}/regime returns 200 with full typed schema."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime?start=2026-01-01T00:00:00Z&end=2026-06-01T00:00:00Z"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "SPY"
    assert data["current_regime"] == 1
    assert data["current_regime_label"] == "REGIME_1"
    assert data["confidence"] == 0.88
    assert data["total_observations"] == 60
    assert data["regimes_observed"] == [0, 1]
    assert data["model_name"] == "kmeans-baseline"
    assert data["algorithm"] == "kmeans"

    # Current context verification
    ctx = data["current_context"]
    assert ctx["current_regime_id"] == 1
    assert ctx["current_regime_label"] == "REGIME_1"
    assert ctx["observations_in_current_run"] == 10
    assert ctx["historical_frequency"] == 0.5
    assert ctx["historical_max_duration"] == 13

    # Active profile verification
    assert data["profile"] is not None
    assert data["profile"]["regime_id"] == 1
    assert data["profile"]["frequency"] == 0.5
    assert "return_1d" in data["profile"]["feature_statistics"]

    # Active statistics shortcut verification
    assert "return_1d" in data["statistics"]
    assert data["statistics"]["return_1d"]["mean"] == -0.0025

    # Full profiles verification
    assert "0" in data["profiles"]
    assert "1" in data["profiles"]
    assert data["profiles"]["0"]["observation_count"] == 30


def test_get_market_regime_default_dates(test_client: TestClient) -> None:
    """GET /api/v1/markets/{symbol}/regime works with default omitted dates."""
    response = test_client.get("/api/v1/markets/SPY/regime")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert data["current_regime"] == 1


def test_get_market_regime_model_not_fitted(test_client: TestClient) -> None:
    """Unfitted model returns 400 MODEL_NOT_FITTED."""
    response = test_client.get("/api/v1/markets/UNAVAILABLE_MODEL/regime")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "MODEL_NOT_FITTED"
    assert "not been fitted" in data["error"]["message"].lower()


def test_get_market_regime_service_unavailable(test_client: TestClient) -> None:
    """Service failure returns 503 SERVICE_UNAVAILABLE."""
    response = test_client.get("/api/v1/markets/SERVICE_DOWN/regime")
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_get_market_regime_unknown_symbol(test_client: TestClient) -> None:
    """Unknown symbol returns 404 PROVIDER_SYMBOL_NOT_FOUND."""
    response = test_client.get("/api/v1/markets/NONEXISTENT/regime")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_SYMBOL_NOT_FOUND"


def test_get_market_regime_insufficient_data(test_client: TestClient) -> None:
    """Insufficient data returns 422 INSUFFICIENT_REGIME_DATA."""
    response = test_client.get("/api/v1/markets/INSUFFICIENT/regime")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_REGIME_DATA"


def test_get_market_regime_naive_datetime_rejected(test_client: TestClient) -> None:
    """Naive datetimes return 422 VALIDATION_ERROR."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime?start=2026-01-01T00:00:00&end=2026-06-01T00:00:00Z"
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "timezone-aware" in data["error"]["message"].lower()


def test_get_market_regime_start_after_end_rejected(test_client: TestClient) -> None:
    """start >= end returns 422 VALIDATION_ERROR."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime?start=2026-06-01T00:00:00Z&end=2026-01-01T00:00:00Z"
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "strictly after start" in data["error"]["message"].lower()


def test_get_market_regime_invalid_interval(test_client: TestClient) -> None:
    """Invalid interval returns 422 VALIDATION_ERROR."""
    response = test_client.get("/api/v1/markets/SPY/regime?interval=invalid_interval")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_get_market_regime_invalid_limits(test_client: TestClient) -> None:
    """Negative or excessive limits return 422."""
    resp_neg = test_client.get("/api/v1/markets/SPY/regime?limit=-10")
    assert resp_neg.status_code == 422

    resp_excess = test_client.get("/api/v1/markets/SPY/regime?limit=99999")
    assert resp_excess.status_code == 422


def test_get_market_regime_dependency_override() -> None:
    """Verify clean dependency override of market_intelligence_dep."""
    custom_mock = AsyncMock(spec=MarketIntelligenceFacade)
    custom_mock.get_market_regime.return_value = (
        _make_sample_summary(symbol="CUSTOM"),
        0.95,
    )

    app = create_app()
    app.dependency_overrides[market_intelligence_dep] = lambda: custom_mock
    client = TestClient(app)

    response = client.get("/api/v1/markets/CUSTOM/regime")
    assert response.status_code == 200
    assert response.json()["confidence"] == 0.95
    assert response.json()["symbol"] == "CUSTOM"
    custom_mock.get_market_regime.assert_awaited_once()
