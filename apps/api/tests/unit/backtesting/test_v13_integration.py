"""
RegimeX Backtesting — Deep V13 Portfolio Risk Engine Integration Tests
=====================================================================
Validates contract compatibility and end-to-end delegation from the backtest equity curve
to the V13 Portfolio Risk Analytics Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.backtesting.domain.models import (
    BacktestConfig,
    MarketEvent,
    OrderRequest,
    OrderSide,
)
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine
from app.modules.portfolio_risk.domain.models import (
    PortfolioRiskResult,
    PriceSeries,
    ReturnSeries,
    ReturnType,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _make_trend_bars(n_bars: int = 30) -> list[MarketEvent]:
    base_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    events: list[MarketEvent] = []
    price = 100.0
    for i in range(n_bars):
        # Create fluctuating series with peak, drop, and recovery
        if i < 10:
            price += 2.0
        elif i < 20:
            price -= 3.0
        else:
            price += 2.5
        events.append(
            MarketEvent(
                timestamp=base_dt + timedelta(days=i),
                symbol="TREND",
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=10_000.0,
            )
        )
    return events


class BuyOnceHold:
    def __init__(self, qty: float = 100.0) -> None:
        self.qty = qty
        self.bought = False

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        if not self.bought:
            self.bought = True
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.BUY,
                    quantity=self.qty,
                )
            ]
        return []


class TestV13IntegrationDeep:
    def test_price_series_generation_contract(self) -> None:
        bars = _make_trend_bars(25)
        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=50_000.0))
        result = engine.run(bars, BuyOnceHold(qty=50.0))

        ps = result.to_price_series()
        assert isinstance(ps, PriceSeries)
        assert len(ps.prices) == 25
        assert len(ps.timestamps) == 25
        assert ps.symbol == "PORTFOLIO_EQUITY"
        # Invariants
        for p in ps.prices:
            assert p > 0.0

    def test_return_series_generation_arithmetic_and_log(self) -> None:
        bars = _make_trend_bars(20)
        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=50_000.0))
        result = engine.run(bars, BuyOnceHold(qty=50.0))

        # Arithmetic
        ret_arith = result.to_return_series(return_type=ReturnType.ARITHMETIC)
        assert isinstance(ret_arith, ReturnSeries)
        assert len(ret_arith.values) == 19
        assert ret_arith.symbol == "PORTFOLIO_RETURNS"

        # Log
        ret_log = result.to_return_series(return_type=ReturnType.LOG)
        assert isinstance(ret_log, ReturnSeries)
        assert len(ret_log.values) == 19

    def test_full_risk_analytics_delegation(self) -> None:
        bars = _make_trend_bars(30)
        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=100_000.0))
        result = engine.run(bars, BuyOnceHold(qty=200.0))

        # Explicit engine injection
        risk_eng = PortfolioRiskEngine()
        risk_res = result.compute_risk_metrics(risk_engine=risk_eng)

        assert isinstance(risk_res, PortfolioRiskResult)
        assert risk_res.series_id == "backtest_portfolio"

        # 1. Volatility invariants without explicit period scaling
        assert risk_res.volatility.period_volatility >= 0.0
        assert risk_res.volatility.annualized_volatility is None

        # Scaling with explicit annualization factor
        scaled_risk = result.compute_risk_metrics(risk_engine=risk_eng, periods_per_year=252.0)
        assert scaled_risk.volatility.annualized_volatility is not None
        assert scaled_risk.volatility.annualized_volatility >= 0.0

        # 2. Drawdown invariants
        assert risk_res.drawdown.max_drawdown <= 0.0
        assert risk_res.drawdown.drawdown_magnitude >= 0.0
        assert (
            abs(abs(risk_res.drawdown.max_drawdown) - risk_res.drawdown.drawdown_magnitude) < 1e-12
        )

        # 3. VaR & Expected Shortfall coherence
        for conf in [0.90, 0.95, 0.99]:
            var_m = risk_res.get_var(conf)
            es_m = risk_res.get_expected_shortfall(conf)
            assert es_m.expected_shortfall >= var_m.var_loss
