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

    def test_regression_missingness_exact_fixtures(self) -> None:
        """
        Regression tests covering specific missingness fixtures:
        - [1, 2, None, 4]
        - [5, None, None]
        - [None, None]
        - [1, NaN, 2]
        - [1, inf, 2]
        - [1, -inf, 2]
        """
        # 1. [1, 2, None, 4] -> valid: 1, 2, 4
        s1 = self.calc.compute("f1", [1.0, 2.0, None, 4.0])
        assert s1.observation_count == 3
        assert s1.mean is not None and math.isclose(s1.mean, 7.0 / 3.0, abs_tol=1e-9)
        assert s1.median == 2.0
        assert s1.min == 1.0
        assert s1.max == 4.0

        # 2. [5, None, None] -> valid: 5 (N=1, std=None)
        s2 = self.calc.compute("f2", [5.0, None, None])
        assert s2.observation_count == 1
        assert s2.mean == 5.0
        assert s2.median == 5.0
        assert s2.std is None
        assert s2.min == 5.0
        assert s2.max == 5.0

        # 3. [None, None] -> count=0, all None
        s3 = self.calc.compute("f3", [None, None])
        assert s3.observation_count == 0
        assert s3.mean is None
        assert s3.median is None
        assert s3.std is None
        assert s3.min is None
        assert s3.max is None

        # 4. [1, NaN, 2] -> valid: 1, 2
        s4 = self.calc.compute("f4", [1.0, float("nan"), 2.0])
        assert s4.observation_count == 2
        assert s4.mean == 1.5
        assert s4.median == 1.5
        assert s4.min == 1.0
        assert s4.max == 2.0

        # 5. [1, inf, 2] -> valid: 1, 2
        s5 = self.calc.compute("f5", [1.0, float("inf"), 2.0])
        assert s5.observation_count == 2
        assert s5.mean == 1.5
        assert s5.median == 1.5
        assert s5.min == 1.0
        assert s5.max == 2.0

        # 6. [1, -inf, 2] -> valid: 1, 2
        s6 = self.calc.compute("f6", [1.0, float("-inf"), 2.0])
        assert s6.observation_count == 2
        assert s6.mean == 1.5
        assert s6.median == 1.5
        assert s6.min == 1.0
        assert s6.max == 2.0

    def test_single_observation_standard_deviation_protection(self) -> None:
        """
        N_valid = 1 must strictly yield std = None.
        Standard deviation is undefined for N < 2 and must never be fabricated as 0.0.
        """
        cases: list[list[float | None]] = [
            [5.0],
            [5.0, None],
            [5.0, float("nan")],
            [5.0, float("inf"), float("-inf")],
        ]
        for c in cases:
            stat = self.calc.compute("single_obs", c)
            assert stat.observation_count == 1
            assert stat.mean == 5.0
            assert stat.median == 5.0
            assert stat.std is None, f"Expected std=None for {c}, got {stat.std}"
            assert stat.min == 5.0
            assert stat.max == 5.0

    def test_all_missing_none_list_produces_clean_none(self) -> None:
        """[None, None, None] produces clean None metrics without any NaN, inf, or 0.0 fallback."""
        stat = self.calc.compute("none_list", [None, None, None])
        assert stat.observation_count == 0
        assert stat.mean is None
        assert stat.median is None
        assert stat.std is None
        assert stat.min is None
        assert stat.max is None

    def test_mixed_non_finite_sample_filtration(self) -> None:
        """
        Input: [10, NaN, 20, inf, 30, -inf]
        Expected valid sample: 10, 20, 30
        Mean=20.0, Median=20.0, Min=10.0, Max=30.0, Sample Std=10.0
        """
        vals = [10.0, float("nan"), 20.0, float("inf"), 30.0, float("-inf")]
        stat = self.calc.compute("mixed_non_finite", vals)

        assert stat.observation_count == 3
        assert stat.mean == 20.0
        assert stat.median == 20.0
        assert stat.min == 10.0
        assert stat.max == 30.0
        assert stat.std is not None and math.isclose(stat.std, 10.0, abs_tol=1e-9)
