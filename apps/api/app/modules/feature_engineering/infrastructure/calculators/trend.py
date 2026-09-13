"""
RegimeX Feature Engineering — Trend Calculators
==============================================
Implements point-in-time trend indicators (SMA ratio, EMA ratio) with strict
backward-looking calculations.

Architectural position: ``infrastructure/calculators/trend.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
"""

from __future__ import annotations

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class SMARatioCalculator(FeatureCalculator):
    """
    Computes ratio of current closing price to its historical Simple Moving Average.

    Formula:
        SMA_ratio_{t, W} = P_t / ( (1/W) * sum_{i=0}^{W-1} P_{t-i} )

    Properties:
        - Strict point-in-time: uses only observations <= t.
        - First W - 1 observations return None (warm-up).
        - Safe against zero or non-positive SMA denominators.
    """

    def __init__(self, window: int = 10) -> None:
        if window < 1:
            raise ValueError("SMA window must be >= 1.")

        self._window = window
        self._definition = FeatureDefinition(
            name=f"sma_ratio_{window}",
            category=FeatureCategory.TREND,
            description=f"Ratio of close price to its {window}-period Simple Moving Average",
            formula=f"P_t / SMA(P, {window})_t",
            required_fields=("close",),
            lookback=window,
            min_observations=window,
            version="1.0.0",
            params={"window": window},
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        if n < self._window:
            return out

        closes = np.asarray(data.closes, dtype=np.float64)

        # Compute rolling sum using cumulative sum for O(N) efficiency
        cumsum = np.cumsum(np.insert(closes, 0, 0.0))
        # Window sum for slice closes[t - W + 1 : t + 1] is cumsum[t + 1] - cumsum[t + 1 - W]
        win_sums = cumsum[self._window :] - cumsum[: -self._window]
        smas = win_sums / self._window

        for idx, (p, sma) in enumerate(
            zip(closes[self._window - 1 :], smas, strict=True), start=self._window - 1
        ):
            if sma > 1e-12:
                ratio = p / sma
                if not np.isnan(ratio) and not np.isinf(ratio):
                    out[idx] = float(ratio)

        return out


class EMARatioCalculator(FeatureCalculator):
    """
    Computes ratio of current closing price to its historical Exponential Moving Average.

    Formula:
        EMA_0 = P_0
        EMA_t = alpha * P_t + (1 - alpha) * EMA_{t-1},  where alpha = 2 / (span + 1)
        EMA_ratio_t = P_t / EMA_t

    Properties:
        - Strict sequential recursion: zero future leakage.
        - First span - 1 observations return None for warmup convergence.
        - Safe against zero or non-positive EMA denominators.
    """

    def __init__(self, span: int = 20) -> None:
        if span < 1:
            raise ValueError("EMA span must be >= 1.")

        self._span = span
        self._alpha = 2.0 / (span + 1)
        self._definition = FeatureDefinition(
            name=f"ema_ratio_{span}",
            category=FeatureCategory.TREND,
            description=f"Ratio of close price to its {span}-period Exponential Moving Average",
            formula=f"P_t / EMA(P, span={span})_t",
            required_fields=("close",),
            lookback=span,
            min_observations=span,
            version="1.0.0",
            params={"span": span, "alpha": self._alpha},
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        if n < self._span:
            return out

        closes = np.asarray(data.closes, dtype=np.float64)
        emas = np.empty(n, dtype=np.float64)
        emas[0] = closes[0]

        alpha = self._alpha
        one_minus_alpha = 1.0 - alpha

        for t in range(1, n):
            emas[t] = alpha * closes[t] + one_minus_alpha * emas[t - 1]

        for t in range(self._span - 1, n):
            ema_val = emas[t]
            if ema_val > 1e-12:
                ratio = closes[t] / ema_val
                if not np.isnan(ratio) and not np.isinf(ratio):
                    out[t] = float(ratio)

        return out
