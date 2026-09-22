"""
RegimeX Regime Transition Module
================================
Historical regime transition extraction, count matrices, empirical transition
probabilities, and transition result analytics.

Conforms to V12 specifications and V03 Clean Architecture guidelines.
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
from app.modules.regime_transition.infrastructure.engine import (
    RegimeTransitionEngine,
)

__all__ = [
    "InsufficientTransitionDataError",
    "InvalidRegimeValueError",
    "InvalidTransitionSequenceError",
    "RegimeTransitionComputationError",
    "RegimeTransitionEngine",
    "RegimeTransitionEngineProtocol",
    "RegimeTransitionError",
    "RegimeTransitionResult",
    "TransitionCountMatrix",
    "TransitionProbability",
    "TransitionProbabilityMatrix",
    "TransitionRecord",
]
