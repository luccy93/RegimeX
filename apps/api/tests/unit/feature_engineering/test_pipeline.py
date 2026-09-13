"""
RegimeX Feature Engineering — Pipeline Unit Tests
=================================================
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
from tests.unit.feature_engineering.conftest import make_bar


class TestFeaturePipeline:
    def test_pipeline_all_baseline_features(self, linear_trending_bars):
        pipeline = FeaturePipeline()
        fset = pipeline.compute(linear_trending_bars)

        assert fset.symbol == "REGX"
        assert fset.record_count == len(linear_trending_bars)
        assert len(fset.feature_names) >= 15
        assert "return_1" in fset.feature_names
        assert "volatility_20" in fset.feature_names
        assert "true_range" in fset.feature_names

    def test_pipeline_selected_features(self, linear_trending_bars):
        config = FeaturePipelineConfig(enabled_features=("return_1", "volatility_10"))
        pipeline = FeaturePipeline(config=config)
        fset = pipeline.compute(linear_trending_bars)

        assert fset.feature_names == ("return_1", "volatility_10")
        assert len(fset.definitions) == 2

    def test_pipeline_with_market_data_result(self, sample_market_result):
        pipeline = FeaturePipeline()
        fset = pipeline.compute(sample_market_result)

        assert fset.symbol == sample_market_result.symbol
        assert fset.record_count == sample_market_result.record_count

    def test_pipeline_empty_input_rejected(self):
        pipeline = FeaturePipeline()
        with pytest.raises(InvalidFeatureInputError):
            pipeline.compute([])

    def test_pipeline_unsorted_timestamps_rejected(self, base_timestamp: datetime):
        b1 = make_bar("REGX", base_timestamp + timedelta(days=1), 100, 101, 99, 100)
        b2 = make_bar("REGX", base_timestamp, 101, 102, 100, 101)  # Earlier!
        pipeline = FeaturePipeline()
        with pytest.raises(InvalidFeatureInputError, match="strictly ascending"):
            pipeline.compute([b1, b2])

    def test_pipeline_insufficient_data_raises(self, base_timestamp: datetime):
        # Only 3 bars provided, but volatility_20 requires at least 21 bars
        bars = [
            make_bar("REGX", base_timestamp + timedelta(days=i), 100 + i, 101 + i, 99 + i, 100 + i)
            for i in range(3)
        ]
        config = FeaturePipelineConfig(enabled_features=("volatility_20",))
        pipeline = FeaturePipeline(config=config)

        with pytest.raises(InsufficientDataError) as exc_info:
            pipeline.compute(bars)
        assert exc_info.value.required == 21
        assert exc_info.value.provided == 3

    def test_pipeline_deterministic_reproducibility(self, linear_trending_bars):
        pipeline = FeaturePipeline()
        fset1 = pipeline.compute(linear_trending_bars)
        fset2 = pipeline.compute(linear_trending_bars)

        assert fset1.to_matrix() == fset2.to_matrix()
        assert fset1.feature_names == fset2.feature_names
