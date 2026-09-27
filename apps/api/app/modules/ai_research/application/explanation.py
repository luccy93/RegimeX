"""
RegimeX AI Research — Model-Aware Explanation Pipeline
======================================================
Constructs structured explanation contexts from regime detection model metadata,
feature engineering outputs, classification confidence, transition dynamics, and
ensemble diagnostics. Generates validated explanations without inventing internal
model reasoning.

Core principle:
    Observed Data → Feature Engineering → Model Output → Model Metadata/Diagnostics
    → Structured Explanation Context → LLM Explanation → Grounding Validation
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.modules.ai_research.domain.models import EvidencePacket
from app.modules.market_data.domain.models import DataInterval

if TYPE_CHECKING:
    from app.modules.market_data.application.service import MarketDataService
    from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade

logger = logging.getLogger(__name__)


class ExplanationContextBuilder:
    """
    Builds structured explanation context from model metadata and diagnostics.

    Gathers feature engineering outputs, model provenance, regime classification
    confidence vectors, feature centroids, transition probabilities, and ensemble
    component information into auditable evidence packets suitable for grounded
    LLM explanation.
    """

    def __init__(
        self,
        market_service: MarketDataService,
        market_intelligence: MarketIntelligenceFacade,
    ) -> None:
        self._market_service = market_service
        self._market_intelligence = market_intelligence

    async def build_explanation_packets(
        self,
        symbol: str,
    ) -> list[EvidencePacket]:
        """
        Assemble all model explanation evidence packets for the given symbol.

        Returns an ordered list containing:
        - Model provenance and configuration packet
        - Feature engineering context packet
        - Regime classification confidence packet
        - Regime profile comparison packet (why this regime vs others)
        - Transition dynamics context packet
        """
        packets: list[EvidencePacket] = []
        clean_symbol = symbol.strip().upper()
        now_utc = datetime.now(UTC)
        start_utc = now_utc - timedelta(days=365)

        # 1. Model Provenance & Classification Context
        provenance_packet = await self._build_model_provenance_packet(
            clean_symbol, start_utc, now_utc
        )
        if provenance_packet:
            packets.append(provenance_packet)

        # 2. Feature Engineering Context
        feature_packet = await self._build_feature_context_packet(clean_symbol, start_utc, now_utc)
        if feature_packet:
            packets.append(feature_packet)

        # 3. Regime Profile Comparison (why this regime, not another)
        profile_comparison = await self._build_profile_comparison_packet(
            clean_symbol, start_utc, now_utc
        )
        if profile_comparison:
            packets.append(profile_comparison)

        # 4. Transition Dynamics Context
        transition_ctx = await self._build_transition_context_packet(
            clean_symbol, start_utc, now_utc
        )
        if transition_ctx:
            packets.append(transition_ctx)

        return packets

    async def _build_model_provenance_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        """Build evidence packet with model metadata, algorithm, version, and confidence."""
        try:
            summary, confidence = await self._market_intelligence.get_market_regime(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )

            current = summary.current_regime
            facts: dict[str, Any] = {
                "symbol": symbol,
                "model_name": summary.model_name,
                "model_version": summary.model_version,
                "algorithm": summary.algorithm,
                "total_observations": summary.total_observations,
                "regimes_observed": list(summary.regimes_observed),
                "feature_names": list(summary.feature_names),
                "current_regime_id": current.current_regime_id if current else None,
                "current_regime_label": current.current_regime_label if current else "UNKNOWN",
                "classification_confidence": (
                    round(confidence, 4) if confidence is not None else None
                ),
                "observations_in_current_run": (
                    current.observations_in_current_run if current else None
                ),
            }

            analysis_window: dict[str, str | None] = {
                "analysis_start": (
                    summary.analysis_start.isoformat() if summary.analysis_start else None
                ),
                "analysis_end": (
                    summary.analysis_end.isoformat() if summary.analysis_end else None
                ),
            }
            facts["analysis_window"] = analysis_window

            return EvidencePacket(
                source_id=f"model-provenance:{symbol}",
                source_type="model_explanation",
                title=f"Model Provenance & Classification — {symbol}",
                facts=facts,
                timestamp=(
                    current.current_timestamp.isoformat()
                    if current and current.current_timestamp
                    else end.isoformat()
                ),
                metadata={
                    "explanation_type": "model_provenance",
                    "algorithm": summary.algorithm,
                    "model_name": summary.model_name,
                },
            )
        except Exception as exc:
            logger.warning("Failed to build model provenance for %s: %s", symbol, exc)
            return None

    async def _build_feature_context_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        """Build evidence packet explaining feature engineering and current feature values."""
        try:
            summary, _ = await self._market_intelligence.get_market_regime(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )

            current = summary.current_regime
            if not current:
                return None

            facts: dict[str, Any] = {
                "symbol": symbol,
                "feature_names": list(summary.feature_names),
                "feature_count": len(summary.feature_names),
            }

            # Current feature values at the latest observation
            if current.current_features:
                current_features: dict[str, float | None] = {}
                for feat_name, feat_val in current.current_features.items():
                    current_features[feat_name] = (
                        round(feat_val, 6) if feat_val is not None else None
                    )
                facts["current_feature_values"] = current_features

            # Feature statistics for the current regime (how features typically
            # look in this state)
            current_profile = summary.get_profile(current.current_regime_id)
            if current_profile and current_profile.feature_statistics:
                regime_feature_stats: dict[str, dict[str, float | None]] = {}
                for feat_name, stat in current_profile.feature_statistics.items():
                    regime_feature_stats[feat_name] = {
                        "mean": round(stat.mean, 6) if stat.mean is not None else None,
                        "std": round(stat.std, 6) if stat.std is not None else None,
                        "min": round(stat.min, 6) if stat.min is not None else None,
                        "max": round(stat.max, 6) if stat.max is not None else None,
                        "observation_count": stat.observation_count,
                    }
                facts["regime_feature_statistics"] = regime_feature_stats

            return EvidencePacket(
                source_id=f"feature-context:{symbol}",
                source_type="model_explanation",
                title=f"Feature Engineering Context — {symbol}",
                facts=facts,
                timestamp=current.current_timestamp.isoformat(),
                metadata={
                    "explanation_type": "feature_context",
                    "current_regime": current.current_regime_label,
                },
            )
        except Exception as exc:
            logger.warning("Failed to build feature context for %s: %s", symbol, exc)
            return None

    async def _build_profile_comparison_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        """Build evidence explaining why the model chose the current regime vs alternatives."""
        try:
            summary, confidence = await self._market_intelligence.get_market_regime(
                symbol=symbol,
                start=start,
                end=end,
                interval=DataInterval.ONE_DAY,
                limit=1000,
            )

            current = summary.current_regime
            if not current or not summary.regime_profiles:
                return None

            facts: dict[str, Any] = {
                "symbol": symbol,
                "assigned_regime_id": current.current_regime_id,
                "assigned_regime_label": current.current_regime_label,
                "classification_confidence": (
                    round(confidence, 4) if confidence is not None else None
                ),
                "total_regimes": len(summary.regime_profiles),
            }

            # Build per-regime comparison summary
            regime_comparison: dict[str, dict[str, Any]] = {}
            for r_id, profile in summary.regime_profiles.items():
                is_current = r_id == current.current_regime_id
                regime_info: dict[str, Any] = {
                    "regime_id": profile.regime_id,
                    "label": profile.regime_label,
                    "is_current_assignment": is_current,
                    "historical_frequency": round(profile.frequency, 4),
                    "historical_percentage": round(profile.percentage, 2),
                    "average_duration": round(profile.average_duration, 1),
                    "max_duration": profile.max_duration,
                    "observation_count": profile.observation_count,
                }

                # Summarize key feature means for comparison
                feature_means: dict[str, float | None] = {}
                for feat_name, stat in profile.feature_statistics.items():
                    feature_means[feat_name] = (
                        round(stat.mean, 6) if stat.mean is not None else None
                    )
                if feature_means:
                    regime_info["feature_means"] = feature_means

                regime_comparison[f"regime_{r_id}_{profile.regime_label}"] = regime_info

            facts["regime_comparison"] = regime_comparison

            return EvidencePacket(
                source_id=f"regime-comparison:{symbol}",
                source_type="model_explanation",
                title=f"Regime Classification Comparison — {symbol}",
                facts=facts,
                timestamp=(
                    current.current_timestamp.isoformat()
                    if current.current_timestamp
                    else end.isoformat()
                ),
                metadata={
                    "explanation_type": "regime_comparison",
                    "assigned_regime": current.current_regime_label,
                },
            )
        except Exception as exc:
            logger.warning("Failed to build regime comparison for %s: %s", symbol, exc)
            return None

    async def _build_transition_context_packet(
        self, symbol: str, start: datetime, end: datetime
    ) -> EvidencePacket | None:
        """Build evidence on transition dynamics relevant to the explanation."""
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
            }

            # Per-regime transition analytics for explanation context
            for r_id, ra in analytics.regime_analytics.items():
                facts[f"regime_{r_id}_{ra.regime_label}_transitions"] = {
                    "persistence_probability": round(ra.persistence_probability, 4),
                    "change_rate": round(ra.change_rate, 4),
                    "most_likely_destination": ra.most_likely_destination,
                    "most_likely_destination_probability": round(
                        ra.most_likely_destination_probability, 4
                    ),
                    "transition_entropy": round(ra.transition_entropy, 4),
                }

            return EvidencePacket(
                source_id=f"transition-explanation:{symbol}",
                source_type="model_explanation",
                title=f"Transition Dynamics Context — {symbol}",
                facts=facts,
                timestamp=end.isoformat(),
                metadata={
                    "explanation_type": "transition_context",
                    "regimes_count": ga.number_of_regimes,
                },
            )
        except Exception as exc:
            logger.warning("Failed to build transition context for %s: %s", symbol, exc)
            return None


class ModelExplanationPipeline:
    """
    Orchestrates model-aware explanation generation.

    Coordinates between ExplanationContextBuilder and grounding validation
    to produce structured, verified explanations of model behavior.
    """

    def __init__(
        self,
        context_builder: ExplanationContextBuilder,
    ) -> None:
        self._context_builder = context_builder

    async def build_explanation_evidence(
        self,
        symbol: str,
    ) -> list[EvidencePacket]:
        """
        Build the full set of explanation evidence packets.

        Returns structured evidence covering:
        - Model provenance and configuration
        - Feature engineering context
        - Regime profile comparison
        - Transition dynamics
        """
        packets = await self._context_builder.build_explanation_packets(symbol)

        # Always append methodology context for explanation queries
        packets.append(self._build_explanation_methodology_packet())

        return packets

    def _build_explanation_methodology_packet(self) -> EvidencePacket:
        """Build methodology packet specific to model explanations."""
        facts: dict[str, Any] = {
            "explanation_scope": (
                "Model explanations describe observable model behavior: which features "
                "were engineered, what algorithm was used, what confidence level was assigned, "
                "and how the current classification compares to historical regime profiles. "
                "Explanations do not reveal internal model weights, gradient information, "
                "or proprietary algorithmic details."
            ),
            "feature_engineering": (
                "Features are computed from OHLCV market data using deterministic statistical "
                "transformations: returns, rolling volatility, momentum indicators, and "
                "volume-weighted metrics. Feature values at each timestamp drive the "
                "classification model input."
            ),
            "classification_methodology": (
                "Regime classification uses statistical machine learning algorithms "
                "(K-Means, GMM, HMM, or ensemble consensus) to partition feature space "
                "into distinct market states. Confidence scores represent model assignment "
                "certainty, not prediction accuracy."
            ),
            "transition_methodology": (
                "Transition probabilities are computed empirically from observed consecutive "
                "regime assignments. They represent historical frequencies, not predictive "
                "forecasts of future regime changes."
            ),
            "limitations": (
                "Model explanations are descriptive, not causal. They describe what the "
                "model observed and classified, not why the market behaved in a particular "
                "way. Past classification patterns do not guarantee future model behavior."
            ),
        }
        return EvidencePacket(
            source_id="methodology:model-explanation",
            source_type="methodology",
            title="Model Explanation Methodology & Scope",
            facts=facts,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={"standards": "V21"},
        )
