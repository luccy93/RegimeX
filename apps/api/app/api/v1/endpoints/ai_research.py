"""
RegimeX API v1 — AI Quantitative Research Endpoints
===================================================
Endpoints providing grounded market research capabilities backed by RegimeX analytics.
Strictly research-oriented: no price prediction, buy/sell signals, or financial advice.

Endpoints:
  POST /api/v1/research/query
  GET  /api/v1/research/context/{symbol}
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Path, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.v1.models import (
    CitationDTO,
    EvidencePacketDTO,
    ResearchQueryRequest,
    ResearchResponseDTO,
)
from app.core.dependencies import AIResearchServiceDep
from app.core.errors import BadRequestError
from app.modules.ai_research.domain.models import ResearchIntent, ResearchQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["AI Research"])


@router.post(
    "/query",
    response_model=ResearchResponseDTO,
    summary="Query AI Quantitative Market Research Assistant",
    description=(
        "Submits a natural language market research query to the RegimeX assistant. "
        "The assistant deterministically retrieves platform regime intelligence, "
        "empirical transition matrices, portfolio risk metrics, and backtest results, "
        "generating an institutional, grounded answer with traceable citations. "
        "Supports both synchronous JSON responses and Server-Sent Events (SSE) streaming."
    ),
)
async def query_research_assistant(
    request: Request,
    payload: ResearchQueryRequest,
    research_service: AIResearchServiceDep,
) -> Response:
    """Execute grounded market research query."""
    request_id: str = getattr(request.state, "request_id", str(uuid.uuid4()))

    clean_question = payload.question.strip()
    if not clean_question:
        raise BadRequestError("Research question cannot be empty or whitespace only.")

    domain_query = ResearchQuery(
        question=clean_question,
        symbol=payload.symbol,
        conversation_id=payload.conversation_id,
        context=payload.context,
        stream=payload.stream,
    )

    accept_header = request.headers.get("accept", "").lower()
    wants_stream = payload.stream or "text/event-stream" in accept_header

    if wants_stream:
        # Stream SSE events
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async for event in research_service.stream_query(domain_query, request_id):
                    event_data = json.dumps(event.data)
                    yield f"event: {event.event}\ndata: {event_data}\n\n"
            except Exception as exc:
                logger.error("Error during AI research stream: %s", exc, exc_info=True)
                err_data = json.dumps(
                    {"error": "Failed during stream generation.", "request_id": request_id}
                )
                yield f"event: error\ndata: {err_data}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )

    # Synchronous evaluation
    result = await research_service.execute_query(domain_query, request_id)

    citation_dtos = [
        CitationDTO(
            id=c.id,
            source_id=c.source_id,
            source_type=c.source_type,
            title=c.title,
            symbol=c.symbol,
            timestamp=c.timestamp,
            model=c.model,
            facts_summary=c.facts_summary,
            details=c.details,
        )
        for c in result.citations
    ]

    evidence_dtos = [
        EvidencePacketDTO(
            source_id=p.source_id,
            source_type=p.source_type,
            title=p.title,
            facts=p.facts,
            timestamp=p.timestamp,
            metadata=p.metadata,
        )
        for p in result.evidence
    ]

    response_dto = ResearchResponseDTO(
        answer=result.answer,
        citations=citation_dtos,
        evidence=evidence_dtos,
        model=result.model,
        generated_at=result.generated_at,
        request_id=result.request_id,
        intent=result.intent.value,
        symbol=result.symbol,
    )

    return JSONResponse(
        content=response_dto.model_dump(),
        headers={"X-Request-ID": request_id},
    )


@router.get(
    "/context/{symbol}",
    response_model=list[EvidencePacketDTO],
    summary="Retrieve Grounded Evidence Context for an Instrument",
    description="Retrieve all factual evidence packets assembled for an instrument symbol.",
)
async def get_instrument_evidence_context(
    symbol: Annotated[
        str, Path(min_length=1, max_length=20, description="Instrument ticker symbol")
    ],
    research_service: AIResearchServiceDep,
) -> list[EvidencePacketDTO]:
    """Retrieve grounded evidence context for an instrument symbol."""
    clean_symbol = symbol.strip().upper()
    evidence = await research_service._evidence_retriever.retrieve_evidence(
        symbol=clean_symbol,
        intent=ResearchIntent.MARKET_OVERVIEW,
    )

    return [
        EvidencePacketDTO(
            source_id=p.source_id,
            source_type=p.source_type,
            title=p.title,
            facts=p.facts,
            timestamp=p.timestamp,
            metadata=p.metadata,
        )
        for p in evidence
    ]
