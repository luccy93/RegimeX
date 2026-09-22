"""
RegimeX Portfolio Risk — Domain Package
=======================================
Exports domain models, errors, and interfaces for portfolio risk analytics.
"""

from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
    InsufficientTailObservationsError,
    InvalidConfidenceLevelError,
    InvalidPriceSeriesError,
    InvalidReturnSeriesError,
    MismatchedAssetAlignmentError,
    MismatchedWeightsError,
    NonFiniteValueError,
    PortfolioRiskError,
    RiskComputationError,
    TemporalOrderError,
)
from app.modules.portfolio_risk.domain.interfaces import (
    PortfolioRiskEngineProtocol,
)
from app.modules.portfolio_risk.domain.models import (
    DownsideRiskMetrics,
    DrawdownMetrics,
    ExpectedShortfallMetrics,
    PortfolioRiskResult,
    PortfolioWeights,
    PriceSeries,
    ReturnObservation,
    ReturnSeries,
    ReturnStatistics,
    ReturnType,
    VaRMetrics,
    VolatilityMetrics,
)

__all__ = [
    # Errors
    "InsufficientRiskDataError",
    "InsufficientTailObservationsError",
    "InvalidConfidenceLevelError",
    "InvalidPriceSeriesError",
    "InvalidReturnSeriesError",
    "MismatchedAssetAlignmentError",
    "MismatchedWeightsError",
    "NonFiniteValueError",
    "PortfolioRiskError",
    "RiskComputationError",
    "TemporalOrderError",
    # Interfaces
    "PortfolioRiskEngineProtocol",
    # Models
    "DownsideRiskMetrics",
    "DrawdownMetrics",
    "ExpectedShortfallMetrics",
    "PortfolioRiskResult",
    "PortfolioWeights",
    "PriceSeries",
    "ReturnObservation",
    "ReturnSeries",
    "ReturnStatistics",
    "ReturnType",
    "VaRMetrics",
    "VolatilityMetrics",
]
