"""
RegimeX AI Research — Domain Model Tests
========================================
Validates query input constraints, immutability, entity invariants, and serialization.
"""

from __future__ import annotations

import pytest
from app.modules.ai_research.domain.models import (
    Citation,
    EvidencePacket,
    ResearchIntent,
    ResearchQuery,
    ResearchResponse,
    ResearchStreamEvent,
)
from pydantic import ValidationError


class TestResearchQueryValidation:
    """Test validation boundaries on user research queries."""

    def test_valid_query(self) -> None:
        query = ResearchQuery(question="What regime is SPY currently in?", symbol="spy")
        assert query.question == "What regime is SPY currently in?"
        assert query.symbol == "SPY"
        assert query.stream is False

    def test_empty_question_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ResearchQuery(question="")

        with pytest.raises(ValidationError):
            ResearchQuery(question="   \n\t  ")

    def test_oversized_question_rejected(self) -> None:
        oversized = "a" * 1001
        with pytest.raises(ValidationError):
            ResearchQuery(question=oversized)

    def test_symbol_normalized_to_uppercase(self) -> None:
        query = ResearchQuery(question="Explain risk", symbol="  qqq  ")
        assert query.symbol == "QQQ"

    def test_none_symbol_preserved(self) -> None:
        query = ResearchQuery(question="What is the methodology?")
        assert query.symbol is None


class TestEvidencePacketAndCitations:
    """Test EvidencePacket and Citation entity semantics."""

    def test_evidence_packet_frozen(self) -> None:
        packet = EvidencePacket(
            source_id="regime:SPY:current",
            source_type="regime",
            title="Regime Intelligence — SPY",
            facts={"confidence": 0.884, "current_regime_label": "BULLISH"},
        )
        assert packet.source_id == "regime:SPY:current"
        with pytest.raises(ValidationError):
            # Immutable / frozen
            packet.source_id = "other"  # type: ignore[misc]

    def test_citation_id_validation(self) -> None:
        cit = Citation(
            id=1,
            source_id="risk:SPY",
            source_type="risk",
            title="Portfolio Risk Profile — SPY",
        )
        assert cit.id == 1

        with pytest.raises(ValidationError):
            Citation(
                id=0,
                source_id="risk:SPY",
                source_type="risk",
                title="Invalid id",
            )

    def test_research_response_structure(self) -> None:
        resp = ResearchResponse(
            answer="SPY is in the Bullish regime [1].",
            citations=[
                Citation(
                    id=1,
                    source_id="regime:SPY:current",
                    source_type="regime",
                    title="Regime SPY",
                )
            ],
            evidence=[],
            model="deterministic-mock",
            generated_at="2026-09-27T10:00:00Z",
            request_id="req-123",
            intent=ResearchIntent.CURRENT_REGIME,
            symbol="SPY",
        )
        assert resp.answer == "SPY is in the Bullish regime [1]."
        assert len(resp.citations) == 1
        assert resp.intent == ResearchIntent.CURRENT_REGIME

    def test_stream_event_serialization(self) -> None:
        event = ResearchStreamEvent(event="token", data={"token": "Hello"})
        dumped = event.model_dump()
        assert dumped["event"] == "token"
        assert dumped["data"]["token"] == "Hello"
