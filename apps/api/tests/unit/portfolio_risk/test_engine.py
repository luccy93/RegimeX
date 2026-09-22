"""
RegimeX Portfolio Risk — End-to-End Engine & Determinism Tests
==============================================================
Tests full analyze_risk pipeline, determinism, and query methods.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.portfolio_risk.domain.models import PriceSeries, ReturnSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestPortfolioRiskEngine:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_analyze_risk_from_return_series(self) -> None:
        ts = tuple(_ts(i) for i in range(25))
        rets = tuple(-0.02 + 0.002 * i for i in range(25))
        series = ReturnSeries(timestamps=ts, values=rets, symbol="EQUITY")

        result = self.engine.analyze_risk(
            data=series,
            periods_per_year=252.0,
            target_return=0.0,
            var_confidences=(0.90, 0.95),
            series_id="EQUITY",
        )

        assert result.series_id == "EQUITY"
        assert result.observation_count == 25
        assert result.return_statistics.observation_count == 25
        assert result.volatility.annualized_volatility is not None
        assert result.volatility.periods_per_year == 252.0
        assert result.downside_risk.target_return == 0.0

        # Check VaR query method
        var_95 = result.get_var(0.95)
        assert var_95.confidence_level == 0.95

        # Check ES query method
        es_95 = result.get_expected_shortfall(0.95)
        assert es_95.confidence_level == 0.95
        assert es_95.expected_shortfall >= var_95.var_loss

    def test_analyze_risk_from_price_series(self) -> None:
        ts = tuple(_ts(i) for i in range(20))
        # Prices starting at 100 with small variations
        prices = tuple(100.0 + (i % 5) * 2.0 - (i % 3) * 1.5 for i in range(20))
        price_series = PriceSeries(timestamps=ts, prices=prices, symbol="INDEX")

        result = self.engine.analyze_risk(
            data=price_series,
            periods_per_year=252.0,
            series_id="INDEX",
        )

        assert result.series_id == "INDEX"
        assert result.observation_count == 19
        assert result.drawdown.max_drawdown <= 0.0

    def test_repeated_runs_produce_deterministic_identical_output(self) -> None:
        ts = tuple(_ts(i) for i in range(30))
        rets = tuple(-0.03 + (i % 7) * 0.01 for i in range(30))
        series = ReturnSeries(timestamps=ts, values=rets, symbol="DETERMINISTIC")

        res_1 = self.engine.analyze_risk(series, periods_per_year=252.0)
        res_2 = self.engine.analyze_risk(series, periods_per_year=252.0)

        assert res_1.return_statistics.mean_return == res_2.return_statistics.mean_return
        s1 = res_1.return_statistics.standard_deviation
        s2 = res_2.return_statistics.standard_deviation
        assert s1 == s2
        assert res_1.volatility.period_volatility == res_2.volatility.period_volatility
        assert res_1.volatility.annualized_volatility == res_2.volatility.annualized_volatility
        assert res_1.downside_risk.downside_deviation == res_2.downside_risk.downside_deviation
        assert res_1.drawdown.max_drawdown == res_2.drawdown.max_drawdown
        assert res_1.get_var(0.95).var_loss == res_2.get_var(0.95).var_loss
        es1 = res_1.get_expected_shortfall(0.95).expected_shortfall
        es2 = res_2.get_expected_shortfall(0.95).expected_shortfall
        assert es1 == es2
