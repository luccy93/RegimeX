"""
RegimeX Regime Detection — Domain Errors
========================================
Defines the domain-specific exception hierarchy for the regime detection module.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, no external or framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class RegimeDetectionError(RegimeXError):
    """Base exception for all regime detection errors."""

    http_status: int = 500
    error_code: str = "REGIME_DETECTION_ERROR"


class ModelNotFittedError(RegimeDetectionError):
    """Raised when inference or prediction is attempted on an unfitted model."""

    http_status: int = 400
    error_code: str = "MODEL_NOT_FITTED"

    def __init__(
        self,
        model_name: str = "RegimeDetector",
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {"model_name": model_name, **(details or {})}
        super().__init__(
            f"Model '{model_name}' has not been fitted. Call fit() before predict().",
            merged,
        )
        self.model_name = model_name


class InvalidModelConfigurationError(RegimeDetectionError):
    """Raised when model hyperparameters or configuration violate domain constraints."""

    http_status: int = 422
    error_code: str = "INVALID_MODEL_CONFIGURATION"


class InsufficientTrainingDataError(RegimeDetectionError):
    """Raised when training data has fewer observations than required for the requested clusters."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_TRAINING_DATA"

    def __init__(
        self,
        required_samples: int,
        available_samples: int,
        requested_clusters: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "required_samples": required_samples,
            "available_samples": available_samples,
            "requested_clusters": requested_clusters,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient training samples for regime model: requires at least {required_samples} "
            f"observations for {requested_clusters} clusters, but got {available_samples}.",
            merged,
        )
        self.required_samples = required_samples
        self.available_samples = available_samples
        self.requested_clusters = requested_clusters


class InvalidFeatureMatrixError(RegimeDetectionError):
    """Raised when input feature matrix fails structural or numerical validation."""

    http_status: int = 422
    error_code: str = "INVALID_FEATURE_MATRIX"


class UnsupportedPredictionError(RegimeDetectionError):
    """Raised when a prediction mode or probability output is not supported by the model."""

    http_status: int = 400
    error_code: str = "UNSUPPORTED_PREDICTION"


class ModelTrainingError(RegimeDetectionError):
    """Raised when an unexpected algorithmic failure occurs during model fitting."""

    http_status: int = 500
    error_code: str = "MODEL_TRAINING_ERROR"


class ModelPredictionError(RegimeDetectionError):
    """Raised when an unexpected algorithmic failure occurs during model inference."""

    http_status: int = 500
    error_code: str = "MODEL_PREDICTION_ERROR"


class InvalidGMMConfigurationError(InvalidModelConfigurationError):
    """Raised when GMM hyperparameters or initialization violate domain constraints."""

    http_status: int = 422
    error_code: str = "INVALID_GMM_CONFIGURATION"


class GMMFitError(ModelTrainingError):
    """Raised when Gaussian Mixture Model fitting fails due to algorithmic or numerical issues."""

    http_status: int = 500
    error_code: str = "GMM_FIT_ERROR"


class GMMConvergenceError(ModelTrainingError):
    """Raised when Gaussian Mixture Model fails to converge within max_iter."""

    http_status: int = 422
    error_code: str = "GMM_CONVERGENCE_ERROR"


class GMMPredictionError(ModelPredictionError):
    """Raised when Gaussian Mixture Model inference or posterior probability estimation fails."""

    http_status: int = 500
    error_code: str = "GMM_PREDICTION_ERROR"


class InvalidHMMConfigurationError(InvalidModelConfigurationError):
    """Raised when HMM hyperparameters or initialization violate domain constraints."""

    http_status: int = 422
    error_code: str = "INVALID_HMM_CONFIGURATION"


class HMMFitError(ModelTrainingError):
    """Raised when Hidden Markov Model fitting fails due to algorithmic or numerical issues."""

    http_status: int = 500
    error_code: str = "HMM_FIT_ERROR"


class HMMConvergenceError(ModelTrainingError):
    """Raised when Hidden Markov Model fails to converge within n_iter."""

    http_status: int = 422
    error_code: str = "HMM_CONVERGENCE_ERROR"


class HMMPredictionError(ModelPredictionError):
    """Raised when Hidden Markov Model inference or posterior probability estimation fails."""

    http_status: int = 500
    error_code: str = "HMM_PREDICTION_ERROR"
