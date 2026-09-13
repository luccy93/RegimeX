"""
RegimeX Data Quality Module
============================
Public API surface for market data validation and quality evaluation.
"""

from app.modules.data_quality.application import (
    MarketDataValidationPipeline,
    ValidationConfig,
)
from app.modules.data_quality.domain import (
    CalendarRegistry,
    DataQualityRule,
    QualityCategory,
    QualityIssue,
    QualityReport,
    QualitySeverity,
    QualityStatistics,
    QualityStatus,
    RuleContext,
    SessionHours,
    TradingCalendar,
)

__all__ = [
    # Pipeline & Config
    "MarketDataValidationPipeline",
    "ValidationConfig",
    # Domain Models
    "QualityStatus",
    "QualitySeverity",
    "QualityCategory",
    "QualityIssue",
    "QualityStatistics",
    "QualityReport",
    # Rule Base
    "DataQualityRule",
    "RuleContext",
    # Calendar Base
    "TradingCalendar",
    "SessionHours",
    "CalendarRegistry",
]
