"""
RegimeX Data Quality — Infrastructure Calendars Package
========================================================
Concrete exchange calendars and default registry factory.
"""

from app.modules.data_quality.domain.calendar import CalendarRegistry
from app.modules.data_quality.infrastructure.calendars.continuous import (
    ContinuousCalendar,
)
from app.modules.data_quality.infrastructure.calendars.nse import NSECalendar
from app.modules.data_quality.infrastructure.calendars.nyse import NYSECalendar


def create_default_calendar_registry() -> CalendarRegistry:
    """Create and pre-populate a CalendarRegistry with standard exchange calendars."""
    registry = CalendarRegistry()

    nyse = NYSECalendar()
    registry.register(
        nyse,
        aliases=["nasdaq", "amex", "bats", "arca", "us", "otc", "index", "cboe"],
    )

    nse = NSECalendar()
    registry.register(nse, aliases=["bse", "india", "in"])

    continuous = ContinuousCalendar()
    registry.register(
        continuous,
        aliases=["crypto", "binance", "coinbase", "fx", "forex", "24_7"],
    )

    registry.set_default(nyse)
    return registry


__all__ = [
    "NYSECalendar",
    "NSECalendar",
    "ContinuousCalendar",
    "create_default_calendar_registry",
]
