"""
RegimeX Data Quality — Application Configuration
=================================================
Defines configurable thresholds, toggles, and tolerances for the validation pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ValidationConfig(BaseModel):
    """
    Configuration settings for MarketDataValidationPipeline.
    """

    model_config = {"frozen": True}

    # Rule toggles
    enable_schema: bool = Field(default=True, description="Enable structural/type validation.")
    enable_timestamp: bool = Field(
        default=True, description="Enable UTC and future timestamp checks."
    )
    enable_ohlc: bool = Field(default=True, description="Enable OHLC price relationship checks.")
    enable_volume: bool = Field(default=True, description="Enable volume checks.")
    enable_duplicate: bool = Field(
        default=True, description="Enable duplicate timestamp detection."
    )
    enable_ordering: bool = Field(default=True, description="Enable chronological ordering checks.")
    enable_calendar: bool = Field(
        default=True, description="Enable exchange calendar & session checks."
    )
    enable_gap: bool = Field(default=True, description="Enable calendar-aware gap detection.")
    enable_staleness: bool = Field(default=True, description="Enable dataset staleness detection.")

    # Staleness threshold
    staleness_threshold_hours: float = Field(
        default=72.0,
        gt=0.0,
        description="Hours before latest observation is considered stale.",
    )

    # Clock skew tolerance for future timestamps
    future_clock_skew_seconds: float = Field(
        default=300.0,  # 5 minutes
        ge=0.0,
        description="Allowed clock skew in seconds for future timestamp validation.",
    )
