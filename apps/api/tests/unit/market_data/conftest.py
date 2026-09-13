"""
Test fixtures for market_data unit tests.

Provides a fully-compliant ``FakeProvider`` (implements ``MarketDataProvider``)
and shared sample objects used across all market_data test modules.
All fixtures are offline — no network calls, no database, no secrets.
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
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)

# ---------------------------------------------------------------------------
# Shared sample datetimes
# ---------------------------------------------------------------------------

START_DT = datetime(2024, 1, 2, tzinfo=UTC)
END_DT = datetime(2024, 1, 10, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Shared sample instrument
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_instrument() -> Instrument:
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Apple Inc.",
    )


@pytest.fixture()
def sample_instrument_in() -> Instrument:
    return Instrument(
        symbol="RELIANCE",
        asset_class=AssetClass.EQUITY_IN,
        exchange="NSE",
        currency="INR",
        description="Reliance Industries Ltd.",
    )


# ---------------------------------------------------------------------------
# Shared sample query
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_query(sample_instrument: Instrument) -> MarketDataQuery:
    return MarketDataQuery(
        instrument=sample_instrument,
        start=START_DT,
        end=END_DT,
        interval=DataInterval.ONE_DAY,
        adjustment_policy=AdjustmentPolicy.SPLIT_ADJUSTED,
    )


# ---------------------------------------------------------------------------
# Shared sample OHLCV records
# ---------------------------------------------------------------------------


def make_record(
    symbol: str = "AAPL",
    ts: datetime | None = None,
    open_: float = 185.0,
    high: float = 187.0,
    low: float = 184.0,
    close: float = 186.0,
    volume: float = 1_000_000.0,
    provider_id: str = "fake_provider",
) -> OHLCVRecord:
    return OHLCVRecord(
        symbol=symbol,
        timestamp=ts or START_DT,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        interval=DataInterval.ONE_DAY,
        adjustment_policy=AdjustmentPolicy.SPLIT_ADJUSTED,
        source_provider_id=provider_id,
        ingested_at=datetime.now(tz=UTC),
    )


@pytest.fixture()
def sample_record(sample_instrument: Instrument) -> OHLCVRecord:
    return make_record(symbol=sample_instrument.symbol)


@pytest.fixture()
def two_records() -> tuple[OHLCVRecord, OHLCVRecord]:
    r1 = make_record(ts=datetime(2024, 1, 2, tzinfo=UTC), close=186.0)
    r2 = make_record(
        ts=datetime(2024, 1, 3, tzinfo=UTC),
        open_=187.0,
        high=190.0,
        low=186.5,
        close=188.0,
    )
    return r1, r2


# ---------------------------------------------------------------------------
# FakeProvider — minimal compliant implementation of MarketDataProvider
# ---------------------------------------------------------------------------


class FakeProvider(MarketDataProvider):
    """
    A synthetic provider that implements the full ``MarketDataProvider`` contract.

    Used in tests to verify that:
    - The ABC can be implemented without modifying domain code.
    - Provider metadata and capabilities work correctly.
    - The registry round-trip is functional.

    No network calls, no secrets, no vendor SDKs.
    """

    PROVIDER_ID = "fake_provider"

    def __init__(self, records: list[OHLCVRecord] | None = None) -> None:
        self._records = records or []

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.PROVIDER_ID,
            display_name="Fake Provider (Test Double)",
            version="0.1.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US, AssetClass.EQUITY_IN}),
            supported_intervals=frozenset({DataInterval.ONE_DAY, DataInterval.ONE_WEEK}),
            supported_exchanges=frozenset({"NASDAQ", "NYSE", "NSE"}),
            supported_adjustment_policies=frozenset(
                {
                    AdjustmentPolicy.RAW,
                    AdjustmentPolicy.SPLIT_ADJUSTED,
                }
            ),
            supports_intraday=False,
            supports_symbol_search=True,
            max_history_days=365 * 5,
            rate_limit_per_minute=60,
        )

    async def supports(self, instrument: Instrument) -> bool:
        caps = await self.capabilities()
        return instrument.asset_class in caps.supported_asset_classes

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        instruments = [
            Instrument(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY_US,
                exchange="NASDAQ",
                currency="USD",
                description="",
            ),
            Instrument(
                symbol="RELIANCE",
                asset_class=AssetClass.EQUITY_IN,
                exchange="NSE",
                currency="INR",
                description="",
            ),
        ]
        if asset_class is not None:
            return [i for i in instruments if i.asset_class == asset_class]
        return instruments

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        filtered = [r for r in self._records if query.start <= r.timestamp < query.end]
        return MarketDataResult(
            query=query,
            provider_id=self.PROVIDER_ID,
            fetched_at=datetime.now(tz=UTC),
            records=tuple(filtered),
        )


@pytest.fixture()
def fake_provider(two_records: tuple[OHLCVRecord, OHLCVRecord]) -> FakeProvider:
    r1, r2 = two_records
    return FakeProvider(records=[r1, r2])


@pytest.fixture()
def empty_fake_provider() -> FakeProvider:
    return FakeProvider(records=[])
