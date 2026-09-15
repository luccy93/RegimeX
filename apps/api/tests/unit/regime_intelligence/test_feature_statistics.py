"""
Unit Tests — Descriptive Feature Statistics
============================================
Validates hand-calculable statistics, sample vs population standard deviation convention,
missing value handling (Dataset F), zero data fabrication, and numerical safety.
"""

from __future__ import annotations

import math

from app.modules.regime_intelligence.infrastructure.analytics.statistics import (
    FeatureStatisticsCalculatorImpl,
)


class TestFeatureStatistics:
    """Tests for FeatureStatisticsCalculatorImpl."""

    def setup_method(self) -> None:
        self.calc = FeatureStatisticsCalculatorImpl()

    def test_hand_calculable_values(self) -> None:
        """
        Verify hand-calculable values: [1.0, 2.0, 3.0, 4.0].

        Expected:
        - count = 4
        - mean = 2.5
        - median = 2.5
        - min = 1.0
        - max = 4.0
        - sample std (ddof=1) = sqrt(5.0 / 3.0) ≈ 1.2909944487
        """
        vals = [1.0, 2.0, 3.0, 4.0]
        stat = self.calc.compute("test_feature", vals)

        assert stat.observation_count == 4
        assert stat.mean is not None and math.isclose(stat.mean, 2.5, abs_tol=1e-9)
        assert stat.median is not None and math.isclose(stat.median, 2.5, abs_tol=1e-9)
        assert stat.min is not None and math.isclose(stat.min, 1.0, abs_tol=1e-9)
        assert stat.max is not None and math.isclose(stat.max, 4.0, abs_tol=1e-9)

        expected_sample_std = math.sqrt(5.0 / 3.0)
        assert stat.std is not None and math.isclose(stat.std, expected_sample_std, abs_tol=1e-9)

    def test_dataset_f_missing_feature_values(self) -> None:
        """
        Dataset F: Missing values (None) must be excluded without zero-filling.

        Input: [1.0, None, 3.0].
        If zero-filled: [1.0, 0.0, 3.0] -> mean would erroneously be 1.333.
        Correct behavior: [1.0, 3.0] -> count = 2, mean = 2.0, min = 1.0, max = 3.0.
        """
        vals = [1.0, None, 3.0]
        stat = self.calc.compute("return_1", vals)

        assert stat.observation_count == 2
        assert stat.mean is not None and math.isclose(stat.mean, 2.0, abs_tol=1e-9)
        assert stat.median is not None and math.isclose(stat.median, 2.0, abs_tol=1e-9)
        assert stat.min is not None and math.isclose(stat.min, 1.0, abs_tol=1e-9)
        assert stat.max is not None and math.isclose(stat.max, 3.0, abs_tol=1e-9)

    def test_single_observation_safety(self) -> None:
        """Single observation produces count=1, std=0.0."""
        stat = self.calc.compute("volatility_20", [0.18])

        assert stat.observation_count == 1
        assert stat.mean == 0.18
        assert stat.median == 0.18
        assert stat.std == 0.0
        assert stat.min == 0.18
        assert stat.max == 0.18

    def test_constant_feature_zero_variance(self) -> None:
        """Constant values produce zero variance and std == 0.0."""
        stat = self.calc.compute("constant_feat", [5.0, 5.0, 5.0, 5.0])

        assert stat.observation_count == 4
        assert stat.mean == 5.0
        assert stat.median == 5.0
        assert stat.std == 0.0
        assert stat.min == 5.0
        assert stat.max == 5.0

    def test_empty_and_all_none_series(self) -> None:
        """Empty series or all-None series return observation_count == 0 and None metrics."""
        stat_empty = self.calc.compute("empty_feat", [])
        assert stat_empty.observation_count == 0
        assert stat_empty.mean is None
        assert stat_empty.std is None

        stat_none = self.calc.compute("none_feat", [None, None, None])
        assert stat_none.observation_count == 0
        assert stat_none.mean is None
        assert stat_none.std is None

    def test_nan_and_inf_filtering(self) -> None:
        """NaN and infinite values are filtered out rather than corrupting statistics."""
        vals = [2.0, float("nan"), float("inf"), float("-inf"), 4.0]
        stat = self.calc.compute("robust_feat", vals)

        assert stat.observation_count == 2
        assert stat.mean == 3.0
        assert stat.min == 2.0
        assert stat.max == 4.0
        assert stat.std is not None and not math.isnan(stat.std)
