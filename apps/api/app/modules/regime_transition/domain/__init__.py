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
    RegimeTransitionAnalyticsProtocol,
    RegimeTransitionEngineProtocol,
)
from app.modules.regime_transition.domain.models import (
    GlobalTransitionAnalytics,
    RankedDestination,
    RegimeTransitionAnalytics,
    RegimeTransitionResult,
    TransitionAnalyticsResult,
    TransitionCountMatrix,
    TransitionProbability,
    TransitionProbabilityMatrix,
    TransitionRecord,
)

__all__ = [
    "GlobalTransitionAnalytics",
    "InsufficientTransitionDataError",
    "InvalidRegimeValueError",
    "InvalidTransitionSequenceError",
    "RankedDestination",
    "RegimeTransitionAnalytics",
    "RegimeTransitionAnalyticsProtocol",
    "RegimeTransitionComputationError",
    "RegimeTransitionEngineProtocol",
    "RegimeTransitionError",
    "RegimeTransitionResult",
    "TransitionAnalyticsResult",
    "TransitionCountMatrix",
    "TransitionProbability",
    "TransitionProbabilityMatrix",
    "TransitionRecord",
]
