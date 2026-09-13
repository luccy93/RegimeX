"""
RegimeX Regime Detection — Domain Layer
=======================================
Domain models, interfaces, and error classes for market regime detection.
"""

from app.modules.regime_detection.domain.errors import (
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    InvalidModelConfigurationError,
    ModelNotFittedError,
    ModelPredictionError,
    ModelTrainingError,
    RegimeDetectionError,
    UnsupportedPredictionError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    ClusterProfile,
    DetectorMetadata,
    FeatureMatrix,
    FitResult,
    ModelState,
    RegimeDetectionResult,
    RegimeModelConfig,
    RegimeRecord,
)

__all__ = [
    "ClusterProfile",
    "DetectorMetadata",
    "FeatureMatrix",
    "FitResult",
    "InsufficientTrainingDataError",
    "InvalidFeatureMatrixError",
    "InvalidModelConfigurationError",
    "ModelNotFittedError",
    "ModelPredictionError",
    "ModelState",
    "ModelTrainingError",
    "RegimeDetectionError",
    "RegimeDetectionResult",
    "RegimeDetector",
    "RegimeModelConfig",
    "RegimeRecord",
    "UnsupportedPredictionError",
]
