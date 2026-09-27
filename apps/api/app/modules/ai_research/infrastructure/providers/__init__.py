"""
RegimeX AI Research — Model Provider Infrastructure
===================================================
Provider implementations connecting to external LLMs and deterministic local engines.
"""

from __future__ import annotations

from app.modules.ai_research.infrastructure.providers.factory import get_model_provider
from app.modules.ai_research.infrastructure.providers.mock_provider import MockModelProvider

__all__ = ["MockModelProvider", "get_model_provider"]
