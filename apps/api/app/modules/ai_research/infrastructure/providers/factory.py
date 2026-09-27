"""
RegimeX AI Research — Provider Factory
======================================
Configuration-driven provider instantiation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.ai_research.domain.interfaces import ResearchModelProvider
from app.modules.ai_research.infrastructure.providers.mock_provider import MockModelProvider
from app.modules.ai_research.infrastructure.providers.openai_provider import (
    OpenAICompatibleProvider,
)

if TYPE_CHECKING:
    from app.core.config import Settings


def get_model_provider(settings: Settings) -> ResearchModelProvider:
    """
    Factory creating a ResearchModelProvider based on application settings.
    """
    provider_type = settings.ai_provider.strip().lower()

    if provider_type == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
            model_name=settings.ai_model,
            timeout=settings.ai_timeout,
            max_tokens=settings.ai_max_tokens,
        )

    # Default to deterministic mock provider
    return MockModelProvider(model_name=settings.ai_model)
