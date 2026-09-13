"""
RegimeX Feature Engineering — Numerical Safety Unit Tests
=========================================================
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from tests.unit.feature_engineering.conftest import make_bar


class TestNumericalSafety:
    def test_constant_prices_all_features_finite(self, constant_price_bars):
        pipeline = FeaturePipeline()
        fset = pipeline.compute(constant_price_bars)

        for record in fset.records:
            for name, val in record.values.items():
                if val is not None:
                    assert not math.isnan(val), f"NaN encountered for feature {name}"
                    assert not math.isinf(val), f"Infinity encountered for feature {name}"

    def test_zero_volume_no_division_by_zero(self, zero_volume_bars):
        pipeline = FeaturePipeline()
        fset = pipeline.compute(zero_volume_bars)

        for record in fset.records:
            for name, val in record.values.items():
                if val is not None:
                    assert not math.isnan(val), f"NaN encountered for feature {name}"
                    assert not math.isinf(val), f"Infinity encountered for feature {name}"

    def test_very_small_prices_handled_safely(self, base_timestamp: datetime):
        # Extremely small prices (e.g. micro-penny crypto token)
        bars = []
        for i in range(25):
            c = 0.0001 + i * 0.000002
            bars.append(
                make_bar(
                    "TINY",
                    base_timestamp + timedelta(days=i),
                    open_=c - 0.000001,
                    high=c + 0.000005,
                    low=c - 0.000003,
                    close=c,
                )
            )
        pipeline = FeaturePipeline()
        fset = pipeline.compute(bars)
        assert fset.record_count == 25

        for record in fset.records:
            for _name, val in record.values.items():
                if val is not None:
                    assert not math.isnan(val)
                    assert not math.isinf(val)

    def test_large_prices_handled_safely(self, base_timestamp: datetime):
        # Very large prices (e.g. Berkshire Hathaway class A, BTC)
        bars = []
        for i in range(25):
            c = 600000.0 + i * 1000.0
            bars.append(
                make_bar(
                    "LARGE",
                    base_timestamp + timedelta(days=i),
                    open_=c - 500.0,
                    high=c + 1500.0,
                    low=c - 1000.0,
                    close=c,
                )
            )
        pipeline = FeaturePipeline()
        fset = pipeline.compute(bars)
        assert fset.record_count == 25

        for record in fset.records:
            for _name, val in record.values.items():
                if val is not None:
                    assert not math.isnan(val)
                    assert not math.isinf(val)
