"""
RegimeX Portfolio Risk — Canonical Domain Models
================================================
Defines immutable, strongly-typed domain models for portfolio and return risk analytics.

Architectural position: ``domain/models.py``
- Pure Python and Pydantic v2.
- Zero external ML/DL or web framework dependencies.
- Strict timezone-aware UTC datetime validation.
- Loss-oriented VaR and CVaR / Expected Shortfall conventions.
- Explicit numerical conventions (sample standard deviation with Bessel's correction ddof=1).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReturnType(StrEnum):
    """Canonical return calculation type."""

    ARITHMETIC = "arithmetic"
    LOG = "log"


class ReturnObservation(BaseModel):
    """Point-in-time discrete return observation."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    return_value: float

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and (v.tzinfo is None or v.utcoffset() != timedelta(0)):
            raise ValueError(f"timestamp must be UTC-aware (got: {v!r}).")
        return v

    @field_validator("return_value")
    @classmethod
    def require_finite_return(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"return_value must be finite (got {v}).")
        return v


class ReturnSeries(BaseModel):
    """
    Validated chronological sequence of discrete returns.

    Guarantees:
    - Strictly monotonic, duplicate-free, timezone-aware UTC timestamps.
    - All returns are finite float values.
    - Preserves sample size and optional asset symbol.
    """

    model_config = ConfigDict(frozen=True)

    timestamps: tuple[datetime, ...]
    values: tuple[float, ...]
    symbol: str | None = None

    @model_validator(mode="after")
    def validate_series_integrity(self) -> ReturnSeries:
        if len(self.timestamps) != len(self.values):
            raise ValueError(
                f"Mismatched timestamps and values length: "
                f"{len(self.timestamps)} timestamps vs {len(self.values)} values."
            )
        if len(self.values) == 0:
            raise ValueError("ReturnSeries cannot be empty.")

        # Validate finite values
        for idx, r in enumerate(self.values):
            if math.isnan(r) or math.isinf(r):
                raise ValueError(f"Return at index {idx} is non-finite: {r}.")

        # Validate strictly increasing UTC timestamps
        prev_ts: datetime | None = None
        for idx, ts in enumerate(self.timestamps):
            if ts.tzinfo is None or ts.utcoffset() != timedelta(0):
                raise ValueError(f"Timestamp at index {idx} must be UTC-aware (got: {ts!r}).")
            if prev_ts is not None and ts <= prev_ts:
                raise ValueError(
                    f"Timestamps must be strictly increasing: "
                    f"timestamp[{idx}] ({ts.isoformat()}) <= timestamp[{idx - 1}] "
                    f"({prev_ts.isoformat()})."
                )
            prev_ts = ts

        return self

    @property
    def length(self) -> int:
        return len(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, idx: int) -> float:
        return self.values[idx]


class PriceSeries(BaseModel):
    """
    Validated chronological sequence of financial asset prices.

    Invariants:
    - Prices must be strictly positive (P_t > 0).
    - Strictly increasing, timezone-aware UTC timestamps.
    - Finite float values.
    """

    model_config = ConfigDict(frozen=True)

    timestamps: tuple[datetime, ...]
    prices: tuple[float, ...]
    symbol: str | None = None

    @model_validator(mode="after")
    def validate_price_series(self) -> PriceSeries:
        if len(self.timestamps) != len(self.prices):
            raise ValueError(
                f"Mismatched timestamps and prices length: "
                f"{len(self.timestamps)} vs {len(self.prices)}."
            )
        if len(self.prices) == 0:
            raise ValueError("PriceSeries cannot be empty.")

        for idx, p in enumerate(self.prices):
            if math.isnan(p) or math.isinf(p):
                raise ValueError(f"Price at index {idx} is non-finite: {p}.")
            if p <= 0.0:
                raise ValueError(f"Price at index {idx} must be strictly positive: {p}.")

        prev_ts: datetime | None = None
        for idx, ts in enumerate(self.timestamps):
            if ts.tzinfo is None or ts.utcoffset() != timedelta(0):
                raise ValueError(f"Timestamp at index {idx} must be UTC-aware (got: {ts!r}).")
            if prev_ts is not None and ts <= prev_ts:
                raise ValueError(
                    f"Price timestamps must be strictly increasing: "
                    f"timestamp[{idx}] ({ts.isoformat()}) <= timestamp[{idx - 1}] "
                    f"({prev_ts.isoformat()})."
                )
            prev_ts = ts

        return self

    @property
    def length(self) -> int:
        return len(self.prices)

    def __len__(self) -> int:
        return len(self.prices)

    def __getitem__(self, idx: int) -> float:
        return self.prices[idx]


