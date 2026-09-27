"""
RegimeX AI Research — Deterministic Evidence Retrieval
======================================================
Retrieval pipeline fetching factual quantitative state from existing platform services
(MarketDataService, MarketIntelligenceFacade, PortfolioRiskService, BacktestingService).
No vector DB or external web searches; guarantees 100% platform-grounded facts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.modules.ai_research.application.explanation import (
    ExplanationContextBuilder,
    ModelExplanationPipeline,
)
from app.modules.ai_research.domain.models import EvidencePacket, ResearchIntent
from app.modules.backtesting.domain.models import (
    ExecutionPriceConvention,
    MarketEvent,
)
from app.modules.market_data.domain.models import DataInterval

if TYPE_CHECKING:
    from app.modules.backtesting.application.service import BacktestingService
    from app.modules.market_data.application.service import MarketDataService
    from app.modules.portfolio_risk.application.service import PortfolioRiskService
    from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Retrieves grounded evidence packets across RegimeX analytical domains.
    """

    def __init__(
        self,
        market_service: MarketDataService,
        market_intelligence: MarketIntelligenceFacade,
        risk_service: PortfolioRiskService,
        backtest_service: BacktestingService,
    ) -> None:
        self._market_service = market_service
        self._market_intelligence = market_intelligence
        self._risk_service = risk_service
        self._backtest_service = backtest_service

        # Lazy-initialized explanation pipeline
        self._explanation_pipeline: ModelExplanationPipeline | None = None

    async def retrieve_evidence(
        self,
        symbol: str | None,
        intent: ResearchIntent,
    ) -> list[EvidencePacket]:
        """
        Retrieve structured, bounded evidence packets based on symbol and intent.
        """
        packets: list[EvidencePacket] = []

        if not symbol:
            packets.append(self._build_methodology_packet())
            return packets

        clean_symbol = symbol.strip().upper()
        now_utc = datetime.now(UTC)
        start_utc = now_utc - timedelta(days=365)

        # MODEL_EXPLANATION intent uses the dedicated explanation pipeline
        if intent == ResearchIntent.MODEL_EXPLANATION:
            return await self._get_explanation_evidence(clean_symbol)

        # Order evidence packets prioritizing the primary subject of the analytical intent
        if intent in (
            ResearchIntent.CURRENT_REGIME,
            ResearchIntent.REGIME_ANALYTICS,
            ResearchIntent.TRANSITIONS,
            ResearchIntent.PREDICTION_REFUSAL,
            ResearchIntent.ADVICE_REFUSAL,
        ):
            regime_packet, profile_packet = await self._retrieve_regime_packets(
                clean_symbol, start_utc, now_utc
            )
            if regime_packet:
                packets.append(regime_packet)
            if profile_packet and intent in (
                ResearchIntent.REGIME_ANALYTICS,
                ResearchIntent.COMPARISON,
            ):
                packets.append(profile_packet)

            if intent in (
                ResearchIntent.TRANSITIONS,
                ResearchIntent.REGIME_ANALYTICS,
                ResearchIntent.COMPARISON,
            ):
                transition_packet = await self._retrieve_transition_packet(
                    clean_symbol, start_utc, now_utc
                )
                if transition_packet:
                    packets.append(transition_packet)

            market_packet = await self._retrieve_market_packet(clean_symbol, start_utc, now_utc)
            if market_packet:
                packets.append(market_packet)

            if intent in (
                ResearchIntent.RISK,
                ResearchIntent.PREDICTION_REFUSAL,
                ResearchIntent.ADVICE_REFUSAL,
            ):
                risk_packet = await self._retrieve_risk_packet(clean_symbol, start_utc, now_utc)
                if risk_packet:
                    packets.append(risk_packet)

        elif intent == ResearchIntent.RISK:
            risk_packet = await self._retrieve_risk_packet(clean_symbol, start_utc, now_utc)
            if risk_packet:
                packets.append(risk_packet)
            market_packet = await self._retrieve_market_packet(clean_symbol, start_utc, now_utc)
            if market_packet:
                packets.append(market_packet)

        elif intent in (ResearchIntent.BACKTEST, ResearchIntent.METHODOLOGY):
            backtest_packet = await self._retrieve_backtest_packet(clean_symbol, start_utc, now_utc)
            if backtest_packet:
                packets.append(backtest_packet)
            market_packet = await self._retrieve_market_packet(clean_symbol, start_utc, now_utc)
            if market_packet:
                packets.append(market_packet)

        else:
            # Default / MARKET_OVERVIEW / COMPARISON
            market_packet = await self._retrieve_market_packet(clean_symbol, start_utc, now_utc)
            if market_packet:
                packets.append(market_packet)

            regime_packet, profile_packet = await self._retrieve_regime_packets(
                clean_symbol, start_utc, now_utc
            )
            if regime_packet:
                packets.append(regime_packet)
            if profile_packet:
                packets.append(profile_packet)

            transition_packet = await self._retrieve_transition_packet(
                clean_symbol, start_utc, now_utc
            )
            if transition_packet:
                packets.append(transition_packet)

            risk_packet = await self._retrieve_risk_packet(clean_symbol, start_utc, now_utc)
            if risk_packet:
                packets.append(risk_packet)

            backtest_packet = await self._retrieve_backtest_packet(clean_symbol, start_utc, now_utc)
            if backtest_packet:
                packets.append(backtest_packet)

        packets.append(self._build_methodology_packet())
        return packets

    async def _retrieve_market_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        try:
            instrument = await self._market_service.resolve_instrument(symbol)
            records, _ = await self._market_service.get_market_data(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=100,
            )
            latest_close = float(records[-1].close) if records else None
            latest_ts = records[-1].timestamp.isoformat() if records else end.isoformat()

            facts: dict[str, Any] = {
                "symbol": symbol,
                "asset_class": instrument.asset_class.value,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "description": instrument.description,
                "latest_close": latest_close,
                "observation_count": len(records),
            }
            return EvidencePacket(
                source_id=f"market:{symbol}",
                source_type="market",
                title=f"Market Instrument — {symbol}",
                facts=facts,
                timestamp=latest_ts,
                metadata={"exchange": instrument.exchange, "currency": instrument.currency},
            )
        except Exception as exc:
            logger.warning("Failed to retrieve market packet for %s: %s", symbol, exc)
            return None

    async def _retrieve_regime_packets(
        self, symbol: str, start: datetime, end: datetime
    ) -> tuple[EvidencePacket | None, EvidencePacket | None]:
        try:
            summary, confidence = await self._market_intelligence.get_market_regime(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )

            current = summary.current_regime
            cur_facts: dict[str, Any] = {
                "symbol": symbol,
                "current_regime_id": current.current_regime_id if current else 0,
                "current_regime_label": current.current_regime_label if current else "UNKNOWN",
                "confidence": round(confidence, 4) if confidence is not None else None,
                "observations_in_current_run": current.observations_in_current_run
                if current
                else 1,
                "historical_frequency": round(current.historical_frequency, 4) if current else 0.0,
                "historical_average_duration": round(current.historical_average_duration, 1)
                if current
                else 0.0,
                "historical_max_duration": current.historical_max_duration if current else 0,
                "historical_run_count": current.historical_run_count if current else 0,
                "model_name": summary.model_name,
                "model_version": summary.model_version,
                "algorithm": summary.algorithm,
            }

            current_ts = (
                current.current_timestamp.isoformat()
                if (current and current.current_timestamp)
                else (summary.analysis_end.isoformat() if summary.analysis_end else end.isoformat())
            )
            analysis_end_str = (
                summary.analysis_end.isoformat() if summary.analysis_end else end.isoformat()
            )

            regime_packet = EvidencePacket(
                source_id=f"regime:{symbol}:current",
                source_type="regime",
                title=f"Regime Intelligence — {symbol}",
                facts=cur_facts,
                timestamp=current_ts,
                metadata={"algorithm": summary.algorithm, "model_name": summary.model_name},
            )

            # Summarized profiles
            profiles_facts: dict[str, Any] = {}
            for r_id, p in summary.regime_profiles.items():
                profiles_facts[f"regime_{r_id}_{p.regime_label}"] = {
                    "regime_id": p.regime_id,
                    "label": p.regime_label,
                    "frequency": round(p.frequency, 4),
                    "percentage": round(p.percentage, 2),
                    "average_duration": round(p.average_duration, 1),
                    "max_duration": p.max_duration,
                    "observation_count": p.observation_count,
                }

            profile_packet = EvidencePacket(
                source_id=f"regime-profiles:{symbol}",
                source_type="regime",
                title=f"Historical Regime Profiles — {symbol}",
                facts=profiles_facts,
                timestamp=analysis_end_str,
                metadata={"total_observations": summary.total_observations},
            )

            return regime_packet, profile_packet
        except Exception as exc:
            logger.warning("Failed to retrieve regime packet for %s: %s", symbol, exc)
            return None, None

    async def _retrieve_transition_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        try:
            analytics = await self._market_intelligence.get_transition_analytics(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )

            ga = analytics.global_analytics
            facts: dict[str, Any] = {
                "symbol": symbol,
                "global_persistence_rate": round(ga.global_persistence_rate, 4),
                "global_change_rate": round(ga.global_change_rate, 4),
                "total_transitions": ga.total_consecutive_transitions,
                "total_regime_changes": ga.total_regime_changes,
                "regimes_analyzed": list(analytics.transition_result.probability_matrix.regimes),
            }

            for r_id, ra in analytics.regime_analytics.items():
                top_dest = [
                    {
                        "target_regime": rk.target_regime,
                        "target_label": rk.target_label,
                        "probability": round(rk.probability, 4),
                    }
                    for rk in ra.rankings[:3]
                ]
                facts[f"regime_{r_id}_{ra.regime_label}_analytics"] = {
                    "persistence_probability": round(ra.persistence_probability, 4),
                    "change_rate": round(ra.change_rate, 4),
                    "most_likely_destination": ra.most_likely_destination,
                    "most_likely_destination_probability": round(
                        ra.most_likely_destination_probability, 4
                    ),
                    "transition_entropy": round(ra.transition_entropy, 4),
                    "top_destinations": top_dest,
                }

            return EvidencePacket(
                source_id=f"regime-transition:{symbol}",
                source_type="regime_transition",
                title=f"Regime Transition Matrix & Dynamics — {symbol}",
                facts=facts,
                timestamp=end.isoformat(),
                metadata={"regimes_count": ga.number_of_regimes},
            )
        except Exception as exc:
            logger.warning("Failed to retrieve transition packet for %s: %s", symbol, exc)
            return None

    async def _retrieve_risk_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        try:
            records, _ = await self._market_service.get_market_data(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )
            if len(records) < 2:
                return None

            prices = tuple(b.close for b in records)
            timestamps = tuple(b.timestamp for b in records)

            result = self._risk_service.analyze_price_series(
                prices=prices,
                timestamps=timestamps,
                symbol=symbol,
                periods_per_year=252.0,
                target_return=0.0,
                var_confidences=(0.90, 0.95, 0.99),
            )

            var_metric = result.var_metrics.get(0.95)
            var_95 = var_metric.var_loss if var_metric is not None else None
            es_metric = result.expected_shortfall_metrics.get(0.95)
            es_95 = es_metric.expected_shortfall if es_metric is not None else None
            downside_dev = result.downside_risk.downside_deviation

            mdd_mag = result.drawdown.drawdown_magnitude

            ann_vol_risk = result.volatility.annualized_volatility
            per_vol_risk = result.volatility.period_volatility
            risk_mdd = result.drawdown.max_drawdown

            facts: dict[str, Any] = {
                "symbol": symbol,
                "annualized_volatility": (
                    round(ann_vol_risk, 4) if ann_vol_risk is not None else None
                ),
                "period_volatility": (round(per_vol_risk, 4) if per_vol_risk is not None else None),
                "max_drawdown": round(risk_mdd, 4) if risk_mdd is not None else None,
                "drawdown_magnitude": round(mdd_mag, 4) if mdd_mag is not None else None,
                "is_drawdown_recovered": result.drawdown.is_recovered,
                "peak_timestamp": (
                    result.drawdown.peak_timestamp.isoformat()
                    if result.drawdown.peak_timestamp
                    else None
                ),
                "trough_timestamp": (
                    result.drawdown.trough_timestamp.isoformat()
                    if result.drawdown.trough_timestamp
                    else None
                ),
                "var_95": round(var_95, 4) if var_95 is not None else None,
                "expected_shortfall_95": round(es_95, 4) if es_95 is not None else None,
                "downside_deviation": round(downside_dev, 4) if downside_dev is not None else None,
                "observation_count": result.observation_count,
            }

            return EvidencePacket(
                source_id=f"risk:{symbol}",
                source_type="risk",
                title=f"Portfolio Risk Profile — {symbol}",
                facts=facts,
                timestamp=result.computed_at.isoformat(),
                metadata={"periods_per_year": 252.0},
            )
        except Exception as exc:
            logger.warning("Failed to retrieve risk packet for %s: %s", symbol, exc)
            return None

    async def _retrieve_backtest_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        try:
            records, _ = await self._market_service.get_market_data(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )
            if len(records) < 3:
                return None

            events = [MarketEvent.from_ohlcv(b) for b in records]
            result, summary_metric, report, strategy_id, strategy_name = (
                self._backtest_service.run_simulation(
                    events=events,
                    strategy_id="BUY_AND_HOLD",
                    initial_cash=100_000.0,
                    commission_rate=0.0005,
                    slippage_rate=0.0005,
                    execution_convention=ExecutionPriceConvention.CURRENT_CLOSE,
                )
            )

            tot_ret = summary_metric.total_return
            ann_ret = summary_metric.annualized_return
            ann_vol = summary_metric.annualized_volatility
            bt_var = summary_metric.var_95
            bt_es = summary_metric.expected_shortfall_95
            bt_mdd = summary_metric.maximum_drawdown
            report_ts = report.generated_at.isoformat() if report.generated_at else end.isoformat()

            facts: dict[str, Any] = {
                "symbol": symbol,
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "initial_cash": result.initial_cash,
                "final_equity": round(summary_metric.final_equity, 2),
                "total_return": round(tot_ret, 4) if tot_ret is not None else None,
                "annualized_return": round(ann_ret, 4) if ann_ret is not None else None,
                "annualized_volatility": round(ann_vol, 4) if ann_vol is not None else None,
                "max_drawdown": round(bt_mdd, 4) if bt_mdd is not None else None,
                "win_rate": (
                    round(summary_metric.trades.win_rate, 4)
                    if summary_metric.trades.win_rate is not None
                    else None
                ),
                "completed_trades": summary_metric.trades.completed_trade_count,
                "total_fees": round(summary_metric.total_fees, 2),
                "commission_rate": 0.0005,
                "slippage_rate": 0.0005,
                "execution_convention": "CURRENT_CLOSE",
                "var_95": round(bt_var, 4) if bt_var is not None else None,
                "expected_shortfall_95": round(bt_es, 4) if bt_es is not None else None,
            }

            return EvidencePacket(
                source_id=f"backtest:{symbol}:{strategy_id}",
                source_type="backtest",
                title=f"Backtest Performance Report — {symbol} ({strategy_name})",
                facts=facts,
                timestamp=report_ts,
                metadata={"report_id": report.report_id, "version": report.report_version},
            )
        except Exception as exc:
            logger.warning("Failed to retrieve backtest packet for %s: %s", symbol, exc)
            return None

    async def _get_explanation_evidence(self, symbol: str) -> list[EvidencePacket]:
        """Retrieve model explanation evidence using the dedicated pipeline."""
        if self._explanation_pipeline is None:
            context_builder = ExplanationContextBuilder(
                market_service=self._market_service,
                market_intelligence=self._market_intelligence,
            )
            self._explanation_pipeline = ModelExplanationPipeline(
                context_builder=context_builder,
            )
        return await self._explanation_pipeline.build_explanation_evidence(symbol)

    def _build_methodology_packet(self) -> EvidencePacket:
        facts: dict[str, Any] = {
            "platform_purpose": (
                "RegimeX is a quantitative research and analytics platform designed to analyze "
                "market regimes, risk distributions, and systematic strategies. It is strictly "
                "a research interface and does not provide financial advice, trading signals, "
                "or future price predictions."
            ),
            "regime_engine": (
                "Statistical machine learning and Markov models classifying "
                "empirical market states."
            ),
            "risk_engine": (
                "Non-parametric empirical risk analytics using 252 annual trading periods."
            ),
            "backtest_engine": (
                "Deterministic event-driven execution with 5 bps commission "
                "and 5 bps slippage friction."
            ),
            "disclaimer": (
                "RegimeX provides quantitative research and historical/model-derived analytics. "
                "It does not provide personalized financial advice or guaranteed future outcomes."
            ),
        }
        return EvidencePacket(
            source_id="methodology:general",
            source_type="methodology",
            title="RegimeX Analytical Methodology & Platform Boundaries",
            facts=facts,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={"standards": "V13-V21"},
        )
