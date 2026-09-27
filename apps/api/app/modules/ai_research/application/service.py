"""
RegimeX AI Research — Application Service
=========================================
Coordinates query analysis, symbol resolution, deterministic evidence retrieval,
prompt assembly, AI model execution, grounding validation, and citation mapping.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.modules.ai_research.application.grounding import GroundingEngine
from app.modules.ai_research.application.retrieval import EvidenceRetriever
from app.modules.ai_research.application.routing import IntentRouter
from app.modules.ai_research.application.symbol_resolver import SymbolResolver
from app.modules.ai_research.application.validator import GroundingValidator
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import (
    ResearchIntent,
    ResearchQuery,
    ResearchResponse,
    ResearchStreamEvent,
)

if TYPE_CHECKING:
    from app.modules.backtesting.application.service import BacktestingService
    from app.modules.market_data.application.service import MarketDataService
    from app.modules.portfolio_risk.application.service import PortfolioRiskService
    from app.modules.regime_intelligence.application.facade import MarketIntelligenceFacade

logger = logging.getLogger(__name__)


class AIResearchService:
    """
    Application orchestrator for grounded AI market research interactions.
    """

    def __init__(
        self,
        market_service: MarketDataService,
        market_intelligence: MarketIntelligenceFacade,
        risk_service: PortfolioRiskService,
        backtest_service: BacktestingService,
        provider: ResearchModelProvider,
    ) -> None:
        self._market_service = market_service
        self._market_intelligence = market_intelligence
        self._risk_service = risk_service
        self._backtest_service = backtest_service
        self._provider = provider

        self._symbol_resolver = SymbolResolver(market_service=market_service)
        self._evidence_retriever = EvidenceRetriever(
            market_service=market_service,
            market_intelligence=market_intelligence,
            risk_service=risk_service,
            backtest_service=backtest_service,
        )

    async def execute_query(
        self,
        query: ResearchQuery,
        request_id: str,
    ) -> ResearchResponse:
        """
        Execute synchronous grounded research query.
        """
        now_iso = datetime.now(UTC).isoformat()

        # 1. Resolve Instrument Symbol
        canonical_symbol, unrecognized = await self._symbol_resolver.resolve(
            question=query.question,
            explicit_symbol=query.symbol,
        )

        if unrecognized and not canonical_symbol:
            return ResearchResponse(
                answer="I couldn't find that market in the current RegimeX catalog.",
                citations=[],
                evidence=[],
                model=self._provider.model_name,
                generated_at=now_iso,
                request_id=request_id,
                intent=ResearchIntent.UNSUPPORTED,
                symbol=None,
            )

        # 2. Classify Intent
        intent = IntentRouter.classify(query.question)

        # 3. Retrieve Grounded Evidence
        evidence = await self._evidence_retriever.retrieve_evidence(
            symbol=canonical_symbol,
            intent=intent,
        )

        # 4. Refusals for Prediction and Advice
        if intent in (ResearchIntent.PREDICTION_REFUSAL, ResearchIntent.ADVICE_REFUSAL):
            _, answer, cited_indices = GroundingValidator.validate(
                answer="",
                evidence=evidence,
                intent=intent,
                symbol=canonical_symbol,
            )
            all_citations = GroundingEngine.build_citations(evidence)
            used_citations = [c for c in all_citations if c.id in cited_indices]
            return ResearchResponse(
                answer=answer,
                citations=used_citations,
                evidence=evidence,
                model=self._provider.model_name,
                generated_at=now_iso,
                request_id=request_id,
                intent=intent,
                symbol=canonical_symbol,
            )

        # 5. Build Prompts and Citations
        system_prompt = GroundingEngine.build_system_prompt()
        user_prompt = GroundingEngine.build_user_prompt(
            question=query.question,
            evidence=evidence,
            symbol=canonical_symbol,
        )
        all_citations = GroundingEngine.build_citations(evidence)

        # 6. Generate Response via Provider
        try:
            raw_answer = await self._provider.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                evidence=evidence,
            )
        except Exception as exc:
            logger.warning("AI provider failed (%s); using deterministic fallback", exc)
            raw_answer = GroundingValidator.generate_grounded_fallback(
                evidence=evidence,
                intent=intent,
                symbol=canonical_symbol,
            )

        # 7. Validate Grounding and Safety
        is_valid, final_answer, cited_indices = GroundingValidator.validate(
            answer=raw_answer,
            evidence=evidence,
            intent=intent,
            symbol=canonical_symbol,
        )

        if not cited_indices and evidence:
            # Default to primary evidence citation
            used_citations = [all_citations[0]] if all_citations else []
        else:
            used_citations = [c for c in all_citations if c.id in cited_indices]

        return ResearchResponse(
            answer=final_answer,
            citations=used_citations,
            evidence=evidence,
            model=self._provider.model_name,
            generated_at=now_iso,
            request_id=request_id,
            intent=intent,
            symbol=canonical_symbol,
        )

    async def stream_query(
        self,
        query: ResearchQuery,
        request_id: str,
    ) -> AsyncGenerator[ResearchStreamEvent, None]:
        """
        Execute streaming research query emitting Server-Sent Events.
        """
        now_iso = datetime.now(UTC).isoformat()

        # 1. Resolve Instrument Symbol
        canonical_symbol, unrecognized = await self._symbol_resolver.resolve(
            question=query.question,
            explicit_symbol=query.symbol,
        )

        if unrecognized and not canonical_symbol:
            yield ResearchStreamEvent(
                event="metadata",
                data={
                    "request_id": request_id,
                    "intent": ResearchIntent.UNSUPPORTED.value,
                    "symbol": None,
                    "model": self._provider.model_name,
                },
            )
            msg = "I couldn't find that market in the current RegimeX catalog."
            yield ResearchStreamEvent(event="token", data={"token": msg})
            yield ResearchStreamEvent(
                event="complete",
                data={
                    "answer": msg,
                    "citations": [],
                    "evidence": [],
                    "model": self._provider.model_name,
                    "generated_at": now_iso,
                    "request_id": request_id,
                    "intent": ResearchIntent.UNSUPPORTED.value,
                    "symbol": None,
                },
            )
            return

        # 2. Classify Intent
        intent = IntentRouter.classify(query.question)

        yield ResearchStreamEvent(
            event="metadata",
            data={
                "request_id": request_id,
                "intent": intent.value,
                "symbol": canonical_symbol,
                "model": self._provider.model_name,
            },
        )

        # 3. Retrieve Evidence
        evidence = await self._evidence_retriever.retrieve_evidence(
            symbol=canonical_symbol,
            intent=intent,
        )

        yield ResearchStreamEvent(
            event="evidence",
            data={"evidence": [p.model_dump() for p in evidence]},
        )

        # 4. Refusals for Prediction and Advice
        if intent in (ResearchIntent.PREDICTION_REFUSAL, ResearchIntent.ADVICE_REFUSAL):
            _, answer, cited_indices = GroundingValidator.validate(
                answer="",
                evidence=evidence,
                intent=intent,
                symbol=canonical_symbol,
            )
            all_citations = GroundingEngine.build_citations(evidence)
            used_citations = [c for c in all_citations if c.id in cited_indices]
            yield ResearchStreamEvent(event="token", data={"token": answer})
            yield ResearchStreamEvent(
                event="citation",
                data={"citations": [c.model_dump() for c in used_citations]},
            )
            yield ResearchStreamEvent(
                event="complete",
                data={
                    "answer": answer,
                    "citations": [c.model_dump() for c in used_citations],
                    "evidence": [p.model_dump() for p in evidence],
                    "model": self._provider.model_name,
                    "generated_at": now_iso,
                    "request_id": request_id,
                    "intent": intent.value,
                    "symbol": canonical_symbol,
                },
            )
            return

        # 5. Build Prompts
        system_prompt = GroundingEngine.build_system_prompt()
        user_prompt = GroundingEngine.build_user_prompt(
            question=query.question,
            evidence=evidence,
            symbol=canonical_symbol,
        )
        all_citations = GroundingEngine.build_citations(evidence)

        # 6. Stream Tokens
        accumulated_chunks: list[str] = []
        try:
            async for token in self._provider.stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                evidence=evidence,
            ):
                accumulated_chunks.append(token)
                yield ResearchStreamEvent(event="token", data={"token": token})
        except Exception as exc:
            logger.warning("AI provider streaming failed (%s); using fallback", exc)
            fallback = GroundingValidator.generate_grounded_fallback(
                evidence=evidence,
                intent=intent,
                symbol=canonical_symbol,
            )
            accumulated_chunks = [fallback]
            yield ResearchStreamEvent(event="token", data={"token": fallback})

        # 7. Validate and Complete
        raw_answer = "".join(accumulated_chunks)
        is_valid, final_answer, cited_indices = GroundingValidator.validate(
            answer=raw_answer,
            evidence=evidence,
            intent=intent,
            symbol=canonical_symbol,
        )

        if not cited_indices and evidence:
            used_citations = [all_citations[0]] if all_citations else []
        else:
            used_citations = [c for c in all_citations if c.id in cited_indices]

        yield ResearchStreamEvent(
            event="citation",
            data={"citations": [c.model_dump() for c in used_citations]},
        )
        yield ResearchStreamEvent(
            event="complete",
            data={
                "answer": final_answer,
                "citations": [c.model_dump() for c in used_citations],
                "evidence": [p.model_dump() for p in evidence],
                "model": self._provider.model_name,
                "generated_at": now_iso,
                "request_id": request_id,
                "intent": intent.value,
                "symbol": canonical_symbol,
            },
        )
