"""
Test fixtures for data quality unit tests.
Provides synthetic clean and defective market data records, queries, and calendars.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.data_quality.domain.calendar import CalendarRegistry
from app.modules.data_quality.domain.rules import RuleContext
from app.modules.data_quality.infrastructure.calendars import (
    ContinuousCalendar,
    NSECalendar,
    NYSECalendar,
    create_default_calendar_registry,
)
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)


@pytest.fixture()
def reference_clock() -> datetime:
    """Deterministic reference clock: Friday 2024-01-05 21:00:00 UTC."""
    return datetime(2024, 1, 5, 21, 0, 0, tzinfo=UTC)


@pytest.fixture()
def aapl_instrument() -> Instrument:
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Apple Inc.",
    )


@pytest.fixture()
def reliance_instrument() -> Instrument:
    return Instrument(
        symbol="RELIANCE",
        asset_class=AssetClass.EQUITY_IN,
        exchange="NSE",
        currency="INR",
        description="Reliance Industries Ltd.",
    )


@pytest.fixture()
def btc_instrument() -> Instrument:
    return Instrument(
        symbol="BTC-USD",
        asset_class=AssetClass.CRYPTO,
        exchange="CRYPTO",
        currency="USD",
        description="Bitcoin",
    )


@pytest.fixture()
def nyse_calendar() -> NYSECalendar:
    return NYSECalendar()


@pytest.fixture()
def nse_calendar() -> NSECalendar:
    return NSECalendar()


@pytest.fixture()
def continuous_calendar() -> ContinuousCalendar:
    return ContinuousCalendar()


@pytest.fixture()
def calendar_registry() -> CalendarRegistry:
    return create_default_calendar_registry()


@pytest.fixture()
def clean_daily_records() -> tuple[OHLCVRecord, ...]:
    """3 consecutive NYSE trading days: Tue Jan 2, Wed Jan 3, Thu Jan 4 2024."""
    r1 = OHLCVRecord(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
        open=185.0,
        high=187.0,
        low=184.5,
        close=186.0,
        volume=10000000.0,
        interval=DataInterval.ONE_DAY,
        source_provider_id="yahoo_finance",
    )
    r2 = OHLCVRecord(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 3, 14, 30, tzinfo=UTC),
        open=186.0,
        high=188.0,
        low=185.0,
        close=187.5,
        volume=11000000.0,
        interval=DataInterval.ONE_DAY,
        source_provider_id="yahoo_finance",
    )
    r3 = OHLCVRecord(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 4, 14, 30, tzinfo=UTC),
        open=187.0,
        high=189.0,
        low=186.0,
        close=188.5,
        volume=9000000.0,
        interval=DataInterval.ONE_DAY,
        source_provider_id="yahoo_finance",
    )
    return (r1, r2, r3)


@pytest.fixture()
def clean_query(aapl_instrument: Instrument) -> MarketDataQuery:
    return MarketDataQuery(
        instrument=aapl_instrument,
        start=datetime(2024, 1, 2, tzinfo=UTC),
        end=datetime(2024, 1, 5, tzinfo=UTC),
        interval=DataInterval.ONE_DAY,
        adjustment_policy=AdjustmentPolicy.FULLY_ADJUSTED,
    )


@pytest.fixture()
def clean_market_data_result(
    clean_query: MarketDataQuery,
    clean_daily_records: tuple[OHLCVRecord, ...],
) -> MarketDataResult:
    return MarketDataResult(
        query=clean_query,
        provider_id="yahoo_finance",
        fetched_at=datetime(2024, 1, 5, 20, 0, tzinfo=UTC),
        records=clean_daily_records,
    )


@pytest.fixture()
def clean_rule_context(
    clean_query: MarketDataQuery,
    clean_daily_records: tuple[OHLCVRecord, ...],
    nyse_calendar: NYSECalendar,
    reference_clock: datetime,
) -> RuleContext:
    return RuleContext(
        query=clean_query,
        records=clean_daily_records,
        calendar=nyse_calendar,
        reference_time=reference_clock,
    )
