"""
RegimeX Regime Transition — Domain Errors
=========================================
Defines the domain-specific exception hierarchy for the regime transition module.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, no external dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class RegimeTransitionError(RegimeXError):
    """Base exception for all regime transition errors."""

    http_status: int = 500
    error_code: str = "REGIME_TRANSITION_ERROR"


class InsufficientTransitionDataError(RegimeTransitionError):
    """Raised when an observation sequence has fewer than 2 items to observe transitions."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_TRANSITION_DATA"

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
            f"Insufficient observations to compute regime transitions: requires at least "
            f"{required_samples} observations, but got {available_samples}.",
            merged,
        )
        self.required_samples = required_samples
        self.available_samples = available_samples


class InvalidTransitionSequenceError(RegimeTransitionError):
    """
    Raised when an observation sequence violates temporal integrity (unsorted, naive, duplicate).
    """

    http_status: int = 422
    error_code: str = "INVALID_TRANSITION_SEQUENCE"


class InvalidRegimeValueError(RegimeTransitionError):
    """
    Raised when an observed regime ID or label violates domain constraints (negative, NaN, inf).
    """

    http_status: int = 422
    error_code: str = "INVALID_REGIME_VALUE"


class RegimeTransitionComputationError(RegimeTransitionError):
    """
    Raised when an unexpected algorithmic or numerical failure occurs during transition analysis.
    """

    http_status: int = 500
    error_code: str = "TRANSITION_COMPUTATION_ERROR"
