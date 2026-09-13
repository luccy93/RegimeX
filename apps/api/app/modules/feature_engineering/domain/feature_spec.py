"""
RegimeX Feature Engineering — Feature Specification
===================================================
Defines the metadata, parameterization, and contract specification for individual
quantitative market features.

Architectural position: ``domain/feature_spec.py`` — pure Python and Pydantic v2 only.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.modules.feature_engineering.domain.models import FeatureCategory


class FeatureDefinition(BaseModel):
    """
    Formal metadata and parameter specification for a quantitative feature.

    Attributes:
        name: Unique feature identifier (e.g. 'return_1', 'volatility_20').
        category: Broad financial category (RETURN, VOLATILITY, MOMENTUM, etc.).
        description: Human-readable explanation of what this feature represents.
        formula: Mathematical expression or algorithm description.
        required_fields: OHLCV fields required (e.g. ('close',), ('high', 'low', 'close')).
        lookback: Observation window required for rolling calculations.
        min_observations: Minimum total bars needed before the feature can produce any valid value.
        version: Semantic version of the calculation algorithm.
        params: Arbitrary calculation parameters (e.g. window=20, annualization_factor=252.0).
    """

    model_config = {"frozen": True}

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            pattern=r"^[a-z][a-z0-9_]*$",
            description="Unique snake_case feature name",
        ),
    ]
    category: FeatureCategory = Field(description="Domain category of the feature")
    description: str = Field(min_length=1, max_length=500, description="Explainable description")
    formula: str = Field(min_length=1, max_length=500, description="Mathematical formulation")
    required_fields: tuple[str, ...] = Field(
        default=("close",),
        description="Required OHLCV input fields",
    )
    lookback: int = Field(
        ge=1,
        description="Window size / lag parameter for the feature",
    )
    min_observations: int = Field(
        ge=1,
        description="Minimum observations required to produce a non-null calculation",
    )
    version: str = Field(
        default="1.0.0",
        max_length=20,
        description="Semantic version of this feature definition",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Static parameters passed to the calculator algorithm",
    )
