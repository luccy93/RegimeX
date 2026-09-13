"""
RegimeX Feature Engineering — Trend Calculator Unit Tests
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.trend import (
    EMARatioCalculator,
    SMARatioCalculator,
)


class TestSMARatioCalculator:
    def test_sma_ratio_hand_calculated(self, base_timestamp: datetime):
        prices = (10.0, 20.0, 30.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = SMARatioCalculator(window=3)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        # At index 2: SMA = (10 + 20 + 30) / 3 = 20.0; ratio = 30 / 20 = 1.5
        assert res[2] == pytest.approx(1.5)

    def test_constant_prices_yields_one(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)
        calc = SMARatioCalculator(window=10)
        res = calc.calculate(data)

        for i in range(9):
            assert res[i] is None
        for val in res[9:]:
            assert val == pytest.approx(1.0)


class TestEMARatioCalculator:
    def test_ema_ratio_hand_calculated(self, base_timestamp: datetime):
        # span=3 => alpha = 2 / 4 = 0.5
        # prices: 10.0, 20.0, 30.0
        # EMA_0 = 10.0
        # EMA_1 = 0.5 * 20 + 0.5 * 10 = 15.0
        # EMA_2 = 0.5 * 30 + 0.5 * 15 = 22.5
        # EMA_ratio_2 = 30 / 22.5 = 1.3333333333333333
        prices = (10.0, 20.0, 30.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(prices)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=prices,
            highs=prices,
            lows=prices,
            closes=prices,
        )

        calc = EMARatioCalculator(span=3)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        assert res[2] == pytest.approx(30.0 / 22.5)

    def test_constant_prices_yields_one(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)
        calc = EMARatioCalculator(span=10)
        res = calc.calculate(data)

        for i in range(9):
            assert res[i] is None
        for val in res[9:]:
            assert val == pytest.approx(1.0)
