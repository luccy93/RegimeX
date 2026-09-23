"""
RegimeX Market Data — Application Service Layer
==============================================
Provides high-level application use cases for market discovery and time-series
data retrieval.

Architectural Position: ``modules/market_data/application/service.py``
- Pure application facade coordinating domain providers and repositories.
- Zero dependencies on HTTP, FastAPI, or Presentation schemas.
- Injected into API endpoints via FastAPI dependency injection.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from app.modules.market_data.domain.errors import (
    ProviderSymbolNotFoundError,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import MarketDataProvider
from app.modules.market_data.domain.repository import MarketDataRepository

logger = logging.getLogger(__name__)

# Canonical benchmark instruments catalog for offline discovery
DEFAULT_BENCHMARK_MARKETS: tuple[Instrument, ...] = (
    Instrument(
        symbol="SPY",
        asset_class=AssetClass.EQUITY_US,
        exchange="NYSE",
        currency="USD",
        description="SPDR S&P 500 ETF Trust",
    ),
    Instrument(
        symbol="QQQ",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Invesco QQQ Trust Series 1",
    ),
    Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Apple Inc. Common Stock",
    ),
    Instrument(
        symbol="MSFT",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Microsoft Corporation Common Stock",
    ),
    Instrument(
        symbol="RELIANCE",
        asset_class=AssetClass.EQUITY_IN,
        exchange="NSE",
        currency="INR",
        description="Reliance Industries Limited",
    ),
    Instrument(
        symbol="NIFTY50",
        asset_class=AssetClass.INDEX,
        exchange="NSE",
        currency="INR",
        description="NIFTY 50 Benchmark Index",
    ),
    Instrument(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        exchange="BINANCE",
        currency="USD",
        description="Bitcoin / US Dollar",
    ),
)


class MarketDataService:
    """
    Application service coordinating market data discovery and OHLCV retrieval.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository | None = None,
        default_markets: Sequence[Instrument] | None = None,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._default_markets = tuple(
            default_markets if default_markets is not None else DEFAULT_BENCHMARK_MARKETS
        )

    async def list_markets(self, asset_class: AssetClass | None = None) -> list[Instrument]:
        """
        List discoverable market instruments.

        Queries the provider's symbol catalog if available; falls back to
        canonical benchmark markets.
        """
        try:
            provider_symbols = await self._provider.get_supported_symbols(asset_class=asset_class)
            if provider_symbols:
                return provider_symbols
        except Exception as exc:
            logger.warning("Provider get_supported_symbols failed: %s; using benchmark list", exc)

        markets = list(self._default_markets)
        if asset_class is not None:
            markets = [m for m in markets if m.asset_class == asset_class]
        return markets

    async def resolve_instrument(self, symbol: str) -> Instrument:
        """
        Resolve an instrument for a given symbol.
        """
        clean_symbol = symbol.strip().upper()
        for inst in self._default_markets:
            if inst.symbol.upper() == clean_symbol:
                return inst

        # Default resolution for US equities
        return Instrument(
            symbol=clean_symbol,
            asset_class=AssetClass.EQUITY_US,
            exchange="US",
            currency="USD",
            description=f"{clean_symbol} Security",
        )

    async def get_market_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
        offset: int = 0,
    ) -> tuple[tuple[OHLCVRecord, ...], int]:
        """
        Retrieve historical OHLCV data for an instrument within the requested date range.

        Parameters
        ----------
        symbol : str
            Instrument symbol identifier.
        start : datetime
            Query start datetime (timezone-aware UTC).
        end : datetime
            Query end datetime (timezone-aware UTC).
        interval : DataInterval
            Data aggregation interval.
        limit : int
            Maximum number of records to return.
        offset : int
            Pagination offset.

        Returns
        -------
        tuple[tuple[OHLCVRecord, ...], int]
            Paginated tuple of records and total records count.
        """
        # Ensure UTC-aware timestamps
        clean_start = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
        clean_end = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)

        instrument = await self.resolve_instrument(symbol)

        # 1. Check repository if available
        records: tuple[OHLCVRecord, ...] = ()
        if self._repository is not None:
            try:
                records = await self._repository.get_range(
                    symbol=instrument.symbol,
                    interval=interval,
                    start=clean_start,
                    end=clean_end,
                )
            except Exception as exc:
                logger.warning("Repository get_range failed: %s; falling back to provider", exc)

        # 2. If no persisted records, query provider
        if not records:
            query = MarketDataQuery(
                instrument=instrument,
                start=clean_start,
                end=clean_end,
                interval=interval,
            )
            result = await self._provider.get_ohlcv(query)
            records = result.records

        if not records and not await self._provider.supports(instrument):
            raise ProviderSymbolNotFoundError(
                f"Symbol {symbol!r} is not supported or was not found.",
                symbol=symbol,
                provider_id=self._provider.provider_id,
            )

        total_count = len(records)
        # Apply deterministic pagination
        paginated_records = records[offset : offset + limit]
        return paginated_records, total_count
