"""
RegimeX Market Data — Yahoo Finance Provider Adapter
=====================================================
Implements the MarketDataProvider interface for Yahoo Finance via yfinance.

Design & Architectural Boundaries:
- Wraps synchronous yfinance/network calls in asyncio.to_thread().
- Catches all vendor-specific exceptions and maps them to ProviderError hierarchy.
- No vendor or pandas objects leak through this boundary.
- Allows injecting a fetcher callable for clean, offline unit testing.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

import pandas as pd

from app.modules.market_data.domain.errors import (
    ProviderConfigurationError,
    ProviderDataError,
    ProviderError,
    ProviderRateLimitError,
    ProviderSymbolNotFoundError,
    ProviderUnavailableError,
)
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
from app.modules.market_data.infrastructure.providers.yahoo_finance.config import (
    YahooFinanceConfig,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance.mapper import (
    map_yahoo_finance_dataframe,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance.symbol_resolver import (
    YahooFinanceSymbolResolver,
)

logger = logging.getLogger(__name__)

# Capability declaration for Yahoo Finance adapter
YAHOO_FINANCE_CAPABILITIES = ProviderCapabilities(
    supported_asset_classes=frozenset(
        {
            AssetClass.EQUITY_US,
            AssetClass.EQUITY_IN,
            AssetClass.INDEX,
            AssetClass.CRYPTO,
            AssetClass.FX,
            AssetClass.COMMODITY,
        }
    ),
    supported_intervals=frozenset(
        {
            DataInterval.ONE_MIN,
            DataInterval.FIVE_MIN,
            DataInterval.FIFTEEN_MIN,
            DataInterval.THIRTY_MIN,
            DataInterval.ONE_HOUR,
            DataInterval.ONE_DAY,
            DataInterval.ONE_WEEK,
        }
    ),
    supported_exchanges=frozenset(
        {
            "NASDAQ",
            "NYSE",
            "AMEX",
            "BATS",
            "ARCA",
            "US",
            "OTC",
            "NSE",
            "BSE",
        }
    ),
    supported_adjustment_policies=frozenset(
        {
            AdjustmentPolicy.RAW,
            AdjustmentPolicy.SPLIT_ADJUSTED,
            AdjustmentPolicy.FULLY_ADJUSTED,
        }
    ),
    supports_intraday=True,
    supports_symbol_search=False,
    max_history_days=None,
    rate_limit_per_minute=None,
)

# Interval mapping from canonical DataInterval to yfinance parameter
_INTERVAL_MAP: dict[DataInterval, str] = {
    DataInterval.ONE_MIN: "1m",
    DataInterval.FIVE_MIN: "5m",
    DataInterval.FIFTEEN_MIN: "15m",
    DataInterval.THIRTY_MIN: "30m",
    DataInterval.ONE_HOUR: "1h",
    DataInterval.ONE_DAY: "1d",
    DataInterval.ONE_WEEK: "1wk",
}


def _default_yfinance_fetcher(
    ticker: str,
    start: datetime,
    end: datetime,
    interval: str,
    auto_adjust: bool,
    timeout: int,
    proxy: str | None,
) -> pd.DataFrame:
    """Synchronous network fetcher using yfinance.download."""
    import yfinance as yf

    download_kwargs: dict[str, Any] = {
        "tickers": ticker,
        "start": start,
        "end": end,
        "interval": interval,
        "auto_adjust": auto_adjust,
        "timeout": timeout,
        "progress": False,
        "multi_level_index": False,
    }
    if proxy is not None:
        download_kwargs["proxy"] = proxy

    df: pd.DataFrame | None = yf.download(**download_kwargs)
    if df is None:
        return pd.DataFrame()
    return df


class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance market data provider adapter.

    Implements the MarketDataProvider interface and translates between
    RegimeX domain models and Yahoo Finance vendor calls.
    """

    PROVIDER_ID = "yahoo_finance"

    def __init__(
        self,
        config: YahooFinanceConfig | None = None,
        resolver: YahooFinanceSymbolResolver | None = None,
        fetcher: Callable[..., pd.DataFrame] | None = None,
    ) -> None:
        self._config = config or YahooFinanceConfig()
        self._resolver = resolver or YahooFinanceSymbolResolver()
        self._fetcher = fetcher or _default_yfinance_fetcher

    @property
    def provider_id(self) -> str:
        """Stable snake_case identifier for this provider."""
        return self.PROVIDER_ID

    async def metadata(self) -> ProviderMetadata:
        """Return identification metadata and capabilities."""
        return ProviderMetadata(
            provider_id=self.PROVIDER_ID,
            display_name="Yahoo Finance",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        return YAHOO_FINANCE_CAPABILITIES

    async def supports(self, instrument: Instrument) -> bool:
        """Return True if this provider supports the given instrument."""
        return self._resolver.supports_instrument(instrument)

    async def get_supported_symbols(
        self,
        asset_class: AssetClass | None = None,
    ) -> list[Instrument]:
        """
        Return supported symbols catalogue.

        Yahoo Finance does not provide a discoverable offline catalogue,
        so supports_symbol_search is False and an empty list is returned.
        """
        return []

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        """
        Fetch historical OHLCV records satisfying the canonical query.

        Translates query parameters, performs network I/O with bounded retries
        in a background thread, translates vendor errors, and maps records.
        """
        # Validate instrument support
        if not await self.supports(query.instrument):
            inst = query.instrument
            raise ProviderSymbolNotFoundError(
                f"Instrument {inst.symbol!r} (exchange={inst.exchange!r}, "
                f"asset_class={inst.asset_class.value!r}) is not supported by Yahoo Finance.",
                symbol=inst.symbol,
                provider_id=self.PROVIDER_ID,
            )

        # Validate interval support
        if query.interval not in YAHOO_FINANCE_CAPABILITIES.supported_intervals:
            raise ProviderConfigurationError(
                f"Interval {query.interval.value!r} is not supported by Yahoo Finance.",
                provider_id=self.PROVIDER_ID,
                details={"interval": query.interval.value},
            )

        # Validate adjustment policy support
        if query.adjustment_policy not in YAHOO_FINANCE_CAPABILITIES.supported_adjustment_policies:
            raise ProviderConfigurationError(
                f"Adjustment policy {query.adjustment_policy.value!r} "
                "is not supported by Yahoo Finance.",
                provider_id=self.PROVIDER_ID,
                details={"adjustment_policy": query.adjustment_policy.value},
            )

        provider_symbol = self._resolver.to_provider_symbol(query.instrument)
        yf_interval = _INTERVAL_MAP[query.interval]
        auto_adjust = query.adjustment_policy != AdjustmentPolicy.RAW

        df = await self._fetch_with_retries(
            ticker=provider_symbol,
            start=query.start,
            end=query.end,
            interval=yf_interval,
            auto_adjust=auto_adjust,
            symbol=query.instrument.symbol,
        )

        try:
            records = map_yahoo_finance_dataframe(
                df=df,
                query=query,
                provider_id=self.PROVIDER_ID,
            )
        except ProviderError:
            raise
        except Exception as err:
            raise ProviderDataError(
                f"Error mapping Yahoo Finance data for {query.instrument.symbol}: {err}",
                provider_id=self.PROVIDER_ID,
            ) from err

        return MarketDataResult(
            query=query,
            provider_id=self.PROVIDER_ID,
            fetched_at=datetime.now(tz=UTC),
            records=records,
        )

    async def _fetch_with_retries(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
        auto_adjust: bool,
        symbol: str,
    ) -> pd.DataFrame:
        """Execute vendor call with bounded retries and error translation."""
        max_retries = self._config.max_retries
        backoff = self._config.backoff_factor
        timeout = self._config.timeout_seconds
        proxy = self._config.proxy

        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                # Wrap synchronous fetcher in asyncio thread pool
                df = await asyncio.to_thread(
                    self._fetcher,
                    ticker,
                    start,
                    end,
                    interval,
                    auto_adjust,
                    timeout,
                    proxy,
                )
                return df

            except (ProviderError, ValueError, TypeError) as known_err:
                # Non-retryable domain or argument errors
                raise known_err

            except Exception as exc:
                last_exception = exc
                err_msg = str(exc).lower()

                # Detect rate limit
                if "429" in err_msg or "too many requests" in err_msg or "rate limit" in err_msg:
                    raise ProviderRateLimitError(
                        f"Yahoo Finance rate limit exceeded: {exc}",
                        provider_id=self.PROVIDER_ID,
                    ) from exc

                # Detect symbol not found
                if "not found" in err_msg or "delisted" in err_msg or "404" in err_msg:
                    raise ProviderSymbolNotFoundError(
                        f"Symbol {symbol!r} not found in Yahoo Finance: {exc}",
                        symbol=symbol,
                        provider_id=self.PROVIDER_ID,
                    ) from exc

                # If attempts remaining, back off exponentially
                if attempt < max_retries:
                    delay = backoff * (2**attempt)
                    logger.warning(
                        "Yahoo Finance fetch attempt %d failed (%s); retrying in %.2fs",
                        attempt + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        raise ProviderUnavailableError(
            f"Yahoo Finance unavailable for {symbol!r} after {max_retries + 1} "
            f"attempts: {last_exception}",
            provider_id=self.PROVIDER_ID,
        ) from last_exception
