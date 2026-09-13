"""
RegimeX Feature Engineering — Volatility Calculators
====================================================
Implements rolling sample standard deviation of discrete returns with strictly
backward-looking windows.

Architectural position: ``infrastructure/calculators/volatility.py``
Vectorized with NumPy. Strictly zero look-ahead bias.
"""

from __future__ import annotations

import math

import numpy as np

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import FeatureCategory, FeatureInputData


class RollingVolatilityCalculator(FeatureCalculator):
    """
    Computes rolling sample standard deviation (ddof=1) of 1-period discrete returns.

    Formula:
        sigma_t = sqrt( sum_{i=0}^{W-1} (r_{t-i} - bar{r}_t)^2 / (W - 1) )
        if annualized: sigma_t * sqrt(annualization_factor)

    Properties:
        - Strict backward-looking window: uses only returns at or before index t.
        - First W observations return None (warm-up).
        - For constant prices/returns, produces 0.0 (not NaN or error).
        - Configurable annualization factor (default: 252.0 for daily trading sessions).
    """

    def __init__(
        self,
        window: int = 20,
        annualized: bool = False,
        annualization_factor: float = 252.0,
    ) -> None:
        if window < 2:
            raise ValueError("Volatility window must be >= 2 for sample standard deviation.")
        if annualization_factor <= 0.0:
            raise ValueError("Annualization factor must be strictly positive.")

        self._window = window
        self._annualized = annualized
        self._annualization_factor = annualization_factor

        name = f"volatility_{window}" if not annualized else f"volatility_{window}_annualized"
        formula_str = (
            f"std_sample(return_1, window={window})"
            if not annualized
            else f"std_sample(return_1, window={window}) * sqrt({annualization_factor})"
        )

        self._definition = FeatureDefinition(
            name=name,
            category=FeatureCategory.VOLATILITY,
            description=(
                f"Rolling {window}-period sample standard deviation of 1-period returns"
                + (f" (annualized by {annualization_factor})" if annualized else "")
            ),
            formula=formula_str,
            required_fields=("close",),
            lookback=window,
            min_observations=window + 1,
            version="1.0.0",
            params={
                "window": window,
                "annualized": annualized,
                "annualization_factor": annualization_factor,
            },
        )

    @property
    def definition(self) -> FeatureDefinition:
        return self._definition

    def calculate(self, data: FeatureInputData) -> list[float | None]:
        n = data.length
        out: list[float | None] = [None] * n

        # We need at least window + 1 prices to compute window returns
        if n <= self._window:
            return out

        closes = np.asarray(data.closes, dtype=np.float64)

        # 1-period simple returns
        prev = closes[:-1]
        curr = closes[1:]

        with np.errstate(divide="ignore", invalid="ignore"):
            valid = prev > 1e-12
            rets = np.where(valid, (curr - prev) / prev, np.nan)

        scale = math.sqrt(self._annualization_factor) if self._annualized else 1.0

        # Rolling window over returns array of length n - 1
        # rets[k] corresponds to price bar index k + 1
        # For a window of W returns ending at rets[k] (which corresponds to bar k + 1):
        # We need W returns: rets[k - W + 1 : k + 1]. This requires k >= W - 1,
        # which means bar index = k + 1 >= W.
        rets_len = len(rets)
        for k in range(self._window - 1, rets_len):
            sub = rets[k - self._window + 1 : k + 1]
            if np.any(np.isnan(sub)):
                continue
            std = float(np.std(sub, ddof=1))
            if not math.isnan(std) and not math.isinf(std):
                out[k + 1] = float(std * scale)

        return out
