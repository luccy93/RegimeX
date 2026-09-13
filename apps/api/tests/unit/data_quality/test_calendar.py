"""
Unit tests for exchange trading calendars and CalendarRegistry.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.modules.data_quality.domain.calendar import CalendarRegistry
from app.modules.data_quality.infrastructure.calendars import (
    ContinuousCalendar,
    NSECalendar,
    NYSECalendar,
)
from app.modules.market_data.domain.models import AssetClass

_EASTERN = ZoneInfo("America/New_York")
_IST = ZoneInfo("Asia/Kolkata")


class TestNYSECalendar:
    def test_weekends_are_not_trading_days(self, nyse_calendar: NYSECalendar) -> None:
        sat = date(2024, 1, 6)
        sun = date(2024, 1, 7)
        assert not nyse_calendar.is_trading_day(sat)
        assert not nyse_calendar.is_trading_day(sun)

    def test_regular_business_day(self, nyse_calendar: NYSECalendar) -> None:
        tue = date(2024, 1, 2)
        assert nyse_calendar.is_trading_day(tue)

    def test_us_holidays(self, nyse_calendar: NYSECalendar) -> None:
        new_years = date(2024, 1, 1)
        mlk = date(2024, 1, 15)
        good_fri = date(2024, 3, 29)
        july_4th = date(2024, 7, 4)

        assert not nyse_calendar.is_trading_day(new_years)
        assert not nyse_calendar.is_trading_day(mlk)
        assert not nyse_calendar.is_trading_day(good_fri)
        assert not nyse_calendar.is_trading_day(july_4th)

    def test_market_open_hours(self, nyse_calendar: NYSECalendar) -> None:
        # 10:00 AM Eastern on a Tuesday -> OPEN
        open_dt = datetime(2024, 1, 2, 10, 0, tzinfo=_EASTERN)
        assert nyse_calendar.is_market_open(open_dt)

        # 08:00 AM Eastern on a Tuesday -> CLOSED (pre-market)
        pre_market = datetime(2024, 1, 2, 8, 0, tzinfo=_EASTERN)
        assert not nyse_calendar.is_market_open(pre_market)

        # 17:00 PM Eastern on a Tuesday -> CLOSED (after-hours)
        after_hours = datetime(2024, 1, 2, 17, 0, tzinfo=_EASTERN)
        assert not nyse_calendar.is_market_open(after_hours)

        # 10:00 AM Eastern on Saturday -> CLOSED
        weekend_dt = datetime(2024, 1, 6, 10, 0, tzinfo=_EASTERN)
        assert not nyse_calendar.is_market_open(weekend_dt)

    def test_expected_trading_days(self, nyse_calendar: NYSECalendar) -> None:
        # Jan 1 (Mon Holiday), Jan 2 (Tue), Jan 3 (Wed), Jan 4 (Thu), Jan 5 (Fri)
        days = nyse_calendar.expected_trading_days(date(2024, 1, 1), date(2024, 1, 5))
        assert days == [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
        ]

    def test_next_trading_day(self, nyse_calendar: NYSECalendar) -> None:
        friday = date(2024, 1, 5)
        next_day = nyse_calendar.next_trading_day(friday)
        assert next_day == date(2024, 1, 8)  # Skips Sat/Sun


class TestNSECalendar:
    def test_indian_holidays(self, nse_calendar: NSECalendar) -> None:
        republic_day = date(2024, 1, 26)
        assert not nse_calendar.is_trading_day(republic_day)

    def test_nse_trading_hours(self, nse_calendar: NSECalendar) -> None:
        # 10:00 AM IST on Tuesday Jan 2 -> OPEN
        open_ist = datetime(2024, 1, 2, 10, 0, tzinfo=_IST)
        assert nse_calendar.is_market_open(open_ist)

        # 08:30 AM IST on Tuesday Jan 2 -> CLOSED
        early_ist = datetime(2024, 1, 2, 8, 30, tzinfo=_IST)
        assert not nse_calendar.is_market_open(early_ist)


class TestContinuousCalendar:
    def test_every_day_is_trading_day(self, continuous_calendar: ContinuousCalendar) -> None:
        sat = date(2024, 1, 6)
        sun = date(2024, 1, 7)
        new_year = date(2024, 1, 1)

        assert continuous_calendar.is_trading_day(sat)
        assert continuous_calendar.is_trading_day(sun)
        assert continuous_calendar.is_trading_day(new_year)

    def test_always_open(self, continuous_calendar: ContinuousCalendar) -> None:
        mid_night = datetime(2024, 1, 1, 3, 0, tzinfo=UTC)
        assert continuous_calendar.is_market_open(mid_night)


class TestCalendarRegistry:
    def test_registry_resolution(self, calendar_registry: CalendarRegistry) -> None:
        nyse = calendar_registry.get("NASDAQ")
        assert isinstance(nyse, NYSECalendar)

        nse = calendar_registry.get("NSE")
        assert isinstance(nse, NSECalendar)

        crypto = calendar_registry.get("CRYPTO")
        assert isinstance(crypto, ContinuousCalendar)

    def test_get_for_instrument(self, calendar_registry: CalendarRegistry) -> None:
        crypto_cal = calendar_registry.get_for_instrument(AssetClass.CRYPTO)
        assert isinstance(crypto_cal, ContinuousCalendar)

        equity_us_cal = calendar_registry.get_for_instrument(AssetClass.EQUITY_US, "NASDAQ")
        assert isinstance(equity_us_cal, NYSECalendar)

        equity_in_cal = calendar_registry.get_for_instrument(AssetClass.EQUITY_IN, "NSE")
        assert isinstance(equity_in_cal, NSECalendar)
