"""
RegimeX Backtesting — Simulated Order Execution
===============================================
Implements deterministic historical order execution incorporating proportional slippage
and commission transaction costs.

Architectural position: ``infrastructure/execution.py``
- Implements ``ExecutionModelProtocol``.
- Pure Python calculation, deterministic and zero lookahead.
"""

from __future__ import annotations

import math
from datetime import datetime

from app.modules.backtesting.domain.errors import ExecutionError, NonFiniteValueError
from app.modules.backtesting.domain.interfaces import ExecutionModelProtocol
from app.modules.backtesting.domain.models import FillEvent, OrderRequest, OrderSide


class SimulatedExecutionModel(ExecutionModelProtocol):
    """
    Deterministic simulated execution model with proportional slippage and commission rates.

    Parameters
    ----------
    commission_rate : float
        Proportional fee charged on executed trade value (e.g., 0.001 = 10 bps). Default is 0.0.
    slippage_rate : float
        Proportional price degradation applied to the execution price (e.g., 0.0005 = 5 bps).
        Default is 0.0.
    """

    def __init__(
        self,
        commission_rate: float = 0.0,
        slippage_rate: float = 0.0,
    ) -> None:
        if math.isnan(commission_rate) or math.isinf(commission_rate) or commission_rate < 0.0:
            raise ExecutionError(
                f"commission_rate must be non-negative and finite: {commission_rate}"
            )
        if math.isnan(slippage_rate) or math.isinf(slippage_rate) or slippage_rate < 0.0:
            raise ExecutionError(f"slippage_rate must be non-negative and finite: {slippage_rate}")

        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def execute_order(
        self,
        order: OrderRequest,
        market_price: float,
        timestamp: datetime,
    ) -> FillEvent:
        """
        Execute an order given the prevailing market price and return a FillEvent.

        Slippage Convention:
        - BUY: execution_price = market_price * (1 + slippage_rate)
        - SELL: execution_price = market_price * (1 - slippage_rate)

        Commission Convention:
        - commission = execution_price * quantity * commission_rate

        Parameters
        ----------
        order : OrderRequest
            The order request to execute.
        market_price : float
            Prevailing market reference price (must be > 0).
        timestamp : datetime
            UTC execution timestamp.

        Returns
        -------
        FillEvent
            The filled execution record.
        """
        if math.isnan(market_price) or math.isinf(market_price):
            raise NonFiniteValueError(f"market_price is non-finite: {market_price}")
        if market_price <= 0.0:
            raise ExecutionError(f"market_price must be strictly positive: {market_price}")

        qty = order.quantity
        if qty <= 0.0:
            raise ExecutionError(f"order quantity must be strictly positive: {qty}")

        if order.side == OrderSide.BUY:
            fill_price = market_price * (1.0 + self.slippage_rate)
            unit_slippage = fill_price - market_price
        else:
            fill_price = market_price * (1.0 - self.slippage_rate)
            unit_slippage = market_price - fill_price

        total_slippage = unit_slippage * qty
        trade_value = fill_price * qty
        commission = trade_value * self.commission_rate

        return FillEvent(
            order_id=order.order_id,
            timestamp=timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=qty,
            price=fill_price,
            commission=commission,
            slippage=total_slippage,
        )
