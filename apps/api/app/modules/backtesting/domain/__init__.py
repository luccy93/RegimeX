"""
RegimeX Backtesting — Domain Layer Exports
==========================================
"""

from app.modules.backtesting.domain.errors import (
    BacktestingError,
    ExecutionError,
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidEventError,
    InvalidMarketDataError,
    InvalidOrderError,
    LookaheadBiasError,
    NonFiniteValueError,
    TemporalOrderError,
)
from app.modules.backtesting.domain.interfaces import (
    BacktestEngineProtocol,
    ExecutionModelProtocol,
    Strategy,
    StrategyContext,
)
from app.modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestResult,
    EquitySnapshot,
    EventType,
    ExecutionPriceConvention,
    FillEvent,
    MarketEvent,
    OrderRequest,
    OrderSide,
    OrderType,
    Position,
    SignalEvent,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngineProtocol",
    "BacktestResult",
    "BacktestingError",
    "EquitySnapshot",
    "EventType",
    "ExecutionError",
    "ExecutionModelProtocol",
    "ExecutionPriceConvention",
    "FillEvent",
    "InsufficientFundsError",
    "InsufficientPositionError",
    "InvalidEventError",
    "InvalidMarketDataError",
    "InvalidOrderError",
    "LookaheadBiasError",
    "MarketEvent",
    "NonFiniteValueError",
    "OrderRequest",
    "OrderSide",
    "OrderType",
    "Position",
    "SignalEvent",
    "Strategy",
    "StrategyContext",
    "TemporalOrderError",
]
