"""
RegimeX Feature Engineering — Pipeline Configuration
====================================================
Defines centralized configuration for the feature pipeline execution.

Architectural position: ``application/config.py``
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.feature_engineering.domain.models import MissingValuePolicy


class FeaturePipelineConfig(BaseModel):
    """
    Centralized configuration for feature calculation execution.

    Attributes:
        enabled_features: Explicit list of feature names to compute, or None for all registered.
        annualization_factor: Multiplier for annualized volatility (default 252 for daily equities).
        missing_value_policy: PRESERVE (keep None in warm-up) or DROP_WARMUP (trim incomplete rows).
        numerical_tolerance: Float comparison tolerance for safety checks.
        version: Pipeline version identifier.
    """

    model_config = {"frozen": True}

    enabled_features: tuple[str, ...] | None = Field(
        default=None,
        description="Explicit list of feature names to compute, or None for all baseline features",
    )
    annualization_factor: float = Field(
        default=252.0,
        gt=0.0,
        description="Annualization scaling factor based on market trading session calendar",
    )
    missing_value_policy: MissingValuePolicy = Field(
        default=MissingValuePolicy.PRESERVE,
        description="Policy for handling warm-up missing values in the output FeatureSet",
    )
    numerical_tolerance: float = Field(
        default=1e-12,
        gt=0.0,
        description="Tolerance threshold for numerical safety checks against division by zero",
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic version of the feature pipeline",
    )
