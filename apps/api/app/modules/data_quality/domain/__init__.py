"""
RegimeX Data Quality — Domain Package
======================================
Public re-exports for data quality domain models, rule abstractions, and calendars.
"""

from app.modules.data_quality.domain.calendar import (
    CalendarRegistry,
    SessionHours,
    TradingCalendar,
)
from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualityReport,
    QualitySeverity,
    QualityStatistics,
    QualityStatus,
)
from app.modules.data_quality.domain.rules import (
    DataQualityRule,
    RuleContext,
)

__all__ = [
    # Models
    "QualitySeverity",
    "QualityStatus",
    "QualityCategory",
    "QualityIssue",
    "QualityStatistics",
    "QualityReport",
    # Rule engine
    "DataQualityRule",
    "RuleContext",
    # Calendar
    "TradingCalendar",
    "SessionHours",
    "CalendarRegistry",
]
