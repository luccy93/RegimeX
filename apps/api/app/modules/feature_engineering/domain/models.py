"""
RegimeX Feature Engineering — Domain Models
===========================================
Defines the core domain representations of feature categories, missing-value
policies, bar-level feature records, and canonical feature input data.

Architectural position: ``domain/models.py`` — pure Python and Pydantic v2 only.
Zero dependencies on NumPy, Pandas, or external database ORMs.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.market_data.domain.models import OHLCVRecord


class FeatureCategory(StrEnum):
    """Canonical feature categorization for RegimeX."""

    RETURN = "return"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    TREND = "trend"
    VOLUME = "volume"
    RANGE = "range"


class MissingValuePolicy(StrEnum):
    """
    Policy for handling missing values and warm-up periods.

    PRESERVE    — Keep warm-up observations as None (preserves temporal alignment).
    DROP_WARMUP — Trim leading rows where any enabled feature is None.
    """

    PRESERVE = "preserve"
    DROP_WARMUP = "drop_warmup"


class FeatureRecord(BaseModel):
    """
    Computed feature vector for a single timestamp.

    Attributes:
        timestamp: Timezone-aware UTC timestamp corresponding to the market data bar.
        values: Mapping of feature_name to numerical value or None if in warm-up.
    """

    model_config = {"frozen": True}

    timestamp: datetime = Field(description="UTC timestamp of the observation bar")
    values: dict[str, float | None] = Field(
        default_factory=dict,
        description="Feature values computed at or before this timestamp",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes — all timestamps must be timezone-aware UTC."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"FeatureRecord timestamp must be timezone-aware (got naive: {v!r}).")
        return v


class FeatureInputData(BaseModel):
    """
    Pure-domain container for ordered time series extracted from canonical OHLCV bars.

    Guarantees:
    - All series have identical length.
    - Timestamps are timezone-aware UTC and strictly monotonically increasing.
    - Zero dependencies on Pandas or NumPy in the domain layer.
    """

    model_config = {"frozen": True}

    timestamps: tuple[datetime, ...] = Field(description="Monotonically increasing UTC timestamps")
    opens: tuple[float, ...] = Field(description="Opening prices")
    highs: tuple[float, ...] = Field(description="High prices")
    lows: tuple[float, ...] = Field(description="Low prices")
    closes: tuple[float, ...] = Field(description="Closing prices")
    volumes: tuple[float, ...] | None = Field(
        default=None,
        description="Volume series, or None if volume is not supported/available",
    )

    @property
    def length(self) -> int:
        """Number of observations in the series."""
        return len(self.timestamps)

    @model_validator(mode="after")
    def validate_series_consistency(self) -> FeatureInputData:
        """Verify length alignment and strict timestamp monotonicity."""
        n = len(self.timestamps)
        if n == 0:
            raise ValueError("FeatureInputData requires at least one observation.")

        if (
            len(self.opens) != n
            or len(self.highs) != n
            or len(self.lows) != n
            or len(self.closes) != n
        ):
            raise ValueError(
                "All price series (opens, highs, lows, closes) must match timestamp length."
            )

        if self.volumes is not None and len(self.volumes) != n:
            raise ValueError("Volume series length must match timestamp length.")

        for i in range(1, n):
            if self.timestamps[i] <= self.timestamps[i - 1]:
                raise ValueError(
                    f"Timestamps must be strictly ascending: "
                    f"{self.timestamps[i - 1]} >= {self.timestamps[i]}"
                )

        return self

    @classmethod
    def from_ohlcv_records(cls, records: Sequence[OHLCVRecord]) -> FeatureInputData:
        """Construct a validated FeatureInputData instance from canonical OHLCV records."""
        if not records:
            raise ValueError("Cannot construct FeatureInputData from empty records sequence.")

        timestamps = tuple(r.timestamp for r in records)
        opens = tuple(r.open for r in records)
        highs = tuple(r.high for r in records)
        lows = tuple(r.low for r in records)
        closes = tuple(r.close for r in records)

        # Check if volumes are present
        has_volume = any(r.volume > 0.0 for r in records)
        volumes: tuple[float, ...] | None = tuple(r.volume for r in records) if has_volume else None

        return cls(
            timestamps=timestamps,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
        )
