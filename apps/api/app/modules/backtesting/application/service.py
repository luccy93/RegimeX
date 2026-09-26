"""
RegimeX Backtesting — Application Service
=========================================
Coordinates deterministic event-driven backtesting execution and performance reporting.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime

from app.modules.backtesting.domain.interfaces import Strategy, StrategyContext
from app.modules.backtesting.domain.models import (
    BacktestConfig,
    BacktestResult,
    ExecutionPriceConvention,
    MarketEvent,
    OrderRequest,
    OrderSide,
    PerformanceReport,
    StrategyComparisonInput,
    StrategySummary,
)
from app.modules.backtesting.infrastructure.comparison import StrategyComparisonEngine
from app.modules.backtesting.infrastructure.engine import EventDrivenBacktestEngine
from app.modules.backtesting.infrastructure.reporting import PerformanceReportBuilder


class BenchmarkBuyAndHoldStrategy:
    """Benchmark buy-and-hold strategy entering a long position on the first bar."""

    def __init__(self) -> None:
        self._invested = False

    def on_market_event(self, event: MarketEvent, context: StrategyContext) -> list[OrderRequest]:
        if not self._invested:
            self._invested = True
            pos = context.current_positions.get(event.symbol)
            if not pos or pos.quantity <= 0:
                cash = context.available_cash
                if cash > 10.0 and event.close > 0:
                    shares = math.floor(cash * 0.999 / event.close)
                    if shares > 0:
                        return [
                            OrderRequest(
                                timestamp=event.timestamp,
                                symbol=event.symbol,
                                side=OrderSide.BUY,
                                quantity=float(shares),
                            )
                        ]
        return []


class RegimeAdaptiveStrategy:
    """Regime-adaptive trend strategy allocating long during regime 0, flat otherwise."""

    def on_market_event(self, event: MarketEvent, context: StrategyContext) -> list[OrderRequest]:
        current_regime = context.current_regime
        pos = context.current_positions.get(event.symbol)
        curr_qty = pos.quantity if pos else 0.0

        if current_regime == 0:
            if curr_qty <= 0.0:
                cash = context.available_cash
                if cash > 10.0 and event.close > 0:
                    shares = math.floor(cash * 0.98 / event.close)
                    if shares > 0:
                        return [
                            OrderRequest(
                                timestamp=event.timestamp,
                                symbol=event.symbol,
                                side=OrderSide.BUY,
                                quantity=float(shares),
                            )
                        ]
        else:
            if curr_qty > 0.0:
                return [
                    OrderRequest(
                        timestamp=event.timestamp,
                        symbol=event.symbol,
                        side=OrderSide.SELL,
                        quantity=curr_qty,
                    )
                ]
        return []


class BacktestingService:
    """
    Application service coordinating simulation runs, comparison analytics,
    and performance report creation.
    """

    def __init__(
        self,
        comparison_engine: StrategyComparisonEngine | None = None,
        report_builder: PerformanceReportBuilder | None = None,
    ) -> None:
        self._comparison_engine = comparison_engine or StrategyComparisonEngine()
        self._report_builder = report_builder or PerformanceReportBuilder()

    def create_strategy(self, strategy_id: str) -> tuple[Strategy, str, str]:
        """Resolve strategy instance, canonical ID, and display name."""
        clean = strategy_id.strip().upper()
        if clean == "REGIME_ADAPTIVE":
            return (
                RegimeAdaptiveStrategy(),
                "REGIME_ADAPTIVE",
                "Regime Adaptive Momentum",
            )
        return (
            BenchmarkBuyAndHoldStrategy(),
            "BUY_AND_HOLD",
            "Benchmark Buy and Hold",
        )

    def run_simulation(
        self,
        events: Sequence[MarketEvent],
        strategy_id: str = "BUY_AND_HOLD",
        initial_cash: float = 100_000.0,
        commission_rate: float = 0.0005,
        slippage_rate: float = 0.0005,
        execution_convention: ExecutionPriceConvention = ExecutionPriceConvention.CURRENT_CLOSE,
        regimes: list[int] | None = None,
        periods_per_year: float = 252.0,
    ) -> tuple[BacktestResult, StrategySummary, PerformanceReport, str, str]:
        """
        Execute an event-driven backtest, compute strategy summary, and build report.
        """
        strat_instance, canonical_id, display_name = self.create_strategy(strategy_id)
        config = BacktestConfig(
            initial_cash=initial_cash,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            execution_convention=execution_convention,
        )

        engine = EventDrivenBacktestEngine(config=config)
        result = engine.run(market_data=list(events), strategy=strat_instance, regimes=regimes)

        strat_input = StrategyComparisonInput(
            strategy_id=canonical_id,
            display_name=display_name,
            backtest_result=result,
        )
        comp_result = self._comparison_engine.compare(
            inputs=[strat_input],
            periods_per_year=periods_per_year,
        )

        summary = comp_result.strategies[0]
        report = self._report_builder.build(
            comparison_result=comp_result,
            generated_at=datetime.now(tz=UTC),
        )

        return result, summary, report, canonical_id, display_name
