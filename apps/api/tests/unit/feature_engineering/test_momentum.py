"""
RegimeX Feature Engineering — Momentum Calculator Unit Tests
============================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.momentum import (
    MomentumCalculator,
)


class TestMomentumCalculator:
    def test_rising_prices(self, base_timestamp: datetime):
        # 10 bars increasing by 10% each
        prices = tuple(100.0 * (1.1**i) for i in range(10))
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = MomentumCalculator(window=5)
        res = calc.calculate(data)

        assert len(res) == 10
        for i in range(5):
            assert res[i] is None

        # At index 5: (prices[5] - prices[0]) / prices[0] = 1.1^5 - 1
        expected = (1.1**5) - 1.0
        assert res[5] is not None
        assert res[5] == pytest.approx(expected)
        assert res[5] > 0.0

    def test_falling_prices(self, base_timestamp: datetime):
        prices = tuple(200.0 - i * 10.0 for i in range(10))
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = MomentumCalculator(window=3)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        assert res[2] is None
        # At index 3: prices[3] = 170, prices[0] = 200 -> (170 - 200) / 200 = -0.15
        assert res[3] is not None
        assert res[3] == pytest.approx(-0.15)
        assert res[3] < 0.0

    def test_flat_prices(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)
        calc = MomentumCalculator(window=10)
        res = calc.calculate(data)

        for i in range(10):
            assert res[i] is None
        for val in res[10:]:
            assert val == pytest.approx(0.0)

    def test_insufficient_history(self, base_timestamp: datetime):
        prices = (100.0, 105.0)
        timestamps = (base_timestamp, base_timestamp + timedelta(days=1))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )
        calc = MomentumCalculator(window=5)
        assert calc.calculate(data) == [None, None]

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            MomentumCalculator(window=0)
