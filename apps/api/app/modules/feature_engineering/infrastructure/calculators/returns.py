"""
RegimeX Feature Engineering — Return Calculators
================================================
Implements point-in-time simple and multi-period return calculations.

Architectural position: ``infrastructure/calculators/returns.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
"""

from __future__ import annotations

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class SimpleReturnCalculator(FeatureCalculator):
    """
    Computes simple discrete return over a specified period lag.

    Formula:
        R_{t, k} = (P_t - P_{t-k}) / P_{t-k} = P_t / P_{t-k} - 1

    Properties:
        - Strict point-in-time: uses only observations at t and t-k.
        - First k observations return None (warm-up).
        - Safe against zero or negative denominators (returns None).
    """

    def __init__(self, period: int = 1) -> None:
        if period < 1:
            raise ValueError("Return period lag must be >= 1.")
        self._period = period
        self._definition = FeatureDefinition(
            name=f"return_{period}",
            category=FeatureCategory.RETURN,
            description=f"Simple discrete price return over a {period}-period lag",
            formula=f"(P_t - P_{{t-{period}}}) / P_{{t-{period}}}",
            required_fields=("close",),
            lookback=period,
            min_observations=period + 1,
            version="1.0.0",
            params={"period": period},
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        if n <= self._period:
            return out

        closes = np.asarray(data.closes, dtype=np.float64)
        prev = closes[: -self._period]
        curr = closes[self._period :]

        with np.errstate(divide="ignore", invalid="ignore"):
            valid = prev > 1e-12
            rets = np.where(valid, (curr - prev) / prev, np.nan)

        for idx, r in enumerate(rets, start=self._period):
            if not np.isnan(r) and not np.isinf(r):
                out[idx] = float(r)

        return out
