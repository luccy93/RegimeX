"""
RegimeX Feature Engineering — Volume Calculator Unit Tests
==========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.volume import (
    VolumeChangeCalculator,
    VolumeRatioCalculator,
)


class TestVolumeCalculators:
    def test_volume_change_hand_calculated(self, base_timestamp: datetime):
        volumes = (1000.0, 1500.0, 1200.0)
        closes = (100.0, 101.0, 102.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(volumes)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=volumes,
        )

        calc = VolumeChangeCalculator()
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] == pytest.approx(0.5)
        assert res[2] == pytest.approx(-0.2)

    def test_volume_change_missing_volume_returns_none(self, base_timestamp: datetime):
        closes = (100.0, 101.0, 102.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(closes)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=None,  # No volume available (e.g. FX)
        )

        calc = VolumeChangeCalculator()
        res = calc.calculate(data)
        assert res == [None, None, None]

    def test_volume_ratio_hand_calculated(self, base_timestamp: datetime):
        volumes = (100.0, 200.0, 300.0)
        closes = (10.0, 10.0, 10.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(volumes)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=volumes,
        )

        calc = VolumeRatioCalculator(window=3)
        res = calc.calculate(data)

        assert res[0] is None
        assert res[1] is None
        assert res[2] == pytest.approx(300.0 / 200.0)

    def test_volume_ratio_missing_volume_returns_none(self, base_timestamp: datetime):
        closes = (10.0, 10.0, 10.0)
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(len(closes)))
        data = FeatureInputData(
            timestamps=timestamps,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=None,
        )

        calc = VolumeRatioCalculator(window=2)
        res = calc.calculate(data)
        assert res == [None, None, None]

    def test_zero_volume_safe(self, zero_volume_bars):
        data = FeatureInputData.from_ohlcv_records(zero_volume_bars)
        calc_chg = VolumeChangeCalculator()
        calc_rat = VolumeRatioCalculator(window=5)

        res_chg = calc_chg.calculate(data)
        res_rat = calc_rat.calculate(data)

        # Zero volume must not cause ZeroDivisionError and must not fabricate artificial zeros
        for val in res_chg:
            assert val is None
        for val in res_rat:
            assert val is None
