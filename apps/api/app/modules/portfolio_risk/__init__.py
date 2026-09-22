"""
RegimeX Portfolio Risk Module
=============================
Provides production-grade portfolio risk analytics:
- Return series calculations (arithmetic & log)
- Descriptive summary return statistics
- Realized & annualized volatility
- Downside deviation and semi-variance
- Peak-to-trough historical maximum drawdown
- Loss-oriented Value at Risk (VaR)
- Expected Shortfall (CVaR / Conditional VaR)
- Time-aligned multi-asset portfolio returns

Architectural position: ``apps/api/app/modules/portfolio_risk/``
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
from app.modules.portfolio_risk.infrastructure.engine import (
    PortfolioRiskEngine,
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
    # Infrastructure Engine
    "PortfolioRiskEngine",
]
