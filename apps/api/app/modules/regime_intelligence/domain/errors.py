"""
RegimeX Regime Intelligence — Domain Errors
===========================================
Defines the domain-specific exception hierarchy for the regime intelligence module.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, zero framework or external dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class RegimeIntelligenceError(RegimeXError):
    """Base exception for all regime intelligence domain errors."""

    http_status: int = 500
    error_code: str = "REGIME_INTELLIGENCE_ERROR"


class InvalidRegimeAssignmentError(RegimeIntelligenceError):
    """Raised when a regime assignment observation contains invalid or malformed data."""

    http_status: int = 422
    error_code: str = "INVALID_REGIME_ASSIGNMENT"


class InvalidRegimeHistoryError(RegimeIntelligenceError):
    """
    Raised when regime history violates temporal integrity.

    Examples:
    - Timestamps are not strictly monotonically increasing.
    - Duplicate timestamps are present.
    - Naive (non-UTC) timestamps are provided.
    """

    http_status: int = 422
    error_code: str = "INVALID_REGIME_HISTORY"


class InsufficientRegimeDataError(RegimeIntelligenceError):
    """
    Raised when an intelligence calculation requires a non-empty history
    or minimum number of observations, but insufficient data was provided.
    """

    http_status: int = 422
    error_code: str = "INSUFFICIENT_REGIME_DATA"

    def __init__(
        self,
        required_samples: int,
        available_samples: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "required_samples": required_samples,
            "available_samples": available_samples,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient observations for regime intelligence: required {required_samples}, "
            f"got {available_samples}.",
            merged,
        )
        self.required_samples = required_samples
        self.available_samples = available_samples


class UnsupportedRankingMetricError(RegimeIntelligenceError):
    """Raised when an unrecognized ranking metric is requested."""

    http_status: int = 400
    error_code: str = "UNSUPPORTED_RANKING_METRIC"

    def __init__(
        self,
        metric: str,
        supported_metrics: tuple[str, ...],
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "requested_metric": metric,
            "supported_metrics": list(supported_metrics),
            **(details or {}),
        }
        super().__init__(
            f"Unsupported ranking metric '{metric}'. Supported metrics: {supported_metrics}.",
            merged,
        )
        self.metric = metric
        self.supported_metrics = supported_metrics


class InvalidFeatureStatisticsError(RegimeIntelligenceError):
    """Raised when descriptive feature statistics calculation fails due to inconsistent shapes."""

    http_status: int = 422
    error_code: str = "INVALID_FEATURE_STATISTICS"
