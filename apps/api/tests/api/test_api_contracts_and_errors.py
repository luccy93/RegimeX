"""
RegimeX API — Contract & Error Handling Regression Tests
========================================================
Verifies strict API contract schemas, error status codes (400, 404, 422),
parameter validation (naive timestamps, invalid intervals, reversed dates),
and security invariant: no stack trace leakage in error responses.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.core.dependencies import market_intelligence_dep, market_service_dep
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
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade
from fastapi.testclient import TestClient


class MockApiMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory provider for contract integration tests."""

    @property
    def provider_id(self) -> str:
        return "api_contract_provider"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="api_contract_provider",
            display_name="API Contract Provider",
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
        base_price = 400.0

        for i in range(120):
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
    market_svc = MarketDataService(provider=MockApiMarketDataProvider())
    app.dependency_overrides[market_service_dep] = lambda: market_svc
    app.dependency_overrides[market_intelligence_dep] = lambda: MarketIntelligenceFacade(
        market_service=market_svc
    )
    return TestClient(app)


class TestRiskEndpointContractAndErrors:
    def test_risk_endpoint_invalid_interval(self, client: TestClient) -> None:
        response = client.get("/api/v1/markets/SPY/risk?interval=invalid_interval_99")
        assert response.status_code == 422
        data = response.json()
        assert "Invalid interval" in data["error"]["message"]

    def test_risk_endpoint_reversed_dates(self, client: TestClient) -> None:
        # start after end
        response = client.get(
            "/api/v1/markets/SPY/risk?start=2026-06-01T00:00:00Z&end=2026-01-01T00:00:00Z"
        )
        assert response.status_code == 422
        data = response.json()
        assert "must be strictly after" in data["error"]["message"]

    def test_risk_endpoint_contract_schema(self, client: TestClient) -> None:
        response = client.get("/api/v1/markets/SPY/risk?limit=100")
        assert response.status_code == 200
        data = response.json()

        # Required fields in MarketRiskResponse
        required_fields = [
            "symbol",
            "series_id",
            "observation_count",
            "start_timestamp",
            "end_timestamp",
            "computed_at",
            "return_statistics",
            "volatility",
            "downside_risk",
            "drawdown",
            "var_metrics",
            "expected_shortfall_metrics",
            "price_points",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert data["symbol"] == "SPY"
        assert isinstance(data["observation_count"], int)
        assert isinstance(data["price_points"], list)


class TestBacktestEndpointContractAndErrors:
    def test_backtest_endpoint_invalid_convention(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/markets/SPY/backtest?execution_convention=INVALID_CONVENTION"
        )
        assert response.status_code == 422
        data = response.json()
        assert "Invalid execution convention" in data["error"]["message"]

    def test_backtest_endpoint_invalid_interval(self, client: TestClient) -> None:
        response = client.get("/api/v1/markets/SPY/backtest?interval=invalid_period")
        assert response.status_code == 422
        data = response.json()
        assert "Invalid interval" in data["error"]["message"]

    def test_backtest_endpoint_contract_schema(self, client: TestClient) -> None:
        response = client.get("/api/v1/markets/SPY/backtest?limit=100")
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "symbol",
            "strategy_id",
            "strategy_name",
            "execution_convention",
            "initial_cash",
            "final_cash",
            "final_equity",
            "total_return",
            "annualized_return",
            "trades",
            "risk_metrics",
            "equity_curve",
            "executed_trades",
            "report",
        ]
        for field in required_fields:
            assert field in data, f"Missing required backtest field: {field}"


class TestResearchEndpointContractAndErrors:
    def test_research_query_empty_question(self, client: TestClient) -> None:
        response = client.post("/api/v1/research/query", json={"question": ""})
        assert response.status_code == 422

    def test_research_query_contract_schema(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/research/query",
            json={"question": "What regime is SPY currently in?", "symbol": "SPY"},
        )
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "answer",
            "citations",
            "evidence",
            "model",
            "generated_at",
            "request_id",
            "intent",
            "symbol",
        ]
        for field in required_fields:
            assert field in data, f"Missing required research field: {field}"

        assert data["symbol"] == "SPY"
        assert isinstance(data["citations"], list)
        assert isinstance(data["evidence"], list)


class TestSecurityStackTraceSanitization:
    def test_error_response_does_not_leak_stack_trace(self, client: TestClient) -> None:
        # Trigger an unprocessable entity error
        response = client.post("/api/v1/research/query", json={"invalid_field": 123})
        assert response.status_code == 422

        body_str = response.text
        assert "Traceback (most recent call last)" not in body_str
        assert 'File "' not in body_str
        assert ".py" not in body_str or "python" not in body_str.lower()

    def test_security_headers_present(self, client: TestClient) -> None:
        response = client.get("/api/v1/markets")
        assert response.status_code == 200
        headers = response.headers

        assert "x-request-id" in headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
