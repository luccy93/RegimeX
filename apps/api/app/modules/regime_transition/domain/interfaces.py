"""
RegimeX Regime Transition — Domain Interfaces
=============================================
Defines protocols and conceptual contracts for the regime transition probability engine.

Architectural position: ``domain/interfaces.py`` — pure Python typing protocols.
Zero third-party library dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.modules.regime_detection.domain.models import (
        RegimeDetectionResult,
        RegimeEnsembleResult,
    )
    from app.modules.regime_intelligence.domain.models import RegimeAssignment
    from app.modules.regime_transition.domain.models import RegimeTransitionResult


@runtime_checkable
class RegimeTransitionEngineProtocol(Protocol):
    """Protocol for the regime transition probability calculation engine."""

    def compute_from_assignments(
        self,
        assignments: Sequence[RegimeAssignment],
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix and transition records from RegimeAssignments.

        Args:
            assignments: Chronologically ordered regime assignments.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).
        """
        ...

    def compute_from_detection_result(
        self,
        result: RegimeDetectionResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from a single model RegimeDetectionResult.

        Args:
            result: RegimeDetectionResult containing chronological RegimeRecords.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).
        """
        ...

    def compute_from_ensemble_result(
        self,
        result: RegimeEnsembleResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from a consensus RegimeEnsembleResult.

        Args:
            result: RegimeEnsembleResult containing chronological EnsembleRecords.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).
        """
        ...

    def compute_from_series(
        self,
        timestamps: Sequence[datetime],
        regime_ids: Sequence[int],
        labels: Sequence[str] | None = None,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from explicit timestamps and regime IDs.

        Args:
            timestamps: Chronologically ordered timezone-aware timestamps.
            regime_ids: Sequence of integer canonical regime IDs.
            labels: Optional sequence of regime string labels.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).
        """
        ...
