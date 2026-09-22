"""
RegimeX Regime Transition — Domain Package
==========================================
Core domain models, error hierarchy, and interfaces for the regime transition module.
"""

from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
    InvalidRegimeValueError,
    InvalidTransitionSequenceError,
    RegimeTransitionComputationError,
    RegimeTransitionError,
)
from app.modules.regime_transition.domain.interfaces import (
    RegimeTransitionEngineProtocol,
)
from app.modules.regime_transition.domain.models import (
    RegimeTransitionResult,
    TransitionCountMatrix,
    TransitionProbability,
    TransitionProbabilityMatrix,
    TransitionRecord,
)

__all__ = [
    "InsufficientTransitionDataError",
    "InvalidRegimeValueError",
    "InvalidTransitionSequenceError",
    "RegimeTransitionComputationError",
    "RegimeTransitionEngineProtocol",
    "RegimeTransitionError",
    "RegimeTransitionResult",
    "TransitionCountMatrix",
    "TransitionProbability",
    "TransitionProbabilityMatrix",
    "TransitionRecord",
]