class ReturnStatistics(BaseModel):
    """
    Summary descriptive statistics of a return series.

    Statistical convention:
    - standard_deviation uses sample Bessel correction (ddof=1).
    - Requires sample size >= 2 for standard deviation.
    """

    model_config = ConfigDict(frozen=True)

    mean_return: float = Field(description="Arithmetic mean of returns")
    median_return: float = Field(description="Median return")
    standard_deviation: float = Field(
        ge=0.0,
        description="Sample standard deviation of returns (ddof=1)",
    )
    minimum_return: float = Field(description="Minimum observed return")
    maximum_return: float = Field(description="Maximum observed return")
    observation_count: int = Field(ge=2, description="Number of observed return periods")

    @model_validator(mode="after")
    def validate_extrema(self) -> ReturnStatistics:
        if self.minimum_return > self.maximum_return:
            raise ValueError(
                f"minimum_return ({self.minimum_return}) cannot exceed "
                f"maximum_return ({self.maximum_return})."
            )
        if not (self.minimum_return <= self.mean_return <= self.maximum_return):
            # Allow numerical precision margin of 1e-12
            if (
                self.mean_return < self.minimum_return - 1e-12
                or self.mean_return > self.maximum_return + 1e-12
            ):
                raise ValueError("mean_return must lie within [minimum_return, maximum_return].")
        return self


class VolatilityMetrics(BaseModel):
    """
    Realized and annualized volatility metrics.

    Convention:
    - period_volatility is the sample standard deviation (ddof=1).
    - annualized_volatility = period_volatility * sqrt(periods_per_year).
    - periods_per_year is explicit; never hardcoded.
    """

    model_config = ConfigDict(frozen=True)

    period_volatility: Annotated[
        float,
        Field(ge=0.0, description="Realized volatility over the observation interval"),
    ]
    annualized_volatility: float | None = Field(
        default=None,
        ge=0.0,
        description="Annualized volatility if frequency is configured",
    )
    periods_per_year: float | None = Field(
        default=None,
        gt=0.0,
        description="Periods per year for annualization (e.g. 252 for daily US equities)",
    )

    @model_validator(mode="after")
    def validate_annualization(self) -> VolatilityMetrics:
        if self.periods_per_year is not None and self.annualized_volatility is None:
            raise ValueError(
                "annualized_volatility must be specified when periods_per_year is provided."
            )
        if self.annualized_volatility is not None and self.periods_per_year is None:
            raise ValueError(
                "periods_per_year must be specified when annualized_volatility is provided."
            )
        return self


class DownsideRiskMetrics(BaseModel):
    """
    Downside deviation and semi-variance metrics relative to a target return.

    Formula:
        downside_t = min(return_t - target_return, 0)
        downside_deviation = sqrt( (1 / N) * sum(downside_t^2) )
    """

    model_config = ConfigDict(frozen=True)

    target_return: float = Field(
        default=0.0,
        description="Threshold return benchmark below which returns are penalized",
    )
    downside_deviation: Annotated[
        float,
        Field(ge=0.0, description="Root-mean-square downside deviation below target"),
    ]
    observations_below_target: Annotated[
        int,
        Field(ge=0, description="Count of return observations falling strictly below target"),
    ]
    total_observations: Annotated[
        int,
        Field(ge=1, description="Total number of return observations analyzed"),
    ]

    @model_validator(mode="after")
    def validate_counts(self) -> DownsideRiskMetrics:
        if self.observations_below_target > self.total_observations:
            raise ValueError(
                f"observations_below_target ({self.observations_below_target}) cannot exceed "
                f"total_observations ({self.total_observations})."
            )
        return self


