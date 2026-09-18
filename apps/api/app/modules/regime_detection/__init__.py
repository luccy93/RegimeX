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
    HMMConvergenceError,
    HMMFitError,
    HMMPredictionError,
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    InvalidGMMConfigurationError,
    InvalidHMMConfigurationError,
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
    HMMModelConfig,
    ModelState,
    RegimeDetectionResult,
    RegimeModelConfig,
    RegimeRecord,
)
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.hmm import (
    GaussianHMMRegimeDetector,
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
    "GaussianHMMRegimeDetector",
    "GaussianMixtureRegimeDetector",
    "HMMConvergenceError",
    "HMMFitError",
    "HMMModelConfig",
    "HMMPredictionError",
    "InsufficientTrainingDataError",
    "InvalidFeatureMatrixError",
    "InvalidGMMConfigurationError",
    "InvalidHMMConfigurationError",
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
