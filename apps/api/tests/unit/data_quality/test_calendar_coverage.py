"""
RegimeX Data Quality — Calendar and Gap Detection Invariant Tests
=================================================================
Verifies:
- ContinuousCalendar (24/7 markets, session hours, expected days)
- NSECalendar (Indian equity trading hours, weekends, mandatory holidays, market open checks)
- GapDetectionRule for both daily and intraday intervals
- Calendar compliance and holiday boundary detection
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest
from app.modules.data_quality.application.rules.gap import GapDetectionRule
from app.modules.data_quality.domain.rules import RuleContext
from app.modules.data_quality.infrastructure.calendars.continuous import (
    ContinuousCalendar,
)
from app.modules.data_quality.infrastructure.calendars.nse import (
    _IST_TZ,
    NSECalendar,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    OHLCVRecord,
)


class TestContinuousCalendar:
    """Verifies continuous 24/7 trading calendar for digital assets and crypto."""

    @pytest.fixture
    def calendar(self) -> ContinuousCalendar:
        return ContinuousCalendar()

    def test_metadata_and_session_hours(self, calendar: ContinuousCalendar) -> None:
        assert calendar.calendar_id == "24_7"
        assert "Continuous" in calendar.name

        hours = calendar.get_session_hours()
        assert hours.open_time == time(0, 0)
        assert hours.close_time == time(23, 59, 59)
        assert hours.timezone_name == "UTC"

    def test_trading_day_and_open_status(self, calendar: ContinuousCalendar) -> None:
        # Weekday, weekend, holiday — all are trading days
        assert calendar.is_trading_day(date(2026, 1, 1))  # New Year
        assert calendar.is_trading_day(date(2026, 1, 3))  # Saturday
        assert calendar.is_trading_day(date(2026, 1, 4))  # Sunday

        now_utc = datetime(2026, 1, 4, 3, 30, tzinfo=UTC)
        assert calendar.is_market_open(now_utc)

    def test_expected_trading_days_and_next_day(self, calendar: ContinuousCalendar) -> None:
        start = date(2026, 5, 1)
        end = date(2026, 5, 5)
        days = calendar.expected_trading_days(start, end)
        assert len(days) == 5
        assert days[0] == start
        assert days[-1] == end

        next_day = calendar.next_trading_day(date(2026, 5, 5))
        assert next_day == date(2026, 5, 6)


class TestNSECalendar:
    """Verifies National Stock Exchange of India (NSE) trading calendar."""

    @pytest.fixture
    def calendar(self) -> NSECalendar:
        return NSECalendar()

    def test_metadata_and_session_hours(self, calendar: NSECalendar) -> None:
        assert calendar.calendar_id == "nse"
        assert "National Stock Exchange" in calendar.name

        hours = calendar.get_session_hours()
        assert hours.open_time == time(9, 15)
        assert hours.close_time == time(15, 30)
        assert hours.timezone_name == "Asia/Kolkata"

    def test_mandatory_holidays_in_2026(self, calendar: NSECalendar) -> None:
        holidays = calendar.get_holidays(2026)
        assert date(2026, 1, 26) in holidays  # Republic Day
        assert date(2026, 8, 15) in holidays  # Independence Day
        assert date(2026, 10, 2) in holidays  # Gandhi Jayanti
        assert date(2026, 12, 25) in holidays  # Christmas

    def test_weekend_and_holiday_exclusion(self, calendar: NSECalendar) -> None:
        # 2026-01-26 is Monday, Republic Day -> NOT trading day
        assert not calendar.is_trading_day(date(2026, 1, 26))

        # 2026-01-25 is Sunday -> NOT trading day
        assert not calendar.is_trading_day(date(2026, 1, 25))

        # 2026-01-27 is Tuesday, regular business day -> trading day
        assert calendar.is_trading_day(date(2026, 1, 27))

    def test_market_open_checks(self, calendar: NSECalendar) -> None:
        # Naive datetime must raise ValueError
        with pytest.raises(ValueError, match="timezone-aware"):
            calendar.is_market_open(datetime(2026, 1, 27, 10, 0))

        # 10:30 AM IST on Tuesday 2026-01-27 -> Market is OPEN
        open_time_ist = datetime(2026, 1, 27, 10, 30, tzinfo=_IST_TZ)
        assert calendar.is_market_open(open_time_ist)

        # 08:30 AM IST -> Before open (09:15) -> Market is CLOSED
        early_time_ist = datetime(2026, 1, 27, 8, 30, tzinfo=_IST_TZ)
        assert not calendar.is_market_open(early_time_ist)

        # 16:00 PM IST -> After close (15:30) -> Market is CLOSED
        late_time_ist = datetime(2026, 1, 27, 16, 0, tzinfo=_IST_TZ)
        assert not calendar.is_market_open(late_time_ist)

        # 11:00 AM IST on Saturday 2026-01-31 -> Weekend -> Market is CLOSED
        weekend_time = datetime(2026, 1, 31, 11, 0, tzinfo=_IST_TZ)
        assert not calendar.is_market_open(weekend_time)

    def test_expected_trading_days_skips_weekends_and_holidays(self, calendar: NSECalendar) -> None:
        # Friday 2026-01-23 to Tuesday 2026-01-27
        # Fri 23: Open
        # Sat 24: Closed (Weekend)
        # Sun 25: Closed (Weekend)
        # Mon 26: Closed (Republic Day)
        # Tue 27: Open
        days = calendar.expected_trading_days(date(2026, 1, 23), date(2026, 1, 27))
        assert days == [date(2026, 1, 23), date(2026, 1, 27)]

    def test_next_trading_day_skips_weekend_and_holiday(self, calendar: NSECalendar) -> None:
        # Friday 2026-01-23 -> next trading day is Tuesday 2026-01-27
        next_day = calendar.next_trading_day(date(2026, 1, 23))
        assert next_day == date(2026, 1, 27)


class TestIntradayGapDetection:
    """Verifies intraday gap detection in GapDetectionRule."""

    @pytest.fixture
    def gap_rule(self) -> GapDetectionRule:
        return GapDetectionRule()

    def test_detects_intraday_gap_on_same_day(self, gap_rule: GapDetectionRule) -> None:
        # Two hourly bars with a 4-hour gap in between on the same day
        t1 = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)
        t2 = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)  # 4 hour jump (> 1.5h allowed)

        records = [
            OHLCVRecord(
                symbol="SPY",
                timestamp=t1,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=50000,
                interval=DataInterval.ONE_HOUR,
                source_provider_id="test",
            ),
            OHLCVRecord(
                symbol="SPY",
                timestamp=t2,
                open=100.5,
                high=102.0,
                low=100.0,
                close=101.5,
                volume=60000,
                interval=DataInterval.ONE_HOUR,
                source_provider_id="test",
            ),
        ]

        instrument = Instrument(
            symbol="SPY",
            asset_class=AssetClass.EQUITY_US,
            exchange="NYSE",
            currency="USD",
        )

        query = MarketDataQuery(
            instrument=instrument,
            start=t1,
            end=t2,
            interval=DataInterval.ONE_HOUR,
        )
        context = RuleContext(
            query=query,
            records=tuple(records),
            calendar=ContinuousCalendar(),
            reference_time=t2,
        )

        issues = gap_rule.validate(context)

        assert len(issues) == 1
        assert "Intraday gap" in issues[0].message
        assert issues[0].details["delta_seconds"] == 14400.0
