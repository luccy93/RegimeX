"""
RegimeX Regime Intelligence — Domain Package
============================================
Core domain models, errors, and interfaces for the regime intelligence layer.
"""

from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
    InvalidFeatureStatisticsError,
    InvalidRegimeAssignmentError,
    InvalidRegimeHistoryError,
    RegimeIntelligenceError,
    UnsupportedRankingMetricError,
)
from app.modules.regime_intelligence.domain.interfaces import (
    DurationAnalyzerProtocol,
    FeatureStatisticsCalculator,
    RegimeIntelligenceServiceProtocol,
)
from app.modules.regime_intelligence.domain.models import (
    CurrentRegimeContext,
    FeatureStatistic,
    RegimeAssignment,
    RegimeHistorySummary,
    RegimeProfile,
)

__all__ = [
    "CurrentRegimeContext",
    "DurationAnalyzerProtocol",
    "FeatureStatistic",
    "FeatureStatisticsCalculator",
    "InsufficientRegimeDataError",
    "InvalidFeatureStatisticsError",
    "InvalidRegimeAssignmentError",
    "InvalidRegimeHistoryError",
    "RegimeAssignment",
    "RegimeHistorySummary",
    "RegimeIntelligenceError",
    "RegimeIntelligenceServiceProtocol",
    "RegimeProfile",
    "UnsupportedRankingMetricError",
]
