"""
RegimeX Feature Engineering — Input Validation & Error Handling Hardening
========================================================================
Validates robustness against corrupted, malformed, edge-case, and boundary data.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.modules.feature_engineering.application.config import FeaturePipelineConfig
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.feature_engineering.domain.errors import (
    InsufficientDataError,
    InvalidFeatureInputError,
)
from app.modules.feature_engineering.domain.models import FeatureInputData, FeatureRecord
from pydantic import ValidationError
from tests.unit.feature_engineering.conftest import make_bar


class TestInputValidationHardening:
    def test_empty_dataset_rejection(self):
        pipeline = FeaturePipeline()
        with pytest.raises(InvalidFeatureInputError, match="empty records"):
            pipeline.compute([])

    def test_single_row_dataset_behavior(self, base_timestamp: datetime):
        single_bar = make_bar("REGX", base_timestamp, 100.0, 105.0, 95.0, 100.0, 1000.0)

        # 1. Pipeline with lookback > 1 must reject with InsufficientDataError
        config_lookback = FeaturePipelineConfig(enabled_features=("return_1",))
        pipeline_lookback = FeaturePipeline(config=config_lookback)
        with pytest.raises(InsufficientDataError) as exc_info:
            pipeline_lookback.compute([single_bar])
        assert exc_info.value.required == 2
        assert exc_info.value.provided == 1

        # 2. Pipeline with min_observations=1 features (range) must succeed
        config_single = FeaturePipelineConfig(enabled_features=("high_low_range", "true_range"))
        pipeline_single = FeaturePipeline(config=config_single)
        fset = pipeline_single.compute([single_bar])
        assert fset.record_count == 1
        assert fset.records[0].values["high_low_range"] == pytest.approx(10.0 / 100.0)
        assert fset.records[0].values["true_range"] == pytest.approx(10.0)

    def test_duplicate_timestamps_rejected(self, base_timestamp: datetime):
        b1 = make_bar("REGX", base_timestamp, 100, 101, 99, 100)
        b2 = make_bar("REGX", base_timestamp, 101, 102, 100, 101)  # Exact duplicate timestamp!
        pipeline = FeaturePipeline()
        with pytest.raises(InvalidFeatureInputError, match="strictly ascending"):
            pipeline.compute([b1, b2])

    def test_descending_timestamps_rejected(self, base_timestamp: datetime):
        b1 = make_bar("REGX", base_timestamp + timedelta(hours=2), 100, 101, 99, 100)
        b2 = make_bar("REGX", base_timestamp, 101, 102, 100, 101)  # Inverted!
        pipeline = FeaturePipeline()
        with pytest.raises(InvalidFeatureInputError, match="strictly ascending"):
            pipeline.compute([b1, b2])

    def test_naive_timestamp_rejected_by_record(self):
        naive_dt = datetime(2024, 1, 1, 12, 0)
        with pytest.raises(ValidationError):
            FeatureRecord(timestamp=naive_dt, values={})

    def test_invalid_ohlc_relationships_rejected_by_bar(self, base_timestamp: datetime):
        # high < low
        with pytest.raises(ValidationError):
            make_bar("BAD", base_timestamp, open_=100, high=90, low=95, close=92)

        # low > open
        with pytest.raises(ValidationError):
            make_bar("BAD", base_timestamp, open_=90, high=105, low=95, close=100)

    def test_missing_volume_never_converted_to_zero(self, base_timestamp: datetime):
        """Missing volume series (e.g. FX) must preserve None and not fabricate 0.0."""
        closes = tuple(100.0 + i for i in range(25))
        timestamps = tuple(base_timestamp + timedelta(days=i) for i in range(25))

        data = FeatureInputData(
            timestamps=timestamps,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=None,  # No volume
        )

        from app.modules.feature_engineering.infrastructure.calculators.volume import (
            VolumeChangeCalculator,
            VolumeRatioCalculator,
        )

        calc_chg = VolumeChangeCalculator()
        calc_rat = VolumeRatioCalculator(20)

        res_chg = calc_chg.calculate(data)
        res_rat = calc_rat.calculate(data)

        assert all(v is None for v in res_chg)
        assert all(v is None for v in res_rat)

    def test_duplicate_features_in_config_handled_gracefully(self, linear_trending_bars):
        """Duplicate feature names in enabled_features should be deduplicated."""
        config = FeaturePipelineConfig(enabled_features=("return_1", "return_1", "volatility_10"))
        pipeline = FeaturePipeline(config=config)
        fset = pipeline.compute(linear_trending_bars)

        assert fset.feature_names == ("return_1", "volatility_10")
        assert len(fset.definitions) == 2
