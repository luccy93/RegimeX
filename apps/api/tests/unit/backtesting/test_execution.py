"""
RegimeX Backtesting — Simulated Execution Tests
===============================================
Tests deterministic order execution, slippage models, and commission calculations.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.backtesting.domain.errors import ExecutionError, NonFiniteValueError
from app.modules.backtesting.domain.models import OrderRequest, OrderSide
from app.modules.backtesting.infrastructure.execution import SimulatedExecutionModel


def _ts() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class TestSimulatedExecutionModel:
    def test_zero_cost_execution(self) -> None:
        model = SimulatedExecutionModel(commission_rate=0.0, slippage_rate=0.0)
        buy_order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.BUY, quantity=10.0)
        fill_buy = model.execute_order(buy_order, market_price=100.0, timestamp=_ts())

        assert fill_buy.price == 100.0
        assert fill_buy.quantity == 10.0
        assert fill_buy.commission == 0.0
        assert fill_buy.slippage == 0.0

        sell_order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.SELL, quantity=5.0)
        fill_sell = model.execute_order(sell_order, market_price=100.0, timestamp=_ts())

        assert fill_sell.price == 100.0
        assert fill_sell.quantity == 5.0
        assert fill_sell.commission == 0.0
        assert fill_sell.slippage == 0.0

    def test_buy_proportional_slippage(self) -> None:
        # Slippage: 1% (0.01)
        model = SimulatedExecutionModel(commission_rate=0.0, slippage_rate=0.01)
        order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.BUY, quantity=100.0)
        fill = model.execute_order(order, market_price=200.0, timestamp=_ts())

        # BUY execution price = 200.0 * 1.01 = 202.0
        assert abs(fill.price - 202.0) < 1e-9
        assert abs(fill.slippage - (2.0 * 100.0)) < 1e-9

    def test_sell_proportional_slippage(self) -> None:
        # Slippage: 0.5% (0.005)
        model = SimulatedExecutionModel(commission_rate=0.0, slippage_rate=0.005)
        order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.SELL, quantity=50.0)
        fill = model.execute_order(order, market_price=100.0, timestamp=_ts())

        # SELL execution price = 100.0 * (1 - 0.005) = 99.50
        assert abs(fill.price - 99.50) < 1e-9
        assert abs(fill.slippage - (0.50 * 50.0)) < 1e-9

    def test_commission_calculation(self) -> None:
        # Commission: 10 bps (0.001)
        model = SimulatedExecutionModel(commission_rate=0.001, slippage_rate=0.0)
        order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.BUY, quantity=100.0)
        fill = model.execute_order(order, market_price=150.0, timestamp=_ts())

        # Trade value = 150.0 * 100 = 15,000. Commission = 15,000 * 0.001 = 15.0
        assert fill.price == 150.0
        assert abs(fill.commission - 15.0) < 1e-9

    def test_combined_slippage_and_commission(self) -> None:
        # Slippage 1% (0.01), Commission 0.1% (0.001)
        model = SimulatedExecutionModel(commission_rate=0.001, slippage_rate=0.01)
        order = OrderRequest(timestamp=_ts(), symbol="TSLA", side=OrderSide.BUY, quantity=10.0)
        fill = model.execute_order(order, market_price=200.0, timestamp=_ts())

        # Exec price = 200 * 1.01 = 202.0
        # Trade value = 202.0 * 10 = 2020.0
        # Commission = 2020.0 * 0.001 = 2.02
        assert abs(fill.price - 202.0) < 1e-9
        assert abs(fill.commission - 2.02) < 1e-9
        assert abs(fill.slippage - 20.0) < 1e-9

    def test_invalid_market_price_rejected(self) -> None:
        model = SimulatedExecutionModel()
        order = OrderRequest(timestamp=_ts(), symbol="AAPL", side=OrderSide.BUY, quantity=10.0)

        with pytest.raises(ExecutionError):
            model.execute_order(order, market_price=0.0, timestamp=_ts())

        with pytest.raises(ExecutionError):
            model.execute_order(order, market_price=-50.0, timestamp=_ts())

        with pytest.raises(NonFiniteValueError):
            model.execute_order(order, market_price=float("nan"), timestamp=_ts())

        with pytest.raises(NonFiniteValueError):
            model.execute_order(order, market_price=float("inf"), timestamp=_ts())

    def test_invalid_model_rates_rejected(self) -> None:
        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(commission_rate=-0.05)

        with pytest.raises(ExecutionError):
            SimulatedExecutionModel(slippage_rate=-0.01)
