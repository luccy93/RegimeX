"""
RegimeX Data Quality — NSE Trading Calendar
============================================
Encapsulates Indian equity market sessions, business days, and national holidays.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.data_quality.domain.calendar import SessionHours, TradingCalendar
from app.modules.data_quality.infrastructure.calendars.base import (
    good_friday,
    is_weekend,
)

_IST_TZ = ZoneInfo("Asia/Kolkata")


class NSECalendar(TradingCalendar):
    """
    Indian Equity Trading Calendar (NSE / BSE).

    Regular trading hours: 09:15 to 15:30 IST.
    """

    @property
    def calendar_id(self) -> str:
        return "nse"

    @property
    def name(self) -> str:
        return "National Stock Exchange of India"

    def get_session_hours(self) -> SessionHours:
        return SessionHours(
            open_time=time(9, 15),
            close_time=time(15, 30),
            timezone_name="Asia/Kolkata",
        )

    def get_holidays(self, year: int) -> set[date]:
        """Compute standard mandatory national holidays for Indian equities."""
        return {
            date(year, 1, 26),  # Republic Day
            good_friday(year),  # Good Friday
            date(year, 8, 15),  # Independence Day
            date(year, 10, 2),  # Mahatma Gandhi Jayanti
            date(year, 12, 25),  # Christmas Day
        }

    def is_trading_day(self, day: date | datetime) -> bool:
        """Check if day is a weekday and not a standard market holiday."""
        d = day.date() if isinstance(day, datetime) else day
        if is_weekend(d):
            return False
        return d not in self.get_holidays(d.year)

    def is_market_open(self, dt: datetime) -> bool:
        """Check if timezone-aware datetime falls within regular NSE trading hours."""
        if dt.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware: {dt!r}")

        dt_ist = dt.astimezone(_IST_TZ)
        if not self.is_trading_day(dt_ist.date()):
            return False

        # Regular session: 09:15 to 15:30
        open_time = time(9, 15)
        close_time = time(15, 30)
        return open_time <= dt_ist.time() <= close_time

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
