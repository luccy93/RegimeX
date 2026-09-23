"""
RegimeX Backtesting — Domain Protocols & Interfaces
===================================================
Defines the structural interfaces for strategies, execution models, and backtesting engines.

Architectural position: ``domain/interfaces.py``
- Pure typing and protocols.
- Zero infrastructure dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.modules.backtesting.domain.models import (
    BacktestResult,
    FillEvent,
    MarketEvent,
    OrderRequest,
    PerformanceReport,
    Position,
    StrategyComparisonInput,
    StrategyComparisonResult,
)

if TYPE_CHECKING:
    from app.modules.portfolio_risk.domain.interfaces import PortfolioRiskEngineProtocol


class StrategyContext(Protocol):
    """
    Restricted contextual view exposed to strategies at each simulation step.

    Strict Anti-Lookahead Guarantee:
    - Only historical observations up to the current timestamp are accessible.
    - Future prices, future events, or future portfolio states are strictly inaccessible.
    """

    @property
    def current_timestamp(self) -> datetime:
        """UTC timestamp of the current simulation step."""
        ...

    @property
    def current_prices(self) -> dict[str, float]:
        """Dictionary of latest known prices for symbols observed up to current step."""
        ...

    @property
    def current_positions(self) -> dict[str, Position]:
        """Read-only copy of current open portfolio positions."""
        ...

    @property
    def available_cash(self) -> float:
        """Current unallocated cash in the portfolio."""
        ...

    @property
    def portfolio_equity(self) -> float:
        """Total marked-to-market portfolio equity at the current step."""
        ...

    @property
    def current_regime(self) -> int | None:
        """Current regime identifier if a regime sequence was provided, else None."""
        ...

    def get_history(self, symbol: str, count: int | None = None) -> tuple[MarketEvent, ...]:
        """
        Retrieve historical MarketEvents observed strictly up to the current step.

        Parameters
        ----------
        symbol : str
            Instrument symbol identifier.
        count : int | None
            Maximum number of trailing observations to return (returns all past if None).
        """
        ...

    def get_regime_history(self, count: int | None = None) -> tuple[int, ...]:
        """
        Retrieve historical regime states observed strictly up to the current step.
        """
        ...


class Strategy(Protocol):
    """
    Protocol defining the strategy decision contract.
    """

    def on_market_event(
        self,
        event: MarketEvent,
        context: StrategyContext,
    ) -> list[OrderRequest]:
        """
        Process an incoming market observation and emit zero or more order requests.

        Parameters
        ----------
        event : MarketEvent
            The market observation at the current simulation step.
        context : StrategyContext
            Restricted historical context (prices, positions, cash, past bars).

        Returns
        -------
        list[OrderRequest]
            Zero or more orders to be placed for historical execution.
        """
        ...


class ExecutionModelProtocol(Protocol):
    """
    Protocol for historical order execution models.
    """

    def execute_order(
        self,
        order: OrderRequest,
        market_price: float,
        timestamp: datetime,
    ) -> FillEvent:
        """
        Execute an order given the prevailing market price and return a FillEvent.
        """
        ...


class BacktestEngineProtocol(Protocol):
    """
    Protocol for the event-driven backtesting execution engine.
    """

    def run(
        self,
        market_data: list[MarketEvent] | dict[str, list[MarketEvent]],
        strategy: Strategy,
        regimes: list[int] | None = None,
    ) -> BacktestResult:
        """
        Execute an end-to-end backtest of the strategy over historical market observations.
        """
        ...


class StrategyComparisonEngineProtocol(Protocol):
    """
    Protocol for comparing multiple backtest strategy results.
    """

    def compare(
        self,
        inputs: Sequence[StrategyComparisonInput],
        periods_per_year: float | None = None,
        risk_engine: PortfolioRiskEngineProtocol | None = None,
    ) -> StrategyComparisonResult:
        """
        Compare two or more strategy backtest results across a common evaluation period.

        Parameters
        ----------
        inputs : Sequence[StrategyComparisonInput]
            Validated sequence of strategy comparison inputs.
        periods_per_year : float | None
            Annualization factor for volatility and return calculations.
        risk_engine : PortfolioRiskEngineProtocol | None
            Optional explicit risk engine instance conforming to V13 protocol.

        Returns
        -------
        StrategyComparisonResult
            Immutable, deterministic strategy comparison result.
        """
        ...


class PerformanceReportBuilderProtocol(Protocol):
    """
    Protocol for generating structured performance reports from strategy comparisons.
    """

    def build(
        self,
        comparison_result: StrategyComparisonResult,
        generated_at: datetime | None = None,
        report_id: str | None = None,
    ) -> PerformanceReport:
        """
        Construct an immutable performance report from a completed strategy comparison result.

        Parameters
        ----------
        comparison_result : StrategyComparisonResult
            The completed, validated strategy comparison analytics result.
        generated_at : datetime | None
            Optional explicit generation timestamp for deterministic reporting.
        report_id : str | None
            Optional explicit report identifier.

        Returns
        -------
        PerformanceReport
            Self-contained, immutable performance report.
        """
        ...
