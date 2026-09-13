"""
RegimeX Feature Engineering — Unit Test Fixtures
================================================
Provides synthetic market data fixtures for deterministic mathematical verification.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)


@pytest.fixture
def test_instrument() -> Instrument:
    return Instrument(
        symbol="REGX",
        asset_class="equity_us",
        exchange="NYSE",
        currency="USD",
        description="RegimeX Test Asset",
    )


@pytest.fixture
def base_timestamp() -> datetime:
    return datetime(2024, 1, 2, 9, 30, tzinfo=UTC)


def make_bar(
    symbol: str,
    timestamp: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1000.0,
    interval: DataInterval = DataInterval.ONE_DAY,
) -> OHLCVRecord:
    return OHLCVRecord(
        symbol=symbol,
        timestamp=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        interval=interval,
        adjustment_policy=AdjustmentPolicy.RAW,
        source_provider_id="test_provider",
        ingested_at=datetime.now(tz=UTC),
    )


@pytest.fixture
def linear_trending_bars(base_timestamp: datetime) -> list[OHLCVRecord]:
    """
    30 bars with linear increasing price: close = 100 + i * 2.
    """
    bars: list[OHLCVRecord] = []
    for i in range(30):
        ts = base_timestamp + timedelta(days=i)
        p = 100.0 + i * 2.0
        bars.append(
            make_bar(
                symbol="REGX",
                timestamp=ts,
                open_=p - 1.0,
                high=p + 2.0,
                low=p - 1.5,
                close=p,
                volume=1000.0 + i * 50.0,
            )
        )
    return bars


@pytest.fixture
def constant_price_bars(base_timestamp: datetime) -> list[OHLCVRecord]:
    """
    30 bars where all prices are constant: open=100, high=100, low=100, close=100.
    """
    bars: list[OHLCVRecord] = []
    for i in range(30):
        ts = base_timestamp + timedelta(days=i)
        bars.append(
            make_bar(
                symbol="REGX",
                timestamp=ts,
                open_=100.0,
                high=100.0,
                low=100.0,
                close=100.0,
                volume=1000.0,
            )
        )
    return bars


@pytest.fixture
def zero_volume_bars(base_timestamp: datetime) -> list[OHLCVRecord]:
    """
    30 bars where volume is 0.0 (e.g. simulated or untraded bars).
    """
    bars: list[OHLCVRecord] = []
    for i in range(30):
        ts = base_timestamp + timedelta(days=i)
        p = 100.0 + i
        bars.append(
            make_bar(
                symbol="REGX",
                timestamp=ts,
                open_=p,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=0.0,
            )
        )
    return bars


@pytest.fixture
def sample_market_result(
    test_instrument: Instrument,
    linear_trending_bars: list[OHLCVRecord],
) -> MarketDataResult:
    start = linear_trending_bars[0].timestamp
    end = linear_trending_bars[-1].timestamp + timedelta(days=1)
    query = MarketDataQuery(
        instrument=test_instrument,
        start=start,
        end=end,
        interval=DataInterval.ONE_DAY,
    )
    return MarketDataResult(
        query=query,
        provider_id="test_provider",
        fetched_at=datetime.now(tz=UTC),
        records=tuple(linear_trending_bars),
    )
