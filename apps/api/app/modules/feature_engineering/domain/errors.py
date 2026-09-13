"""
RegimeX Feature Engineering — Domain Errors
===========================================
Defines the domain-specific exception hierarchy for the feature engineering module.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, no external or framework dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class FeatureEngineeringError(RegimeXError):
    """Base exception for all feature engineering errors."""

    http_status: int = 500
    error_code: str = "FEATURE_ENGINEERING_ERROR"


class FeatureNotFoundError(FeatureEngineeringError):
    """Raised when a requested feature is not registered in the feature registry."""

    http_status: int = 404
    error_code: str = "FEATURE_NOT_FOUND"

    def __init__(self, feature_name: str, details: dict[str, Any] | None = None) -> None:
        merged = {"feature_name": feature_name, **(details or {})}
        super().__init__(f"Feature '{feature_name}' not found in registry.", merged)
        self.feature_name = feature_name


class DuplicateFeatureError(FeatureEngineeringError):
    """Raised when registering a feature whose identifier is already registered."""

    http_status: int = 409
    error_code: str = "DUPLICATE_FEATURE"

    def __init__(self, feature_name: str, details: dict[str, Any] | None = None) -> None:
        merged = {"feature_name": feature_name, **(details or {})}
        super().__init__(
            f"Feature '{feature_name}' is already registered in the feature registry.",
            merged,
        )
        self.feature_name = feature_name


class InsufficientDataError(FeatureEngineeringError):
    """Raised when input observations are fewer than the minimum lookback required."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_DATA"

    def __init__(
        self,
        required: int,
        provided: int,
        feature_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "required_observations": required,
            "provided_observations": provided,
            "feature_name": feature_name,
            **(details or {}),
        }
        feat_str = f" for feature '{feature_name}'" if feature_name else ""
        super().__init__(
            f"Insufficient data observations{feat_str}: "
            f"required at least {required}, got {provided}.",
            merged,
        )
        self.required = required
        self.provided = provided
        self.feature_name = feature_name


class InvalidFeatureInputError(FeatureEngineeringError):
    """Raised when input data fails structural validation (empty, unsorted, naive timestamps)."""

    http_status: int = 422
    error_code: str = "INVALID_FEATURE_INPUT"


class FeatureCalculationError(FeatureEngineeringError):
    """Raised when an unexpected error occurs during numerical feature calculation."""

    http_status: int = 500
    error_code: str = "FEATURE_CALCULATION_ERROR"


class LookaheadBiasError(FeatureEngineeringError):
    """Raised when a calculation or pipeline step violates point-in-time constraints."""

    http_status: int = 500
    error_code: str = "LOOKAHEAD_BIAS_VIOLATION"
