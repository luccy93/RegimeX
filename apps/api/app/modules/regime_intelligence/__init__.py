"""
RegimeX Regime Intelligence Module
==================================
Transforms raw regime assignments into descriptive, explainable historical analytics:
profiles, frequency analysis, duration properties, feature characteristics,
current regime context, and deterministic ranking.

Conforms to V03 Architecture and V09 Specifications.
"""

from app.modules.regime_intelligence.application.facade import (
    MarketIntelligenceFacade,
)
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
    InvalidFeatureStatisticsError,
    InvalidRegimeAssignmentError,
    InvalidRegimeHistoryError,
    RegimeIntelligenceError,
    UnsupportedRankingMetricError,
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
    "FeatureStatistic",
    "InsufficientRegimeDataError",
    "InvalidFeatureStatisticsError",
    "InvalidRegimeAssignmentError",
    "InvalidRegimeHistoryError",
    "MarketIntelligenceFacade",
    "RegimeAssignment",
    "RegimeHistorySummary",
    "RegimeIntelligenceError",
    "RegimeIntelligenceService",
    "RegimeProfile",
    "UnsupportedRankingMetricError",
]
