"""
RegimeX AI Research — Mock / Deterministic Grounded Model Provider
==================================================================
Deterministic, high-fidelity model provider for offline testing and default environments.
Generates institutional, 100% grounded answers with exact numerical precision and citations.
Requires zero external API keys or network access.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

import anyio

from app.modules.ai_research.application.routing import IntentRouter
from app.modules.ai_research.application.validator import GroundingValidator
from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.domain.models import EvidencePacket, ResearchIntent


class MockModelProvider(ResearchModelProvider):
    """
    Deterministic grounded model provider generating factual, cited answers from evidence packets.
    """

    def __init__(self, model_name: str = "deterministic-grounded-v1") -> None:
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> str:
        """
        Generate a fully cited response derived directly from the evidence packets.
        """
        intent = self._infer_intent_from_prompt(prompt)
        symbol = self._infer_symbol_from_prompt(prompt, evidence)

        # Build grounded response using verified deterministic synthesizer
        return GroundingValidator.generate_grounded_fallback(evidence, intent, symbol)

    async def stream(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens.
        """
        full_text = await self.generate(prompt, system_prompt, evidence)
        # Yield words with trailing whitespace
        words = re.findall(r"\S+\s*", full_text)
        for word in words:
            await anyio.sleep(0.005)
            yield word

    def _infer_intent_from_prompt(self, prompt: str) -> ResearchIntent:
        question = prompt
        for line in prompt.splitlines():
            if line.startswith("User Question:"):
                question = line.replace("User Question:", "").strip()
                break
        return IntentRouter.classify(question)

    def _infer_symbol_from_prompt(self, prompt: str, evidence: list[EvidencePacket]) -> str | None:
        for p in evidence:
            sym = p.facts.get("symbol")
            if sym and isinstance(sym, str):
                return sym
        return None
