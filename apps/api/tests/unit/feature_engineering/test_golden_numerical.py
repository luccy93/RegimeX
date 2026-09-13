"""
RegimeX Feature Engineering — Golden Numerical Unit Tests
=========================================================
Verifies all baseline features against exact hand-calculated expected values.
Does not rely on third-party library abstractions to verify the same formulas.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.momentum import (
    MomentumCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.range import (
    HighLowRangeCalculator,
    NormalizedTrueRangeCalculator,
    TrueRangeCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.returns import (
    SimpleReturnCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.trend import (
    EMARatioCalculator,
    SMARatioCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.volatility import (
    RollingVolatilityCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.volume import (
    VolumeChangeCalculator,
    VolumeRatioCalculator,
)


def _make_input(
    prices: tuple[float, ...],
    highs: tuple[float, ...] | None = None,
    lows: tuple[float, ...] | None = None,
    volumes: tuple[float, ...] | None = None,
) -> FeatureInputData:
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(base_ts + timedelta(days=i) for i in range(len(prices)))
    high_vals = highs if highs is not None else prices
    low_vals = lows if lows is not None else prices
    return FeatureInputData(
        timestamps=timestamps,
        opens=prices,
        highs=high_vals,
        lows=low_vals,
        closes=prices,
        volumes=volumes,
    )


class TestGoldenReturns:
    def test_return_1_positive_negative_zero(self):
        # 100 -> 110 (+10%), 110 -> 99 (-10%), 99 -> 99 (0%)
        # Plus 100 -> 90 (-10%)
        prices = (100.0, 110.0, 99.0, 99.0, 89.1)
        data = _make_input(prices)
        calc = SimpleReturnCalculator(1)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] == pytest.approx(0.10, abs=1e-7)
        assert res[2] == pytest.approx(-0.10, abs=1e-7)
        assert res[3] == pytest.approx(0.0, abs=1e-7)
        assert res[4] == pytest.approx(-0.10, abs=1e-7)

    @pytest.mark.parametrize("period", [5, 10, 20])
    def test_multi_period_returns_exact_offset(self, period: int):
        # Price: 100 + 2 * i
        # P_{t} - P_{t-k} = 2 * k
        # Return = 2 * k / (100 + 2 * (t - k))
        n = period + 5
        prices = tuple(100.0 + 2.0 * i for i in range(n))
        data = _make_input(prices)

        calc = SimpleReturnCalculator(period)
        res = calc.calculate(data)

        for i in range(period):
            assert res[i] is None

        for t in range(period, n):
            expected = (2.0 * period) / (100.0 + 2.0 * (t - period))
            assert res[t] == pytest.approx(expected, abs=1e-7)


class TestGoldenVolatility:
    def test_volatility_exact_sample_std(self):
        # Construct 4 prices producing 3 returns: r = [0.02, -0.01, 0.05]
        # Mean r = (0.02 - 0.01 + 0.05) / 3 = 0.06 / 3 = 0.02
        # Deviations: (0.02 - 0.02)=0, (-0.01 - 0.02)=-0.03, (0.05 - 0.02)=0.03
        # Sum of squared deviations = 0 + 0.0009 + 0.0009 = 0.0018
        # Sample variance (ddof=1) = 0.0018 / (3 - 1) = 0.0009
        # Sample std dev = sqrt(0.0009) = 0.03
        p0 = 100.0
        p1 = p0 * 1.02  # 102.0
        p2 = p1 * 0.99  # 100.98
        p3 = p2 * 1.05  # 106.029
        prices = (p0, p1, p2, p3)
        data = _make_input(prices)

        calc = RollingVolatilityCalculator(window=3, annualized=False)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        assert res[2] is None
        assert res[3] == pytest.approx(0.03, abs=1e-7)

    def test_annualized_volatility_exact(self):
        p0 = 100.0
        p1 = p0 * 1.02
        p2 = p1 * 0.99
        p3 = p2 * 1.05
        prices = (p0, p1, p2, p3)
        data = _make_input(prices)

        factor = 252.0
        calc = RollingVolatilityCalculator(window=3, annualized=True, annualization_factor=factor)
        res = calc.calculate(data)

        expected = 0.03 * math.sqrt(factor)
        assert res[3] == pytest.approx(expected, abs=1e-6)


class TestGoldenMomentum:
    def test_momentum_exact_values(self):
        prices = tuple(100.0 + 5.0 * i for i in range(15))
        data = _make_input(prices)

        calc = MomentumCalculator(window=10)
        res = calc.calculate(data)

        for i in range(10):
            assert res[i] is None

        # At t=10: P_10 = 150.0, P_0 = 100.0 -> (150 - 100) / 100 = 0.50
        assert res[10] == pytest.approx(0.50, abs=1e-7)
        # At t=11: P_11 = 155.0, P_1 = 105.0 -> 50 / 105
        assert res[11] == pytest.approx(50.0 / 105.0, abs=1e-7)


class TestGoldenTrend:
    def test_sma_ratio_exact(self):
        # 10 prices: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
        # Sum = 550, Mean = 55.0. P_9 = 100. Ratio = 100 / 55 = 1.8181818...
        prices = tuple(float(10 * (i + 1)) for i in range(10))
        data = _make_input(prices)

        calc = SMARatioCalculator(window=10)
        res = calc.calculate(data)

        for i in range(9):
            assert res[i] is None

        assert res[9] == pytest.approx(100.0 / 55.0, abs=1e-7)

    def test_ema_ratio_exact_manual_recursion(self):
        # span=3 => alpha = 2 / 4 = 0.5
        # prices = [100.0, 110.0, 120.0, 130.0]
        # EMA_0 = 100.0
        # EMA_1 = 0.5 * 110 + 0.5 * 100 = 105.0
        # EMA_2 = 0.5 * 120 + 0.5 * 105 = 112.5 -> ratio = 120 / 112.5 = 1.0666667
        # EMA_3 = 0.5 * 130 + 0.5 * 112.5 = 121.25 -> ratio = 130 / 121.25 = 1.0721649
        prices = (100.0, 110.0, 120.0, 130.0)
        data = _make_input(prices)

        calc = EMARatioCalculator(span=3)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        assert res[2] == pytest.approx(120.0 / 112.5, abs=1e-7)
        assert res[3] == pytest.approx(130.0 / 121.25, abs=1e-7)


class TestGoldenVolume:
    def test_volume_change_and_ratio_exact(self):
        # volumes = [1000, 1200, 1500, 1800]
        # V_change:
        # t=1: (1200 - 1000) / 1000 = 0.20
        # t=2: (1500 - 1200) / 1200 = 0.25
        # t=3: (1800 - 1500) / 1500 = 0.20
        volumes = (1000.0, 1200.0, 1500.0, 1800.0)
        prices = (10.0, 10.0, 10.0, 10.0)
        data = _make_input(prices, volumes=volumes)

        calc_chg = VolumeChangeCalculator()
        res_chg = calc_chg.calculate(data)

        assert res_chg[0] is None
        assert res_chg[1] == pytest.approx(0.20, abs=1e-7)
        assert res_chg[2] == pytest.approx(0.25, abs=1e-7)
        assert res_chg[3] == pytest.approx(0.20, abs=1e-7)

        # V_ratio window=3:
        # t=2: SMA(1000, 1200, 1500) = 1233.3333333333333 -> ratio = 1500 / 1233.3333333333333
        calc_rat = VolumeRatioCalculator(window=3)
        res_rat = calc_rat.calculate(data)
        assert res_rat[0] is None
        assert res_rat[1] is None
        assert res_rat[2] == pytest.approx(1500.0 / (3700.0 / 3.0), abs=1e-7)


class TestGoldenRange:
    def test_range_first_observation_and_gaps(self):
        # Bar 0: H=105, L=95, C=100
        # TR_0 = 105 - 95 = 10.0
        # HL_0 = (105 - 95) / 100 = 0.10
        # NTR_0 = 10.0 / 100 = 0.10
        #
        # Bar 1 (Gap Up): O=112, H=118, L=110, C=115
        # HL_1 = (118 - 110) / 115 = 8 / 115
        # TR_1 = max(118-110=8, |118-100|=18, |110-100|=10) = 18.0
        # NTR_1 = 18.0 / 115
        #
        # Bar 2 (Gap Down): O=85, H=88, L=80, C=82
        # HL_2 = (88 - 80) / 82 = 8 / 82
        # TR_2 = max(88-80=8, |88-115|=27, |80-115|=35) = 35.0
        # NTR_2 = 35.0 / 82
        #
        # Bar 3 (Inside Day): O=82, H=83, L=81, C=82.5
        # HL_3 = (83 - 81) / 82.5 = 2 / 82.5
        # TR_3 = max(83-81=2, |83-82|=1, |81-82|=1) = 2.0
        # NTR_3 = 2.0 / 82.5
        prices = (100.0, 115.0, 82.0, 82.5)
        highs = (105.0, 118.0, 88.0, 83.0)
        lows = (95.0, 110.0, 80.0, 81.0)
        data = _make_input(prices, highs=highs, lows=lows)

        calc_hl = HighLowRangeCalculator()
        calc_tr = TrueRangeCalculator()
        calc_ntr = NormalizedTrueRangeCalculator()

        res_hl = calc_hl.calculate(data)
        res_tr = calc_tr.calculate(data)
        res_ntr = calc_ntr.calculate(data)

        assert res_hl[0] == pytest.approx(10.0 / 100.0, abs=1e-7)
        assert res_tr[0] == pytest.approx(10.0, abs=1e-7)
        assert res_ntr[0] == pytest.approx(0.10, abs=1e-7)

        assert res_tr[1] == pytest.approx(18.0, abs=1e-7)
        assert res_ntr[1] == pytest.approx(18.0 / 115.0, abs=1e-7)

        assert res_tr[2] == pytest.approx(35.0, abs=1e-7)
        assert res_ntr[2] == pytest.approx(35.0 / 82.0, abs=1e-7)

        assert res_tr[3] == pytest.approx(2.0, abs=1e-7)
        assert res_ntr[3] == pytest.approx(2.0 / 82.5, abs=1e-7)
