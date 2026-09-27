"""
RegimeX AI Research — Domain Errors
===================================
Domain exceptions representing business and invariant violations in the research assistant.
Pure Python, free of framework-specific error wrappers.
"""

from __future__ import annotations


class ResearchDomainError(Exception):
    """Base exception for all AI research assistant domain errors."""

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GroundingValidationError(ResearchDomainError):
    """Raised when generated response fails citation grounding, integrity, or safety checks."""


class SymbolNotFoundError(ResearchDomainError):
    """Raised when an instrument symbol cannot be identified in the RegimeX market catalog."""


class InvalidQueryError(ResearchDomainError):
    """Raised when a research query is syntactically invalid or exceeds boundary constraints."""


class ProviderUnavailableError(ResearchDomainError):
    """
    Raised when the configured AI provider cannot complete generation due to timeout or failure.
    """


class UnsupportedQueryError(ResearchDomainError):
    """Raised when a question cannot be serviced by the research assistant."""
