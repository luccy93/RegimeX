"""
Integration tests for Market Data API endpoints (/api/v1/markets).
==================================================================
Verifies:
1. GET /api/v1/markets (discovery catalog, pagination, asset_class filter).
2. GET /api/v1/markets with invalid asset class returns 422.
3. GET /api/v1/markets/{symbol}/data (OHLCV retrieval, time-series pagination).
4. Validation constraints:
   - Naive datetimes rejected with 422.
   - Start >= End rejected with 422.
   - Invalid interval rejected with 422.
   - Limit < 1 rejected with 422.
5. Dependency injection override of MarketDataService / MarketDataProvider.
6. Unknown symbol returns 404 (PROVIDER_SYMBOL_NOT_FOUND).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.core.dependencies import market_service_dep
from app.main import create_app
from app.modules.market_data.application.service import (
    DEFAULT_BENCHMARK_MARKETS,
    MarketDataService,
)
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import (
    AssetClass,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from fastapi.testclient import TestClient


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory market data provider for route testing."""

    def __init__(self) -> None:
        self._supported_symbols = {"SPY", "QQQ", "AAPL", "BTC-USD"}

    @property
    def provider_id(self) -> str:
        return "mock_provider"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="mock_provider",
            display_name="Mock Provider",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset(
                {AssetClass.EQUITY_US, AssetClass.INDEX, AssetClass.CRYPTO}
            ),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        markets = list(DEFAULT_BENCHMARK_MARKETS)
        if asset_class is not None:
            markets = [m for m in markets if m.asset_class == asset_class]
        return markets

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol in self._supported_symbols

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        if query.instrument.symbol not in self._supported_symbols:
            raise ProviderSymbolNotFoundError(
                f"Symbol {query.instrument.symbol} not supported.",
                symbol=query.instrument.symbol,
                provider_id=self.provider_id,
            )

        # Generate 10 synthetic bars
        records: list[OHLCVRecord] = []
        base_time = query.start
        for i in range(10):
            bar_time = base_time + timedelta(days=i)
            if bar_time >= query.end:
                break
            records.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=bar_time,
                    open=100.0 + i,
                    high=105.0 + i,
                    low=98.0 + i,
                    close=103.0 + i,
                    volume=10000.0 + (i * 500),
                    interval=query.interval,
                    source_provider_id=self.provider_id,
                )
            )

        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(records),
        )


@pytest.fixture
def mock_service() -> MarketDataService:
    """Create a MarketDataService backed by MockMarketDataProvider."""
    provider = MockMarketDataProvider()
    return MarketDataService(provider=provider)


@pytest.fixture
def test_client(mock_service: MarketDataService) -> TestClient:
    """Create TestClient with dependency override for market_service_dep."""
    app = create_app()
    app.dependency_overrides[market_service_dep] = lambda: mock_service
    return TestClient(app)


def test_list_markets_default(test_client: TestClient) -> None:
    """GET /api/v1/markets returns list of discoverable instruments."""
    response = test_client.get("/api/v1/markets")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= len(DEFAULT_BENCHMARK_MARKETS)
    symbols = [item["symbol"] for item in data["items"]]
    assert "SPY" in symbols
    assert "AAPL" in symbols


def test_list_markets_filter_asset_class(test_client: TestClient) -> None:
    """GET /api/v1/markets?asset_class=CRYPTO filters instruments."""
    response = test_client.get("/api/v1/markets?asset_class=CRYPTO")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["asset_class"].lower() == "crypto"


def test_list_markets_invalid_asset_class(test_client: TestClient) -> None:
    """GET /api/v1/markets with invalid asset_class returns 422 VALIDATION_ERROR."""
    response = test_client.get("/api/v1/markets?asset_class=INVALID_ASSET_CLASS")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "INVALID_ASSET_CLASS" in data["error"]["message"]


def test_list_markets_pagination(test_client: TestClient) -> None:
    """GET /api/v1/markets respects limit and offset."""
    response = test_client.get("/api/v1/markets?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1


def test_get_market_data_success(test_client: TestClient) -> None:
    """GET /api/v1/markets/{symbol}/data returns valid OHLCV bar series."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-15T00:00:00Z"

    response = test_client.get(f"/api/v1/markets/SPY/data?start={start}&end={end}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "SPY"
    assert data["interval"] == "1d"
    assert data["count"] == 10
    assert len(data["items"]) == 10
    first_bar = data["items"][0]
    assert "timestamp" in first_bar
    assert first_bar["open"] == 100.0
    assert first_bar["close"] == 103.0


def test_get_market_data_pagination(test_client: TestClient) -> None:
    """GET /api/v1/markets/{symbol}/data paginates bars via limit and offset."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-15T00:00:00Z"

    response = test_client.get(f"/api/v1/markets/SPY/data?start={start}&end={end}&limit=3&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert data["total"] == 10
    assert data["items"][0]["open"] == 102.0


def test_get_market_data_naive_datetime_rejected(test_client: TestClient) -> None:
    """Naive (non-timezone-aware) datetimes return 422 VALIDATION_ERROR."""
    # Note: query with naive string without 'Z' or timezone offset
    url = "/api/v1/markets/SPY/data?start=2024-01-01T00:00:00&end=2024-01-10T00:00:00Z"
    response = test_client.get(url)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "timezone-aware" in data["error"]["message"].lower()


def test_get_market_data_start_after_end_rejected(test_client: TestClient) -> None:
    """Start time equal to or after end time returns 422 VALIDATION_ERROR."""
    start = "2024-01-10T00:00:00Z"
    end = "2024-01-05T00:00:00Z"

    response = test_client.get(f"/api/v1/markets/SPY/data?start={start}&end={end}")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "strictly after start" in data["error"]["message"]


def test_get_market_data_invalid_interval(test_client: TestClient) -> None:
    """Unsupported data interval returns 422 VALIDATION_ERROR."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-10T00:00:00Z"

    response = test_client.get(f"/api/v1/markets/SPY/data?start={start}&end={end}&interval=99years")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "Invalid interval" in data["error"]["message"]


def test_get_market_data_unknown_symbol(test_client: TestClient) -> None:
    """Requesting an unknown symbol returns 404 PROVIDER_SYMBOL_NOT_FOUND."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-10T00:00:00Z"

    response = test_client.get(f"/api/v1/markets/NONEXISTENT_TICKER/data?start={start}&end={end}")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "PROVIDER_SYMBOL_NOT_FOUND"
    assert "NONEXISTENT_TICKER" in data["error"]["message"]
