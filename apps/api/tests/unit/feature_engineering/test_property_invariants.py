"""
RegimeX Feature Engineering — Mathematical Property Invariant Tests
===================================================================
Validates fundamental mathematical invariants:
- Price scale invariance for ratios and percentage returns
- Non-negativity of volatility and range metrics
- Identity and zero properties on constant time series
"""

from __future__ import annotations

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


def _generate_synthetic_series(n: int = 30) -> tuple[FeatureInputData, FeatureInputData]:
    """Return base FeatureInputData and scaled FeatureInputData (multiplied by 3.75)."""
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(base_ts + timedelta(days=i) for i in range(n))

    # Fluctuating prices
    closes = tuple(100.0 + 5.0 * (i % 4) + 2.0 * i for i in range(n))
    highs = tuple(c + 3.0 for c in closes)
    lows = tuple(c - 2.0 for c in closes)
    opens = tuple(c - 0.5 for c in closes)

    data_base = FeatureInputData(
        timestamps=timestamps,
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    scale = 3.75
    data_scaled = FeatureInputData(
        timestamps=timestamps,
        opens=tuple(o * scale for o in opens),
        highs=tuple(h * scale for h in highs),
        lows=tuple(lw * scale for lw in lows),
        closes=tuple(c * scale for c in closes),
    )

    return data_base, data_scaled


class TestPriceScaleInvariance:
    def test_return_scale_invariance(self):
        data_base, data_scaled = _generate_synthetic_series()
        for k in (1, 5, 10):
            calc = SimpleReturnCalculator(k)
            res_base = calc.calculate(data_base)
            res_scaled = calc.calculate(data_scaled)

            for b, s in zip(res_base, res_scaled, strict=True):
                if b is None:
                    assert s is None
                else:
                    assert s is not None
                    assert b == pytest.approx(s, rel=1e-7)

    def test_momentum_scale_invariance(self):
        data_base, data_scaled = _generate_synthetic_series()
        for k in (10, 20):
            calc = MomentumCalculator(k)
            res_base = calc.calculate(data_base)
            res_scaled = calc.calculate(data_scaled)

            for b, s in zip(res_base, res_scaled, strict=True):
                if b is None:
                    assert s is None
                else:
                    assert s is not None
                    assert b == pytest.approx(s, rel=1e-7)

    def test_sma_ratio_scale_invariance(self):
        data_base, data_scaled = _generate_synthetic_series()
        for k in (10, 20):
            calc = SMARatioCalculator(k)
            res_base = calc.calculate(data_base)
            res_scaled = calc.calculate(data_scaled)

            for b, s in zip(res_base, res_scaled, strict=True):
                if b is None:
                    assert s is None
                else:
                    assert s is not None
                    assert b == pytest.approx(s, rel=1e-7)

    def test_ema_ratio_scale_invariance(self):
        data_base, data_scaled = _generate_synthetic_series()
        calc = EMARatioCalculator(span=20)
        res_base = calc.calculate(data_base)
        res_scaled = calc.calculate(data_scaled)

        for b, s in zip(res_base, res_scaled, strict=True):
            if b is None:
                assert s is None
            else:
                assert s is not None
                assert b == pytest.approx(s, rel=1e-7)

    def test_normalized_range_scale_invariance(self):
        data_base, data_scaled = _generate_synthetic_series()
        calc_hl = HighLowRangeCalculator()
        calc_ntr = NormalizedTrueRangeCalculator()

        for calc in (calc_hl, calc_ntr):
            res_base = calc.calculate(data_base)
            res_scaled = calc.calculate(data_scaled)

            for b, s in zip(res_base, res_scaled, strict=True):
                if b is None:
                    assert s is None
                else:
                    assert s is not None
                    assert b == pytest.approx(s, rel=1e-7)


class TestNonNegativityInvariants:
    def test_volatility_is_always_non_negative(self):
        data_base, _ = _generate_synthetic_series()
        for window in (10, 20):
            calc = RollingVolatilityCalculator(window)
            res = calc.calculate(data_base)
            for val in res:
                if val is not None:
                    assert val >= 0.0, f"Negative volatility encountered: {val}"

    def test_ranges_are_always_non_negative(self):
        data_base, _ = _generate_synthetic_series()
        for calc in (
            HighLowRangeCalculator(),
            TrueRangeCalculator(),
            NormalizedTrueRangeCalculator(),
        ):
            res = calc.calculate(data_base)
            for val in res:
                if val is not None:
                    assert val >= 0.0, f"Negative range encountered: {val}"


class TestConstantSeriesInvariants:
    def test_constant_series_identities(self, constant_price_bars):
        data = FeatureInputData.from_ohlcv_records(constant_price_bars)

        # Returns == 0.0
        ret_calc = SimpleReturnCalculator(1)
        for r in ret_calc.calculate(data)[1:]:
            assert r == pytest.approx(0.0)

        # Volatility == 0.0
        vol_calc = RollingVolatilityCalculator(10)
        for v in vol_calc.calculate(data)[10:]:
            assert v == pytest.approx(0.0)

        # Momentum == 0.0
        mom_calc = MomentumCalculator(10)
        for m in mom_calc.calculate(data)[10:]:
            assert m == pytest.approx(0.0)

        # SMA Ratio == 1.0
        sma_calc = SMARatioCalculator(10)
        for s in sma_calc.calculate(data)[9:]:
            assert s == pytest.approx(1.0)

        # EMA Ratio == 1.0
        ema_calc = EMARatioCalculator(10)
        for e in ema_calc.calculate(data)[9:]:
            assert e == pytest.approx(1.0)

        # High-Low Range == 0.0
        hl_calc = HighLowRangeCalculator()
        for hl in hl_calc.calculate(data):
            assert hl == pytest.approx(0.0)

        # True Range == 0.0
        tr_calc = TrueRangeCalculator()
        for tr in tr_calc.calculate(data):
            assert tr == pytest.approx(0.0)
