"""
RegimeX Regime Detection Module
===============================
Unsupervised and statistical market regime detection framework.

Architecture:
- ``domain/``: Core models (RegimeModelConfig, FeatureMatrix, ClusterProfile,
  FitResult, RegimeDetectionResult), RegimeDetector ABC interface, and typed errors.
- ``application/``: FeatureMatrixBuilder, RegimeDetectionService.
- ``infrastructure/``: KMeansRegimeDetector (StandardScaler + KMeans adapter).
"""

from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.errors import (
    GMMConvergenceError,
    GMMFitError,
    GMMPredictionError,
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    InvalidGMMConfigurationError,
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
    GMMModelConfig,
    ModelState,
    RegimeDetectionResult,
    RegimeModelConfig,
    RegimeRecord,
)
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)

__all__ = [
    "ClusterProfile",
    "DetectorMetadata",
    "FeatureMatrix",
    "FeatureMatrixBuilder",
    "FitResult",
    "GMMConvergenceError",
    "GMMFitError",
    "GMMModelConfig",
    "GMMPredictionError",
    "GaussianMixtureRegimeDetector",
    "InsufficientTrainingDataError",
    "InvalidFeatureMatrixError",
    "InvalidGMMConfigurationError",
    "InvalidModelConfigurationError",
    "KMeansRegimeDetector",
    "ModelNotFittedError",
    "ModelPredictionError",
    "ModelState",
    "ModelTrainingError",
    "RegimeDetectionError",
    "RegimeDetectionResult",
    "RegimeDetectionService",
    "RegimeDetector",
    "RegimeModelConfig",
    "RegimeRecord",
    "UnsupportedPredictionError",
]
