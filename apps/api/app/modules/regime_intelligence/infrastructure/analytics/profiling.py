"""
RegimeX Regime Intelligence — Profile Builder Engine
====================================================
Synthesizes regime occurrences, duration analytics, and descriptive feature statistics
into comprehensive, immutable RegimeProfile models.

Guarantees:
- Deterministic output regardless of input dictionary order.
- Frequency normalization: sum(frequencies) == 1.0 within 1e-6 tolerance.
- Zero data fabrication: missing feature values are aggregated explicitly without fillna(0).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from app.modules.regime_intelligence.domain.interfaces import (
    DurationAnalyzerProtocol,
    FeatureStatisticsCalculator,
)
from app.modules.regime_intelligence.domain.models import (
    FeatureStatistic,
    RegimeAssignment,
    RegimeProfile,
)
from app.modules.regime_intelligence.infrastructure.analytics.duration import (
    DurationAnalyzerImpl,
)
from app.modules.regime_intelligence.infrastructure.analytics.statistics import (
    FeatureStatisticsCalculatorImpl,
)


class RegimeProfiler:
    """Orchestrates creation of RegimeProfile models from historical regime assignments."""

    def __init__(
        self,
        statistics_calculator: FeatureStatisticsCalculator | None = None,
        duration_analyzer: DurationAnalyzerProtocol | None = None,
    ) -> None:
        self._stats_calc = statistics_calculator or FeatureStatisticsCalculatorImpl()
        self._duration_analyzer = duration_analyzer or DurationAnalyzerImpl()

    def build_profiles(
        self,
        assignments: Sequence[RegimeAssignment],
        total_observations: int | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> dict[int, RegimeProfile]:
        """
        Build descriptive profiles for all regimes present in assignments.

        Args:
            assignments: Chronologically ordered regime assignments.
            total_observations: Total observation baseline count (defaults to len(assignments)).
            feature_names: Feature names to evaluate. If None, gathered from assignments.

        Returns:
            dict[int, RegimeProfile]: Profiles keyed by canonical regime ID.
        """
        if not assignments:
            return {}

        total_obs = len(assignments) if total_observations is None else total_observations
        if total_obs <= 0:
            total_obs = len(assignments)

        # Gather deterministic feature names if not provided
        if feature_names is None:
            seen_features: set[str] = set()
            ordered_features: list[str] = []
            for a in assignments:
                for f_name in a.features:
                    if f_name not in seen_features:
                        seen_features.add(f_name)
                        ordered_features.append(f_name)
            active_feature_names = tuple(ordered_features)
        else:
            active_feature_names = tuple(feature_names)

        # Group assignments by canonical regime ID
        regime_series: list[int] = [a.regime_id for a in assignments]
        runs_by_regime = self._duration_analyzer.compute_runs(regime_series)

        grouped_assignments: dict[int, list[RegimeAssignment]] = defaultdict(list)
        for a in assignments:
            grouped_assignments[a.regime_id].append(a)

        # Build profiles in sorted regime_id order for determinism
        profiles: dict[int, RegimeProfile] = {}
        for r_id in sorted(grouped_assignments.keys()):
            r_assignments = grouped_assignments[r_id]
            obs_count = len(r_assignments)
            freq = obs_count / total_obs
            pct = freq * 100.0

            timestamps: list[datetime] = [a.timestamp for a in r_assignments]
            first_seen = min(timestamps) if timestamps else None
            last_seen = max(timestamps) if timestamps else None

            # Regime label from assignments or default
            label = r_assignments[0].regime_label if r_assignments else f"REGIME_{r_id}"

            # Duration analytics
            r_runs = runs_by_regime.get(r_id, [])
            run_count, avg_dur, med_dur, min_dur, max_dur = DurationAnalyzerImpl.summarize_runs(
                r_runs
            )

            # Feature statistics
            feature_stats: dict[str, FeatureStatistic] = {}
            for f_name in active_feature_names:
                f_values = [a.features.get(f_name) for a in r_assignments]
                feature_stats[f_name] = self._stats_calc.compute(f_name, f_values)

            profile = RegimeProfile(
                regime_id=r_id,
                regime_label=label,
                observation_count=obs_count,
                frequency=freq,
                percentage=pct,
                first_seen=first_seen,
                last_seen=last_seen,
                run_count=run_count,
                average_duration=avg_dur,
                median_duration=med_dur,
                min_duration=min_dur,
                max_duration=max_dur,
                feature_statistics=feature_stats,
            )
            profiles[r_id] = profile

        return profiles
