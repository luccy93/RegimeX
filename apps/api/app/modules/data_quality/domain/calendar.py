"""
RegimeX Data Quality — Trading Calendar Abstraction
===================================================
Defines the abstract interface for exchange trading calendars and sessions.

Design Principles:
- Provider-independent and exchange-extensible.
- Distinguishes 24/7 continuous markets (Crypto/FX) from session-based equity markets.
- All session time comparisons are timezone-aware.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.modules.market_data.domain.models import AssetClass


class SessionHours(BaseModel):
    """Trading session start and close times in the exchange's local timezone."""

    model_config = {"frozen": True}

    open_time: time = Field(description="Market session open time.")
    close_time: time = Field(description="Market session close time.")
    timezone_name: str = Field(description="IANA timezone identifier, e.g. 'America/New_York'.")


class TradingCalendar(ABC):
    """
    Abstract trading calendar interface.

    Subclasses encapsulate holiday schedules, trading hours, and session definitions
    for specific markets/exchanges without hardcoding exchange logic into validation rules.
    """

    @property
    @abstractmethod
    def calendar_id(self) -> str:
        """Stable snake_case identifier for this calendar (e.g. 'nyse', 'nse', '24_7')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name for the calendar."""
        ...

    @abstractmethod
    def is_trading_day(self, day: date | datetime) -> bool:
        """Return True if the date is an active trading session (not weekend, not holiday)."""
        ...

    @abstractmethod
    def is_market_open(self, dt: datetime) -> bool:
        """Return True if the specific timezone-aware datetime falls within trading hours."""
        ...

    @abstractmethod
    def get_session_hours(self) -> SessionHours:
        """Return typical session open/close hours and timezone."""
        ...

    @abstractmethod
    def expected_trading_days(self, start_date: date, end_date: date) -> list[date]:
        """Return all scheduled trading dates in the inclusive range [start_date, end_date]."""
        ...

    @abstractmethod
    def next_trading_day(self, day: date) -> date:
        """Return the next trading date strictly after the given date."""
        ...


class CalendarRegistry:
    """
    In-memory registry mapping exchange identifiers and asset classes to TradingCalendars.
    """

    def __init__(self) -> None:
        self._calendars: dict[str, TradingCalendar] = {}
        self._default_calendar: TradingCalendar | None = None

    def register(self, calendar: TradingCalendar, aliases: list[str] | None = None) -> None:
        """Register a calendar under its ID and optional exchange aliases."""
        self._calendars[calendar.calendar_id.lower()] = calendar
        if aliases:
            for alias in aliases:
                self._calendars[alias.lower()] = calendar

    def set_default(self, calendar: TradingCalendar) -> None:
        """Set fallback calendar when an exchange is unknown."""
        self._default_calendar = calendar
        self.register(calendar)

    def get(self, exchange_or_id: str) -> TradingCalendar:
        """Retrieve a calendar by exchange or calendar ID."""
        key = exchange_or_id.strip().lower()
        if key in self._calendars:
            return self._calendars[key]
        if self._default_calendar is not None:
            return self._default_calendar
        raise KeyError(f"No trading calendar registered for {exchange_or_id!r}")

    def get_for_instrument(self, asset_class: AssetClass, exchange: str = "") -> TradingCalendar:
        """Resolve the appropriate calendar for an instrument."""
        if asset_class in (AssetClass.CRYPTO, AssetClass.FX):
            return self.get("24_7")
        if exchange and exchange.strip().lower() in self._calendars:
            return self.get(exchange)
        if self._default_calendar is not None:
            return self._default_calendar
        raise KeyError(f"No calendar found for asset_class={asset_class.value} exchange={exchange}")
