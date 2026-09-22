"""
RegimeX Backtesting — Event-Driven Backtesting Engine
=====================================================
Orchestrates sequential simulation of market events, strategy decisions, order execution,
and portfolio accounting with zero lookahead bias and strict determinism.

Architectural position: ``infrastructure/engine.py``
- Implements ``BacktestEngineProtocol``.
- Pure Python calculation, deterministic, no network/broker/DB dependencies.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta

from app.modules.backtesting.domain.errors import (
    InvalidMarketDataError,
    InvalidOrderError,
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
    ExecutionPriceConvention,
    FillEvent,
    MarketEvent,
    OrderRequest,
    Position,
)
from app.modules.backtesting.infrastructure.execution import SimulatedExecutionModel
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio


class StrategyContextImpl(StrategyContext):
    """
    Concrete implementation of StrategyContext providing a restricted historical view.
    """

    def __init__(
        self,
        current_timestamp: datetime,
        current_prices: dict[str, float],
        positions: dict[str, Position],
        cash: float,
        equity: float,
        history: dict[str, list[MarketEvent]],
        current_regime: int | None = None,
        regime_history: list[int] | None = None,
    ) -> None:
        self._current_timestamp = current_timestamp
        self._current_prices = dict(current_prices)
        self._positions = dict(positions)
        self._cash = cash
        self._equity = equity
        self._history = history
        self._current_regime = current_regime
        self._regime_history = tuple(regime_history) if regime_history is not None else ()

    @property
    def current_timestamp(self) -> datetime:
        return self._current_timestamp

    @property
    def current_prices(self) -> dict[str, float]:
        return dict(self._current_prices)

    @property
    def current_positions(self) -> dict[str, Position]:
        return dict(self._positions)

    @property
    def available_cash(self) -> float:
        return self._cash

    @property
    def portfolio_equity(self) -> float:
        return self._equity

    @property
    def current_regime(self) -> int | None:
        return self._current_regime

    def get_history(self, symbol: str, count: int | None = None) -> tuple[MarketEvent, ...]:
        sym = symbol.strip().upper()
        bars = self._history.get(sym, [])
        if count is None or count >= len(bars):
            return tuple(bars)
        if count <= 0:
            return ()
        return tuple(bars[-count:])

    def get_regime_history(self, count: int | None = None) -> tuple[int, ...]:
        if count is None or count >= len(self._regime_history):
            return self._regime_history
        if count <= 0:
            return ()
        return self._regime_history[-count:]


class EventDrivenBacktestEngine(BacktestEngineProtocol):
    """
    Event-driven historical backtesting engine.

    Guarantees:
    - Point-in-time chronological simulation (no lookahead bias).
    - Sequential delivery of market events.
    - Deterministic order execution and portfolio reconciliation.
    """

    def __init__(
        self,
        config: BacktestConfig | None = None,
        execution_model: ExecutionModelProtocol | None = None,
    ) -> None:
        self.config = config or BacktestConfig()
        self.execution_model = execution_model or SimulatedExecutionModel(
            commission_rate=self.config.commission_rate,
            slippage_rate=self.config.slippage_rate,
        )

    def _normalize_and_validate_events(
        self,
        market_data: list[MarketEvent] | dict[str, list[MarketEvent]],
    ) -> list[MarketEvent]:
        """
        Validate and sort market events chronologically.
        """
        raw_events: list[MarketEvent] = []
        if isinstance(market_data, dict):
            for events_list in market_data.values():
                raw_events.extend(events_list)
        elif isinstance(market_data, list):
            raw_events.extend(market_data)
        else:
            raise InvalidMarketDataError("market_data must be a list or dict of MarketEvent items.")

        if not raw_events:
            raise InvalidMarketDataError("market_data cannot be empty.")

        # Sort with deterministic tie-breaking (timestamp ascending, symbol ascending)
        sorted_events = sorted(raw_events, key=lambda e: (e.timestamp, e.symbol))

        # Validate strictly increasing timestamps per symbol & check non-finite/non-positive
        symbol_last_ts: dict[str, datetime] = {}
        for idx, event in enumerate(sorted_events):
            ts = event.timestamp
            if ts.tzinfo is None or ts.utcoffset() != timedelta(0):
                raise TemporalOrderError(
                    f"MarketEvent at index {idx} ({event.symbol}) has non-UTC timestamp: {ts!r}."
                )

            sym = event.symbol.strip().upper()
            if sym in symbol_last_ts:
                prev_ts = symbol_last_ts[sym]
                if ts <= prev_ts:
                    raise TemporalOrderError(
                        f"Duplicate or decreasing timestamp detected for {sym}: "
                        f"{ts.isoformat()} <= {prev_ts.isoformat()}."
                    )
            symbol_last_ts[sym] = ts

            for p_name, p_val in [
                ("open", event.open),
                ("high", event.high),
                ("low", event.low),
                ("close", event.close),
            ]:
                if math.isnan(p_val) or math.isinf(p_val):
                    raise NonFiniteValueError(f"{p_name} is non-finite for {sym}: {p_val}")
                if p_val <= 0.0:
                    raise InvalidMarketDataError(f"{p_name} must be strictly positive: {p_val}")

            if math.isnan(event.volume) or math.isinf(event.volume) or event.volume < 0.0:
                raise InvalidMarketDataError(f"volume is invalid for {sym}: {event.volume}")

        return sorted_events

    def run(
        self,
        market_data: list[MarketEvent] | dict[str, list[MarketEvent]],
        strategy: Strategy,
        regimes: list[int] | None = None,
    ) -> BacktestResult:
        """
        Execute an event-driven backtest simulation.

        Parameters
        ----------
        market_data : list[MarketEvent] | dict[str, list[MarketEvent]]
            Chronological market data to simulate.
        strategy : Strategy
            The strategy instance implementing the Strategy protocol.
        regimes : list[int] | None
            Optional sequence of historical regime states aligned with simulation steps.

        Returns
        -------
        BacktestResult
            Comprehensive immutable simulation result.
        """
        events = self._normalize_and_validate_events(market_data)

        if regimes is not None and len(regimes) != len(events):
            raise InvalidMarketDataError(
                f"Regimes sequence length ({len(regimes)}) must match "
                f"market events count ({len(events)})."
            )

        portfolio = SimulatedPortfolio(
            initial_cash=self.config.initial_cash,
            allow_short=self.config.allow_short,
        )

        all_orders: list[OrderRequest] = []
        all_fills: list[FillEvent] = []
        history_by_symbol: dict[str, list[MarketEvent]] = defaultdict(list)
        current_prices: dict[str, float] = {}
        observed_regimes: list[int] = []

        pending_orders: list[tuple[OrderRequest, datetime]] = []

        for step_idx, event in enumerate(events):
            sym = event.symbol.strip().upper()
            step_ts = event.timestamp

            # Update historical context up to step_idx (point-in-time)
            history_by_symbol[sym].append(event)
            current_prices[sym] = event.close

            current_regime = regimes[step_idx] if regimes is not None else None
            if current_regime is not None:
                observed_regimes.append(current_regime)

            # 1. If NEXT_OPEN convention, execute any pending orders from previous bar
            if self.config.execution_convention == ExecutionPriceConvention.NEXT_OPEN:
                next_pending: list[tuple[OrderRequest, datetime]] = []
                for pending_order, order_ts in pending_orders:
                    if pending_order.symbol == sym:
                        fill = self.execution_model.execute_order(
                            order=pending_order,
                            market_price=event.open,
                            timestamp=step_ts,
                        )
                        portfolio.apply_fill(fill)
                        all_fills.append(fill)
                    else:
                        next_pending.append((pending_order, order_ts))
                pending_orders = next_pending

            # 2. Build isolated strategy context
            context = StrategyContextImpl(
                current_timestamp=step_ts,
                current_prices=current_prices,
                positions=portfolio.positions,
                cash=portfolio.cash,
                equity=portfolio.total_equity,
                history=history_by_symbol,
                current_regime=current_regime,
                regime_history=observed_regimes,
            )

            # 3. Strategy decision
            orders = strategy.on_market_event(event, context)
            if orders:
                for order in orders:
                    if not isinstance(order, OrderRequest):
                        raise InvalidOrderError(
                            f"Expected OrderRequest, got {type(order)}: {order!r}"
                        )
                    if (
                        order.quantity <= 0.0
                        or math.isnan(order.quantity)
                        or math.isinf(order.quantity)
                    ):
                        raise InvalidOrderError(f"Invalid order quantity: {order.quantity}")
                    if order.symbol != sym and order.symbol not in current_prices:
                        raise InvalidOrderError(
                            f"Order symbol {order.symbol} has not been observed in market data."
                        )

                    all_orders.append(order)

                    if self.config.execution_convention == ExecutionPriceConvention.CURRENT_CLOSE:
                        ref_price = current_prices.get(order.symbol, event.close)
                        fill = self.execution_model.execute_order(
                            order=order,
                            market_price=ref_price,
                            timestamp=step_ts,
                        )
                        portfolio.apply_fill(fill)
                        all_fills.append(fill)
                    else:
                        pending_orders.append((order, step_ts))

            # 4. Record chronological equity snapshot if last event for this timestamp
            is_last_for_timestamp = (
                step_idx == len(events) - 1 or events[step_idx + 1].timestamp != step_ts
            )
            if is_last_for_timestamp:
                portfolio.record_snapshot(timestamp=step_ts, current_prices=current_prices)

        return BacktestResult(
            start_timestamp=events[0].timestamp,
            end_timestamp=events[-1].timestamp,
            initial_cash=self.config.initial_cash,
            final_cash=portfolio.cash,
            final_equity=portfolio.total_equity,
            orders=tuple(all_orders),
            fills=tuple(all_fills),
            positions=dict(portfolio.positions),
            equity_curve=tuple(portfolio.equity_curve),
            total_fees=portfolio.total_fees,
            trade_count=len(all_fills),
            metadata={
                "event_count": len(events),
                "execution_convention": str(self.config.execution_convention),
                "commission_rate": self.config.commission_rate,
                "slippage_rate": self.config.slippage_rate,
            },
        )
