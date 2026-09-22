"""
RegimeX Portfolio Risk — Domain Errors
======================================
Defines the domain-specific exception hierarchy for the portfolio risk module.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, no external dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class PortfolioRiskError(RegimeXError):
    """Base exception for all portfolio risk analysis errors."""

    http_status: int = 500
    error_code: str = "PORTFOLIO_RISK_ERROR"


class InsufficientRiskDataError(PortfolioRiskError):
    """Raised when an observation sequence has fewer than the required observations."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_RISK_DATA"

    def __init__(
        self,
        required_samples: int = 2,
        available_samples: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "required_samples": required_samples,
            "available_samples": available_samples,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient observations for risk analysis: requires at least "
            f"{required_samples} observations, but got {available_samples}.",
            merged,
        )
        self.required_samples = required_samples
        self.available_samples = available_samples


class InsufficientTailObservationsError(PortfolioRiskError):
    """Raised when the tail contains zero or insufficient observations for VaR or ES."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_TAIL_OBSERVATIONS"

    def __init__(
        self,
        confidence_level: float,
        required_samples: int,
        available_samples: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "confidence_level": confidence_level,
            "required_samples": required_samples,
            "available_samples": available_samples,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient tail observations at confidence level {confidence_level:.4f}: "
            f"requires at least {required_samples} observations, but got {available_samples}.",
            merged,
        )
        self.confidence_level = confidence_level
        self.required_samples = required_samples
        self.available_samples = available_samples


class InvalidReturnSeriesError(PortfolioRiskError):
    """Raised when a return series contains invalid values, NaN, inf, or is empty."""

    http_status: int = 422
    error_code: str = "INVALID_RETURN_SERIES"


class InvalidPriceSeriesError(PortfolioRiskError):
    """Raised when a price series contains non-positive, non-finite, or empty prices."""

    http_status: int = 422
    error_code: str = "INVALID_PRICE_SERIES"


class InvalidConfidenceLevelError(PortfolioRiskError):
    """Raised when a requested risk confidence level is outside the open interval (0, 1)."""

    http_status: int = 422
    error_code: str = "INVALID_CONFIDENCE_LEVEL"


class NonFiniteValueError(PortfolioRiskError):
    """Raised when NaN, +inf, or -inf is encountered in financial inputs."""

    http_status: int = 422
    error_code: str = "NON_FINITE_VALUE"


class MismatchedWeightsError(PortfolioRiskError):
    """Raised when portfolio weights do not match assets or violate domain constraints."""

    http_status: int = 422
    error_code: str = "MISMATCHED_WEIGHTS"


class MismatchedAssetAlignmentError(PortfolioRiskError):
    """Raised when multi-asset return series cannot be aligned chronologically."""

    http_status: int = 422
    error_code: str = "MISMATCHED_ASSET_ALIGNMENT"


class TemporalOrderError(PortfolioRiskError):
    """Raised when observation timestamps violate chronological ordering or contain duplicates."""

    http_status: int = 422
    error_code: str = "TEMPORAL_ORDER_ERROR"


class RiskComputationError(PortfolioRiskError):
    """Raised when an algorithmic or numerical failure occurs during risk calculation."""

    http_status: int = 500
    error_code: str = "RISK_COMPUTATION_ERROR"
