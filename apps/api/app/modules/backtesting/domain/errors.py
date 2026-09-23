"""
RegimeX Backtesting — Domain Errors
===================================
Defines the domain-specific exception hierarchy for event-driven backtesting.

All errors inherit from ``RegimeXError`` for standard error serialization and status mapping.
Architectural position: ``domain/errors.py`` — pure Python, no external dependencies.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import RegimeXError


class BacktestingError(RegimeXError):
    """Base exception for all backtesting errors."""

    http_status: int = 500
    error_code: str = "BACKTESTING_ERROR"


class InvalidEventError(BacktestingError):
    """Raised when an event has invalid attributes or fails validation."""

    http_status: int = 422
    error_code: str = "INVALID_EVENT"


class InvalidOrderError(BacktestingError):
    """Raised when an order request is malformed (e.g. non-positive quantity, unknown symbol)."""

    http_status: int = 422
    error_code: str = "INVALID_ORDER"


class InsufficientFundsError(BacktestingError):
    """Raised when cash balance is insufficient to execute a purchase."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_FUNDS"

    def __init__(
        self,
        required: float,
        available: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "required_cash": required,
            "available_cash": available,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient cash for order execution: requires {required:.4f}, "
            f"but available cash is {available:.4f}.",
            merged,
        )
        self.required = required
        self.available = available


class InsufficientPositionError(BacktestingError):
    """Raised when attempting to sell more shares than currently held in long-only mode."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_POSITION"

    def __init__(
        self,
        symbol: str,
        requested_quantity: float,
        available_quantity: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged = {
            "symbol": symbol,
            "requested_quantity": requested_quantity,
            "available_quantity": available_quantity,
            **(details or {}),
        }
        super().__init__(
            f"Insufficient position in {symbol}: requested sell quantity {requested_quantity}, "
            f"but currently held quantity is {available_quantity}.",
            merged,
        )
        self.symbol = symbol
        self.requested_quantity = requested_quantity
        self.available_quantity = available_quantity


class InvalidMarketDataError(BacktestingError):
    """Raised when historical market data is empty, non-positive, unsorted, or invalid."""

    http_status: int = 422
    error_code: str = "INVALID_MARKET_DATA"


class LookaheadBiasError(BacktestingError):
    """Raised when a strategy or component attempts to access future or unobserved information."""

    http_status: int = 400
    error_code: str = "LOOKAHEAD_BIAS_VIOLATION"


class ExecutionError(BacktestingError):
    """Raised when an error occurs during order execution or fill processing."""

    http_status: int = 500
    error_code: str = "EXECUTION_ERROR"


class TemporalOrderError(BacktestingError):
    """Raised when timestamps are naive, non-UTC, out of order, or regressing in time."""

    http_status: int = 422
    error_code: str = "TEMPORAL_ORDER_ERROR"


class NonFiniteValueError(BacktestingError):
    """Raised when non-finite values (NaN, +inf, -inf) are encountered."""

    http_status: int = 422
    error_code: str = "NON_FINITE_VALUE"


class ComparisonError(BacktestingError):
    """Base exception for all strategy comparison errors."""

    http_status: int = 422
    error_code: str = "COMPARISON_ERROR"


class EmptyComparisonError(ComparisonError):
    """Raised when a comparison is attempted with an empty collection of strategies."""

    http_status: int = 422
    error_code: str = "EMPTY_COMPARISON"


class DuplicateStrategyIdError(ComparisonError):
    """Raised when multiple strategies in a comparison share an identical identifier."""

    http_status: int = 422
    error_code: str = "DUPLICATE_STRATEGY_ID"


class InvalidStrategyIdError(ComparisonError):
    """Raised when a strategy identifier is empty, whitespace-only, or invalid."""

    http_status: int = 422
    error_code: str = "INVALID_STRATEGY_ID"


class IncompatibleEvaluationPeriodError(ComparisonError):
    """Raised when strategies have non-overlapping or incompatible evaluation time periods."""

    http_status: int = 422
    error_code: str = "INCOMPATIBLE_EVALUATION_PERIOD"


class InvalidEquityError(ComparisonError):
    """Raised when initial equity is non-positive or non-finite."""

    http_status: int = 422
    error_code: str = "INVALID_EQUITY"


class InsufficientComparisonDataError(ComparisonError):
    """Raised when a strategy's equity series has insufficient observations in the common period."""

    http_status: int = 422
    error_code: str = "INSUFFICIENT_COMPARISON_DATA"
