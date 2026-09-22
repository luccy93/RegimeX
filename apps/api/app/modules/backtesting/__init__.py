"""
RegimeX Backtesting Module
==========================
Event-driven backtesting engine with point-in-time sequential simulation,
realistic transaction costs (slippage and commissions), portfolio accounting,
and seamless integration with the V13 Portfolio Risk Engine.
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
from app.modules.backtesting.infrastructure.engine import (
    EventDrivenBacktestEngine,
    StrategyContextImpl,
)
from app.modules.backtesting.infrastructure.execution import SimulatedExecutionModel
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio

__all__ = [
    "BacktestConfig",
    "BacktestEngineProtocol",
    "BacktestResult",
    "BacktestingError",
    "EquitySnapshot",
    "EventType",
    "EventDrivenBacktestEngine",
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
    "SimulatedExecutionModel",
    "SimulatedPortfolio",
    "Strategy",
    "StrategyContext",
    "StrategyContextImpl",
    "TemporalOrderError",
]
