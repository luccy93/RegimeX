"""
RegimeX Regime Intelligence — Domain Models
===========================================
Defines the core domain representations of regime assignments, descriptive statistics,
regime profiles, current regime context, and historical regime summaries.

Guarantees:
- Pure Python and Pydantic v2 only (zero dependencies on NumPy, Pandas, or scikit-learn).
- Immutable, frozen domain models with strict validation.
- Zero data fabrication (no fillna(0), no invented regimes or probabilities).
- Neutral statistical terminology (no unwarranted 'bull'/'bear'/'crash' labels).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class FeatureStatistic(BaseModel):
    """
    Descriptive statistical characteristics of a single feature within a regime.

    Guarantees:
    - Never contains NaN, +inf, or -inf (missing metrics represented as None).
    - Uses sample standard deviation (ddof=1) when sample size >= 2.
    """

    model_config = {"frozen": True}

    feature_name: Annotated[
        str,
        Field(min_length=1, description="Identifier of the feature variable"),
    ]
    observation_count: Annotated[
        int,
        Field(ge=0, description="Count of valid non-null observations in this regime"),
    ]
    mean: float | None = Field(
        default=None,
        description="Arithmetic mean of feature values, or None if observation_count == 0",
    )
    median: float | None = Field(
        default=None,
        description="Median of feature values, or None if observation_count == 0",
    )
    std: float | None = Field(
        default=None,
        description=(
            "Sample standard deviation (ddof=1) of feature values, 0.0 if count == 1 "
            "or values identical, or None if observation_count == 0"
        ),
    )
    min: float | None = Field(
        default=None,
        description="Minimum feature value observed, or None if observation_count == 0",
    )
    max: float | None = Field(
        default=None,
        description="Maximum feature value observed, or None if observation_count == 0",
    )

    @field_validator("mean", "median", "std", "min", "max")
    @classmethod
    def validate_finite_numbers(cls, v: float | None) -> float | None:
        """Ensure no NaN or infinite float values are stored."""
        if v is not None:
            if math.isnan(v):
                raise ValueError("Statistic cannot be NaN; represent missingness as None.")
            if math.isinf(v):
                raise ValueError("Statistic cannot be infinite.")
        return v


class RegimeAssignment(BaseModel):
    """
    Point-in-time market regime assignment for a single observation bar.

    Combines temporal identity, assigned canonical regime identifier,
    and concurrent feature values.
    """

    model_config = {"frozen": True}

    timestamp: datetime = Field(description="Timezone-aware observation timestamp (UTC)")
    regime_id: Annotated[
        int,
        Field(ge=0, description="Canonical regime index (0..K-1)"),
    ]
    regime_label: Annotated[
        str,
        Field(min_length=1, description="Canonical regime label (e.g., 'REGIME_0')"),
    ]
    features: dict[str, float | None] = Field(
        default_factory=dict,
        description="Feature values observed at this timestamp",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional probability or confidence score for this assignment (0..1)",
    )
    model_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional model provenance metadata (model_name, version, etc.)",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"timestamp must be timezone-aware (got naive: {v!r}).")
        return v

    @field_validator("features")
    @classmethod
    def validate_feature_values(cls, v: dict[str, float | None]) -> dict[str, float | None]:
        """Ensure feature values are finite floats or explicit None."""
        for name, val in v.items():
            if val is not None:
                if math.isnan(val):
                    raise ValueError(
                        f"Feature '{name}' has NaN value. Missing values must be None."
                    )
                if math.isinf(val):
                    raise ValueError(f"Feature '{name}' has infinite value ({val}).")
        return v


class RegimeProfile(BaseModel):
    """
    Historical descriptive profile of an identified market regime.

    Aggregates empirical frequency, duration properties, and feature distributions.
    Duration semantics: measured in discrete observation units (bars).
    """

    model_config = {"frozen": True}

    regime_id: Annotated[int, Field(ge=0, description="Canonical regime identifier")]
    regime_label: Annotated[str, Field(min_length=1, description="Canonical regime label")]
    observation_count: Annotated[
        int,
        Field(ge=0, description="Total number of observations spent in this regime"),
    ]
    frequency: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Empirical occurrence frequency (observation_count / total_observations)",
        ),
    ]
    percentage: Annotated[
        float,
        Field(
            ge=0.0,
            le=100.0,
            description="Empirical occurrence percentage (frequency * 100.0)",
        ),
    ]
    first_seen: datetime | None = Field(
        default=None,
        description="UTC timestamp of earliest observation in this regime",
    )
    last_seen: datetime | None = Field(
        default=None,
        description="UTC timestamp of most recent observation in this regime",
    )
    run_count: Annotated[
        int,
        Field(ge=0, description="Number of contiguous runs/spells in this regime"),
    ]
    average_duration: Annotated[
        float,
        Field(ge=0.0, description="Mean consecutive observations per run (duration_observations)"),
    ]
    median_duration: Annotated[
        float,
        Field(
            ge=0.0,
            description="Median consecutive observations per run (duration_observations)",
        ),
    ]
    min_duration: Annotated[
        int,
        Field(ge=0, description="Minimum consecutive observations in a single run"),
    ]
    max_duration: Annotated[
        int,
        Field(ge=0, description="Maximum consecutive observations in a single run"),
    ]
    feature_statistics: dict[str, FeatureStatistic] = Field(
        default_factory=dict,
        description="Descriptive statistics for each feature within this regime",
    )

    @field_validator("first_seen", "last_seen", mode="before")
    @classmethod
    def validate_timestamps(cls, v: datetime | None) -> datetime | None:
        """Ensure timestamps are timezone-aware if present."""
        if v is not None and isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware (got naive: {v!r}).")
        return v

    @model_validator(mode="after")
    def validate_duration_invariants(self) -> RegimeProfile:
        """Validate duration ordering invariants when runs exist."""
        if self.run_count > 0:
            if not (self.min_duration <= self.median_duration <= self.max_duration):
                raise ValueError(
                    f"Duration invariant violated: min ({self.min_duration}) <= "
                    f"median ({self.median_duration}) <= max ({self.max_duration}) required."
                )
            if not (self.min_duration <= self.average_duration <= self.max_duration):
                raise ValueError(
                    f"Duration invariant violated: min ({self.min_duration}) <= "
                    f"average ({self.average_duration}) <= max ({self.max_duration}) required."
                )
        return self


class CurrentRegimeContext(BaseModel):
    """
    Descriptive point-in-time context for the current (latest) market regime.

    Provides context on how long the current regime spell has persisted relative
    to its historical characteristics. Does NOT offer future forecasting or trade signals.
    """

    model_config = {"frozen": True}

    current_regime_id: Annotated[
        int,
        Field(ge=0, description="Active regime index at latest observation"),
    ]
    current_regime_label: Annotated[str, Field(min_length=1, description="Active regime label")]
    current_timestamp: datetime = Field(description="UTC timestamp of the latest observation")
    observations_in_current_run: Annotated[
        int,
        Field(ge=1, description="Number of consecutive observations in active trailing spell"),
    ]
    historical_frequency: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Historical overall frequency of this regime"),
    ]
    historical_average_duration: Annotated[
        float,
        Field(ge=0.0, description="Historical mean duration in observation units"),
    ]
    historical_max_duration: Annotated[
        int,
        Field(ge=0, description="Historical maximum duration in observation units"),
    ]
    historical_min_duration: Annotated[
        int,
        Field(ge=0, description="Historical minimum duration in observation units"),
    ]
    historical_run_count: Annotated[
        int,
        Field(ge=0, description="Historical total number of runs for this regime"),
    ]
    current_features: dict[str, float | None] | None = Field(
        default=None,
        description="Feature values recorded at the latest observation timestamp",
    )

    @field_validator("current_timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"current_timestamp must be timezone-aware (got naive: {v!r}).")
        return v


class RegimeHistorySummary(BaseModel):
    """
    Complete immutable historical analytics container for a sequence of regime observations.

    Captures dataset scope, per-regime profiles, active context, and model provenance.
    """

    model_config = {"frozen": True}

    analysis_start: datetime | None = Field(
        default=None,
        description="Earliest observation timestamp in the analyzed history",
    )
    analysis_end: datetime | None = Field(
        default=None,
        description="Latest observation timestamp in the analyzed history",
    )
    total_observations: Annotated[
        int,
        Field(ge=0, description="Total number of observations analyzed"),
    ]
    regimes_observed: tuple[int, ...] = Field(
        default=(),
        description="Sorted tuple of distinct canonical regime IDs observed",
    )
    regime_profiles: dict[int, RegimeProfile] = Field(
        default_factory=dict,
        description="Detailed descriptive profiles keyed by canonical regime ID",
    )
    current_regime: CurrentRegimeContext | None = Field(
        default=None,
        description="Context of the latest observation, or None if history is empty",
    )
    model_name: str | None = Field(default=None, description="Name of detection model")
    model_version: str | None = Field(default=None, description="Version of detection model")
    algorithm: str | None = Field(default=None, description="Algorithm utilized")
    feature_names: tuple[str, ...] = Field(
        default=(),
        description="Names of features evaluated in chronological column order",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when summary analytics were computed",
    )

    @field_validator("analysis_start", "analysis_end", "computed_at", mode="before")
    @classmethod
    def validate_timestamps(cls, v: datetime | None) -> datetime | None:
        """Ensure timestamps are timezone-aware if present."""
        if v is not None and isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware (got naive: {v!r}).")
        return v

    @property
    def is_empty(self) -> bool:
        """True if history contains zero observations."""
        return self.total_observations == 0

    def get_profile(self, regime_id: int) -> RegimeProfile | None:
        """Retrieve the profile for a given regime, or None if not found."""
        return self.regime_profiles.get(regime_id)
