"""
RegimeX Feature Engineering — Volatility Calculator Unit Tests
==============================================================
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.volatility import (
    RollingVolatilityCalculator,
)


class TestRollingVolatilityCalculator:
    def test_volatility_hand_calculated(self, base_timestamp: datetime):
        # 4 prices producing 3 returns: 0.01, 0.02, 0.03
        # std dev of [0.01, 0.02, 0.03] with ddof=1 is 0.01
        p0 = 100.0
        p1 = 100.0 * 1.01
        p2 = p1 * 1.02
        p3 = p2 * 1.03
        prices = (p0, p1, p2, p3)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))

        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = RollingVolatilityCalculator(window=3)
        res = calc.calculate(data)

        assert len(res) == 4
        assert res[0] is None
        assert res[1] is None
        assert res[2] is None
        assert res[3] == pytest.approx(0.01, abs=1e-6)

    def test_annualization_scaling(self, base_timestamp: datetime):
        p0 = 100.0
        p1 = 100.0 * 1.01
        p2 = p1 * 1.02
        p3 = p2 * 1.03
        prices = (p0, p1, p2, p3)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc_raw = RollingVolatilityCalculator(window=3, annualized=False)
        calc_ann = RollingVolatilityCalculator(
            window=3,
            annualized=True,
            annualization_factor=252.0,
        )

        res_raw = calc_raw.calculate(data)
        res_ann = calc_ann.calculate(data)

        assert res_raw[3] is not None
        assert res_ann[3] is not None
        assert res_ann[3] == pytest.approx(res_raw[3] * math.sqrt(252.0))

    def test_constant_prices_yields_zero_volatility(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)
        calc = RollingVolatilityCalculator(window=10)
        res = calc.calculate(data)

        # First 10 observations must be None
        for i in range(10):
            assert res[i] is None

        # Remaining observations must be 0.0
        for val in res[10:]:
            assert val == pytest.approx(0.0)

    def test_insufficient_history(self, base_timestamp: datetime):
        prices = (100.0, 101.0, 102.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )
        calc = RollingVolatilityCalculator(window=10)
        res = calc.calculate(data)
        assert res == [None, None, None]

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            RollingVolatilityCalculator(window=1)
