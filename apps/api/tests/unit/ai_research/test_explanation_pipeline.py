"""
RegimeX AI Research — Model Explanation Pipeline Tests
======================================================
Verifies the model-aware explanation pipeline including:
- ExplanationContextBuilder packet assembly
- ModelExplanationPipeline orchestration
- Routing for explanation-type queries
- Grounding validator fallback for MODEL_EXPLANATION intent
- End-to-end service integration with explanation queries
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.modules.ai_research.application.explanation import (
    ExplanationContextBuilder,
    ModelExplanationPipeline,
)
from app.modules.ai_research.application.routing import IntentRouter
from app.modules.ai_research.application.service import AIResearchService
from app.modules.ai_research.application.validator import GroundingValidator
from app.modules.ai_research.domain.models import (
    EvidencePacket,
    ResearchIntent,
    ResearchQuery,
)
from app.modules.ai_research.infrastructure.providers.mock_provider import MockModelProvider
from app.modules.backtesting.application.service import BacktestingService
from app.modules.market_data.application.service import (
    DEFAULT_BENCHMARK_MARKETS,
    MarketDataService,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from app.modules.portfolio_risk.application.service import PortfolioRiskService
from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade


class SyntheticMarketDataProvider(MarketDataProvider):
    """Provides deterministic synthetic bars for tests."""

    @property
    def provider_id(self) -> str:
        return "synthetic"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="synthetic",
            display_name="Synthetic",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        return list(DEFAULT_BENCHMARK_MARKETS)

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol in {m.symbol for m in DEFAULT_BENCHMARK_MARKETS}

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        base_time = query.start
        bars: list[OHLCVRecord] = []
        base_price = 100.0

        for i in range(120):
            t = base_time + timedelta(days=i)
            if t >= query.end:
                break
            p = base_price + (i * 0.2)
            bars.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=t,
                    open=p - 0.5,
                    high=p + 1.0,
                    low=p - 1.0,
                    close=p,
                    volume=1_000_000,
                    interval=query.interval,
                    source_provider_id=self.provider_id,
                )
            )

        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(bars),
        )


class TestExplanationRouting:
    """Test that explanation-type queries route to MODEL_EXPLANATION intent."""

    @pytest.mark.parametrize(
        "question,expected",
        [
            ("Why is SPY classified in this regime?", ResearchIntent.MODEL_EXPLANATION),
            ("How did the model decide on the current regime?", ResearchIntent.MODEL_EXPLANATION),
            ("Explain the classification for SPY", ResearchIntent.MODEL_EXPLANATION),
            ("What features drove the regime assignment?", ResearchIntent.MODEL_EXPLANATION),
            ("What is the model confidence for SPY?", ResearchIntent.MODEL_EXPLANATION),
            ("Why this regime and not another?", ResearchIntent.MODEL_EXPLANATION),
            (
                "How confident is the model in this classification?",
                ResearchIntent.MODEL_EXPLANATION,
            ),
            ("Explain the confidence for SPY regime", ResearchIntent.MODEL_EXPLANATION),
            ("What factors contributed to the regime detection?", ResearchIntent.MODEL_EXPLANATION),
            ("What algorithm is used for regime detection?", ResearchIntent.MODEL_EXPLANATION),
            ("Model provenance for SPY", ResearchIntent.MODEL_EXPLANATION),
            ("What made the model choose this regime?", ResearchIntent.MODEL_EXPLANATION),
            ("Why not another regime for SPY?", ResearchIntent.MODEL_EXPLANATION),
            ("Feature importance for regime classification", ResearchIntent.MODEL_EXPLANATION),
            # These should NOT route to MODEL_EXPLANATION
            ("What regime is SPY in?", ResearchIntent.CURRENT_REGIME),
            ("What is the methodology?", ResearchIntent.METHODOLOGY),
            ("Should I buy SPY?", ResearchIntent.ADVICE_REFUSAL),
            ("Will SPY rise tomorrow?", ResearchIntent.PREDICTION_REFUSAL),
        ],
    )
    def test_explanation_routing(self, question: str, expected: ResearchIntent) -> None:
        result = IntentRouter.classify(question)
        assert result == expected, f"Expected {expected.value} for '{question}', got {result.value}"


class TestExplanationContextBuilder:
    """Test ExplanationContextBuilder assembles correct evidence packets."""

    @pytest.fixture
    def builder(self) -> ExplanationContextBuilder:
        market_service = MarketDataService(provider=SyntheticMarketDataProvider())
        market_intel = MarketIntelligenceFacade(market_service=market_service)
        return ExplanationContextBuilder(
            market_service=market_service,
            market_intelligence=market_intel,
        )

    @pytest.mark.asyncio
    async def test_build_explanation_packets_returns_multiple(
        self, builder: ExplanationContextBuilder
    ) -> None:
        packets = await builder.build_explanation_packets("SPY")

        assert len(packets) >= 2, "Should have at least provenance + feature context packets"

        # Verify packet source types
        source_types = [p.source_type for p in packets]
        assert "model_explanation" in source_types

    @pytest.mark.asyncio
    async def test_provenance_packet_contains_model_metadata(
        self, builder: ExplanationContextBuilder
    ) -> None:
        packets = await builder.build_explanation_packets("SPY")

        provenance = next(
            (p for p in packets if p.metadata.get("explanation_type") == "model_provenance"),
            None,
        )
        assert provenance is not None, "Provenance packet must be present"
        assert provenance.facts.get("symbol") == "SPY"
        assert provenance.facts.get("model_name") is not None
        assert provenance.facts.get("algorithm") is not None
        assert provenance.facts.get("feature_names") is not None
        assert provenance.facts.get("classification_confidence") is not None
        assert provenance.facts.get("current_regime_label") is not None

    @pytest.mark.asyncio
    async def test_feature_context_packet_contains_features(
        self, builder: ExplanationContextBuilder
    ) -> None:
        packets = await builder.build_explanation_packets("SPY")

        feature_ctx = next(
            (p for p in packets if p.metadata.get("explanation_type") == "feature_context"),
            None,
        )
        assert feature_ctx is not None, "Feature context packet must be present"
        assert feature_ctx.facts.get("symbol") == "SPY"
        feature_count = feature_ctx.facts.get("feature_count")
        assert feature_count is not None
        assert isinstance(feature_count, int) and feature_count > 0

    @pytest.mark.asyncio
    async def test_regime_comparison_packet_present(
        self, builder: ExplanationContextBuilder
    ) -> None:
        packets = await builder.build_explanation_packets("SPY")

        comparison = next(
            (p for p in packets if p.metadata.get("explanation_type") == "regime_comparison"),
            None,
        )
        assert comparison is not None, "Regime comparison packet must be present"
        assert comparison.facts.get("assigned_regime_label") is not None
        assert comparison.facts.get("total_regimes") is not None
        assert comparison.facts.get("regime_comparison") is not None

    @pytest.mark.asyncio
    async def test_transition_context_packet_present(
        self, builder: ExplanationContextBuilder
    ) -> None:
        packets = await builder.build_explanation_packets("SPY")

        transition_ctx = next(
            (p for p in packets if p.metadata.get("explanation_type") == "transition_context"),
            None,
        )
        assert transition_ctx is not None, "Transition context packet must be present"
        assert transition_ctx.facts.get("global_persistence_rate") is not None
        assert transition_ctx.facts.get("global_change_rate") is not None


class TestModelExplanationPipeline:
    """Test ModelExplanationPipeline orchestration."""

    @pytest.fixture
    def pipeline(self) -> ModelExplanationPipeline:
        market_service = MarketDataService(provider=SyntheticMarketDataProvider())
        market_intel = MarketIntelligenceFacade(market_service=market_service)
        context_builder = ExplanationContextBuilder(
            market_service=market_service,
            market_intelligence=market_intel,
        )
        return ModelExplanationPipeline(context_builder=context_builder)

    @pytest.mark.asyncio
    async def test_build_explanation_evidence_includes_methodology(
        self, pipeline: ModelExplanationPipeline
    ) -> None:
        packets = await pipeline.build_explanation_evidence("SPY")

        # Should include methodology packet for explanation scope
        methodology = next(
            (p for p in packets if p.source_type == "methodology"),
            None,
        )
        assert methodology is not None
        assert "explanation_scope" in methodology.facts

    @pytest.mark.asyncio
    async def test_build_explanation_evidence_all_packets(
        self, pipeline: ModelExplanationPipeline
    ) -> None:
        packets = await pipeline.build_explanation_evidence("SPY")

        # At minimum: provenance, feature_context, comparison, transition, methodology
        assert len(packets) >= 4

        explanation_types = [
            p.metadata.get("explanation_type")
            for p in packets
            if p.source_type == "model_explanation"
        ]
        assert "model_provenance" in explanation_types
        assert "feature_context" in explanation_types


class TestExplanationValidatorFallback:
    """Test that GroundingValidator generates correct fallback for MODEL_EXPLANATION."""

    def _make_explanation_evidence(self) -> list[EvidencePacket]:
        return [
            EvidencePacket(
                source_id="model-provenance:SPY",
                source_type="model_explanation",
                title="Model Provenance & Classification — SPY",
                facts={
                    "symbol": "SPY",
                    "model_name": "kmeans-baseline",
                    "model_version": "1.0.0",
                    "algorithm": "KMeans",
                    "total_observations": 120,
                    "feature_names": ["return_1d", "volatility_20d", "momentum_10d"],
                    "current_regime_id": 0,
                    "current_regime_label": "REGIME_0",
                    "classification_confidence": 0.8567,
                    "observations_in_current_run": 5,
                },
                timestamp="2026-01-15T12:00:00+00:00",
                metadata={
                    "explanation_type": "model_provenance",
                    "algorithm": "KMeans",
                    "model_name": "kmeans-baseline",
                },
            ),
            EvidencePacket(
                source_id="feature-context:SPY",
                source_type="model_explanation",
                title="Feature Engineering Context — SPY",
                facts={
                    "symbol": "SPY",
                    "feature_names": ["return_1d", "volatility_20d", "momentum_10d"],
                    "feature_count": 3,
                    "current_feature_values": {
                        "return_1d": 0.0012,
                        "volatility_20d": 0.1523,
                        "momentum_10d": 0.0345,
                    },
                },
                timestamp="2026-01-15T12:00:00+00:00",
                metadata={
                    "explanation_type": "feature_context",
                    "current_regime": "REGIME_0",
                },
            ),
            EvidencePacket(
                source_id="regime-comparison:SPY",
                source_type="model_explanation",
                title="Regime Classification Comparison — SPY",
                facts={
                    "symbol": "SPY",
                    "assigned_regime_id": 0,
                    "assigned_regime_label": "REGIME_0",
                    "classification_confidence": 0.8567,
                    "total_regimes": 3,
                    "regime_comparison": {
                        "regime_0_REGIME_0": {
                            "regime_id": 0,
                            "label": "REGIME_0",
                            "is_current_assignment": True,
                            "historical_frequency": 0.45,
                            "observation_count": 54,
                        },
                        "regime_1_REGIME_1": {
                            "regime_id": 1,
                            "label": "REGIME_1",
                            "is_current_assignment": False,
                            "historical_frequency": 0.35,
                            "observation_count": 42,
                        },
                    },
                },
                timestamp="2026-01-15T12:00:00+00:00",
                metadata={
                    "explanation_type": "regime_comparison",
                    "assigned_regime": "REGIME_0",
                },
            ),
        ]

    def test_fallback_contains_model_metadata(self) -> None:
        evidence = self._make_explanation_evidence()
        result = GroundingValidator.generate_grounded_fallback(
            evidence=evidence,
            intent=ResearchIntent.MODEL_EXPLANATION,
            symbol="SPY",
        )

        assert "KMeans" in result
        assert "REGIME_0" in result
        assert "kmeans-baseline" in result
        assert "[1]" in result

    def test_fallback_contains_feature_values(self) -> None:
        evidence = self._make_explanation_evidence()
        result = GroundingValidator.generate_grounded_fallback(
            evidence=evidence,
            intent=ResearchIntent.MODEL_EXPLANATION,
            symbol="SPY",
        )

        assert "return_1d" in result
        assert "[2]" in result

    def test_fallback_contains_regime_comparison(self) -> None:
        evidence = self._make_explanation_evidence()
        result = GroundingValidator.generate_grounded_fallback(
            evidence=evidence,
            intent=ResearchIntent.MODEL_EXPLANATION,
            symbol="SPY",
        )

        assert "3" in result  # total_regimes
        assert "[3]" in result
        assert "REGIME_0" in result


class TestExplanationServiceIntegration:
    """End-to-end integration tests for explanation queries."""

    @pytest.fixture
    def service(self) -> AIResearchService:
        market_service = MarketDataService(provider=SyntheticMarketDataProvider())
        market_intel = MarketIntelligenceFacade(market_service=market_service)
        risk_service = PortfolioRiskService()
        backtest_service = BacktestingService()
        provider = MockModelProvider()

        return AIResearchService(
            market_service=market_service,
            market_intelligence=market_intel,
            risk_service=risk_service,
            backtest_service=backtest_service,
            provider=provider,
        )

    @pytest.mark.asyncio
    async def test_explanation_query_routes_and_responds(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="Why is SPY classified in this regime?")
        response = await service.execute_query(query, request_id="req-explain-1")

        assert response.intent == ResearchIntent.MODEL_EXPLANATION
        assert response.symbol == "SPY"
        assert len(response.evidence) > 0
        assert len(response.citations) > 0

    @pytest.mark.asyncio
    async def test_explanation_evidence_contains_model_packets(
        self, service: AIResearchService
    ) -> None:
        query = ResearchQuery(question="How did the model classify SPY?")
        response = await service.execute_query(query, request_id="req-explain-2")

        assert response.intent == ResearchIntent.MODEL_EXPLANATION

        # Evidence should contain model_explanation packets
        explanation_packets = [p for p in response.evidence if p.source_type == "model_explanation"]
        assert len(explanation_packets) >= 2

    @pytest.mark.asyncio
    async def test_explanation_query_has_grounded_answer(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What features drove the regime assignment for SPY?")
        response = await service.execute_query(query, request_id="req-explain-3")

        assert response.intent == ResearchIntent.MODEL_EXPLANATION
        # Answer must contain citation markers
        assert "[1]" in response.answer

    @pytest.mark.asyncio
    async def test_model_confidence_query(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="How confident is the model in SPY's classification?")
        response = await service.execute_query(query, request_id="req-explain-4")

        assert response.intent == ResearchIntent.MODEL_EXPLANATION
        assert response.symbol == "SPY"
        assert len(response.citations) > 0

    @pytest.mark.asyncio
    async def test_algorithm_query(self, service: AIResearchService) -> None:
        query = ResearchQuery(question="What algorithm is used for SPY regime detection?")
        response = await service.execute_query(query, request_id="req-explain-5")

        assert response.intent == ResearchIntent.MODEL_EXPLANATION
        assert response.symbol == "SPY"

    @pytest.mark.asyncio
    async def test_explanation_stream(self, service: AIResearchService) -> None:
        query = ResearchQuery(
            question="Why is SPY classified in this regime?",
            stream=True,
        )
        events = []
        async for event in service.stream_query(query, request_id="req-explain-stream"):
            events.append(event)

        event_types = [e.event for e in events]
        assert "metadata" in event_types
        assert "evidence" in event_types
        assert "token" in event_types
        assert "complete" in event_types

        # Verify the metadata event contains MODEL_EXPLANATION intent
        meta_event = next(e for e in events if e.event == "metadata")
        assert meta_event.data["intent"] == ResearchIntent.MODEL_EXPLANATION.value