class DrawdownMetrics(BaseModel):
    """
    Historical drawdown analysis from running equity/wealth curve.

    Definitions:
    - max_drawdown: Deepest fractional loss from running peak (signed <= 0, e.g. -0.25).
    - drawdown_magnitude: Absolute magnitude of max_drawdown (>= 0, e.g. 0.25).
    - peak_value: Highest wealth reached prior to the trough.
    - trough_value: Deepest wealth reached at the trough.
    - peak_timestamp: Timestamp when peak was formed.
    - trough_timestamp: Timestamp when trough occurred.
    - recovery_timestamp: Timestamp when wealth first recovered to >= peak_value (or None).
    - is_recovered: True if wealth recovered to peak level after trough.
    """

    model_config = ConfigDict(frozen=True)

    max_drawdown: Annotated[
        float,
        Field(le=0.0, description="Maximum drawdown from peak to trough (signed negative)"),
    ]
    drawdown_magnitude: Annotated[
        float,
        Field(ge=0.0, description="Absolute magnitude of maximum drawdown (|max_drawdown|)"),
    ]
    peak_value: Annotated[float, Field(gt=0.0, description="Wealth level at the peak")]
    trough_value: Annotated[float, Field(ge=0.0, description="Wealth level at the trough")]
    peak_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp when running peak was attained",
    )
    trough_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp when deepest trough occurred",
    )
    recovery_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp when wealth recovered to peak, or None if not yet recovered",
    )
    is_recovered: bool = Field(
        default=False,
        description="Indicates whether wealth fully recovered from the maximum drawdown",
    )

    @field_validator("peak_timestamp", "trough_timestamp", "recovery_timestamp", mode="before")
    @classmethod
    def require_tz_aware_optional(cls, v: datetime | None) -> datetime | None:
        if (
            v is not None
            and isinstance(v, datetime)
            and (v.tzinfo is None or v.utcoffset() != timedelta(0))
        ):
            raise ValueError(f"Drawdown timestamp must be UTC-aware (got: {v!r}).")
        return v

    @model_validator(mode="after")
    def validate_drawdown_consistency(self) -> DrawdownMetrics:
        if abs(abs(self.max_drawdown) - self.drawdown_magnitude) > 1e-12:
            raise ValueError("drawdown_magnitude must equal abs(max_drawdown).")
        if self.trough_value > self.peak_value:
            raise ValueError(
                f"trough_value ({self.trough_value}) cannot exceed peak_value ({self.peak_value})."
            )
        if self.is_recovered and self.recovery_timestamp is None:
            raise ValueError("recovery_timestamp must be present when is_recovered is True.")
        return self


class VaRMetrics(BaseModel):
    """
    Value at Risk (VaR) metric under historical simulation.

    Conventions:
    - Loss-oriented: var_loss is expressed as a positive loss quantity.
      Example: If the 5th percentile return is -0.035 (-3.5%), var_loss = +0.035.
    - return_quantile is the unnegated empirical return quantile (q_{1 - alpha}).
    - confidence_level is the probability level alpha (e.g. 0.90, 0.95, 0.99).
    """

    model_config = ConfigDict(frozen=True)

    confidence_level: Annotated[
        float,
        Field(gt=0.0, lt=1.0, description="Confidence level alpha (0 < alpha < 1)"),
    ]
    var_loss: float = Field(
        description="Loss-oriented VaR: positive value denotes a loss (var_loss = -return_quantile)"
    )
    return_quantile: float = Field(
        description="Empirical quantile of the return distribution at 1 - confidence_level"
    )
    method: str = Field(
        default="historical",
        description="VaR estimation methodology (historical empirical simulation)",
    )
    tail_observations: Annotated[
        int,
        Field(ge=1, description="Count of observations falling in the tail (<= quantile)"),
    ]
    total_observations: Annotated[
        int,
        Field(ge=1, description="Total number of returns analyzed"),
    ]

    @model_validator(mode="after")
    def validate_var_consistency(self) -> VaRMetrics:
        if abs(self.var_loss - (-self.return_quantile)) > 1e-12:
            raise ValueError("var_loss must equal -return_quantile.")
        if self.tail_observations > self.total_observations:
            raise ValueError(
                f"tail_observations ({self.tail_observations}) cannot exceed "
                f"total_observations ({self.total_observations})."
            )
        return self


class ExpectedShortfallMetrics(BaseModel):
    """
    Expected Shortfall (CVaR / Conditional Value at Risk) under historical simulation.

    Conventions:
    - Loss-oriented: expected_shortfall is expressed as a positive loss quantity.
      ES_alpha = - E[R | R <= q_{1 - alpha}].
    - tail_mean_return is the average return in the tail (negative value).
    - Consistency invariant: For empirical distribution, expected_shortfall >= var_loss.
    """

    model_config = ConfigDict(frozen=True)

    confidence_level: Annotated[
        float,
        Field(gt=0.0, lt=1.0, description="Confidence level alpha (0 < alpha < 1)"),
    ]
    expected_shortfall: float = Field(
        description="Loss-oriented Expected Shortfall: positive value denotes average tail loss"
    )
    tail_mean_return: float = Field(
        description="Empirical average return of observations in the tail (tail_mean = -ES)"
    )
    var_loss: float = Field(
        description="Associated Value at Risk loss threshold at the same confidence level"
    )
    tail_observations: Annotated[
        int,
        Field(ge=1, description="Count of observations in the tail"),
    ]
    total_observations: Annotated[
        int,
        Field(ge=1, description="Total number of returns analyzed"),
    ]

    @model_validator(mode="after")
    def validate_es_consistency(self) -> ExpectedShortfallMetrics:
        if abs(self.expected_shortfall - (-self.tail_mean_return)) > 1e-12:
            raise ValueError("expected_shortfall must equal -tail_mean_return.")
        if self.tail_observations > self.total_observations:
            raise ValueError(
                f"tail_observations ({self.tail_observations}) cannot exceed "
                f"total_observations ({self.total_observations})."
            )
        # Numerical tolerance for tail mean <= quantile in loss space
        if self.expected_shortfall < self.var_loss - 1e-10:
            raise ValueError(
                f"Expected Shortfall loss ({self.expected_shortfall}) cannot be less than "
                f"VaR loss ({self.var_loss})."
            )
        return self


