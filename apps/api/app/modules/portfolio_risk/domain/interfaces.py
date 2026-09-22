"""
RegimeX Portfolio Risk — Domain Interfaces
==========================================
Defines protocols and abstract contracts for portfolio risk calculation engines.

Architectural position: ``domain/interfaces.py``
- Pure Python typing protocols.
- Zero infrastructure or framework dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from app.modules.portfolio_risk.domain.models import (
    DownsideRiskMetrics,
    DrawdownMetrics,
    ExpectedShortfallMetrics,
    PortfolioRiskResult,
    PortfolioWeights,
    PriceSeries,
    ReturnSeries,
    ReturnStatistics,
    VaRMetrics,
    VolatilityMetrics,
)


class PortfolioRiskEngineProtocol(Protocol):
    """Protocol interface for portfolio risk calculation engines."""

    def compute_arithmetic_returns(
        self,
        prices: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        symbol: str | None = None,
    ) -> ReturnSeries:
        """Calculate discrete arithmetic percentage returns r_t = P_t / P_{t-1} - 1."""
        ...

    def compute_log_returns(
        self,
        prices: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        symbol: str | None = None,
    ) -> ReturnSeries:
        """Calculate continuously compounded log returns r_t = ln(P_t / P_{t-1})."""
        ...

    def compute_statistics(
        self,
        returns: ReturnSeries | Sequence[float],
    ) -> ReturnStatistics:
        """Calculate summary statistics (mean, median, sample std ddof=1, min, max)."""
        ...

    def compute_volatility(
        self,
        returns: ReturnSeries | Sequence[float],
        periods_per_year: float | None = None,
    ) -> VolatilityMetrics:
        """Calculate realized period and annualized volatility."""
        ...

    def compute_downside_risk(
        self,
        returns: ReturnSeries | Sequence[float],
        target_return: float = 0.0,
    ) -> DownsideRiskMetrics:
        """Calculate downside deviation below a target return threshold."""
        ...

    def compute_drawdown_from_returns(
        self,
        returns: ReturnSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> DrawdownMetrics:
        """Calculate peak-to-trough drawdown from an equity curve initialized at 1.0."""
        ...

    def compute_drawdown_from_prices(
        self,
        prices: PriceSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> DrawdownMetrics:
        """Calculate peak-to-trough drawdown directly from price series."""
        ...

    def compute_var(
        self,
        returns: ReturnSeries | Sequence[float],
        confidence_level: float = 0.95,
    ) -> VaRMetrics:
        """Calculate historical Value at Risk at confidence_level (loss-oriented)."""
        ...

    def compute_expected_shortfall(
        self,
        returns: ReturnSeries | Sequence[float],
        confidence_level: float = 0.95,
    ) -> ExpectedShortfallMetrics:
        """Calculate historical Expected Shortfall / CVaR beyond VaR threshold."""
        ...

    def compute_portfolio_returns(
        self,
        asset_returns: dict[str, ReturnSeries],
        weights: PortfolioWeights,
    ) -> ReturnSeries:
        """Calculate timestamp-aligned multi-asset weighted portfolio returns."""
        ...

    def analyze_risk(
        self,
        data: ReturnSeries | PriceSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        is_price_series: bool = False,
        periods_per_year: float | None = None,
        target_return: float = 0.0,
        var_confidences: Sequence[float] = (0.90, 0.95, 0.99),
        series_id: str = "portfolio",
    ) -> PortfolioRiskResult:
        """Run the comprehensive end-to-end portfolio risk analysis pipeline."""
        ...
