"""
RegimeX AI Research — Service Error Handling & Fallback Tests
==============================================================
Verifies AIResearchService error paths:
- Provider failure in execute_query falls back to deterministic grounded answer
- Provider streaming exception falls back to deterministic grounded token
- Unrecognized market in streaming yields safe response
- Refusal intents in streaming yield proper refusal events
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from app.modules.ai_research.application.service import AIResearchService
from app.modules.ai_research.domain.errors import ProviderUnavailableError
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import (
    EvidencePacket,
    ResearchIntent,
    ResearchQuery,
)
from app.modules.backtesting.application.service import BacktestingService
from app.modules.market_data.application.service import MarketDataService
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


class FailingModelProvider(ResearchModelProvider):
    """Provider that always fails to test fallback mechanics."""

    @property
    def provider_name(self) -> str:
        return "failing-provider"

    @property
    def model_name(self) -> str:
        return "failing-v1"

    async def generate(
        self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]
    ) -> str:
        raise ProviderUnavailableError("Simulated LLM provider outage")

    async def stream(
        self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]
    ) -> AsyncGenerator[str, None]:
        raise ProviderUnavailableError("Simulated LLM stream outage")
        yield  # make it a generator


class DummyMarketProvider(MarketDataProvider):
    @property
    def provider_id(self) -> str:
        return "dummy"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="dummy",
            display_name="Dummy",
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
        return [
            Instrument(
                symbol="SPY",
                asset_class=AssetClass.EQUITY_US,
                exchange="NYSE",
                currency="USD",
            )
        ]

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol == "SPY"

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        from datetime import UTC, datetime, timedelta

        records = [
            OHLCVRecord(
                symbol="SPY",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i),
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1_000_000,
                interval=query.interval,
                source_provider_id="dummy",
            )
            for i in range(120)
        ]
        return MarketDataResult(query=query, provider_id="dummy", records=tuple(records))


@pytest.fixture
def failing_service() -> AIResearchService:
    market_svc = MarketDataService(provider=DummyMarketProvider())
    market_intel = MarketIntelligenceFacade(market_service=market_svc)
    risk_svc = PortfolioRiskService()
    backtest_svc = BacktestingService()
    provider = FailingModelProvider()

    return AIResearchService(
        market_service=market_svc,
        market_intelligence=market_intel,
        risk_service=risk_svc,
        backtest_service=backtest_svc,
        provider=provider,
    )


class TestServiceErrorHandling:
    @pytest.mark.asyncio
    async def test_execute_query_uses_fallback_when_provider_fails(
        self, failing_service: AIResearchService
    ) -> None:
        query = ResearchQuery(question="What regime is SPY currently in?")
        response = await failing_service.execute_query(query, request_id="req-fail-1")

        assert response.intent == ResearchIntent.CURRENT_REGIME
        assert response.symbol == "SPY"
        assert len(response.citations) > 0
        assert "[1]" in response.answer

    @pytest.mark.asyncio
    async def test_stream_query_uses_fallback_token_when_provider_fails(
        self, failing_service: AIResearchService
    ) -> None:
        query = ResearchQuery(question="What regime is SPY currently in?", stream=True)
        events = []
        async for event in failing_service.stream_query(query, request_id="req-fail-stream"):
            events.append(event)

        event_types = [e.event for e in events]
        assert "metadata" in event_types
        assert "evidence" in event_types
        assert "token" in event_types
        assert "complete" in event_types

        # Complete event should have valid grounded answer
        complete_event = next(e for e in events if e.event == "complete")
        assert complete_event.data["answer"] != ""

    @pytest.mark.asyncio
    async def test_stream_unrecognized_symbol_aborts_safely(
        self, failing_service: AIResearchService
    ) -> None:
        # Question with an unknown/unsupported ticker
        query = ResearchQuery(
            question="What is the price of UNKNOWN?", symbol="UNKNOWN", stream=True
        )
        events = []

        async for event in failing_service.stream_query(query, request_id="req-unrec"):
            events.append(event)

        meta = next(e for e in events if e.event == "metadata")
        assert meta.data["intent"] == ResearchIntent.UNSUPPORTED.value

        tokens = [e.data["token"] for e in events if e.event == "token"]
        assert any("couldn't find that market" in t for t in tokens)

    @pytest.mark.asyncio
    async def test_stream_prediction_refusal_emits_refusal_events(
        self, failing_service: AIResearchService
    ) -> None:
        query = ResearchQuery(question="Will SPY go to $600 next week?", stream=True)
        events = []
        async for event in failing_service.stream_query(query, request_id="req-pred-stream"):
            events.append(event)

        meta = next(e for e in events if e.event == "metadata")
        assert meta.data["intent"] == ResearchIntent.PREDICTION_REFUSAL.value

        complete = next(e for e in events if e.event == "complete")
        assert "does not provide future price predictions" in complete.data["answer"]
