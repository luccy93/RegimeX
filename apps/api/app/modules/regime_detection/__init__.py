"""
RegimeX Regime Detection Module
===============================
Unsupervised and statistical market regime detection framework.

Architecture:
- ``domain/``: Core models (RegimeModelConfig, FeatureMatrix, ClusterProfile,
  FitResult, RegimeDetectionResult, EnsembleModelConfig, RegimeEnsembleResult),
  RegimeDetector ABC interface, and typed errors.
- ``application/``: FeatureMatrixBuilder, RegimeDetectionService.
- ``infrastructure/``: KMeansRegimeDetector, GaussianMixtureRegimeDetector,
  GaussianHMMRegimeDetector, RegimeModelEnsemble.
"""

from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.errors import (
    EnsembleError,
    EnsembleExecutionError,
    EnsembleModelUnavailableError,
    GMMConvergenceError,
    GMMFitError,
    GMMPredictionError,
    HMMConvergenceError,
    HMMFitError,
    HMMPredictionError,
    InsufficientTrainingDataError,
    InsufficientUsableModelsError,
    InvalidEnsembleConfigurationError,
    InvalidFeatureMatrixError,
    InvalidGMMConfigurationError,
    InvalidHMMConfigurationError,
    InvalidModelConfigurationError,
    ModelNotFittedError,
    ModelPredictionError,
    ModelTrainingError,
    RegimeAlignmentError,
    RegimeDetectionError,
    UnsupportedPredictionError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    AggregationStrategy,
    AlignmentPolicy,
    ClusterProfile,
    DetectorMetadata,
    EnsembleModelConfig,
    EnsembleRecord,
    EnsembleTieBreaker,
    FailurePolicy,
    FeatureMatrix,
    FitResult,
    GMMModelConfig,
    HMMModelConfig,
    ModelState,
    RegimeDetectionResult,
    RegimeEnsembleResult,
    RegimeModelConfig,
    RegimeRecord,
)
from app.modules.regime_detection.infrastructure.ensemble.aggregation import (
    EnsembleAggregator,
)
from app.modules.regime_detection.infrastructure.ensemble.alignment import (
    RegimeAlignmentEngine,
)
from app.modules.regime_detection.infrastructure.ensemble.registry import (
    RegimeModelRegistry,
)
from app.modules.regime_detection.infrastructure.models.ensemble import (
    RegimeModelEnsemble,
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
    "AggregationStrategy",
    "AlignmentPolicy",
    "ClusterProfile",
    "DetectorMetadata",
    "EnsembleAggregator",
    "EnsembleError",
    "EnsembleExecutionError",
    "EnsembleModelConfig",
    "EnsembleModelUnavailableError",
    "EnsembleRecord",
    "EnsembleTieBreaker",
    "FailurePolicy",
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
    "InsufficientUsableModelsError",
    "InvalidEnsembleConfigurationError",
    "InvalidFeatureMatrixError",
    "InvalidGMMConfigurationError",
    "InvalidHMMConfigurationError",
    "InvalidModelConfigurationError",
    "KMeansRegimeDetector",
    "ModelNotFittedError",
    "ModelPredictionError",
    "ModelState",
    "ModelTrainingError",
    "RegimeAlignmentEngine",
    "RegimeAlignmentError",
    "RegimeDetectionError",
    "RegimeDetectionResult",
    "RegimeDetectionService",
    "RegimeDetector",
    "RegimeEnsembleResult",
    "RegimeModelConfig",
    "RegimeModelEnsemble",
    "RegimeModelRegistry",
    "RegimeRecord",
    "UnsupportedPredictionError",
]
