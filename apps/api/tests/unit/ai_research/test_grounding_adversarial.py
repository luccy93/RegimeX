"""
RegimeX AI Research — Grounding Adversarial & Safety Tests
==========================================================
Verifies that GroundingValidator rejects malicious, inaccurate, or injected
responses, and enforces strict numeric integrity and safety invariants:
- Numerical fabrication rejection (e.g. volatility 42% when evidence is 18%)
- Invalid/out-of-bounds citation indices rejection
- Missing citation on factual answers rejection
- Prohibited trading recommendations and price target rejection
- Deterministic fallback generation upon validation failure
"""

from __future__ import annotations

import pytest
from app.modules.ai_research.application.validator import GroundingValidator
from app.modules.ai_research.domain.models import EvidencePacket, ResearchIntent


@pytest.fixture
def standard_evidence() -> list[EvidencePacket]:
    return [
        EvidencePacket(
            source_id="regime:SPY:current",
            source_type="regime",
            title="Regime Intelligence — SPY",
            facts={
                "symbol": "SPY",
                "current_regime_label": "BULLISH",
                "current_regime_id": 0,
                "confidence": 0.84,
                "observations_in_current_run": 25,
            },
            timestamp="2026-09-26T20:00:00Z",
            metadata={"algorithm": "Ensemble", "model_name": "v1.0"},
        ),
        EvidencePacket(
            source_id="risk:SPY",
            source_type="risk",
            title="Portfolio Risk Profile — SPY",
            facts={
                "symbol": "SPY",
                "annualized_volatility": 0.18,
                "max_drawdown": 0.085,
                "var_95": 0.015,
            },
            timestamp="2026-09-26T20:00:00Z",
            metadata={"engine": "Parametric"},
        ),
    ]


class TestGroundingValidatorAdversarial:
    """Tests defense against hallucinated or maliciously manipulated answers."""

    def test_rejects_fabricated_volatility(self, standard_evidence: list[EvidencePacket]) -> None:
        """Evidence has volatility = 0.18 (18%). Generated answer claims 42%."""
        hallucinated_answer = (
            "The annualized volatility of SPY is 42.0%, indicating severe market stress [2]."
        )
        is_valid, answer, citations = GroundingValidator.validate(
            answer=hallucinated_answer,
            evidence=standard_evidence,
            intent=ResearchIntent.RISK,
            symbol="SPY",
        )

        assert not is_valid, "Fabricated volatility must be rejected"
        # Must return the verified grounded fallback containing real values
        assert "18.00%" in answer or "18.0%" in answer or "0.18" in answer
        assert "42.0%" not in answer

    def test_rejects_fabricated_confidence(self, standard_evidence: list[EvidencePacket]) -> None:
        """Evidence has confidence = 0.84 (84%). Generated answer claims 99%."""
        hallucinated_answer = "SPY is classified in BULLISH regime with confidence of 99.0% [1]."
        is_valid, answer, _ = GroundingValidator.validate(
            answer=hallucinated_answer,
            evidence=standard_evidence,
            intent=ResearchIntent.CURRENT_REGIME,
            symbol="SPY",
        )

        assert not is_valid, "Fabricated confidence must be rejected"
        assert "84.0%" in answer or "0.84" in answer

    def test_rejects_out_of_bounds_citations(self, standard_evidence: list[EvidencePacket]) -> None:
        """Answer cites [99] when only [1] and [2] exist."""
        bad_citation_answer = "SPY is BULLISH [99]."
        is_valid, fallback, _ = GroundingValidator.validate(
            answer=bad_citation_answer,
            evidence=standard_evidence,
            intent=ResearchIntent.CURRENT_REGIME,
            symbol="SPY",
        )

        assert not is_valid, "Citation out of bounds must be rejected"
        assert "[99]" not in fallback

    def test_rejects_uncredited_factual_answer(
        self, standard_evidence: list[EvidencePacket]
    ) -> None:
        """Answer contains factual claim with zero citations."""
        uncited_answer = "SPY is currently in the BULLISH regime."
        is_valid, fallback, citations = GroundingValidator.validate(
            answer=uncited_answer,
            evidence=standard_evidence,
            intent=ResearchIntent.CURRENT_REGIME,
            symbol="SPY",
        )

        assert not is_valid, "Uncited factual answer must be rejected"
        assert len(citations) == 0

    def test_rejects_prohibited_recommendations(
        self, standard_evidence: list[EvidencePacket]
    ) -> None:
        """Answer attempts to give a buy recommendation."""
        recommendation_answers = [
            "You should buy SPY immediately [1].",
            "I recommend sell on SPY given the regime [1].",
            "This is a strong buy signal [1].",
            "Price target of $650 by next quarter [1].",
            "SPY will reach $600 by tomorrow [1].",
        ]

        for ans in recommendation_answers:
            is_valid, fallback, _ = GroundingValidator.validate(
                answer=ans,
                evidence=standard_evidence,
                intent=ResearchIntent.CURRENT_REGIME,
                symbol="SPY",
            )
            assert not is_valid, f"Prohibited recommendation must be rejected: {ans}"
            assert "buy" not in fallback.lower() or "not provide" in fallback.lower()

    def test_accepts_accurate_grounded_answer(
        self, standard_evidence: list[EvidencePacket]
    ) -> None:
        """Accurate answer matching evidence passes validation."""
        accurate_answer = (
            "Based on platform analytics, SPY is classified in the **BULLISH** regime "
            "with **84.0%** confidence [1]. The annualized realized volatility is **18.0%** [2]."
        )
        is_valid, answer, citations = GroundingValidator.validate(
            answer=accurate_answer,
            evidence=standard_evidence,
            intent=ResearchIntent.CURRENT_REGIME,
            symbol="SPY",
        )

        assert is_valid
        assert answer == accurate_answer
        assert citations == [1, 2]

    def test_prediction_refusal_intent_enforces_safety(
        self, standard_evidence: list[EvidencePacket]
    ) -> None:
        """Queries classified as PREDICTION_REFUSAL must refuse forward forecasts."""
        is_valid, answer, citations = GroundingValidator.validate(
            answer="Will SPY go up?",
            evidence=standard_evidence,
            intent=ResearchIntent.PREDICTION_REFUSAL,
            symbol="SPY",
        )

        assert is_valid
        assert "does not provide future price predictions" in answer
        assert "BULLISH" in answer  # redirects to verifiable historical regime

    def test_advice_refusal_intent_enforces_safety(self) -> None:
        """Queries classified as ADVICE_REFUSAL must refuse financial advice."""
        is_valid, answer, citations = GroundingValidator.validate(
            answer="Should I buy?",
            evidence=[],
            intent=ResearchIntent.ADVICE_REFUSAL,
            symbol="SPY",
        )

        assert is_valid
        assert "does not provide personalized financial advice" in answer
        assert citations == []

    def test_unsupported_intent_returns_bounded_scope(self) -> None:
        """Queries classified as UNSUPPORTED must state research scope."""
        is_valid, answer, citations = GroundingValidator.validate(
            answer="What is the weather?",
            evidence=[],
            intent=ResearchIntent.UNSUPPORTED,
        )

        assert is_valid
        assert "outside the scope of RegimeX" in answer
        assert citations == []
