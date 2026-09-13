"""
RegimeX Feature Engineering — Momentum Calculators
==================================================
Implements point-in-time price momentum and rate of change calculations.

Architectural position: ``infrastructure/calculators/momentum.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
"""

from __future__ import annotations

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class MomentumCalculator(FeatureCalculator):
    """
    Computes price momentum as percentage rate of change over a historical window.

    Formula:
        M_{t, W} = (P_t - P_{t-W}) / P_{t-W}

    Properties:
        - Strict backward-looking: uses only observations at t and t-W.
        - First W observations return None (warm-up).
        - Safe against zero or non-positive denominators.
    """

    def __init__(self, window: int = 10) -> None:
        if window < 1:
            raise ValueError("Momentum window must be >= 1.")

        self._window = window
        self._definition = FeatureDefinition(
            name=f"momentum_{window}",
            category=FeatureCategory.MOMENTUM,
            description=f"Price rate-of-change momentum over a {window}-period lookback",
            formula=f"(P_t - P_{{t-{window}}}) / P_{{t-{window}}}",
            required_fields=("close",),
            lookback=window,
            min_observations=window + 1,
            version="1.0.0",
            params={"window": window},
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        if n <= self._window:
            return out

        closes = np.asarray(data.closes, dtype=np.float64)
        prev = closes[: -self._window]
        curr = closes[self._window :]

        with np.errstate(divide="ignore", invalid="ignore"):
            valid = prev > 1e-12
            mom = np.where(valid, (curr - prev) / prev, np.nan)

        for idx, m in enumerate(mom, start=self._window):
            if not np.isnan(m) and not np.isinf(m):
                out[idx] = float(m)

        return out
