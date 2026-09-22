"""
RegimeX Portfolio Risk — Public Contract Tests
==============================================
Validates public API contracts and accessor queries for PortfolioRiskResult
and its constituent metrics to guarantee stable semantics for downstream modules (V14+).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.portfolio_risk.domain.models import (
    DownsideRiskMetrics,
    DrawdownMetrics,
    ExpectedShortfallMetrics,
    PortfolioRiskResult,
    ReturnSeries,
    ReturnStatistics,
    VaRMetrics,
    VolatilityMetrics,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestRiskContracts:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_portfolio_risk_result_contract_and_queries(self) -> None:
        ts = tuple(_ts(i) for i in range(20))
        rets = tuple(-0.02 + 0.002 * i for i in range(20))
        series = ReturnSeries(timestamps=ts, values=rets, symbol="PORTFOLIO_1")

        result = self.engine.analyze_risk(
            data=series,
            periods_per_year=252.0,
            target_return=0.0,
            var_confidences=(0.90, 0.95, 0.99),
            series_id="PORTFOLIO_1",
        )

        # Contract guarantees
        assert isinstance(result, PortfolioRiskResult)
        assert isinstance(result.return_statistics, ReturnStatistics)
        assert isinstance(result.volatility, VolatilityMetrics)
        assert isinstance(result.downside_risk, DownsideRiskMetrics)
        assert isinstance(result.drawdown, DrawdownMetrics)

        # Query methods
        var_90 = result.get_var(0.90)
        var_95 = result.get_var(0.95)
        var_99 = result.get_var(0.99)
        assert isinstance(var_90, VaRMetrics)
        assert var_99.var_loss >= var_95.var_loss >= var_90.var_loss

        es_95 = result.get_expected_shortfall(0.95)
        assert isinstance(es_95, ExpectedShortfallMetrics)
        assert es_95.expected_shortfall >= var_95.var_loss

        # Unknown confidence query raises KeyError
        with pytest.raises(KeyError):
            result.get_var(0.85)

        with pytest.raises(KeyError):
            result.get_expected_shortfall(0.85)

        # Metadata contracts
        assert result.series_id == "PORTFOLIO_1"
        assert result.start_timestamp == _ts(0)
        assert result.end_timestamp == _ts(19)
        assert result.computed_at.tzinfo == UTC
