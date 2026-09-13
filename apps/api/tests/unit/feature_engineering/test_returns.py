"""
RegimeX Feature Engineering — Return Calculator Unit Tests
==========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.returns import (
    SimpleReturnCalculator,
)


class TestSimpleReturnCalculator:
    def test_return_1_hand_calculated(self, base_timestamp: datetime):
        # Known sequence
        prices = (100.0, 105.0, 102.9, 102.9)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = SimpleReturnCalculator(1)
        res = calc.calculate(data)

        assert len(res) == 4
        assert res[0] is None
        assert res[1] == pytest.approx(0.05)
        assert res[2] == pytest.approx(-0.02)
        assert res[3] == pytest.approx(0.0)

    def test_multi_period_return_5(self, base_timestamp: datetime):
        # 10 bars: close = 100 + 10 * i
        # prices: 100, 110, 120, 130, 140, 150, 160, 170, 180, 190
        prices = tuple(100.0 + i * 10.0 for i in range(10))
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = SimpleReturnCalculator(5)
        res = calc.calculate(data)

        # First 5 must be None
        for i in range(5):
            assert res[i] is None

        # At index 5: (150 - 100) / 100 = 0.5
        assert res[5] == pytest.approx(0.5)
        # At index 6: (160 - 110) / 110 = 50 / 110
        assert res[6] == pytest.approx(50.0 / 110.0)

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
        calc = SimpleReturnCalculator(5)
        res = calc.calculate(data)
        assert res == [None, None]

    def test_constant_prices(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)
        calc = SimpleReturnCalculator(1)
        res = calc.calculate(data)
        assert res[0] is None
        for val in res[1:]:
            assert val == pytest.approx(0.0)

    def test_invalid_period_raises(self):
        with pytest.raises(ValueError):
            SimpleReturnCalculator(0)
