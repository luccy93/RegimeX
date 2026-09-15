"""
Unit Tests — Descriptive Feature Statistics
============================================
Validates hand-calculable statistics, sample vs population standard deviation convention,
missing value handling (Datasets A–F), zero data fabrication, and numerical safety.
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

    def test_test_a_nan_exclusion(self) -> None:
        """
        Test A — NaN exclusion.
        Input: [1.0, 2.0, NaN, 4.0]
        Expected: count=3, mean=7/3, median=2.0, min=1.0, max=4.0
        """
        vals = [1.0, 2.0, float("nan"), 4.0]
        stat = self.calc.compute("feature_x", vals)

        assert stat.observation_count == 3
        assert stat.mean is not None and math.isclose(stat.mean, 7.0 / 3.0, abs_tol=1e-9)
        assert stat.median is not None and math.isclose(stat.median, 2.0, abs_tol=1e-9)
        assert stat.min is not None and math.isclose(stat.min, 1.0, abs_tol=1e-9)
        assert stat.max is not None and math.isclose(stat.max, 4.0, abs_tol=1e-9)
        assert stat.std is not None and not math.isnan(stat.std)

    def test_test_b_single_valid_observation(self) -> None:
        """
        Test B — Single valid observation.
        Input: [5.0, NaN, NaN]
        Expected: count=1, mean=5.0, median=5.0, std=None, min=5.0, max=5.0
        """
        vals = [5.0, float("nan"), float("nan")]
        stat = self.calc.compute("single_valid", vals)

        assert stat.observation_count == 1
        assert stat.mean == 5.0
        assert stat.median == 5.0
        assert stat.std is None  # Standard deviation is unavailable when sample size < 2
        assert stat.min == 5.0
        assert stat.max == 5.0

    def test_test_c_all_missing(self) -> None:
        """
        Test C — All missing values.
        Input: [NaN, NaN, NaN]
        Expected: count=0, mean=None, median=None, std=None, min=None, max=None
        """
        vals = [float("nan"), float("nan"), float("nan")]
        stat = self.calc.compute("all_nan", vals)

        assert stat.observation_count == 0
        assert stat.mean is None
        assert stat.median is None
        assert stat.std is None
        assert stat.min is None
        assert stat.max is None

    def test_test_d_non_finite_values(self) -> None:
        """
        Test D — Non-finite values.
        Input: [1.0, 2.0, inf, -inf, NaN]
        Expected: Invalid values excluded without being converted to zero.
        count=2, mean=1.5, median=1.5, min=1.0, max=2.0
        """
        vals = [1.0, 2.0, float("inf"), float("-inf"), float("nan")]
        stat = self.calc.compute("non_finite_feat", vals)

        assert stat.observation_count == 2
        assert stat.mean == 1.5
        assert stat.median == 1.5
        assert stat.min == 1.0
        assert stat.max == 2.0

    def test_test_e_no_artificial_observations(self) -> None:
        """
        Test E — No artificial observations.
        Input: [10.0, NaN, 20.0]
        Expected: count=2, not count=3.
        """
        vals = [10.0, float("nan"), 20.0]
        stat = self.calc.compute("two_valid", vals)

        assert stat.observation_count == 2
        assert stat.mean == 15.0
        assert stat.median == 15.0
        assert stat.min == 10.0
        assert stat.max == 20.0

    def test_dataset_f_missing_feature_values(self) -> None:
        """
        Dataset F: Missing values (None) must be excluded without zero-filling.
        Input: [1.0, None, 3.0].
        """
        vals = [1.0, None, 3.0]
        stat = self.calc.compute("return_1", vals)

        assert stat.observation_count == 2
        assert stat.mean is not None and math.isclose(stat.mean, 2.0, abs_tol=1e-9)
        assert stat.median is not None and math.isclose(stat.median, 2.0, abs_tol=1e-9)
        assert stat.min is not None and math.isclose(stat.min, 1.0, abs_tol=1e-9)
        assert stat.max is not None and math.isclose(stat.max, 3.0, abs_tol=1e-9)

    def test_constant_feature_zero_variance(self) -> None:
        """Constant values with count >= 2 produce zero variance and std == 0.0."""
        stat = self.calc.compute("constant_feat", [5.0, 5.0, 5.0, 5.0])

        assert stat.observation_count == 4
        assert stat.mean == 5.0
        assert stat.median == 5.0
        assert stat.std == 0.0
        assert stat.min == 5.0
        assert stat.max == 5.0