class PortfolioWeights(BaseModel):
    """
    Asset allocation weights for multi-asset portfolio return aggregation.

    Guarantees:
    - Length of symbols matches length of weights.
    - All weights are finite.
    - Preserves whether weights are unit-normalized.
    """

    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...]
    weights: tuple[float, ...]
    is_normalized: bool = True

    @model_validator(mode="after")
    def validate_weights(self) -> PortfolioWeights:
        if len(self.symbols) != len(self.weights):
            raise ValueError(
                f"Symbols length ({len(self.symbols)}) != weights length ({len(self.weights)})."
            )
        if len(self.symbols) == 0:
            raise ValueError("PortfolioWeights cannot be empty.")

        for idx, w in enumerate(self.weights):
            if math.isnan(w) or math.isinf(w):
                raise ValueError(f"Weight at index {idx} ({self.symbols[idx]}) is non-finite: {w}.")

        if self.is_normalized:
            total = sum(self.weights)
            if abs(total - 1.0) > 1e-5:
                raise ValueError(
                    f"Normalized portfolio weights must sum to 1.0 within tolerance "
                    f"(got sum={total:.6f})."
                )

        return self

    @property
    def asset_count(self) -> int:
        return len(self.symbols)

    def get_weight(self, symbol: str) -> float:
        try:
            idx = self.symbols.index(symbol)
            return self.weights[idx]
        except ValueError:
            raise KeyError(f"Symbol {symbol!r} not in portfolio symbols: {self.symbols}.") from None


class PortfolioRiskResult(BaseModel):
    """
    Comprehensive result container for portfolio risk analytics.

    Encapsulates:
    - Descriptive return statistics
    - Realized and annualized volatility
    - Downside risk semi-deviations
    - Peak-to-trough drawdown dynamics
    - Multi-confidence Value at Risk (VaR)
    - Multi-confidence Expected Shortfall (CVaR)
    - Metadata and date range
    """

    model_config = ConfigDict(frozen=True)

    series_id: str = Field(
        default="portfolio",
        description="Identifier of the return series or portfolio analyzed",
    )
    return_statistics: ReturnStatistics
    volatility: VolatilityMetrics
    downside_risk: DownsideRiskMetrics
    drawdown: DrawdownMetrics
    var_metrics: dict[float, VaRMetrics] = Field(
        description="Dictionary mapping confidence levels (e.g. 0.95) to VaRMetrics"
    )
    expected_shortfall_metrics: dict[float, ExpectedShortfallMetrics] = Field(
        description="Dictionary mapping confidence levels to ExpectedShortfallMetrics"
    )
    observation_count: Annotated[int, Field(ge=2, description="Total returns analyzed")]
    start_timestamp: datetime | None = Field(
        default=None,
        description="Earliest timestamp in the return series",
    )
    end_timestamp: datetime | None = Field(
        default=None,
        description="Latest timestamp in the return series",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when the risk analytics were evaluated",
    )

    @field_validator("start_timestamp", "end_timestamp", "computed_at", mode="before")
    @classmethod
    def require_tz_aware_timestamps(cls, v: datetime | None) -> datetime | None:
        if (
            v is not None
            and isinstance(v, datetime)
            and (v.tzinfo is None or v.utcoffset() != timedelta(0))
        ):
            raise ValueError(f"Timestamp must be UTC-aware (got: {v!r}).")
        return v

    def get_var(self, confidence_level: float) -> VaRMetrics:
        """Retrieve VaRMetrics for a specific evaluated confidence level."""
        for c, m in self.var_metrics.items():
            if abs(c - confidence_level) < 1e-6:
                return m
        raise KeyError(
            f"Confidence level {confidence_level} not found in computed VaR metrics: "
            f"{list(self.var_metrics.keys())}."
        )

    def get_expected_shortfall(self, confidence_level: float) -> ExpectedShortfallMetrics:
        """Retrieve ExpectedShortfallMetrics for a specific evaluated confidence level."""
        for c, m in self.expected_shortfall_metrics.items():
            if abs(c - confidence_level) < 1e-6:
                return m
        raise KeyError(
            f"Confidence level {confidence_level} not found in computed Expected Shortfall: "
            f"{list(self.expected_shortfall_metrics.keys())}."
        )
