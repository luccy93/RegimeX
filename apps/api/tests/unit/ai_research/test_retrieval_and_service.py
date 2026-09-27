"""
RegimeX AI Research — Retrieval and Application Service Tests
=============================================================
Verifies end-to-end orchestration, deterministic fallback upon provider failure,
and SSE event streaming pipeline.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.modules.ai_research.application.service import AIResearchService
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import (
    EvidencePacket,
    ResearchIntent,
    ResearchQuery,
)
from app.modules.ai_research.infrastructure.providers.mock_provider import MockModelProvider
from app.modules.backtesting.application.service import BacktestingService
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
from app.modules.portfolio_risk.application.service import PortfolioRiskService
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade


class SyntheticMarketDataProvider(MarketDataProvider):
    """Provides deterministic synthetic bars for tests."""

    @property
    def provider_id(self) -> str:
        return "synthetic"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="synthetic",
            display_name="Synthetic",
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
        base_price = 100.0

        for i in range(120):
            t = base_time + timedelta(days=i)
            if t >= query.end:
                break
            p = base_price + (i * 0.2)
            bars.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=t,
                    open=p - 0.5,
                    high=p + 1.0,
                    low=p - 1.0,
                    close=p,
                    volume=1_000_000,
                    interval=query.interval,
                    source_provider_id=self.provider_id,
                )
            )

        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(bars),
        )


class FailingModelProvider(ResearchModelProvider):
    """Simulates provider timeout or outage."""

    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def model_name(self) -> str:
        return "failing-model"

    async def generate(
        self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]
    ) -> str:
        raise RuntimeError("Provider connection timeout.")

    async def stream(self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]):
        raise RuntimeError("Provider streaming failure.")
        yield ""


class TestAIResearchService:
    """Test AIResearchService operations."""

    @pytest.fixture
    def service(self) -> AIResearchService:
        market_service = MarketDataService(provider=SyntheticMarketDataProvider())
        market_intel = MarketIntelligenceFacade(market_service=market_service)
        risk_service = PortfolioRiskService()
        backtest_service = BacktestingService()
        provider = MockModelProvider()

        return AIResearchService(
            market_service=market_service,
            market_intelligence=market_intel,
            risk_service=risk_service,
            backtest_service=backtest_service,
            provider=provider,
        )

    @pytest.mark.asyncio
    async def test_execute_query_current_regime(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What regime is SPY currently in?")
        response = await service.execute_query(query, request_id="req-1")

        assert response.request_id == "req-1"
        assert response.intent == ResearchIntent.CURRENT_REGIME
        assert response.symbol == "SPY"
        assert len(response.citations) > 0
        assert "[1]" in response.answer

    @pytest.mark.asyncio
    async def test_execute_query_risk(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What is the current volatility of SPY?")
        response = await service.execute_query(query, request_id="req-2")

        assert response.intent == ResearchIntent.RISK
        assert response.symbol == "SPY"
        assert len(response.citations) > 0
        assert "volatility" in response.answer.lower()

    @pytest.mark.asyncio
    async def test_execute_query_transitions(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What does the transition matrix show for SPY?")
        response = await service.execute_query(query, request_id="req-3")

        assert response.intent == ResearchIntent.TRANSITIONS
        assert "persistence" in response.answer.lower()
        assert len(response.citations) > 0

    @pytest.mark.asyncio
    async def test_execute_query_unknown_market(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What is the regime of FOOBAR?")
        response = await service.execute_query(query, request_id="req-4")

        assert "couldn't find that market" in response.answer
        assert response.citations == []
        assert response.intent == ResearchIntent.UNSUPPORTED

    @pytest.mark.asyncio
    async def test_execute_query_prediction_refusal(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="Will SPY rise tomorrow?")
        response = await service.execute_query(query, request_id="req-5")

        assert response.intent == ResearchIntent.PREDICTION_REFUSAL
        assert "does not provide future price predictions" in response.answer

    @pytest.mark.asyncio
    async def test_execute_query_advice_refusal(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="Should I buy SPY right now?")
        response = await service.execute_query(query, request_id="req-6")

        assert response.intent == ResearchIntent.ADVICE_REFUSAL
        assert "does not provide personalized financial advice" in response.answer

    @pytest.mark.asyncio
    async def test_failing_provider_uses_deterministic_fallback(self) -> None:
        market_service = MarketDataService(provider=SyntheticMarketDataProvider())
        market_intel = MarketIntelligenceFacade(market_service=market_service)
        risk_service = PortfolioRiskService()
        backtest_service = BacktestingService()

        svc = AIResearchService(
            market_service=market_service,
            market_intelligence=market_intel,
            risk_service=risk_service,
            backtest_service=backtest_service,
            provider=FailingModelProvider(),
        )

        query = ResearchQuery(question="What regime is SPY currently in?")
        response = await svc.execute_query(query, request_id="req-fallback")

        assert response.intent == ResearchIntent.CURRENT_REGIME
        assert "[1]" in response.answer
        assert len(response.citations) > 0

    @pytest.mark.asyncio
    async def test_stream_query(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What regime is SPY currently in?", stream=True)
        events = []
        async for event in service.stream_query(query, request_id="req-stream"):
            events.append(event)

        event_types = [e.event for e in events]
        assert "metadata" in event_types
        assert "evidence" in event_types
        assert "token" in event_types
        assert "citation" in event_types
        assert "complete" in event_types
