"""
RegimeX API v1 — Risk and Backtesting Route Integration Tests
=============================================================
Tests the FastAPI endpoints exposing V13 Portfolio Risk and V14/V15
Backtesting and Performance Reporting.
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
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade
from fastapi.testclient import TestClient


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory market data provider for route testing."""

    def __init__(self) -> None:
        self._supported_symbols = {"SPY", "QQQ", "AAPL"}

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
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        return list(DEFAULT_BENCHMARK_MARKETS)

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol in self._supported_symbols

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        if query.instrument.symbol not in self._supported_symbols:
            raise ProviderSymbolNotFoundError(
                f"Symbol {query.instrument.symbol} not supported.",
                symbol=query.instrument.symbol,
                provider_id=self.provider_id,
            )

        # Generate 25 synthetic bars
        records: list[OHLCVRecord] = []
        base_time = query.start
        for i in range(25):
            bar_time = base_time + timedelta(days=i)
            if bar_time >= query.end:
                break
            records.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=bar_time,
                    open=100.0 + (i * 0.5),
                    high=102.0 + (i * 0.5),
                    low=99.0 + (i * 0.5),
                    close=101.0 + (i * 0.5),
                    volume=10_000.0,
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
    provider = MockMarketDataProvider()
    return MarketDataService(provider=provider)


@pytest.fixture
def test_client(mock_service: MarketDataService) -> TestClient:
    app = create_app()
    app.dependency_overrides[market_service_dep] = lambda: mock_service
    app.dependency_overrides[market_intelligence_dep] = lambda: MarketIntelligenceFacade(
        market_service=mock_service
    )
    return TestClient(app)


class TestMarketRiskRoutes:
    """Test suite for GET /api/v1/markets/{symbol}/risk."""

    def test_get_risk_success(self, test_client: TestClient) -> None:
        response = test_client.get("/api/v1/markets/SPY/risk")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "SPY"
        assert data["series_id"] == "SPY"
        assert data["observation_count"] >= 2
        assert "computed_at" in data

        # Return statistics
        stats = data["return_statistics"]
        assert "mean_return" in stats
        assert "median_return" in stats
        assert "standard_deviation" in stats
        assert stats["standard_deviation"] >= 0.0

        # Volatility
        vol = data["volatility"]
        assert vol["period_volatility"] >= 0.0
        assert vol["periods_per_year"] == 252.0
        assert vol["annualized_volatility"] is not None

        # Downside risk
        downside = data["downside_risk"]
        assert downside["downside_deviation"] >= 0.0
        assert downside["target_return"] == 0.0

        # Maximum drawdown
        dd = data["drawdown"]
        assert dd["max_drawdown"] <= 0.0
        assert dd["drawdown_magnitude"] >= 0.0
        assert dd["peak_value"] > 0.0

        # VaR and Expected Shortfall
        assert "0.95" in data["var_metrics"]
        assert data["var_metrics"]["0.95"]["var_loss"] is not None
        assert "0.95" in data["expected_shortfall_metrics"]

        # Price points
        assert len(data["price_points"]) >= 2
        first_point = data["price_points"][0]
        assert "price" in first_point
        assert "drawdown" in first_point
        assert first_point["drawdown"] <= 0.0001

    def test_get_risk_custom_annualization_and_target(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/api/v1/markets/SPY/risk",
            params={"periods_per_year": 365.0, "target_return": 0.001},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["volatility"]["periods_per_year"] == 365.0
        assert data["downside_risk"]["target_return"] == 0.001

    def test_get_risk_invalid_dates(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/api/v1/markets/SPY/risk",
            params={"start": "2026-06-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"},
        )
        assert response.status_code == 422


class TestMarketBacktestRoutes:
    """Test suite for GET /api/v1/markets/{symbol}/backtest."""

    def test_get_backtest_buy_and_hold_success(self, test_client: TestClient) -> None:
        response = test_client.get("/api/v1/markets/SPY/backtest")
        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "SPY"
        assert data["strategy_id"] == "BUY_AND_HOLD"
        assert data["strategy_name"] == "Benchmark Buy and Hold"
        assert data["execution_convention"] == "CURRENT_CLOSE"
        assert data["initial_cash"] == 100_000.0
        assert data["final_equity"] > 0.0
        assert "total_return" in data
        assert "total_fees" in data

        # Trade statistics
        trades = data["trades"]
        assert trades["order_count"] >= 1
        assert trades["fill_count"] >= 1

        # Risk metrics evaluated on equity curve
        risk = data["risk_metrics"]
        assert risk["volatility"] >= 0.0
        assert risk["maximum_drawdown"] <= 0.0

        # Equity curve
        assert len(data["equity_curve"]) >= 3
        snapshot = data["equity_curve"][-1]
        assert "equity" in snapshot
        assert "drawdown" in snapshot
        assert snapshot["drawdown"] <= 0.0001

        # Performance report
        report = data["report"]
        assert report["report_id"] is not None
        assert report["report_version"] == "1.0"
        assert "methodology" in report
        assert len(report["metric_definitions"]) > 0

    def test_get_backtest_regime_adaptive_strategy(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/api/v1/markets/SPY/backtest",
            params={"strategy": "REGIME_ADAPTIVE"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "REGIME_ADAPTIVE"
        assert data["strategy_name"] == "Regime Adaptive Momentum"

    def test_get_backtest_execution_convention(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/api/v1/markets/SPY/backtest",
            params={"execution_convention": "NEXT_OPEN"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["execution_convention"] == "NEXT_OPEN"

    def test_get_backtest_invalid_convention(self, test_client: TestClient) -> None:
        response = test_client.get(
            "/api/v1/markets/SPY/backtest",
            params={"execution_convention": "INVALID_TIMING"},
        )
        assert response.status_code == 422
