"""
Unit tests for YahooFinanceProvider adapter (mocked, offline).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from app.modules.market_data.domain.errors import (
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderSymbolNotFoundError,
    ProviderUnavailableError,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
)
from app.modules.market_data.domain.provider import (
    ProviderCapabilities,
    ProviderMetadata,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance import (
    YahooFinanceConfig,
    YahooFinanceProvider,
)


class TestYahooFinanceProvider:
    @pytest.mark.asyncio
    async def test_provider_id(self, yf_provider: YahooFinanceProvider) -> None:
        assert yf_provider.provider_id == "yahoo_finance"

    @pytest.mark.asyncio
    async def test_metadata(self, yf_provider: YahooFinanceProvider) -> None:
        meta = await yf_provider.metadata()
        assert isinstance(meta, ProviderMetadata)
        assert meta.provider_id == "yahoo_finance"
        assert meta.display_name == "Yahoo Finance"
        assert meta.version == "1.0.0"
        assert isinstance(meta.capabilities, ProviderCapabilities)

    @pytest.mark.asyncio
    async def test_capabilities(self, yf_provider: YahooFinanceProvider) -> None:
        caps = await yf_provider.capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.supports_intraday
        assert not caps.supports_symbol_search
        assert AssetClass.EQUITY_US in caps.supported_asset_classes
        assert AssetClass.EQUITY_IN in caps.supported_asset_classes
        assert DataInterval.ONE_DAY in caps.supported_intervals

    @pytest.mark.asyncio
    async def test_supports(
        self,
        yf_provider: YahooFinanceProvider,
        sample_aapl_instrument: Instrument,
        sample_reliance_instrument: Instrument,
    ) -> None:
        assert await yf_provider.supports(sample_aapl_instrument)
        assert await yf_provider.supports(sample_reliance_instrument)

        unsupported = Instrument(
            symbol="XYZ",
            asset_class=AssetClass.EQUITY_IN,
            exchange="UNKNOWN_EXCHANGE",
            currency="INR",
            description="",
        )
        assert not await yf_provider.supports(unsupported)

    @pytest.mark.asyncio
    async def test_get_supported_symbols_empty(
        self,
        yf_provider: YahooFinanceProvider,
    ) -> None:
        symbols = await yf_provider.get_supported_symbols()
        assert symbols == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_successful(
        self,
        yf_provider: YahooFinanceProvider,
        sample_query: MarketDataQuery,
    ) -> None:
        result = await yf_provider.get_ohlcv(sample_query)
        assert isinstance(result, MarketDataResult)
        assert result.provider_id == "yahoo_finance"
        assert result.query == sample_query
        assert len(result.records) == 3
        assert not result.is_empty
        assert result.records[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_ohlcv_empty_dataframe(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        empty_provider = YahooFinanceProvider(
            config=YahooFinanceConfig(),
            fetcher=lambda *args, **kwargs: pd.DataFrame(),
        )
        result = await empty_provider.get_ohlcv(sample_query)
        assert isinstance(result, MarketDataResult)
        assert result.is_empty
        assert len(result.records) == 0

    @pytest.mark.asyncio
    async def test_get_ohlcv_unsupported_instrument(
        self,
        yf_provider: YahooFinanceProvider,
    ) -> None:
        bad_instrument = Instrument(
            symbol="BAD",
            asset_class=AssetClass.EQUITY_IN,
            exchange="PARIS",
            currency="EUR",
            description="",
        )
        query = MarketDataQuery(
            instrument=bad_instrument,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )
        with pytest.raises(ProviderSymbolNotFoundError) as exc_info:
            await yf_provider.get_ohlcv(query)
        assert exc_info.value.provider_id == "yahoo_finance"
        assert exc_info.value.symbol == "BAD"

    @pytest.mark.asyncio
    async def test_get_ohlcv_unsupported_interval(
        self,
        sample_aapl_instrument: Instrument,
    ) -> None:
        unsupported_query = MarketDataQuery(
            instrument=sample_aapl_instrument,
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
            interval=DataInterval.FOUR_HOUR,  # Yahoo Finance does not support 4h
        )
        provider = YahooFinanceProvider()
        with pytest.raises(ProviderConfigurationError) as exc_info:
            await provider.get_ohlcv(unsupported_query)
        assert "not supported" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_ohlcv_rate_limit_translated(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        def rate_limited_fetcher(*args, **kwargs):
            raise RuntimeError("HTTP 429 Too Many Requests: Rate limit reached")

        provider = YahooFinanceProvider(fetcher=rate_limited_fetcher)
        with pytest.raises(ProviderRateLimitError) as exc_info:
            await provider.get_ohlcv(sample_query)
        assert exc_info.value.provider_id == "yahoo_finance"

    @pytest.mark.asyncio
    async def test_get_ohlcv_symbol_not_found_translated(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        def not_found_fetcher(*args, **kwargs):
            raise RuntimeError("Symbol AAPL not found: may be delisted")

        provider = YahooFinanceProvider(fetcher=not_found_fetcher)
        with pytest.raises(ProviderSymbolNotFoundError) as exc_info:
            await provider.get_ohlcv(sample_query)
        assert exc_info.value.provider_id == "yahoo_finance"
        assert exc_info.value.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_ohlcv_retries_transient_failure(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        attempts = 0

        def failing_fetcher(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            raise ConnectionError("Connection timeout to api.finance.yahoo.com")

        provider = YahooFinanceProvider(
            config=YahooFinanceConfig(timeout_seconds=2, max_retries=2, backoff_factor=0.01),
            fetcher=failing_fetcher,
        )
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await provider.get_ohlcv(sample_query)

        # Initial attempt + 2 retries = 3 attempts total
        assert attempts == 3
        assert exc_info.value.provider_id == "yahoo_finance"

    @pytest.mark.asyncio
    async def test_get_ohlcv_retries_then_succeeds(
        self,
        sample_query: MarketDataQuery,
        sample_aapl_df: pd.DataFrame,
    ) -> None:
        attempts = 0

        def flaky_fetcher(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise TimeoutError("Temporary network blip")
            return sample_aapl_df

        provider = YahooFinanceProvider(
            config=YahooFinanceConfig(timeout_seconds=2, max_retries=2, backoff_factor=0.01),
            fetcher=flaky_fetcher,
        )
        result = await provider.get_ohlcv(sample_query)
        assert attempts == 2
        assert len(result.records) == 3
