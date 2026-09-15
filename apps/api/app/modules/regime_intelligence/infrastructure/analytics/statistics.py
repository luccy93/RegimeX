"""
RegimeX Regime Intelligence — Statistics Engine
===============================================
Numerically safe computation of descriptive feature statistics for market regimes.

Guarantees:
- Safe handling of empty datasets, single observations, constant features, and missing values.
- Zero NaN, +inf, or -inf propagation (returns None or 0.0 where mathematically appropriate).
- Uses sample standard deviation (Bessel's correction, ddof=1) when sample size >= 2.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from app.modules.regime_intelligence.domain.models import FeatureStatistic


class FeatureStatisticsCalculatorImpl:
    """Production implementation of FeatureStatisticsCalculator."""

    def compute(
        self,
        feature_name: str,
        values: Sequence[float | None],
    ) -> FeatureStatistic:
        """
        Compute descriptive summary statistics for a feature series.

        None, NaN, and infinite values are excluded from statistical aggregation.
        Missing values are never zero-filled.

        Args:
            feature_name: Name of the feature variable.
            values: Sequence of observed numerical values or None.

        Returns:
            FeatureStatistic containing observation_count, mean, median, std, min, max.
        """
        valid_values: list[float] = [
            float(v) for v in values if v is not None and not math.isnan(v) and not math.isinf(v)
        ]

        count = len(valid_values)
        if count == 0:
            return FeatureStatistic(
                feature_name=feature_name,
                observation_count=0,
                mean=None,
                median=None,
                std=None,
                min=None,
                max=None,
            )

        if count == 1:
            val = valid_values[0]
            return FeatureStatistic(
                feature_name=feature_name,
                observation_count=1,
                mean=val,
                median=val,
                std=0.0,
                min=val,
                max=val,
            )

        # count >= 2
        f_mean = float(statistics.mean(valid_values))
        f_median = float(statistics.median(valid_values))
        f_min = float(min(valid_values))
        f_max = float(max(valid_values))

        # Sample standard deviation (ddof=1)
        # If all values are identical, variance is 0.0
        if math.isclose(f_min, f_max, rel_tol=1e-12, abs_tol=1e-12):
            f_std = 0.0
        else:
            try:
                f_std = float(statistics.stdev(valid_values))
            except statistics.StatisticsError:
                f_std = 0.0

        return FeatureStatistic(
            feature_name=feature_name,
            observation_count=count,
            mean=f_mean,
            median=f_median,
            std=f_std,
            min=f_min,
            max=f_max,
        )
