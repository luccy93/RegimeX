"""
RegimeX Portfolio Risk — Application Service
===========================================
Coordinates portfolio risk analysis use cases.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.modules.portfolio_risk.domain.models import PortfolioRiskResult, PriceSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class PortfolioRiskService:
    """
    Application service orchestrating portfolio risk calculation pipelines.
    """

    def __init__(self, engine: PortfolioRiskEngine | None = None) -> None:
        self._engine = engine or PortfolioRiskEngine()

    def analyze_price_series(
        self,
        prices: Sequence[float],
        timestamps: Sequence[datetime],
        symbol: str,
        periods_per_year: float = 252.0,
        target_return: float = 0.0,
        var_confidences: Sequence[float] = (0.90, 0.95, 0.99),
    ) -> PortfolioRiskResult:
        """
        Analyze portfolio risk metrics for a sequence of prices and timestamps.
        """
        price_series = PriceSeries(
            timestamps=tuple(timestamps),
            prices=tuple(prices),
            symbol=symbol,
        )
        return self._engine.analyze_risk(
            data=price_series,
            periods_per_year=periods_per_year,
            target_return=target_return,
            var_confidences=var_confidences,
            series_id=symbol,
        )
