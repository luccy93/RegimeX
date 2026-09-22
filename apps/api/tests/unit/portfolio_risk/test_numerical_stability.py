"""
RegimeX Portfolio Risk — Numerical Stability Tests
==================================================
Tests numerical robustness across extreme scales and floating-point boundaries:
- Microscopic returns (order of 10^-8 to 10^-6).
- Massive finite returns (+500%, -99%).
- Nearly identical prices (difference < 1e-7).
- Repeated constant prices (zero volatility, zero drawdown).
- Large sample sizes (10,000 observations).
- Zero NaN or Inf propagation in outputs.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
from app.modules.portfolio_risk.domain.models import ReturnSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestNumericalStability:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_microscopic_returns_stability(self) -> None:
        # Returns around 1e-8
        rets = [1e-8, -2e-8, 1.5e-8, -0.5e-8, 2.5e-8] * 10
        ts = tuple(_ts(i) for i in range(len(rets)))
        series = ReturnSeries(timestamps=ts, values=tuple(rets))

        res = self.engine.analyze_risk(series, periods_per_year=252.0)

        assert not math.isnan(res.return_statistics.mean_return)
        assert not math.isinf(res.return_statistics.mean_return)
        assert not math.isnan(res.volatility.period_volatility)
        assert res.volatility.period_volatility >= 0.0
        assert res.downside_risk.downside_deviation >= 0.0
        assert not math.isnan(res.get_var(0.95).var_loss)
        assert not math.isnan(res.get_expected_shortfall(0.95).expected_shortfall)

    def test_large_finite_returns_stability(self) -> None:
        # Massive returns: +500% (5.0), -90% (-0.90)
        rets = [5.0, -0.90, 2.5, -0.50, 1.2]
        ts = tuple(_ts(i) for i in range(len(rets)))
        series = ReturnSeries(timestamps=ts, values=tuple(rets))

        res = self.engine.analyze_risk(series, periods_per_year=252.0)

        assert not math.isnan(res.return_statistics.mean_return)
        assert not math.isnan(res.volatility.period_volatility)
        assert res.drawdown.max_drawdown <= 0.0
        assert res.drawdown.drawdown_magnitude <= 1.0

    def test_nearly_identical_prices_stability(self) -> None:
        # Prices differing by 1e-7
        base_p = 1000.0
        prices = [base_p + 1e-7 * (i % 3) for i in range(20)]
        ret_series = self.engine.compute_arithmetic_returns(prices)

        stats = self.engine.compute_statistics(ret_series)
        assert abs(stats.mean_return) < 1e-6
        assert stats.standard_deviation >= 0.0

    def test_repeated_constant_prices_stability(self) -> None:
        prices = [150.0] * 20
        ret_series = self.engine.compute_arithmetic_returns(prices)
        vol = self.engine.compute_volatility(ret_series, periods_per_year=252.0)

        assert vol.period_volatility == 0.0
        assert vol.annualized_volatility == 0.0

        dd = self.engine.compute_drawdown_from_prices(prices)
        assert dd.max_drawdown == 0.0
        assert dd.drawdown_magnitude == 0.0

    def test_large_dataset_performance_and_stability(self) -> None:
        # 10,000 observations
        np.random.seed(404)
        rets = list(np.random.normal(0.0002, 0.01, size=10000))
        ts = tuple(_ts(i) for i in range(len(rets)))
        series = ReturnSeries(timestamps=ts, values=tuple(rets))

        res = self.engine.analyze_risk(series, periods_per_year=252.0)

        assert res.observation_count == 10000
        assert not math.isnan(res.volatility.period_volatility)
        assert not math.isnan(res.drawdown.max_drawdown)
        assert not math.isnan(res.get_var(0.99).var_loss)
        assert not math.isnan(res.get_expected_shortfall(0.99).expected_shortfall)
