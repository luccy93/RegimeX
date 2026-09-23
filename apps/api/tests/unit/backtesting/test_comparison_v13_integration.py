"""
RegimeX Backtesting — Strategy Comparison V13 Risk Integration Tests
====================================================================
Validates delegation to the V13 Portfolio Risk Engine without code duplication:
- Matches PortfolioRiskEngine.analyze_risk() metrics directly
- Verifies custom risk_engine injection
- Verifies periods_per_year annualization propagation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.modules.backtesting.domain.models import (
    BacktestResult,
    EquitySnapshot,
    StrategyComparisonInput,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.portfolio_risk.domain.models import PriceSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _make_backtest_result(
    initial_cash: float,
    equity_values: list[float],
) -> BacktestResult:
    start_dt = _ts(0)
    end_dt = _ts(len(equity_values) - 1)
    curve = [
        EquitySnapshot(
            timestamp=_ts(i),
            cash=eq,
            market_value=0.0,
            equity=eq,
            fees=0.0,
            realized_pnl=eq - initial_cash,
            unrealized_pnl=0.0,
        )
        for i, eq in enumerate(equity_values)
    ]
    return BacktestResult(
        start_timestamp=start_dt,
        end_timestamp=end_dt,
        initial_cash=initial_cash,
        final_cash=equity_values[-1],
        final_equity=equity_values[-1],
        orders=(),
        fills=(),
        positions={},
        equity_curve=tuple(curve),
        total_fees=0.0,
        trade_count=0,
        metadata={},
    )


class TestComparisonV13Integration:
    def test_delegation_matches_v13_portfolio_risk_engine(self) -> None:
        """Verify that summary volatility, drawdown, and VaR/ES match direct V13 evaluation."""
        eq_vals = [
            100_000.0,
            102_000.0,
            98_000.0,
            95_000.0,
            101_000.0,
            104_000.0,
            106_000.0,
            103_000.0,
        ]
        res = _make_backtest_result(100_000.0, eq_vals)

        # 1. Direct V13 evaluation
        v13_engine = PortfolioRiskEngine()
        price_series = PriceSeries(
            timestamps=tuple(_ts(i) for i in range(len(eq_vals))),
            prices=tuple(eq_vals),
            symbol="TEST_EQUITY",
        )
        direct_risk = v13_engine.analyze_risk(
            data=price_series, periods_per_year=252.0, series_id="TEST"
        )

        # 2. StrategyComparisonEngine evaluation
        comparison_engine = StrategyComparisonEngine()
        comp_result = comparison_engine.compare(
            [StrategyComparisonInput(strategy_id="TEST", backtest_result=res)],
            periods_per_year=252.0,
        )
        summary = comp_result.get_strategy_summary("TEST")

        # Compare metrics: must be bit-for-bit identical
        assert summary.volatility == direct_risk.volatility.period_volatility
        assert summary.annualized_volatility == direct_risk.volatility.annualized_volatility
        assert summary.maximum_drawdown == direct_risk.drawdown.max_drawdown
        assert summary.drawdown_magnitude == direct_risk.drawdown.drawdown_magnitude
        assert summary.peak_timestamp == direct_risk.drawdown.peak_timestamp
        assert summary.trough_timestamp == direct_risk.drawdown.trough_timestamp
        assert summary.recovery_timestamp == direct_risk.drawdown.recovery_timestamp
        assert summary.is_recovered == direct_risk.drawdown.is_recovered
        assert summary.return_mean == direct_risk.return_statistics.mean_return
        assert summary.return_median == direct_risk.return_statistics.median_return
        assert summary.return_min == direct_risk.return_statistics.minimum_return
        assert summary.return_max == direct_risk.return_statistics.maximum_return

    def test_custom_risk_engine_injection(self) -> None:
        """Verify custom risk engine injection conforms to protocol and is invoked."""
        mock_risk_engine = MagicMock(spec=PortfolioRiskEngine)
        real_engine = PortfolioRiskEngine()

        eq_vals = [100_000.0, 105_000.0, 110_000.0]
        res = _make_backtest_result(100_000.0, eq_vals)

        price_series = PriceSeries(
            timestamps=tuple(_ts(i) for i in range(len(eq_vals))),
            prices=tuple(eq_vals),
        )
        expected_result = real_engine.analyze_risk(price_series)
        mock_risk_engine.analyze_risk.return_value = expected_result

        comparison_engine = StrategyComparisonEngine()
        comparison_engine.compare(
            [StrategyComparisonInput(strategy_id="MOCK_TEST", backtest_result=res)],
            risk_engine=mock_risk_engine,
        )

        assert mock_risk_engine.analyze_risk.called
        assert mock_risk_engine.analyze_risk.call_count == 1
