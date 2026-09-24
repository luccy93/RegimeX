"""
Integration tests for Transition Analytics API endpoints.
Route: /api/v1/markets/{symbol}/regime/transitions
===================================================================================
Verifies:
1. Valid response & schema conformance (200 OK, MarketTransitionResponse).
2. Analytics mapping (probabilities, count_matrix, probability_matrix, rankings, entropy).
3. Invalid parameter handling (naive datetime, start >= end, invalid interval, negative limits).
4. Unavailable / insufficient data handling (422 INSUFFICIENT_TRANSITION_DATA).
5. Deterministic ordering of regime matrices, rankings, and observed regimes.
6. Dependency injection override of MarketIntelligenceFacade.
7. Unknown symbol returns 404.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.core.dependencies import market_intelligence_dep
from app.main import create_app
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_intelligence.application.facade import (
    MarketIntelligenceFacade,
)
from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
)
from app.modules.regime_transition.domain.models import (
    TransitionAnalyticsResult,
)
from app.modules.regime_transition.infrastructure.analytics import (
    RegimeTransitionAnalytics,
)
from fastapi.testclient import TestClient


def _make_sample_transition_analytics() -> TransitionAnalyticsResult:
    """Generate authentic, fully validated TransitionAnalyticsResult via the V12 engine."""
    analytics = RegimeTransitionAnalytics()
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    timestamps = tuple(base_time + timedelta(days=i) for i in range(40))
    # Pattern: 0, 0, 0, 1, 1, 2, 2, 0, 0, 1...
    regimes = tuple((i // 4) % 3 for i in range(40))
    return analytics.analyze_from_series(timestamps=timestamps, regime_ids=regimes, n_regimes=3)


class MockTransitionFacade:
    """Mock facade for transition route integration testing."""

    def __init__(self, analytics: TransitionAnalyticsResult | None = None) -> None:
        self.analytics = analytics or _make_sample_transition_analytics()

    async def get_transition_analytics(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
    ) -> TransitionAnalyticsResult:
        if symbol == "NONEXISTENT":
            raise ProviderSymbolNotFoundError(
                f"Symbol {symbol!r} not found",
                symbol=symbol,
                provider_id="mock",
            )
        if symbol == "INSUFFICIENT":
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=1,
            )
        return self.analytics


@pytest.fixture
def test_client() -> TestClient:
    """Create TestClient with overridden market_intelligence_dep."""
    app = create_app()
    facade = MockTransitionFacade()
    app.dependency_overrides[market_intelligence_dep] = lambda: facade
    return TestClient(app)


def test_get_regime_transitions_success(test_client: TestClient) -> None:
    """GET /api/v1/markets/{symbol}/regime/transitions returns 200 with complete analytics."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime/transitions?start=2026-01-01T00:00:00Z&end=2026-06-01T00:00:00Z"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "SPY"
    assert data["regimes"] == [0, 1, 2]

    # Verify probability and count matrices
    assert len(data["probability_matrix"]) == 3
    assert len(data["count_matrix"]) == 3
    for row in data["probability_matrix"]:
        assert len(row) == 3
        assert sum(row) == pytest.approx(1.0, abs=1e-5)

    # Verify shift matrices
    assert len(data["regime_change_counts"]) == 3
    assert len(data["regime_change_probabilities"]) == 3
    # Diagonal of shift matrix must be 0
    for i in range(3):
        assert data["regime_change_counts"][i][i] == 0

    # Verify per-regime analytics
    assert "0" in data["regime_analytics"]
    assert "1" in data["regime_analytics"]
    assert "2" in data["regime_analytics"]

    r0 = data["regime_analytics"]["0"]
    assert r0["regime_id"] == 0
    assert r0["persistence_probability"] > 0.0
    assert r0["change_rate"] >= 0.0
    assert "transition_entropy" in r0
    assert "rankings" in r0
    assert isinstance(r0["rankings"], list)

    # Verify global analytics
    ga = data["global_analytics"]
    assert ga["total_observations"] == 40
    assert ga["total_consecutive_transitions"] == 39
    assert ga["number_of_regimes"] == 3
    assert ga["global_change_rate"] + ga["global_persistence_rate"] == pytest.approx(1.0, abs=1e-5)

    # Verify flat pairwise probabilities
    assert len(data["probabilities"]) == 9  # 3x3 matrix


def test_get_regime_transitions_default_dates(test_client: TestClient) -> None:
    """Transitions endpoint works with omitted default date window."""
    response = test_client.get("/api/v1/markets/SPY/regime/transitions")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert "probability_matrix" in data


def test_get_regime_transitions_unknown_symbol(test_client: TestClient) -> None:
    """Unknown symbol returns 404 PROVIDER_SYMBOL_NOT_FOUND."""
    response = test_client.get("/api/v1/markets/NONEXISTENT/regime/transitions")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_SYMBOL_NOT_FOUND"


def test_get_regime_transitions_insufficient_data(test_client: TestClient) -> None:
    """Fewer than 2 observations returns 422 INSUFFICIENT_TRANSITION_DATA."""
    response = test_client.get("/api/v1/markets/INSUFFICIENT/regime/transitions")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INSUFFICIENT_TRANSITION_DATA"


def test_get_regime_transitions_naive_datetime_rejected(test_client: TestClient) -> None:
    """Naive start/end timestamps return 422 VALIDATION_ERROR."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime/transitions?start=2026-01-01T00:00:00&end=2026-06-01T00:00:00Z"
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "timezone-aware" in data["error"]["message"].lower()


def test_get_regime_transitions_start_after_end_rejected(test_client: TestClient) -> None:
    """start >= end returns 422 VALIDATION_ERROR."""
    response = test_client.get(
        "/api/v1/markets/SPY/regime/transitions?start=2026-06-01T00:00:00Z&end=2026-01-01T00:00:00Z"
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "strictly after start" in data["error"]["message"].lower()


def test_get_regime_transitions_invalid_interval(test_client: TestClient) -> None:
    """Invalid interval returns 422 VALIDATION_ERROR."""
    response = test_client.get("/api/v1/markets/SPY/regime/transitions?interval=bad")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_get_regime_transitions_invalid_limits(test_client: TestClient) -> None:
    """Negative or excessive limits return 422."""
    assert test_client.get("/api/v1/markets/SPY/regime/transitions?limit=0").status_code == 422
    assert test_client.get("/api/v1/markets/SPY/regime/transitions?limit=99999").status_code == 422


def test_get_regime_transitions_deterministic_ordering(test_client: TestClient) -> None:
    """Matrix rows and regime lists are deterministically ordered by canonical regime ID."""
    resp1 = test_client.get("/api/v1/markets/SPY/regime/transitions")
    resp2 = test_client.get("/api/v1/markets/SPY/regime/transitions")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["probability_matrix"] == resp2.json()["probability_matrix"]
    assert resp1.json()["count_matrix"] == resp2.json()["count_matrix"]
    assert resp1.json()["regimes"] == [0, 1, 2]


def test_get_regime_transitions_dependency_override() -> None:
    """Verify clean dependency injection override."""
    custom_mock = AsyncMock(spec=MarketIntelligenceFacade)
    custom_mock.get_transition_analytics.return_value = _make_sample_transition_analytics()

    app = create_app()
    app.dependency_overrides[market_intelligence_dep] = lambda: custom_mock
    client = TestClient(app)

    response = client.get("/api/v1/markets/OVERRIDDEN/regime/transitions")
    assert response.status_code == 200
    assert response.json()["symbol"] == "OVERRIDDEN"
    custom_mock.get_transition_analytics.assert_awaited_once()
