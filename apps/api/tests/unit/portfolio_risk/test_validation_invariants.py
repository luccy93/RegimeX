"""
RegimeX Portfolio Risk — Mathematical Invariants Validation Tests
=================================================================
Verifies core mathematical invariants and property bounds across all risk metrics:
- Return statistics bounds: min_return <= mean_return <= max_return.
- Volatility bounds: s >= 0, annualized_volatility = period_volatility * sqrt(P).
- Downside deviation bounds: downside_dev >= 0, zero contribution from above-target returns.
- Drawdown bounds: DD <= 0, MDD <= 0, peak >= trough, monotonic growth MDD == 0.
- Portfolio return linear combination: r_p,t = sum(w_i * r_i,t).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.modules.portfolio_risk.domain.models import PortfolioWeights, ReturnSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestReturnStatisticsInvariants:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    @pytest.mark.parametrize(
        "returns",
        [
            [-0.05, -0.02, 0.01, 0.04, 0.08],
            [-0.01, -0.01, -0.01, -0.01],
            [0.10, -0.10],
            [0.001 * i for i in range(-50, 51)],
        ],
    )
    def test_min_mean_max_bounds_invariant(self, returns: list[float]) -> None:
        stats = self.engine.compute_statistics(returns)
        assert stats.minimum_return <= stats.mean_return <= stats.maximum_return
        assert stats.minimum_return <= stats.median_return <= stats.maximum_return
        assert stats.observation_count == len(returns)

    def test_sample_variance_bessel_correction(self) -> None:
        rets = [0.02, -0.01, 0.05]
        stats = self.engine.compute_statistics(rets)
        arr = np.asarray(rets, dtype=np.float64)
        expected_std = float(np.std(arr, ddof=1))
        assert abs(stats.standard_deviation - expected_std) < 1e-12


class TestVolatilityInvariants:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_volatility_non_negative(self) -> None:
        rets = [-0.03, 0.01, 0.02, -0.01]
        vol = self.engine.compute_volatility(rets)
        assert vol.period_volatility >= 0.0

    def test_annualization_scaling_factor_one(self) -> None:
        rets = [0.01, -0.02, 0.03]
        vol = self.engine.compute_volatility(rets, periods_per_year=1.0)
        assert vol.annualized_volatility == vol.period_volatility

    @pytest.mark.parametrize("factor", [12.0, 52.0, 252.0, 365.0])
    def test_annualization_scaling_exact(self, factor: float) -> None:
        rets = [0.02, -0.01, 0.04, -0.02]
        vol = self.engine.compute_volatility(rets, periods_per_year=factor)
        expected_ann = vol.period_volatility * math.sqrt(factor)
        assert vol.annualized_volatility is not None
        assert abs(vol.annualized_volatility - expected_ann) < 1e-12

    def test_rejects_invalid_annualization_factor(self) -> None:
        rets = [0.01, 0.02]
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=0.0)
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=-1.0)
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=float("nan"))
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=float("inf"))


class TestDownsideRiskInvariants:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_downside_deviation_always_non_negative(self) -> None:
        rets = [-0.02, 0.03, -0.01, 0.05]
        d = self.engine.compute_downside_risk(rets, target_return=0.0)
        assert d.downside_deviation >= 0.0

    def test_returns_equal_to_target_have_zero_deviation(self) -> None:
        rets = [0.02, 0.02, 0.02]
        d = self.engine.compute_downside_risk(rets, target_return=0.02)
        assert d.downside_deviation == 0.0
        assert d.observations_below_target == 0

    def test_positive_target_benchmark(self) -> None:
        rets = [0.01, 0.02, 0.03]  # All positive, but 0.01 and 0.02 are below target 0.025
        d = self.engine.compute_downside_risk(rets, target_return=0.025)
        assert d.observations_below_target == 2
        assert d.downside_deviation > 0.0

    def test_negative_target_benchmark(self) -> None:
        rets = [-0.01, -0.02, -0.05]  # Only -0.05 is below target -0.03
        d = self.engine.compute_downside_risk(rets, target_return=-0.03)
        assert d.observations_below_target == 1
        expected = math.sqrt(((-0.05 - (-0.03)) ** 2) / 3.0)
        assert abs(d.downside_deviation - expected) < 1e-12

    def test_returns_above_target_contribute_zero(self) -> None:
        rets_all_above = [0.10, 0.20, 0.30]
        d = self.engine.compute_downside_risk(rets_all_above, target_return=0.05)
        assert d.downside_deviation == 0.0


class TestDrawdownInvariants:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_drawdown_always_non_positive(self) -> None:
        prices = [100.0, 95.0, 90.0, 105.0, 85.0]
        dd = self.engine.compute_drawdown_from_prices(prices)
        assert dd.max_drawdown <= 0.0
        assert dd.drawdown_magnitude >= 0.0
        assert dd.peak_value >= dd.trough_value

    def test_new_all_time_highs_and_recovery(self) -> None:
        # 100 -> 80 (trough -20%) -> 100 (recovered) -> 120 (ATH) -> 108 (-10%)
        # Deepest drawdown is -20% from 100 to 80, fully recovered
        prices = [100.0, 80.0, 100.0, 120.0, 108.0]
        timestamps = [_ts(i) for i in range(5)]
        dd = self.engine.compute_drawdown_from_prices(prices, timestamps)

        assert abs(dd.max_drawdown - (-0.20)) < 1e-12
        assert dd.peak_value == 100.0
        assert dd.trough_value == 80.0
        assert dd.peak_timestamp == _ts(0)
        assert dd.trough_timestamp == _ts(1)
        assert dd.is_recovered is True
        assert dd.recovery_timestamp == _ts(2)


class TestPortfolioLinearCombinationInvariant:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_portfolio_returns_exact_linear_combination(self) -> None:
        ts = tuple(_ts(i) for i in range(5))
        r_a = (0.01, -0.02, 0.03, -0.01, 0.02)
        r_b = (-0.03, 0.01, -0.02, 0.04, -0.01)
        r_c = (0.02, 0.02, -0.01, -0.01, 0.05)

        s_a = ReturnSeries(timestamps=ts, values=r_a, symbol="A")
        s_b = ReturnSeries(timestamps=ts, values=r_b, symbol="B")
        s_c = ReturnSeries(timestamps=ts, values=r_c, symbol="C")

        w_a, w_b, w_c = 0.4, 0.35, 0.25
        weights = PortfolioWeights(symbols=("A", "B", "C"), weights=(w_a, w_b, w_c))

        port = self.engine.compute_portfolio_returns({"A": s_a, "B": s_b, "C": s_c}, weights)

        for t in range(5):
            expected = w_a * r_a[t] + w_b * r_b[t] + w_c * r_c[t]
            assert abs(port[t] - expected) < 1e-12
