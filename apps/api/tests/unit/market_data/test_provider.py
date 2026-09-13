"""
Unit tests — MarketDataProvider interface and ProviderCapabilities / ProviderMetadata.

Tests verify that:
- FakeProvider correctly implements the MarketDataProvider ABC.
- Attempting to instantiate MarketDataProvider directly raises TypeError.
- ProviderMetadata validates its provider_id pattern.
- ProviderCapabilities defaults are conservative.
- The provider contract methods return correct types.
- supports() and get_supported_symbols() honour asset class filtering.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from pydantic import ValidationError

from tests.unit.market_data.conftest import (
    FakeProvider,
)

# =============================================================================
# ProviderCapabilities
# =============================================================================


class TestProviderCapabilities:
    def test_defaults_are_conservative(self) -> None:
        caps = ProviderCapabilities()
        assert len(caps.supported_asset_classes) == 0
        assert len(caps.supported_intervals) == 0
        assert len(caps.supported_exchanges) == 0
        assert not caps.supports_intraday
        assert not caps.supports_symbol_search
        assert caps.max_history_days is None
        assert caps.rate_limit_per_minute is None

    def test_raw_adjustment_in_default_policies(self) -> None:
        caps = ProviderCapabilities()
        assert AdjustmentPolicy.RAW in caps.supported_adjustment_policies

    def test_fully_specified_capabilities(self) -> None:
        caps = ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.CRYPTO}),
            supported_intervals=frozenset({DataInterval.ONE_HOUR}),
            supported_exchanges=frozenset({"BINANCE"}),
            supports_intraday=True,
            supports_symbol_search=True,
            max_history_days=730,
            rate_limit_per_minute=300,
        )
        assert AssetClass.CRYPTO in caps.supported_asset_classes
        assert caps.supports_intraday
        assert caps.max_history_days == 730

    def test_capabilities_are_frozen(self) -> None:
        caps = ProviderCapabilities()
        with pytest.raises((TypeError, ValidationError)):
            caps.supports_intraday = True  # type: ignore[misc]


# =============================================================================
# ProviderMetadata
# =============================================================================


class TestProviderMetadata:
    def test_valid_metadata(self) -> None:
        meta = ProviderMetadata(
            provider_id="test_provider",
            display_name="Test Provider",
            version="1.0.0",
            capabilities=ProviderCapabilities(),
        )
        assert meta.provider_id == "test_provider"
        assert meta.version == "1.0.0"

    def test_provider_id_must_be_snake_case(self) -> None:
        """provider_id must match ^[a-z][a-z0-9_]*$"""
        with pytest.raises(ValidationError):
            ProviderMetadata(
                provider_id="TestProvider",  # uppercase — invalid
                display_name="Test",
                version="1.0.0",
                capabilities=ProviderCapabilities(),
            )

    def test_provider_id_cannot_start_with_digit(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(
                provider_id="1provider",
                display_name="Test",
                version="1.0.0",
                capabilities=ProviderCapabilities(),
            )

    def test_provider_id_cannot_start_with_underscore(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(
                provider_id="_provider",
                display_name="Test",
                version="1.0.0",
                capabilities=ProviderCapabilities(),
            )

    def test_empty_display_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProviderMetadata(
                provider_id="my_provider",
                display_name="",
                version="1.0.0",
                capabilities=ProviderCapabilities(),
            )

    def test_metadata_is_frozen(self) -> None:
        meta = ProviderMetadata(
            provider_id="my_provider",
            display_name="My Provider",
            version="1.0.0",
            capabilities=ProviderCapabilities(),
        )
        with pytest.raises((TypeError, ValidationError)):
            meta.version = "2.0.0"  # type: ignore[misc]


# =============================================================================
# MarketDataProvider — ABC enforcement
# =============================================================================


class TestMarketDataProviderABC:
    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError):
            MarketDataProvider()  # type: ignore[abstract]

    def test_fake_provider_implements_contract(self, fake_provider: FakeProvider) -> None:
        assert isinstance(fake_provider, MarketDataProvider)

    def test_provider_id_property(self, fake_provider: FakeProvider) -> None:
        assert fake_provider.provider_id == "fake_provider"


# =============================================================================
# FakeProvider — async method tests
# =============================================================================


class TestFakeProviderMethods:
    @pytest.mark.asyncio
    async def test_metadata_returns_correct_type(self, fake_provider: FakeProvider) -> None:
        meta = await fake_provider.metadata()
        assert isinstance(meta, ProviderMetadata)
        assert meta.provider_id == fake_provider.provider_id

    @pytest.mark.asyncio
    async def test_capabilities_returns_correct_type(self, fake_provider: FakeProvider) -> None:
        caps = await fake_provider.capabilities()
        assert isinstance(caps, ProviderCapabilities)

    @pytest.mark.asyncio
    async def test_capabilities_consistent_with_metadata(self, fake_provider: FakeProvider) -> None:
        meta = await fake_provider.metadata()
        caps = await fake_provider.capabilities()
        assert meta.capabilities == caps

    @pytest.mark.asyncio
    async def test_supports_known_asset_class(
        self, fake_provider: FakeProvider, sample_instrument: Instrument
    ) -> None:
        result = await fake_provider.supports(sample_instrument)
        assert result is True

    @pytest.mark.asyncio
    async def test_does_not_support_crypto(self, fake_provider: FakeProvider) -> None:
        crypto_instrument = Instrument(
            symbol="BTC",
            asset_class=AssetClass.CRYPTO,
            exchange="BINANCE",
            currency="USD",
            description="",
        )
        result = await fake_provider.supports(crypto_instrument)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_supported_symbols_returns_list(self, fake_provider: FakeProvider) -> None:
        symbols = await fake_provider.get_supported_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert all(isinstance(s, Instrument) for s in symbols)

    @pytest.mark.asyncio
    async def test_get_supported_symbols_filters_by_asset_class(
        self, fake_provider: FakeProvider
    ) -> None:
        us_only = await fake_provider.get_supported_symbols(asset_class=AssetClass.EQUITY_US)
        assert all(s.asset_class == AssetClass.EQUITY_US for s in us_only)

    @pytest.mark.asyncio
    async def test_get_ohlcv_returns_result(
        self, fake_provider: FakeProvider, sample_query: MarketDataQuery
    ) -> None:
        result = await fake_provider.get_ohlcv(sample_query)
        assert isinstance(result, MarketDataResult)
        assert result.provider_id == fake_provider.provider_id

    @pytest.mark.asyncio
    async def test_get_ohlcv_echoes_query(
        self, fake_provider: FakeProvider, sample_query: MarketDataQuery
    ) -> None:
        result = await fake_provider.get_ohlcv(sample_query)
        assert result.query == sample_query

    @pytest.mark.asyncio
    async def test_empty_provider_returns_empty_result(
        self, empty_fake_provider: FakeProvider, sample_query: MarketDataQuery
    ) -> None:
        result = await empty_fake_provider.get_ohlcv(sample_query)
        assert result.is_empty

    @pytest.mark.asyncio
    async def test_get_ohlcv_filters_by_date_range(
        self, fake_provider: FakeProvider, sample_instrument: Instrument
    ) -> None:
        narrow_query = MarketDataQuery(
            instrument=sample_instrument,
            start=datetime(2024, 1, 2, tzinfo=UTC),
            end=datetime(2024, 1, 3, tzinfo=UTC),
            interval=DataInterval.ONE_DAY,
        )
        result = await fake_provider.get_ohlcv(narrow_query)
        for r in result.records:
            assert narrow_query.start <= r.timestamp < narrow_query.end
