"""
RegimeX AI Research — Symbol Resolution Tests
=============================================
Verifies ticker extraction from query text and resolution against platform market catalog.
"""

from __future__ import annotations

import pytest
from app.modules.ai_research.application.symbol_resolver import SymbolResolver
from app.modules.market_data.application.service import (
    DEFAULT_BENCHMARK_MARKETS,
    MarketDataService,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic in-memory provider for testing."""

    @property
    def provider_id(self) -> str:
        return "mock"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="mock",
            display_name="Mock",
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
        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=(),
        )


class TestSymbolResolver:
    """Test symbol resolution logic."""

    @pytest.fixture
    def resolver(self) -> SymbolResolver:
        service = MarketDataService(provider=MockMarketDataProvider())
        return SymbolResolver(market_service=service)

    @pytest.mark.asyncio
    async def test_resolve_explicit_symbol(self, resolver: SymbolResolver) -> None:
        canonical, unrec = await resolver.resolve("What is this?", explicit_symbol="spy")
        assert canonical == "SPY"
        assert unrec is None

    @pytest.mark.asyncio
    async def test_resolve_from_question_text(self, resolver: SymbolResolver) -> None:
        canonical, unrec = await resolver.resolve("What regime is SPY currently in?")
        assert canonical == "SPY"
        assert unrec is None

        canonical, unrec = await resolver.resolve("Summarize QQQ risk analytics")
        assert canonical == "QQQ"
        assert unrec is None

    @pytest.mark.asyncio
    async def test_unrecognized_symbol_flagged(self, resolver: SymbolResolver) -> None:
        canonical, unrec = await resolver.resolve("Tell me about FOOBAR security")
        assert canonical is None
        assert unrec == "FOOBAR"

    @pytest.mark.asyncio
    async def test_general_question_no_symbol(self, resolver: SymbolResolver) -> None:
        canonical, unrec = await resolver.resolve("How is regime transition entropy calculated?")
        assert canonical is None
        assert unrec is None

    @pytest.mark.asyncio
    async def test_common_english_words_ignored(self, resolver: SymbolResolver) -> None:
        canonical, unrec = await resolver.resolve("WHAT CAN YOU TELL ME ABOUT ALL THE REGIMES?")
        assert canonical is None
        assert unrec is None
