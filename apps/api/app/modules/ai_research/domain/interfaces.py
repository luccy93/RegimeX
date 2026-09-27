"""
RegimeX AI Research — Domain Interfaces
=======================================
Abstract interfaces and protocols governing external AI model providers and retrieval contracts.
Decoupled from third-party vendor SDKs and network protocols.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.modules.ai_research.domain.models import EvidencePacket


class ResearchModelProvider(ABC):
    """
    Abstract contract for AI model providers capable of generating grounded responses.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider implementation (e.g. 'mock', 'openai')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the underlying model (e.g. 'gpt-4o-mini', 'deterministic-mock')."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> str:
        """
        Generate a complete grounded response string given prompt and structured evidence.
        """
        ...

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: str,
        evidence: list[EvidencePacket],
    ) -> AsyncGenerator[str, None]:
        """
        Yield partial token strings as they become available.
        """
        ...
