"""
RegimeX Backtesting — V13 Risk Engine Integration Tests
=======================================================
Verifies seamless integration between the backtest equity curve and the
canonical V13 Portfolio Risk Engine.
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


def _make_bars(prices: list[float]) -> list[MarketEvent]:
    base_dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    return [
        MarketEvent(
            timestamp=base_dt + timedelta(days=i),
            symbol="RISK_ASSET",
            open=p,
            high=p * 1.01,
            low=p * 0.99,
            close=p,
            volume=5000.0,
        )
        for i, p in enumerate(prices)
    ]


class BuyAndHold:
    def __init__(self, quantity: float = 100.0) -> None:
        self.quantity = quantity
        self.bought = False

    def on_market_event(self, event: MarketEvent, context) -> list[OrderRequest]:
        if not self.bought:
            self.bought = True
            return [
                OrderRequest(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    side=OrderSide.BUY,
                    quantity=self.quantity,
                )
            ]
        return []


class TestV13RiskIntegration:
    def test_equity_curve_to_price_series(self) -> None:
        prices = [100.0, 105.0, 102.0, 108.0, 115.0]
        bars = _make_bars(prices)

        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=50_000.0))
        result = engine.run(bars, BuyAndHold(quantity=100.0))

        price_series = result.to_price_series()
        assert isinstance(price_series, PriceSeries)
        assert len(price_series.prices) == len(bars)
        assert len(price_series.timestamps) == len(bars)
        assert price_series.prices[0] == 50_000.0
        assert price_series.prices[-1] == result.final_equity

    def test_equity_curve_to_return_series(self) -> None:
        prices = [100.0, 105.0, 102.0, 108.0, 115.0]
        bars = _make_bars(prices)

        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=50_000.0))
        result = engine.run(bars, BuyAndHold(quantity=100.0))

        return_series = result.to_return_series(return_type=ReturnType.ARITHMETIC)
        assert isinstance(return_series, ReturnSeries)
        assert len(return_series.values) == len(bars) - 1
        assert len(return_series.timestamps) == len(bars) - 1

    def test_compute_risk_metrics_delegates_to_v13(self) -> None:
        prices = [100.0, 105.0, 95.0, 90.0, 110.0, 115.0, 105.0, 120.0, 130.0, 125.0]
        bars = _make_bars(prices)

        engine = EventDrivenBacktestEngine(config=BacktestConfig(initial_cash=50_000.0))
        result = engine.run(bars, BuyAndHold(quantity=200.0))

        risk_result = result.compute_risk_metrics()
        assert isinstance(risk_result, PortfolioRiskResult)
        assert risk_result.series_id == "backtest_portfolio"

        # Check that standard V13 metrics are computed correctly
        assert risk_result.return_statistics.observation_count == len(bars) - 1
        assert risk_result.volatility.period_volatility > 0.0
        assert risk_result.drawdown.max_drawdown < 0.0
        assert 0.95 in risk_result.var_metrics
        assert 0.95 in risk_result.expected_shortfall_metrics

        # Tail risk hierarchy from V13 holds
        var_95 = risk_result.get_var(0.95)
        es_95 = risk_result.get_expected_shortfall(0.95)
        assert es_95.expected_shortfall >= var_95.var_loss
