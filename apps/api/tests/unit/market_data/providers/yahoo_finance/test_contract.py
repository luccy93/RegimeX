"""
Provider contract tests for YahooFinanceProvider.
Verifies full compliance with the abstract MarketDataProvider contract.
"""

from __future__ import annotations

import pytest
from app.core.errors import ConflictError
from app.modules.market_data.application.registry import ProviderRegistry
from app.modules.market_data.domain.models import (
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance import (
    YahooFinanceProvider,
)


class TestYahooFinanceContractCompliance:
    def test_implements_market_data_provider_abc(self, yf_provider: YahooFinanceProvider) -> None:
        assert isinstance(yf_provider, MarketDataProvider)

    @pytest.mark.asyncio
    async def test_metadata_contract(self, yf_provider: YahooFinanceProvider) -> None:
        meta = await yf_provider.metadata()
        assert isinstance(meta, ProviderMetadata)
        assert meta.provider_id == yf_provider.provider_id
        assert len(meta.display_name) > 0
        assert len(meta.version) > 0

    @pytest.mark.asyncio
    async def test_capabilities_contract(self, yf_provider: YahooFinanceProvider) -> None:
        caps = await yf_provider.capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert isinstance(caps.supported_asset_classes, frozenset)
        assert isinstance(caps.supported_intervals, frozenset)
        assert isinstance(caps.supported_exchanges, frozenset)

    @pytest.mark.asyncio
    async def test_registry_integration(self, yf_provider: YahooFinanceProvider) -> None:
        registry = ProviderRegistry()
        registry.register(yf_provider)

        assert registry.is_registered("yahoo_finance")
        retrieved = registry.get("yahoo_finance")
        assert retrieved is yf_provider

        # Duplicate registration conflict
        with pytest.raises(ConflictError):
            registry.register(yf_provider)

    @pytest.mark.asyncio
    async def test_get_ohlcv_contract_and_no_pandas_leak(
        self,
        yf_provider: YahooFinanceProvider,
        sample_query: MarketDataQuery,
    ) -> None:
        result = await yf_provider.get_ohlcv(sample_query)
        assert isinstance(result, MarketDataResult)
        assert result.provider_id == yf_provider.provider_id

        # Structural validation on records
        for record in result.records:
            assert isinstance(record, OHLCVRecord)
            assert record.timestamp.tzinfo is not None
            assert type(record.open) is float
            assert type(record.close) is float
            assert type(record.high) is float
            assert type(record.low) is float
            assert type(record.volume) is float
            # Guarantee no pandas timestamp or Series leaked
            assert "pandas" not in type(record.timestamp).__module__

        # Price range contract
        pr = result.price_range()
        assert pr is not None
        low, high = pr
        assert low <= high
