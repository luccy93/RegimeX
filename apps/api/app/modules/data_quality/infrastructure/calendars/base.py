"""
RegimeX Data Quality — Calendar Utilities
=========================================
Common calendar calculations: Easter, nth-weekday, holiday observation rules.
"""

from __future__ import annotations

from datetime import date, timedelta


def is_weekend(d: date) -> bool:
    """Return True if the date is Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5


def observed_holiday(d: date) -> date:
    """
    US/standard holiday observation rule:
    If a holiday falls on a Saturday, it is observed on Friday.
    If it falls on a Sunday, it is observed on Monday.
    """
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """
    Find the nth occurrence of a specific weekday in a month (1-indexed).
    weekday: 0 = Monday, ..., 6 = Sunday.
    """
    first_day = date(year, month, 1)
    day_diff = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=day_diff)
    return first_occurrence + timedelta(weeks=n - 1)


def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Find the last occurrence of a specific weekday in a month."""
    # Find first day of next month, subtract 1 day
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    day_diff = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=day_diff)


def compute_easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def good_friday(year: int) -> date:
    """Good Friday is 2 days before Easter Sunday."""
    return compute_easter(year) - timedelta(days=2)
