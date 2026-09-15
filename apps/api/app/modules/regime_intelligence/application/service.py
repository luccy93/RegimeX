"""
RegimeX Regime Intelligence — Application Service
=================================================
Application facade providing deterministic historical regime intelligence analytics.

Guarantees:
- Zero scikit-learn or model training dependencies.
- Descriptive historical analytics only (no forecasting or trading signals).
- Strict timestamp integrity (timezone-aware UTC, strictly monotonic increasing).
- Rejects duplicate timestamps with InvalidRegimeHistoryError.
- Deterministic ranking with canonical tie-breaking by regime_id ascending.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.regime_detection.domain.models import (
        FeatureMatrix,
        RegimeDetectionResult,
    )

from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
    InvalidRegimeAssignmentError,
    InvalidRegimeHistoryError,
    UnsupportedRankingMetricError,
)
from app.modules.regime_intelligence.domain.interfaces import (
    DurationAnalyzerProtocol,
    FeatureStatisticsCalculator,
    RegimeIntelligenceServiceProtocol,
)
from app.modules.regime_intelligence.domain.models import (
    CurrentRegimeContext,
    RegimeAssignment,
    RegimeHistorySummary,
    RegimeProfile,
)
from app.modules.regime_intelligence.infrastructure.analytics.duration import (
    DurationAnalyzerImpl,
)
from app.modules.regime_intelligence.infrastructure.analytics.profiling import (
    RegimeProfiler,
)
from app.modules.regime_intelligence.infrastructure.analytics.statistics import (
    FeatureStatisticsCalculatorImpl,
)


class RegimeIntelligenceService(RegimeIntelligenceServiceProtocol):
    """
    Application service orchestrating historical regime intelligence and analytics.

    Conforms to V03 Service Boundaries and Interface Specifications.
    """

    SUPPORTED_BASE_METRICS: tuple[str, ...] = (
        "frequency",
        "observation_count",
        "average_duration",
        "median_duration",
        "min_duration",
        "max_duration",
        "run_count",
    )

    def __init__(
        self,
        statistics_calculator: FeatureStatisticsCalculator | None = None,
        duration_analyzer: DurationAnalyzerProtocol | None = None,
    ) -> None:
        self._stats_calc = statistics_calculator or FeatureStatisticsCalculatorImpl()
        self._duration_analyzer = duration_analyzer or DurationAnalyzerImpl()
        self._profiler = RegimeProfiler(
            statistics_calculator=self._stats_calc,
            duration_analyzer=self._duration_analyzer,
        )

    def validate_assignments(
        self,
        assignments: Sequence[RegimeAssignment],
    ) -> None:
        """
        Validate timestamp monotonicity, timezone awareness, and regime ID validity.

        Raises:
            InvalidRegimeHistoryError: If timestamps are naive, non-ascending, or duplicated.
            InvalidRegimeAssignmentError: If regime IDs are negative or malformed.
        """
        if not assignments:
            return

        for i, a in enumerate(assignments):
            # Validate regime ID
            if not isinstance(a.regime_id, int) or a.regime_id < 0:
                raise InvalidRegimeAssignmentError(
                    f"Assignment at index {i} has invalid regime_id: {a.regime_id!r}."
                )

            # Validate timezone
            if a.timestamp.tzinfo is None:
                raise InvalidRegimeHistoryError(
                    f"Timestamp at index {i} is naive ({a.timestamp!r}). UTC required."
                )

            # Validate strict monotonicity
            if i > 0:
                prev_ts = assignments[i - 1].timestamp
                if a.timestamp == prev_ts:
                    raise InvalidRegimeHistoryError(
                        f"Duplicate timestamp detected at index {i}: {a.timestamp}."
                    )
                if a.timestamp < prev_ts:
                    raise InvalidRegimeHistoryError(
                        f"Timestamps must be strictly ascending: index {i} ({a.timestamp}) "
                        f"< index {i - 1} ({prev_ts})."
                    )

    def build_profiles(
        self,
        assignments: Sequence[RegimeAssignment],
        total_observations: int | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> dict[int, RegimeProfile]:
        """
        Build historical descriptive profiles for all regimes observed in assignments.

        Args:
            assignments: Chronologically ordered regime assignments.
            total_observations: Total observation count (defaults to len(assignments)).
            feature_names: Names of features to summarize.

        Returns:
            dict[int, RegimeProfile]: Profiles keyed by canonical regime ID.
        """
        self.validate_assignments(assignments)
        return self._profiler.build_profiles(
            assignments=assignments,
            total_observations=total_observations,
            feature_names=feature_names,
        )

    def get_current_context(
        self,
        assignments: Sequence[RegimeAssignment],
        profiles: dict[int, RegimeProfile] | None = None,
    ) -> CurrentRegimeContext:
        """
        Compute descriptive context for the latest regime observation.

        Args:
            assignments: Chronologically ordered regime assignments.
            profiles: Pre-computed profiles. If None, computed on the fly.

        Returns:
            CurrentRegimeContext: Context of the current active regime.

        Raises:
            InsufficientRegimeDataError: If assignments sequence is empty.
        """
        self.validate_assignments(assignments)
        if not assignments:
            raise InsufficientRegimeDataError(
                required_samples=1,
                available_samples=0,
                details={"message": "Cannot determine current context from empty history."},
            )

        active_profiles = profiles or self.build_profiles(assignments)
        regime_series = [a.regime_id for a in assignments]
        current_r_id, trailing_length = self._duration_analyzer.compute_current_run(regime_series)

        latest_assignment = assignments[-1]
        profile = active_profiles.get(current_r_id)

        if profile is not None:
            hist_freq = profile.frequency
            hist_avg_dur = profile.average_duration
            hist_max_dur = profile.max_duration
            hist_min_dur = profile.min_duration
            hist_run_count = profile.run_count
        else:
            hist_freq = 1.0
            hist_avg_dur = float(trailing_length)
            hist_max_dur = trailing_length
            hist_min_dur = trailing_length
            hist_run_count = 1

        return CurrentRegimeContext(
            current_regime_id=current_r_id,
            current_regime_label=latest_assignment.regime_label,
            current_timestamp=latest_assignment.timestamp,
            observations_in_current_run=trailing_length,
            historical_frequency=hist_freq,
            historical_average_duration=hist_avg_dur,
            historical_max_duration=hist_max_dur,
            historical_min_duration=hist_min_dur,
            historical_run_count=hist_run_count,
            current_features=latest_assignment.features or None,
        )

    def summarize_history(
        self,
        assignments: Sequence[RegimeAssignment],
        model_name: str | None = None,
        model_version: str | None = None,
        algorithm: str | None = None,
        feature_names: Sequence[str] | None = None,
    ) -> RegimeHistorySummary:
        """
        Compute a complete, immutable historical summary of regime observations.

        Args:
            assignments: Chronologically ordered regime assignments.
            model_name: Name of the generating regime model.
            model_version: Version of the generating regime model.
            algorithm: Algorithm identifier (e.g., 'kmeans_baseline').
            feature_names: Names of feature columns evaluated.

        Returns:
            RegimeHistorySummary: Complete historical analytics container.
        """
        self.validate_assignments(assignments)

        total_obs = len(assignments)
        if total_obs == 0:
            return RegimeHistorySummary(
                analysis_start=None,
                analysis_end=None,
                total_observations=0,
                regimes_observed=(),
                regime_profiles={},
                current_regime=None,
                model_name=model_name,
                model_version=model_version,
                algorithm=algorithm,
                feature_names=tuple(feature_names or ()),
                computed_at=datetime.now(tz=UTC),
            )

        profiles = self.build_profiles(
            assignments=assignments,
            total_observations=total_obs,
            feature_names=feature_names,
        )
        current_context = self.get_current_context(assignments, profiles=profiles)
        regimes_observed = tuple(sorted(profiles.keys()))

        # Determine feature names evaluated
        if feature_names is None:
            seen_f: set[str] = set()
            active_f: list[str] = []
            for a in assignments:
                for f_name in a.features:
                    if f_name not in seen_f:
                        seen_f.add(f_name)
                        active_f.append(f_name)
            resolved_feature_names = tuple(active_f)
        else:
            resolved_feature_names = tuple(feature_names)

        return RegimeHistorySummary(
            analysis_start=assignments[0].timestamp,
            analysis_end=assignments[-1].timestamp,
            total_observations=total_obs,
            regimes_observed=regimes_observed,
            regime_profiles=profiles,
            current_regime=current_context,
            model_name=model_name,
            model_version=model_version,
            algorithm=algorithm,
            feature_names=resolved_feature_names,
            computed_at=datetime.now(tz=UTC),
        )

    def rank_regimes(
        self,
        profiles: dict[int, RegimeProfile] | Sequence[RegimeProfile],
        metric: str = "frequency",
        ascending: bool = False,
    ) -> list[RegimeProfile]:
        """
        Deterministically rank regime profiles by a specified metric.

        Supported base metrics:
            - 'frequency'
            - 'observation_count'
            - 'average_duration'
            - 'median_duration'
            - 'min_duration'
            - 'max_duration'
            - 'run_count'

        Supported feature statistics metrics:
            - 'feature_mean:<feature_name>'
            - 'feature_median:<feature_name>'
            - 'feature_std:<feature_name>'
            - 'feature_min:<feature_name>'
            - 'feature_max:<feature_name>'

        Tie-breaking rule:
            Always breaks ties by regime_id ascending to guarantee determinism.

        Raises:
            UnsupportedRankingMetricError: If metric is unrecognized.
        """
        profile_list: list[RegimeProfile] = (
            list(profiles.values()) if isinstance(profiles, dict) else list(profiles)
        )
        if not profile_list:
            return []

        def get_metric_value(p: RegimeProfile) -> float:
            if metric == "frequency":
                return p.frequency
            if metric == "observation_count":
                return float(p.observation_count)
            if metric == "average_duration":
                return p.average_duration
            if metric == "median_duration":
                return p.median_duration
            if metric == "min_duration":
                return float(p.min_duration)
            if metric == "max_duration":
                return float(p.max_duration)
            if metric == "run_count":
                return float(p.run_count)

            # Feature statistics metrics
            if metric.startswith("feature_mean:"):
                f_name = metric.split(":", 1)[1]
                stat = p.feature_statistics.get(f_name)
                return stat.mean if (stat and stat.mean is not None) else float("-inf")
            if metric.startswith("feature_median:"):
                f_name = metric.split(":", 1)[1]
                stat = p.feature_statistics.get(f_name)
                return stat.median if (stat and stat.median is not None) else float("-inf")
            if metric.startswith("feature_std:"):
                f_name = metric.split(":", 1)[1]
                stat = p.feature_statistics.get(f_name)
                return stat.std if (stat and stat.std is not None) else float("-inf")
            if metric.startswith("feature_min:"):
                f_name = metric.split(":", 1)[1]
                stat = p.feature_statistics.get(f_name)
                return stat.min if (stat and stat.min is not None) else float("-inf")
            if metric.startswith("feature_max:"):
                f_name = metric.split(":", 1)[1]
                stat = p.feature_statistics.get(f_name)
                return stat.max if (stat and stat.max is not None) else float("-inf")

            raise UnsupportedRankingMetricError(
                metric=metric,
                supported_metrics=self.SUPPORTED_BASE_METRICS,
            )

        # First validate metric validity on the first profile
        get_metric_value(profile_list[0])

        # Sort: primary key = metric value, secondary key = regime_id (ascending for stability)
        # Note: when descending, higher metric comes first; ties broken by smaller regime_id
        if ascending:
            return sorted(profile_list, key=lambda p: (get_metric_value(p), p.regime_id))
        else:
            return sorted(profile_list, key=lambda p: (-get_metric_value(p), p.regime_id))

    @staticmethod
    def from_v08_result(
        detection_result: RegimeDetectionResult,
        feature_matrix: FeatureMatrix | None = None,
    ) -> list[RegimeAssignment]:
        """
        Translate V08 RegimeDetectionResult and optional FeatureMatrix into RegimeAssignments.

        Args:
            detection_result: V08 RegimeDetectionResult domain model.
            feature_matrix: Optional V08 FeatureMatrix domain model.

        Returns:
            list[RegimeAssignment]: Standardized V09 domain assignments.
        """
        assignments: list[RegimeAssignment] = []
        matrix_rows_by_ts: dict[datetime, dict[str, float | None]] = {}

        if feature_matrix is not None and hasattr(feature_matrix, "timestamps"):
            f_names = tuple(feature_matrix.feature_names)
            for ts, row in zip(feature_matrix.timestamps, feature_matrix.values, strict=False):
                matrix_rows_by_ts[ts] = dict(zip(f_names, row, strict=False))

        metadata = {
            "model_version": getattr(detection_result, "model_version", None),
            "algorithm": getattr(detection_result, "algorithm", None),
        }

        for record in getattr(detection_result, "records", ()):
            ts = record.timestamp
            f_vals = matrix_rows_by_ts.get(ts, {})
            # Confidence: max probability if probabilities provided
            conf = max(record.probabilities) if getattr(record, "probabilities", None) else None

            assignment = RegimeAssignment(
                timestamp=ts,
                regime_id=record.canonical_regime_id,
                regime_label=record.canonical_regime_label,
                features=f_vals,
                confidence=conf,
                model_metadata=metadata,
            )
            assignments.append(assignment)

        return assignments
