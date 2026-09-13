"""
RegimeX Feature Engineering — Missing Value Policy Unit Tests
=============================================================
"""

from __future__ import annotations

from app.modules.feature_engineering.application.config import FeaturePipelineConfig
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.feature_engineering.domain.models import MissingValuePolicy


class TestMissingValuePolicy:
    def test_preserve_policy_keeps_all_records(self, linear_trending_bars):
        config = FeaturePipelineConfig(
            enabled_features=("return_1", "volatility_10"),
            missing_value_policy=MissingValuePolicy.PRESERVE,
        )
        pipeline = FeaturePipeline(config=config)
        fset = pipeline.compute(linear_trending_bars)

        assert fset.record_count == len(linear_trending_bars)
        # Bar 0 should have None for both
        assert fset.records[0].values["return_1"] is None
        assert fset.records[0].values["volatility_10"] is None

    def test_drop_warmup_policy_trims_incomplete_rows(self, linear_trending_bars):
        # volatility_10 requires 10 returns, which means first 10 bars (indices 0..9) have None
        config = FeaturePipelineConfig(
            enabled_features=("return_1", "volatility_10"),
            missing_value_policy=MissingValuePolicy.DROP_WARMUP,
        )
        pipeline = FeaturePipeline(config=config)
        fset = pipeline.compute(linear_trending_bars)

        # Total 30 bars, 10 warm-up bars dropped -> 20 remaining
        assert fset.record_count == 20

        # All records in fset must have non-None values
        for record in fset.records:
            assert record.values["return_1"] is not None
            assert record.values["volatility_10"] is not None

    def test_no_artificial_zero_fill(self, linear_trending_bars):
        config = FeaturePipelineConfig(
            enabled_features=("return_10",),
            missing_value_policy=MissingValuePolicy.PRESERVE,
        )
        pipeline = FeaturePipeline(config=config)
        fset = pipeline.compute(linear_trending_bars)

        # The first 10 values must be explicitly None, NOT 0.0
        for i in range(10):
            assert fset.records[i].values["return_10"] is None
