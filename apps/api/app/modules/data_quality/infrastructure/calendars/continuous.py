"""
RegimeX Data Quality — Continuous 24/7 Market Calendar
======================================================
Represents 24/7/365 markets (Crypto, round-the-clock FX) where there are no weekends,
market holidays, or session closes.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.modules.data_quality.domain.calendar import SessionHours, TradingCalendar


class ContinuousCalendar(TradingCalendar):
    """
    Continuous 24/7 Calendar for digital assets and decentralized markets.
    """

    @property
    def calendar_id(self) -> str:
        return "24_7"

    @property
    def name(self) -> str:
        return "Continuous 24/7 Market Calendar"

    def get_session_hours(self) -> SessionHours:
        return SessionHours(
            open_time=time(0, 0),
            close_time=time(23, 59, 59),
            timezone_name="UTC",
        )

    def is_trading_day(self, day: date | datetime) -> bool:
        """Every calendar day is an active trading session in 24/7 markets."""
        return True

    def is_market_open(self, dt: datetime) -> bool:
        """Continuous markets are always open."""
        return True

    def expected_trading_days(self, start_date: date, end_date: date) -> list[date]:
        """All calendar dates in [start_date, end_date]."""
        current = start_date
        sessions: list[date] = []
        while current <= end_date:
            sessions.append(current)
            current += timedelta(days=1)
        return sessions

    def next_trading_day(self, day: date) -> date:
        return day + timedelta(days=1)
