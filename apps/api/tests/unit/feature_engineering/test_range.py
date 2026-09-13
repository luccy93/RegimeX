"""
RegimeX Feature Engineering — Price Range Calculator Unit Tests
===============================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.models import FeatureInputData
from app.modules.feature_engineering.infrastructure.calculators.range import (
    HighLowRangeCalculator,
    NormalizedTrueRangeCalculator,
    TrueRangeCalculator,
)


class TestPriceRangeCalculators:
    def test_high_low_range(self, base_timestamp: datetime):
        data = FeatureInputData(
            timestamps=(base_timestamp,),
            opens=(100.0,),
            highs=(105.0,),
            lows=(95.0,),
            closes=(100.0,),
        )
        calc = HighLowRangeCalculator()
        res = calc.calculate(data)
        assert len(res) == 1
        assert res[0] == pytest.approx(10.0 / 100.0)

    def test_true_range_first_bar_and_gap_scenarios(self, base_timestamp: datetime):
        # Bar 0: H=105, L=95, C=100 -> TR = 105 - 95 = 10.0
        # Bar 1 (gap up): H=115, L=108, C=112 -> |H-C0|=15, |L-C0|=8, H-L=7 -> max=15.0
        # Bar 2 (gap down): H=92, L=85, C=88 -> |H-C1|=20, |L-C1|=27, H-L=7 -> max=27.0
        timestamps = (
            base_timestamp,
            base_timestamp + timedelta(days=1),
            base_timestamp + timedelta(days=2),
        )
        data = FeatureInputData(
            timestamps=timestamps,
            opens=(100.0, 110.0, 90.0),
            highs=(105.0, 115.0, 92.0),
            lows=(95.0, 108.0, 85.0),
            closes=(100.0, 112.0, 88.0),
        )

        calc = TrueRangeCalculator()
        res = calc.calculate(data)

        assert res[0] == pytest.approx(10.0)
        assert res[1] == pytest.approx(15.0)
        assert res[2] == pytest.approx(27.0)

    def test_normalized_true_range(self, base_timestamp: datetime):
        timestamps = (
            base_timestamp,
            base_timestamp + timedelta(days=1),
        )
        data = FeatureInputData(
            timestamps=timestamps,
            opens=(100.0, 110.0),
            highs=(105.0, 115.0),
            lows=(95.0, 108.0),
            closes=(100.0, 112.0),
        )

        calc = NormalizedTrueRangeCalculator()
        res = calc.calculate(data)

        assert res[0] == pytest.approx(10.0 / 100.0)
        assert res[1] == pytest.approx(15.0 / 112.0)
