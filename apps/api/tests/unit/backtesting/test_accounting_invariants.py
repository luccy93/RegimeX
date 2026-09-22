"""
RegimeX Backtesting — Portfolio Accounting Invariants Tests
===========================================================
Validates dynamic average cost basis calculation, step-by-step partial exits,
oversell and insufficient funds protection, and conservation equation invariants.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.backtesting.domain.errors import (
    InsufficientFundsError,
    InsufficientPositionError,
)
from app.modules.backtesting.domain.models import FillEvent, OrderSide
from app.modules.backtesting.infrastructure.portfolio import SimulatedPortfolio


def _ts() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class TestPortfolioAccountingInvariants:
    def test_multiple_buys_weighted_average_cost(self) -> None:
        """
        Verify exact weighted average cost calculation:
        BUY 10 @ 100 + BUY 20 @ 120 -> 30 @ 113.33333333333333
        """
        portfolio = SimulatedPortfolio(initial_cash=50_000.0)

        # 1. Buy 10 @ 100
        portfolio.apply_fill(
            FillEvent(
                order_id="b1",
                timestamp=_ts(),
                symbol="TEST",
                side=OrderSide.BUY,
                quantity=10.0,
                price=100.0,
                commission=0.0,
                slippage=0.0,
            )
        )
        pos = portfolio.get_position("TEST")
        assert pos.quantity == 10.0
        assert pos.average_entry_price == 100.0

        # 2. Buy 20 @ 120
        portfolio.apply_fill(
            FillEvent(
                order_id="b2",
                timestamp=_ts(),
                symbol="TEST",
                side=OrderSide.BUY,
                quantity=20.0,
                price=120.0,
                commission=0.0,
                slippage=0.0,
            )
        )
        pos = portfolio.get_position("TEST")
        assert pos.quantity == 30.0
        expected_avg = (10.0 * 100.0 + 20.0 * 120.0) / 30.0
        assert abs(pos.average_entry_price - expected_avg) < 1e-12
        assert abs(pos.average_entry_price - (3400.0 / 30.0)) < 1e-12

    def test_step_by_step_partial_sells(self) -> None:
        """
        Test:
        BUY 100 @ 50
        SELL 30 @ 60
        SELL 20 @ 70
        SELL 50 @ 80
        Check state, cash, average entry price, and realized PnL at each step.
        """
        portfolio = SimulatedPortfolio(initial_cash=20_000.0)

        # 1. BUY 100 @ 50 (cost 5000)
        portfolio.apply_fill(
            FillEvent(
                order_id="b1",
                timestamp=_ts(),
                symbol="STK",
                side=OrderSide.BUY,
                quantity=100.0,
                price=50.0,
                commission=5.0,
                slippage=0.0,
            )
        )
        assert portfolio.cash == 14_995.0
        assert portfolio.get_position("STK").quantity == 100.0
        assert portfolio.get_position("STK").average_entry_price == 50.0

        # 2. SELL 30 @ 60 (proceeds = 1800 - 1.8 = 1798.2)
        # Realized PnL = (60 - 50) * 30 = 300
        portfolio.apply_fill(
            FillEvent(
                order_id="s1",
                timestamp=_ts(),
                symbol="STK",
                side=OrderSide.SELL,
                quantity=30.0,
                price=60.0,
                commission=1.8,
                slippage=0.0,
            )
        )
        assert abs(portfolio.cash - (14_995.0 + 1798.2)) < 1e-9
        assert portfolio.get_position("STK").quantity == 70.0
        assert portfolio.get_position("STK").average_entry_price == 50.0
        assert abs(portfolio.realized_pnl - 300.0) < 1e-9

        # 3. SELL 20 @ 70 (proceeds = 1400 - 1.4 = 1398.6)
        # Realized PnL += (70 - 50) * 20 = 400 (total 700)
        portfolio.apply_fill(
            FillEvent(
                order_id="s2",
                timestamp=_ts(),
                symbol="STK",
                side=OrderSide.SELL,
                quantity=20.0,
                price=70.0,
                commission=1.4,
                slippage=0.0,
            )
        )
        assert portfolio.get_position("STK").quantity == 50.0
        assert portfolio.get_position("STK").average_entry_price == 50.0
        assert abs(portfolio.realized_pnl - 700.0) < 1e-9

        # 4. SELL 50 @ 80 (proceeds = 4000 - 4.0 = 3996.0)
        # Realized PnL += (80 - 50) * 50 = 1500 (total 2200)
        portfolio.apply_fill(
            FillEvent(
                order_id="s3",
                timestamp=_ts(),
                symbol="STK",
                side=OrderSide.SELL,
                quantity=50.0,
                price=80.0,
                commission=4.0,
                slippage=0.0,
            )
        )
        pos = portfolio.get_position("STK")
        assert pos.quantity == 0.0
        assert pos.average_entry_price == 0.0
        assert abs(portfolio.realized_pnl - 2200.0) < 1e-9

        # Total fees = 5.0 + 1.8 + 1.4 + 4.0 = 12.2
        assert abs(portfolio.total_fees - 12.2) < 1e-9

        # Final cash = initial (20000) + gross realized (2200) - fees (12.2) = 22187.8
        assert abs(portfolio.cash - 22_187.8) < 1e-9
        assert abs(portfolio.total_equity - 22_187.8) < 1e-9

    def test_oversell_protection_rejection(self) -> None:
        """
        Verify: held = 10, sell = 11 raises InsufficientPositionError.
        No partial execution; cash and position must remain intact.
        """
        portfolio = SimulatedPortfolio(initial_cash=10_000.0)
        portfolio.apply_fill(
            FillEvent(
                order_id="b1",
                timestamp=_ts(),
                symbol="OVER",
                side=OrderSide.BUY,
                quantity=10.0,
                price=100.0,
                commission=0.0,
                slippage=0.0,
            )
        )
        cash_prior = portfolio.cash
        pos_prior = portfolio.get_position("OVER").quantity

        with pytest.raises(InsufficientPositionError) as exc_info:
            portfolio.apply_fill(
                FillEvent(
                    order_id="s_bad",
                    timestamp=_ts(),
                    symbol="OVER",
                    side=OrderSide.SELL,
                    quantity=11.0,  # 11 > 10
                    price=100.0,
                    commission=0.0,
                    slippage=0.0,
                )
            )

        assert exc_info.value.requested_quantity == 11.0
        assert exc_info.value.available_quantity == 10.0
        # Verify state did not mutate
        assert portfolio.cash == cash_prior
        assert portfolio.get_position("OVER").quantity == pos_prior

    def test_insufficient_funds_protection_rejection(self) -> None:
        """
        Verify: available_cash < required_cash raises InsufficientFundsError.
        No partial fill; cash and positions must remain unchanged.
        """
        portfolio = SimulatedPortfolio(initial_cash=500.0)
        with pytest.raises(InsufficientFundsError) as exc_info:
            portfolio.apply_fill(
                FillEvent(
                    order_id="b_broke",
                    timestamp=_ts(),
                    symbol="EXPENSIVE",
                    side=OrderSide.BUY,
                    quantity=10.0,
                    price=100.0,  # 1000 > 500
                    commission=5.0,
                    slippage=0.0,
                )
            )
        assert exc_info.value.required == 1005.0
        assert exc_info.value.available == 500.0
        assert portfolio.cash == 500.0
        assert portfolio.get_position("EXPENSIVE").quantity == 0.0

    def test_conservation_invariant_across_multiple_assets(self) -> None:
        """
        Test that for every recorded snapshot:
        equity == cash + sum(market_value) == initial + realized + unrealized - fees
        """
        initial = 100_000.0
        portfolio = SimulatedPortfolio(initial_cash=initial)

        # Fill 1: AAPL
        portfolio.apply_fill(
            FillEvent(
                order_id="1",
                timestamp=_ts(),
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=100.0,
                price=150.0,
                commission=10.0,
                slippage=0.0,
            )
        )
        # Fill 2: MSFT
        portfolio.apply_fill(
            FillEvent(
                order_id="2",
                timestamp=_ts(),
                symbol="MSFT",
                side=OrderSide.BUY,
                quantity=200.0,
                price=50.0,
                commission=5.0,
                slippage=0.0,
            )
        )
        # Snapshot 1
        s1 = portfolio.record_snapshot(_ts(), current_prices={"AAPL": 160.0, "MSFT": 55.0})
        assert abs(s1.equity - (s1.cash + s1.market_value)) < 1e-9
        assert abs(s1.equity - (initial + s1.realized_pnl + s1.unrealized_pnl - s1.fees)) < 1e-9

        # Fill 3: Partial sell AAPL
        portfolio.apply_fill(
            FillEvent(
                order_id="3",
                timestamp=_ts(),
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=40.0,
                price=170.0,
                commission=4.0,
                slippage=0.0,
            )
        )
        # Snapshot 2
        s2 = portfolio.record_snapshot(_ts(), current_prices={"AAPL": 175.0, "MSFT": 52.0})
        assert abs(s2.equity - (s2.cash + s2.market_value)) < 1e-9
        assert abs(s2.equity - (initial + s2.realized_pnl + s2.unrealized_pnl - s2.fees)) < 1e-9
