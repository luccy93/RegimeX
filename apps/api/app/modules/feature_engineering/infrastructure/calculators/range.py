"""
RegimeX Feature Engineering — Price Range Calculators
====================================================
Implements point-in-time price range features: High-Low range, True Range,
and Normalized True Range.

Architectural position: ``infrastructure/calculators/range.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
"""

from __future__ import annotations

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class HighLowRangeCalculator(FeatureCalculator):
    """
    Computes normalized High-Low price range for each bar.

    Formula:
        HL_range_t = (H_t - L_t) / C_t

    Properties:
        - Scale-invariant percentage of closing price.
        - Valid from the first observation (lookback = 1).
        - Safe against zero or negative closing prices.
    """

    def __init__(self) -> None:
        self._definition = FeatureDefinition(
            name="high_low_range",
            category=FeatureCategory.RANGE,
            description="Normalized bar range: (High - Low) / Close",
            formula="(H_t - L_t) / C_t",
            required_fields=("high", "low", "close"),
            lookback=1,
            min_observations=1,
            version="1.0.0",
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        highs = np.asarray(data.highs, dtype=np.float64)
        lows = np.asarray(data.lows, dtype=np.float64)
        closes = np.asarray(data.closes, dtype=np.float64)

        with np.errstate(divide="ignore", invalid="ignore"):
            valid = closes > 1e-12
            ranges = np.where(valid, (highs - lows) / closes, np.nan)

        for idx, r in enumerate(ranges):
            if not np.isnan(r) and not np.isinf(r):
                out[idx] = float(r)

        return out


class TrueRangeCalculator(FeatureCalculator):
    """
    Computes Welles Wilder's True Range (TR).

    Formula:
        TR_0 = H_0 - L_0
        TR_t = max( H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}| ) for t >= 1

    Properties:
        - Captures overnight gaps and intraday expansion.
        - First observation correctly falls back to H_0 - L_0.
        - Pure point-in-time calculation.
    """

    def __init__(self) -> None:
        self._definition = FeatureDefinition(
            name="true_range",
            category=FeatureCategory.RANGE,
            description="Welles Wilder True Range: max(H-L, |H-C_{t-1}|, |L-C_{t-1}|)",
            formula="max(H_t - L_t, abs(H_t - C_{t-1}), abs(L_t - C_{t-1}))",
            required_fields=("high", "low", "close"),
            lookback=1,
            min_observations=1,
            version="1.0.0",
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        highs = np.asarray(data.highs, dtype=np.float64)
        lows = np.asarray(data.lows, dtype=np.float64)
        closes = np.asarray(data.closes, dtype=np.float64)

        # First observation: H_0 - L_0
        out[0] = float(highs[0] - lows[0])

        if n > 1:
            hl = highs[1:] - lows[1:]
            hc = np.abs(highs[1:] - closes[:-1])
            lc = np.abs(lows[1:] - closes[:-1])
            trs = np.maximum(hl, np.maximum(hc, lc))

            for idx, tr in enumerate(trs, start=1):
                if not np.isnan(tr) and not np.isinf(tr):
                    out[idx] = float(tr)

        return out


class NormalizedTrueRangeCalculator(FeatureCalculator):
    """
    Computes Normalized True Range (NTR) scaled by the closing price.

    Formula:
        NTR_t = TR_t / C_t

    Properties:
        - Scale-invariant across asset price regimes.
        - First observation is (H_0 - L_0) / C_0.
        - Safe against zero or negative closing prices.
    """

    def __init__(self) -> None:
        self._definition = FeatureDefinition(
            name="normalized_true_range",
            category=FeatureCategory.RANGE,
            description="Normalized True Range: True Range / Close",
            formula="TR_t / C_t",
            required_fields=("high", "low", "close"),
            lookback=1,
            min_observations=1,
            version="1.0.0",
        )
        self._tr_calc = TrueRangeCalculator()

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        trs = self._tr_calc.calculate(data)
        closes = np.asarray(data.closes, dtype=np.float64)

        for idx, (tr, c) in enumerate(zip(trs, closes, strict=True)):
            if tr is not None and c > 1e-12:
                ntr = tr / c
                if not np.isnan(ntr) and not np.isinf(ntr):
                    out[idx] = float(ntr)

        return out
