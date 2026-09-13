"""
RegimeX Feature Engineering Module
==================================
Transforms normalized, validated market data into deterministic, explainable,
point-in-time correct quantitative features with zero look-ahead bias.
"""

from app.modules.feature_engineering.application import (
    FeaturePipeline,
    FeaturePipelineConfig,
    FeatureRegistry,
    FeatureService,
    get_default_registry,
)
from app.modules.feature_engineering.domain import (
    DuplicateFeatureError,
    FeatureCalculationError,
    FeatureCalculator,
    FeatureCategory,
    FeatureDefinition,
    FeatureEngineeringError,
    FeatureInputData,
    FeatureNotFoundError,
    FeatureRecord,
    FeatureSet,
    InsufficientDataError,
    InvalidFeatureInputError,
    LookaheadBiasError,
    MissingValuePolicy,
)

__all__ = [
    "DuplicateFeatureError",
    "FeatureCalculationError",
    "FeatureCalculator",
    "FeatureCategory",
    "FeatureDefinition",
    "FeatureEngineeringError",
    "FeatureInputData",
    "FeatureNotFoundError",
    "FeaturePipeline",
    "FeaturePipelineConfig",
    "FeatureRecord",
    "FeatureRegistry",
    "FeatureService",
    "FeatureSet",
    "InsufficientDataError",
    "InvalidFeatureInputError",
    "LookaheadBiasError",
    "MissingValuePolicy",
    "get_default_registry",
]
