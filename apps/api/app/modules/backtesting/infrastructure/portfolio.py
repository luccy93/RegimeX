"""
RegimeX Backtesting — Simulated Portfolio Accounting
=====================================================
Manages cash balances, position states, fee accumulation, and marked-to-market valuations
with strict conservation and accounting invariants.

Architectural position: ``infrastructure/portfolio.py``
- Pure Python accounting logic.
- Enforces long-only validation and cash sufficiency.
- Deterministic, zero lookahead.
"""

from __future__ import annotations

import math
from datetime import datetime

from app.modules.backtesting.domain.errors import (
    InsufficientFundsError,
    InsufficientPositionError,
    NonFiniteValueError,
)
from app.modules.backtesting.domain.models import (
    EquitySnapshot,
    FillEvent,
    OrderSide,
    Position,
)


class SimulatedPortfolio:
    """
    Portfolio state tracker maintaining cash, positions, realized/unrealized PnL,
    and historical equity snapshots.

    Parameters
    ----------
    initial_cash : float
        Starting capital for the simulation (must be > 0).
    allow_short : bool
        Whether short selling is permitted (default False: strict long-only).
    """

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        allow_short: bool = False,
    ) -> None:
        if math.isnan(initial_cash) or math.isinf(initial_cash) or initial_cash <= 0.0:
            raise NonFiniteValueError(f"initial_cash must be positive and finite: {initial_cash}")

        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.allow_short = allow_short
        self.positions: dict[str, Position] = {}
        self.total_fees = 0.0
        self.realized_pnl = 0.0
        self.fills: list[FillEvent] = []
        self.equity_curve: list[EquitySnapshot] = []

    def get_position(self, symbol: str) -> Position:
        """Retrieve current position for symbol or default zero position."""
        sym = symbol.strip().upper()
        if sym not in self.positions:
            self.positions[sym] = Position(symbol=sym)
        return self.positions[sym]

    def update_market_prices(self, current_prices: dict[str, float]) -> None:
        """
        Update the current market reference prices for all open positions.
        """
        for symbol, price in current_prices.items():
            sym = symbol.strip().upper()
            if sym in self.positions:
                pos = self.positions[sym]
                self.positions[sym] = Position(
                    symbol=sym,
                    quantity=pos.quantity,
                    average_entry_price=pos.average_entry_price,
                    market_price=price,
                    realized_pnl=pos.realized_pnl,
                )

    def apply_fill(self, fill: FillEvent) -> None:
        """
        Process an executed fill event and update cash, position, and fees.

        Parameters
        ----------
        fill : FillEvent
            The executed fill to incorporate.
        """
        sym = fill.symbol.strip().upper()
        pos = self.get_position(sym)

        if fill.side == OrderSide.BUY:
            total_cost = (fill.price * fill.quantity) + fill.commission
            # Check cash sufficiency (with small floating point tolerance)
            if not self.allow_short and (self.cash < total_cost - 1e-9):
                raise InsufficientFundsError(required=total_cost, available=self.cash)

            self.cash -= total_cost
            self.total_fees += fill.commission

            old_qty = pos.quantity
            new_qty = old_qty + fill.quantity
            new_avg_entry = (
                old_qty * pos.average_entry_price + fill.quantity * fill.price
            ) / new_qty

            self.positions[sym] = Position(
                symbol=sym,
                quantity=new_qty,
                average_entry_price=new_avg_entry,
                market_price=fill.price,
                realized_pnl=pos.realized_pnl,
            )

        elif fill.side == OrderSide.SELL:
            # Long-only check
            if not self.allow_short and (pos.quantity < fill.quantity - 1e-9):
                raise InsufficientPositionError(
                    symbol=sym,
                    requested_quantity=fill.quantity,
                    available_quantity=pos.quantity,
                )

            proceeds = (fill.price * fill.quantity) - fill.commission
            self.cash += proceeds
            self.total_fees += fill.commission

            # Calculate gross realized profit/loss
            trade_realized_pnl = (fill.price - pos.average_entry_price) * fill.quantity
            self.realized_pnl += trade_realized_pnl

            new_qty = max(0.0, pos.quantity - fill.quantity)
            new_avg_entry = pos.average_entry_price if new_qty > 1e-9 else 0.0

            self.positions[sym] = Position(
                symbol=sym,
                quantity=new_qty,
                average_entry_price=new_avg_entry,
                market_price=fill.price,
                realized_pnl=pos.realized_pnl + trade_realized_pnl,
            )

        self.fills.append(fill)

    def record_snapshot(
        self,
        timestamp: datetime,
        current_prices: dict[str, float] | None = None,
    ) -> EquitySnapshot:
        """
        Record and return an EquitySnapshot at the given timestamp.
        """
        if current_prices:
            self.update_market_prices(current_prices)

        market_val = sum(pos.market_value for pos in self.positions.values())
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        equity = self.cash + market_val

        snapshot = EquitySnapshot(
            timestamp=timestamp,
            cash=self.cash,
            market_value=market_val,
            equity=equity,
            fees=self.total_fees,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=unrealized,
        )
        self.equity_curve.append(snapshot)
        return snapshot

    @property
    def total_equity(self) -> float:
        """Current total marked-to-market equity."""
        return self.cash + sum(pos.market_value for pos in self.positions.values())
