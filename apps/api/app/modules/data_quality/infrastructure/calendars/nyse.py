"""
RegimeX Data Quality — NYSE Trading Calendar
=============================================
Encapsulates NYSE/NASDAQ trading sessions, business days, and US equity holidays.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.data_quality.domain.calendar import SessionHours, TradingCalendar
from app.modules.data_quality.infrastructure.calendars.base import (
    good_friday,
    is_weekend,
    last_weekday_of_month,
    nth_weekday_of_month,
    observed_holiday,
)

_EASTERN_TZ = ZoneInfo("America/New_York")


class NYSECalendar(TradingCalendar):
    """
    US Equity Trading Calendar (NYSE / NASDAQ).

    Regular trading hours: 09:30 to 16:00 US/Eastern.
    """

    @property
    def calendar_id(self) -> str:
        return "nyse"

    @property
    def name(self) -> str:
        return "New York Stock Exchange"

    def get_session_hours(self) -> SessionHours:
        return SessionHours(
            open_time=time(9, 30),
            close_time=time(16, 0),
            timezone_name="America/New_York",
        )

    def get_holidays(self, year: int) -> set[date]:
        """Compute all observed US equity market holidays for a given year."""
        holidays: set[date] = {
            observed_holiday(date(year, 1, 1)),  # New Year's Day
            nth_weekday_of_month(year, 1, weekday=0, n=3),  # MLK Day (3rd Mon Jan)
            nth_weekday_of_month(year, 2, weekday=0, n=3),  # Washington/Presidents (3rd Mon Feb)
            good_friday(year),  # Good Friday
            last_weekday_of_month(year, 5, weekday=0),  # Memorial Day (Last Mon May)
            observed_holiday(date(year, 7, 4)),  # Independence Day
            nth_weekday_of_month(year, 9, weekday=0, n=1),  # Labor Day (1st Mon Sep)
            nth_weekday_of_month(year, 11, weekday=3, n=4),  # Thanksgiving (4th Thu Nov)
            observed_holiday(date(year, 12, 25)),  # Christmas Day
        }
        # Juneteenth became federal holiday in 2021/observed from 2022
        if year >= 2022:
            holidays.add(observed_holiday(date(year, 6, 19)))

        return holidays

    def is_trading_day(self, day: date | datetime) -> bool:
        """Check if day is a weekday and not an official market holiday."""
        d = day.date() if isinstance(day, datetime) else day
        if is_weekend(d):
            return False
        return d not in self.get_holidays(d.year)

    def is_market_open(self, dt: datetime) -> bool:
        """Check if timezone-aware datetime falls within regular NYSE trading hours."""
        if dt.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware: {dt!r}")

        dt_eastern = dt.astimezone(_EASTERN_TZ)
        if not self.is_trading_day(dt_eastern.date()):
            return False

        # Regular session: 09:30 to 16:00
        open_time = time(9, 30)
        close_time = time(16, 0)
        return open_time <= dt_eastern.time() <= close_time

    def expected_trading_days(self, start_date: date, end_date: date) -> list[date]:
        """Return all scheduled trading days in [start_date, end_date]."""
        current = start_date
        sessions: list[date] = []
        while current <= end_date:
            if self.is_trading_day(current):
                sessions.append(current)
            current += timedelta(days=1)
        return sessions

    def next_trading_day(self, day: date) -> date:
        """Return the next trading day strictly after day."""
        current = day + timedelta(days=1)
        while not self.is_trading_day(current):
            current += timedelta(days=1)
        return current
