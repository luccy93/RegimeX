"""
RegimeX Backtesting — Simulated Portfolio Accounting Tests
==========================================================
Tests cash movements, position accounting, partial/full fills, and reconciliation invariants.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.backtesting.domain.errors import (
    InsufficientFundsError,
    InsufficientPositionError,
    NonFiniteValueError,
)
from app.modules.backtesting.domain.models import FillEvent, OrderSide
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio


def _ts() -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)


class TestSimulatedPortfolio:
    def test_initial_state(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=50_000.0)
        assert portfolio.cash == 50_000.0
        assert portfolio.total_equity == 50_000.0
        assert len(portfolio.positions) == 0
        assert portfolio.total_fees == 0.0
        assert portfolio.realized_pnl == 0.0

    def test_invalid_initial_cash(self) -> None:
        with pytest.raises(NonFiniteValueError):
            SimulatedPortfolio(initial_cash=-1000.0)
        with pytest.raises(NonFiniteValueError):
            SimulatedPortfolio(initial_cash=0.0)
        with pytest.raises(NonFiniteValueError):
            SimulatedPortfolio(initial_cash=float("nan"))

    def test_buy_fill_accounting(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=10_000.0)
        fill = FillEvent(
            order_id="ord_1",
            timestamp=_ts(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=20.0,
            price=150.0,
            commission=5.0,
            slippage=0.0,
        )
        portfolio.apply_fill(fill)

        # Cost = 20 * 150 + 5 = 3005.0. Cash = 10000 - 3005 = 6995.0
        assert abs(portfolio.cash - 6995.0) < 1e-9
        assert portfolio.total_fees == 5.0
        pos = portfolio.get_position("AAPL")
        assert pos.quantity == 20.0
        assert pos.average_entry_price == 150.0
        assert pos.market_price == 150.0

    def test_multiple_buys_average_entry_price(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=50_000.0)
        # Buy 10 @ 100
        portfolio.apply_fill(
            FillEvent(
                order_id="o1",
                timestamp=_ts(),
                symbol="MSFT",
                side=OrderSide.BUY,
                quantity=10.0,
                price=100.0,
                commission=0.0,
                slippage=0.0,
            )
        )
        # Buy 10 @ 200
        portfolio.apply_fill(
            FillEvent(
                order_id="o2",
                timestamp=_ts(),
                symbol="MSFT",
                side=OrderSide.BUY,
                quantity=10.0,
                price=200.0,
                commission=0.0,
                slippage=0.0,
            )
        )

        pos = portfolio.get_position("MSFT")
        assert pos.quantity == 20.0
        assert abs(pos.average_entry_price - 150.0) < 1e-9

    def test_partial_sell_and_full_sell_accounting(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=20_000.0)
        # Buy 20 @ 100 (cost = 2000)
        portfolio.apply_fill(
            FillEvent(
                order_id="o1",
                timestamp=_ts(),
                symbol="XYZ",
                side=OrderSide.BUY,
                quantity=20.0,
                price=100.0,
                commission=2.0,
                slippage=0.0,
            )
        )
        # Sell 10 @ 150 (proceeds = 1500 - 1.5 = 1498.5)
        # Trade realized PnL = (150 - 100) * 10 = 500
        portfolio.apply_fill(
            FillEvent(
                order_id="o2",
                timestamp=_ts(),
                symbol="XYZ",
                side=OrderSide.SELL,
                quantity=10.0,
                price=150.0,
                commission=1.5,
                slippage=0.0,
            )
        )

        pos = portfolio.get_position("XYZ")
        assert pos.quantity == 10.0
        assert pos.average_entry_price == 100.0
        assert abs(portfolio.realized_pnl - 500.0) < 1e-9
        assert abs(portfolio.total_fees - 3.5) < 1e-9

        # Sell remaining 10 @ 180 (trade realized PnL = (180 - 100) * 10 = 800)
        portfolio.apply_fill(
            FillEvent(
                order_id="o3",
                timestamp=_ts(),
                symbol="XYZ",
                side=OrderSide.SELL,
                quantity=10.0,
                price=180.0,
                commission=1.8,
                slippage=0.0,
            )
        )

        pos = portfolio.get_position("XYZ")
        assert pos.quantity == 0.0
        assert pos.average_entry_price == 0.0
        assert abs(portfolio.realized_pnl - 1300.0) < 1e-9

    def test_insufficient_funds_rejected(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=1000.0)
        fill = FillEvent(
            order_id="o1",
            timestamp=_ts(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=10.0,
            price=150.0,  # 1500 > 1000
            commission=0.0,
            slippage=0.0,
        )
        with pytest.raises(InsufficientFundsError):
            portfolio.apply_fill(fill)

    def test_insufficient_position_rejected(self) -> None:
        portfolio = SimulatedPortfolio(initial_cash=10_000.0)
        sell_fill = FillEvent(
            order_id="o1",
            timestamp=_ts(),
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=10.0,  # 0 held
            price=150.0,
            commission=0.0,
            slippage=0.0,
        )
        with pytest.raises(InsufficientPositionError):
            portfolio.apply_fill(sell_fill)

    def test_accounting_reconciliation_invariant(self) -> None:
        initial = 100_000.0
        portfolio = SimulatedPortfolio(initial_cash=initial)

        # 1. Buy 100 AAPL @ 150, fee 10
        portfolio.apply_fill(
            FillEvent(
                order_id="b1",
                timestamp=_ts(),
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=100.0,
                price=150.0,
                commission=10.0,
                slippage=0.0,
            )
        )
        # 2. Buy 200 MSFT @ 50, fee 5
        portfolio.apply_fill(
            FillEvent(
                order_id="b2",
                timestamp=_ts(),
                symbol="MSFT",
                side=OrderSide.BUY,
                quantity=200.0,
                price=50.0,
                commission=5.0,
                slippage=0.0,
            )
        )
        # 3. Sell 50 AAPL @ 180, fee 5 (PnL = (180-150)*50 = 1500)
        portfolio.apply_fill(
            FillEvent(
                order_id="s1",
                timestamp=_ts(),
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=50.0,
                price=180.0,
                commission=5.0,
                slippage=0.0,
            )
        )

        # Snapshot at new market prices: AAPL = 200, MSFT = 60
        prices = {"AAPL": 200.0, "MSFT": 60.0}
        snapshot = portfolio.record_snapshot(_ts(), current_prices=prices)

        # Invariant 1: equity == cash + market_value
        assert abs(snapshot.equity - (snapshot.cash + snapshot.market_value)) < 1e-9

        # Invariant 2: equity == initial_cash + realized_pnl + unrealized_pnl - total_fees
        reconciled_equity = (
            initial + snapshot.realized_pnl + snapshot.unrealized_pnl - snapshot.fees
        )
        assert abs(snapshot.equity - reconciled_equity) < 1e-9
