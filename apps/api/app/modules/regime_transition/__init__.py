"""
RegimeX Regime Transition Module
================================
Historical regime transition extraction, count matrices, empirical transition
probabilities, and downstream transition analytics.

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
    RegimeTransitionAnalyticsProtocol,
    RegimeTransitionEngineProtocol,
)
from app.modules.regime_transition.domain.models import (
    GlobalTransitionAnalytics,
    RankedDestination,
    RegimeTransitionResult,
    TransitionAnalyticsResult,
    TransitionCountMatrix,
    TransitionProbability,
    TransitionProbabilityMatrix,
    TransitionRecord,
)
from app.modules.regime_transition.domain.models import (
    RegimeTransitionAnalytics as RegimeTransitionAnalyticsModel,
)
from app.modules.regime_transition.infrastructure.analytics import (
    RegimeTransitionAnalytics,
)
from app.modules.regime_transition.infrastructure.engine import (
    RegimeTransitionEngine,
)

__all__ = [
    "GlobalTransitionAnalytics",
    "InsufficientTransitionDataError",
    "InvalidRegimeValueError",
    "InvalidTransitionSequenceError",
    "RankedDestination",
    "RegimeTransitionAnalytics",
    "RegimeTransitionAnalyticsModel",
    "RegimeTransitionAnalyticsProtocol",
    "RegimeTransitionComputationError",
    "RegimeTransitionEngine",
    "RegimeTransitionEngineProtocol",
    "RegimeTransitionError",
    "RegimeTransitionResult",
    "TransitionAnalyticsResult",
    "TransitionCountMatrix",
    "TransitionProbability",
    "TransitionProbabilityMatrix",
    "TransitionRecord",
]
