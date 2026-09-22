"""
RegimeX Backtesting — Deterministic Replay Tests
===============================================
Verifies that replaying identical backtests produces bit-for-bit identical results
across orders, fills, positions, cash, fees, realized/unrealized PnL, equity curves,
and downstream V13 risk metrics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.backtesting.domain.models import (
    BacktestConfig,
    ExecutionPriceConvention,
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine


def _generate_multi_asset_data() -> list[MarketEvent]:
    base_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    events: list[MarketEvent] = []

    prices_a = [100.0, 102.0, 105.0, 98.0, 103.0, 110.0, 115.0, 108.0]
    prices_b = [50.0, 52.0, 49.0, 51.0, 53.0, 55.0, 52.0, 54.0]

    for i, (pa, pb) in enumerate(zip(prices_a, prices_b, strict=True)):
        ts = base_dt + timedelta(days=i)
        events.append(
            MarketEvent(
                timestamp=ts,
                symbol="SYM_A",
                open=pa,
                high=pa * 1.02,
                low=pa * 0.98,
                close=pa,
                volume=10_000.0,
            )
        )
        events.append(
            MarketEvent(
                timestamp=ts,
                symbol="SYM_B",
                open=pb,
                high=pb * 1.02,
                low=pb * 0.98,
                close=pb,
                volume=5_000.0,
            )
        )
    return events


class MultiAssetMomentumStrategy:
    def __init__(self, window: int = 2) -> None:
        self.window = window

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        history = context.get_history(event.symbol, count=self.window)
        if len(history) < self.window:
            return []

        avg_price = sum(b.close for b in history) / len(history)
        pos = context.current_positions.get(event.symbol)
        curr_qty = pos.quantity if pos else 0.0

        if event.close > avg_price and curr_qty == 0.0:
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.BUY,
                    quantity=20.0,
                )
            ]
        elif event.close < avg_price and curr_qty > 0.0:
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.SELL,
                    quantity=curr_qty,
                )
            ]
        return []


class TestDeterministicReplay:
    @pytest.mark.parametrize("run_seed", [1, 2, 3])
    def test_repeated_replay_is_bit_for_bit_identical(self, run_seed: int) -> None:
        events = _generate_multi_asset_data()
        config = BacktestConfig(
            initial_cash=100_000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            execution_convention=ExecutionPriceConvention.CURRENT_CLOSE,
        )

        engine1 = EventDrivenBacktestEngine(config=config)
        engine2 = EventDrivenBacktestEngine(config=config)

        res1 = engine1.run(events, MultiAssetMomentumStrategy(window=2))
        res2 = engine2.run(events, MultiAssetMomentumStrategy(window=2))

        # 1. Summary balances
        assert res1.final_cash == res2.final_cash
        assert res1.final_equity == res2.final_equity
        assert res1.total_fees == res2.total_fees
        assert res1.trade_count == res2.trade_count

        # 2. Fills bit-for-bit
        assert len(res1.fills) == len(res2.fills)
        for f1, f2 in zip(res1.fills, res2.fills, strict=True):
            assert f1.timestamp == f2.timestamp
            assert f1.symbol == f2.symbol
            assert f1.side == f2.side
            assert f1.quantity == f2.quantity
            assert f1.price == f2.price
            assert f1.commission == f2.commission
            assert f1.slippage == f2.slippage

        # 3. Positions bit-for-bit
        for sym in ["SYM_A", "SYM_B"]:
            p1 = res1.positions.get(sym)
            p2 = res2.positions.get(sym)
            if p1 is not None and p2 is not None:
                assert p1.quantity == p2.quantity
                assert p1.average_entry_price == p2.average_entry_price
                assert p1.market_price == p2.market_price
                assert p1.realized_pnl == p2.realized_pnl

        # 4. Equity curve bit-for-bit
        assert len(res1.equity_curve) == len(res2.equity_curve)
        for s1, s2 in zip(res1.equity_curve, res2.equity_curve, strict=True):
            assert s1.timestamp == s2.timestamp
            assert s1.cash == s2.cash
            assert s1.market_value == s2.market_value
            assert s1.equity == s2.equity
            assert s1.realized_pnl == s2.realized_pnl
            assert s1.unrealized_pnl == s2.unrealized_pnl
            assert s1.fees == s2.fees

        # 5. Risk analytics bit-for-bit
        risk1 = res1.compute_risk_metrics()
        risk2 = res2.compute_risk_metrics()
        assert risk1.return_statistics.mean_return == risk2.return_statistics.mean_return
        assert risk1.volatility.period_volatility == risk2.volatility.period_volatility
        assert risk1.drawdown.max_drawdown == risk2.drawdown.max_drawdown
        assert risk1.get_var(0.95).var_loss == risk2.get_var(0.95).var_loss
        assert risk1.get_expected_shortfall(0.95).expected_shortfall == (
            risk2.get_expected_shortfall(0.95).expected_shortfall
        )
