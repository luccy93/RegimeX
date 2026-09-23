"""
RegimeX Backtesting — Infrastructure Layer Exports
==================================================
"""

from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.backtesting.infrastructure.engine import (
    EventDrivenBacktestEngine,
    StrategyContextImpl,
)
from app.modules.backtesting.infrastructure.execution import SimulatedExecutionModel
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio
from app.modules.backtesting.infrastructure.reporting import (
    DEFAULT_LIMITATIONS,
    DEFAULT_METHODOLOGY,
    DEFAULT_METRIC_DEFINITIONS,
    PerformanceReportBuilder,
)

__all__ = [
    "DEFAULT_LIMITATIONS",
    "DEFAULT_METHODOLOGY",
    "DEFAULT_METRIC_DEFINITIONS",
    "EventDrivenBacktestEngine",
    "PerformanceReportBuilder",
    "SimulatedExecutionModel",
    "SimulatedPortfolio",
    "StrategyComparisonEngine",
    "StrategyContextImpl",
]
