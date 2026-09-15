"""
RegimeX Regime Intelligence — Domain Interfaces
===============================================
Defines protocols and conceptual contracts for regime intelligence components.

Architectural position: ``domain/interfaces.py`` — pure Python typing protocols.
Zero third-party library dependencies.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.modules.regime_intelligence.domain.models import (
    CurrentRegimeContext,
    FeatureStatistic,
    RegimeAssignment,
    RegimeHistorySummary,
    RegimeProfile,
)


@runtime_checkable
class FeatureStatisticsCalculator(Protocol):
    """Protocol for computing descriptive feature statistics from an observed series."""

    def compute(
        self,
        feature_name: str,
        values: Sequence[float | None],
    ) -> FeatureStatistic:
        """Compute descriptive statistics for a feature series, ignoring None values."""
        ...


@runtime_checkable
class DurationAnalyzerProtocol(Protocol):
    """Protocol for calculating regime duration runs and trailing run length."""

    def compute_runs(
        self,
        regime_series: Sequence[int],
    ) -> dict[int, list[int]]:
        """Compute run lengths (consecutive observation counts) for each observed regime."""
        ...

    def compute_current_run(
        self,
        regime_series: Sequence[int],
    ) -> tuple[int, int]:
        """
        Compute the active regime ID and its trailing consecutive observation count.

        Returns:
            tuple[int, int]: (current_regime_id, observations_in_current_run)
        """
        ...


@runtime_checkable
class RegimeIntelligenceServiceProtocol(Protocol):
    """Protocol for the application facade managing historical regime intelligence."""

    def build_profiles(
        self,
        assignments: Sequence[RegimeAssignment],
        total_observations: int | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> dict[int, RegimeProfile]:
        """Build historical profiles for all regimes observed in assignments."""
        ...

    def summarize_history(
        self,
        assignments: Sequence[RegimeAssignment],
        model_name: str | None = None,
        model_version: str | None = None,
        algorithm: str | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> RegimeHistorySummary:
        """Generate comprehensive historical summary analytics for a sequence of assignments."""
        ...

    def get_current_context(
        self,
        assignments: Sequence[RegimeAssignment],
        profiles: dict[int, RegimeProfile] | None = None,
    ) -> CurrentRegimeContext:
        """Compute descriptive context for the latest regime observation."""
        ...

    def rank_regimes(
        self,
        profiles: dict[int, RegimeProfile] | Sequence[RegimeProfile],
        metric: str = "frequency",
        ascending: bool = False,
    ) -> list[RegimeProfile]:
        """Rank regime profiles deterministically by a specified metric."""
        ...
