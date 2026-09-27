"""
RegimeX API v1 — AI Quantitative Research Endpoint Tests
========================================================
Integration tests for /api/v1/research/query and /api/v1/research/context/{symbol}.
Verifies synchronous responses, SSE streaming, input validation, and safety disclaimers.
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


class TestMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory provider for route integration testing."""

    @property
    def provider_id(self) -> str:
        return "route_test_provider"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="route_test_provider",
            display_name="Route Test Provider",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        return list(DEFAULT_BENCHMARK_MARKETS)

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol in {m.symbol for m in DEFAULT_BENCHMARK_MARKETS}

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        base_time = query.start
        bars: list[OHLCVRecord] = []
        base_price = 450.0

        for i in range(100):
            t = base_time + timedelta(days=i)
            if t >= query.end:
                break
            p = base_price + (i * 0.5)
            bars.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=t,
                    open=p - 1.0,
                    high=p + 2.0,
                    low=p - 2.0,
                    close=p,
                    volume=50_000_000,
                    interval=query.interval,
                    source_provider_id=self.provider_id,
                )
            )

        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(bars),
        )


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    market_svc = MarketDataService(provider=TestMarketDataProvider())
    app.dependency_overrides[market_service_dep] = lambda: market_svc
    return TestClient(app)


class TestResearchRoutes:
    """Test /api/v1/research endpoints."""

    def test_synchronous_query_success(self, client: TestClient) -> None:
        payload = {
            "question": "What regime is SPY currently in?",
            "symbol": "SPY",
        }
        headers = {"X-Request-ID": "test-req-001"}
        response = client.post("/api/v1/research/query", json=payload, headers=headers)

        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "test-req-001"
        data = response.json()
        assert data["request_id"] == "test-req-001"
        assert data["intent"] == "CURRENT_REGIME"
        assert data["symbol"] == "SPY"
        assert len(data["citations"]) > 0
        assert "[1]" in data["answer"]
        assert len(data["evidence"]) > 0

    def test_streaming_query_success(self, client: TestClient) -> None:
        payload = {
            "question": "What is the volatility of SPY?",
            "symbol": "SPY",
            "stream": True,
        }
        response = client.post("/api/v1/research/query", json=payload)

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        body_text = response.text
        assert "event: metadata" in body_text
        assert "event: evidence" in body_text
        assert "event: token" in body_text
        assert "event: complete" in body_text

    def test_prediction_refusal_endpoint(self, client: TestClient) -> None:
        payload = {"question": "Will SPY go up tomorrow?"}
        response = client.post("/api/v1/research/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "PREDICTION_REFUSAL"
        assert "does not provide future price predictions" in data["answer"]

    def test_advice_refusal_endpoint(self, client: TestClient) -> None:
        payload = {"question": "Should I buy SPY?"}
        response = client.post("/api/v1/research/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "ADVICE_REFUSAL"
        assert "does not provide personalized financial advice" in data["answer"]

    def test_unknown_market_endpoint(self, client: TestClient) -> None:
        payload = {"question": "What is the regime of FOOBAR?"}
        response = client.post("/api/v1/research/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "couldn't find that market" in data["answer"]
        assert data["citations"] == []

    def test_empty_question_rejected(self, client: TestClient) -> None:
        payload = {"question": "   "}
        response = client.post("/api/v1/research/query", json=payload)
        assert response.status_code in (400, 422)

    def test_oversized_question_rejected(self, client: TestClient) -> None:
        payload = {"question": "x" * 1001}
        response = client.post("/api/v1/research/query", json=payload)
        assert response.status_code in (400, 422)

    def test_context_endpoint(self, client: TestClient) -> None:
        response = client.get("/api/v1/research/context/SPY")
        assert response.status_code == 200
        evidence_list = response.json()
        assert isinstance(evidence_list, list)
        assert len(evidence_list) > 0
        source_ids = [p["source_id"] for p in evidence_list]
        assert "methodology:general" in source_ids
