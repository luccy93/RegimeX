"""
RegimeX Backtesting — Transaction Cost & Slippage Reconciliation Tests
=====================================================================
Validates slippage monotonicity, commission calculations, and exact portfolio cash reconciliation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.backtesting.domain.errors import ExecutionError
from app.modules.backtesting.domain.models import (
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.execution import SimulatedExecutionModel
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio


def _ts() -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)


class TestSlippageAndCommission:
    def test_slippage_monotonicity(self) -> None:
        rates = [0.0, 0.001, 0.005, 0.01, 0.05]
        ref_price = 100.0
        qty = 10.0

        buy_order = OrderRequest(timestamp=_ts(), symbol="SLIP", side=OrderSide.BUY, quantity=qty)
        sell_order = OrderRequest(timestamp=_ts(), symbol="SLIP", side=OrderSide.SELL, quantity=qty)

        prev_buy_price = 0.0
        prev_sell_price = 999999.0

        for rate in rates:
            model = SimulatedExecutionModel(slippage_rate=rate, commission_rate=0.0)
            fill_buy = model.execute_order(buy_order, market_price=ref_price, timestamp=_ts())
            fill_sell = model.execute_order(sell_order, market_price=ref_price, timestamp=_ts())

            # BUY prices must be strictly increasing with slippage rate
            assert fill_buy.price >= prev_buy_price
            prev_buy_price = fill_buy.price

            # SELL prices must be strictly decreasing with slippage rate
            assert fill_sell.price <= prev_sell_price
            prev_sell_price = fill_sell.price

    def test_commission_scaling(self) -> None:
        exec_model = SimulatedExecutionModel(commission_rate=0.002, slippage_rate=0.0)
        order = OrderRequest(timestamp=_ts(), symbol="COMM", side=OrderSide.BUY, quantity=50.0)
        fill = exec_model.execute_order(order, market_price=100.0, timestamp=_ts())

        # Trade value = 100.0 * 50 = 5000. Commission = 5000 * 0.002 = 10.0
        assert fill.price == 100.0
        assert abs(fill.commission - 10.0) < 1e-9

    def test_invalid_costs_rejected(self) -> None:
        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(commission_rate=-0.01)
        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(slippage_rate=-0.001)
        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(commission_rate=float("nan"))
        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(slippage_rate=float("inf"))

    def test_transaction_cost_cash_reconciliation(self) -> None:
        """
        Prove that for every fill:
        gross trade value + slippage impact + commission = total portfolio cash delta.
        """
        initial_cash = 100_000.0
        portfolio = SimulatedPortfolio(initial_cash=initial_cash)
        model = SimulatedExecutionModel(commission_rate=0.001, slippage_rate=0.01)

        # 1. BUY: Market price 100.0, 100 shares
        buy_order = OrderRequest(
            timestamp=_ts(), symbol="RECON", side=OrderSide.BUY, quantity=100.0
        )
        fill_buy = model.execute_order(buy_order, market_price=100.0, timestamp=_ts())
        cash_before_buy = portfolio.cash
        portfolio.apply_fill(fill_buy)
        cash_after_buy = portfolio.cash

        # Fill price = 100.0 * 1.01 = 101.0
        # Slippage cost = (101.0 - 100.0) * 100 = 100.0
        # Commission = 101.0 * 100 * 0.001 = 10.10
        # Gross market value = 100.0 * 100 = 10,000.0
        # Total cash spent = 10,000 + 100 + 10.10 = 10,110.10
        cash_spent = cash_before_buy - cash_after_buy
        reconciled_spent = (100.0 * 100.0) + fill_buy.slippage + fill_buy.commission
        assert abs(cash_spent - reconciled_spent) < 1e-9
        assert abs(cash_spent - 10_110.10) < 1e-9

        # 2. SELL: Market price 150.0, 50 shares
        sell_order = OrderRequest(
            timestamp=_ts(), symbol="RECON", side=OrderSide.SELL, quantity=50.0
        )
        fill_sell = model.execute_order(sell_order, market_price=150.0, timestamp=_ts())
        cash_before_sell = portfolio.cash
        portfolio.apply_fill(fill_sell)
        cash_after_sell = portfolio.cash

        # Fill price = 150.0 * (1 - 0.01) = 148.50
        # Slippage cost = (150.0 - 148.50) * 50 = 75.0
        # Commission = 148.50 * 50 * 0.001 = 7.425
        # Gross value = 150.0 * 50 = 7500.0
        # Net proceeds = 7500.0 - 75.0 - 7.425 = 7417.575
        cash_received = cash_after_sell - cash_before_sell
        reconciled_received = (150.0 * 50.0) - fill_sell.slippage - fill_sell.commission
        assert abs(cash_received - reconciled_received) < 1e-9
        assert abs(cash_received - 7417.575) < 1e-9

        # Total fees in portfolio must match sum of commissions
        assert abs(portfolio.total_fees - (fill_buy.commission + fill_sell.commission)) < 1e-9
