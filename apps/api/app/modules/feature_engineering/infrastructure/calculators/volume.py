"""
RegimeX Feature Engineering — Volume Calculators
================================================
Implements point-in-time volume change and volume ratio calculations.

Architectural position: ``infrastructure/calculators/volume.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
Safely handles unavailable or zero-volume series without fabricating artificial zeros.
"""

from __future__ import annotations

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class VolumeChangeCalculator(FeatureCalculator):
    """
    Computes percentage change in traded volume over a 1-period lag.

    Formula:
        V_change_{t, 1} = (V_t - V_{t-1}) / V_{t-1}

    Properties:
        - Returns all None if volume is not available for the instrument (e.g. FX).
        - First observation returns None (warm-up).
        - Safe against zero volume denominators (returns None).
    """

    def __init__(self) -> None:
        self._definition = FeatureDefinition(
            name="volume_change_1",
            category=FeatureCategory.VOLUME,
            description="Percentage change in volume over a 1-period lag",
            formula="(V_t - V_{t-1}) / V_{t-1}",
            required_fields=("volume",),
            lookback=1,
            min_observations=2,
            version="1.0.0",
            params={"period": 1},
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        if data.volumes is None or n < 2:
            return out

        volumes = np.asarray(data.volumes, dtype=np.float64)
        prev = volumes[:-1]
        curr = volumes[1:]

        with np.errstate(divide="ignore", invalid="ignore"):
            valid = prev > 1e-12
            changes = np.where(valid, (curr - prev) / prev, np.nan)

        for idx, c in enumerate(changes, start=1):
            if not np.isnan(c) and not np.isinf(c):
                out[idx] = float(c)

        return out


class VolumeRatioCalculator(FeatureCalculator):
    """
    Computes ratio of current bar volume to its historical Simple Moving Average.

    Formula:
        V_ratio_{t, W} = V_t / ( (1/W) * sum_{i=0}^{W-1} V_{t-i} )

    Properties:
        - Returns all None if volume is not available.
        - First W - 1 observations return None (warm-up).
        - Safe against zero or non-positive volume moving averages (returns None).
    """

    def __init__(self, window: int = 20) -> None:
        if window < 1:
            raise ValueError("Volume ratio window must be >= 1.")

        self._window = window
        self._definition = FeatureDefinition(
            name=f"volume_ratio_{window}",
            category=FeatureCategory.VOLUME,
            description=f"Ratio of volume to its {window}-period Simple Moving Average",
            formula=f"V_t / SMA(V, {window})_t",
            required_fields=("volume",),
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

        if data.volumes is None or n < self._window:
            return out

        volumes = np.asarray(data.volumes, dtype=np.float64)
        cumsum = np.cumsum(np.insert(volumes, 0, 0.0))
        win_sums = cumsum[self._window :] - cumsum[: -self._window]
        smas = win_sums / self._window

        for idx, (v, sma) in enumerate(
            zip(volumes[self._window - 1 :], smas, strict=True), start=self._window - 1
        ):
            if sma > 1e-12:
                ratio = v / sma
                if not np.isnan(ratio) and not np.isinf(ratio):
                    out[idx] = float(ratio)

        return out
