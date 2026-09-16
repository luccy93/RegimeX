"""
Unit Tests — Regime Intelligence Domain Models
===============================================
Validates Pydantic v2 domain models for immutability, timezone validation,
mathematical invariants, and defensive error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_intelligence.domain.models import (
    CurrentRegimeContext,
    FeatureStatistic,
    RegimeAssignment,
    RegimeHistorySummary,
    RegimeProfile,
)
from pydantic import ValidationError


def _ts(offset_hours: int = 0) -> datetime:
    """Helper to generate timezone-aware UTC datetime."""
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    return base + timedelta(hours=offset_hours)


class TestFeatureStatisticModel:
    """Tests for FeatureStatistic domain model."""

    def test_valid_feature_statistic_creation(self) -> None:
        """Valid inputs construct a frozen FeatureStatistic."""
        stat = FeatureStatistic(
            feature_name="volatility_20",
            observation_count=100,
            mean=0.15,
            median=0.14,
            std=0.03,
            min=0.08,
            max=0.25,
        )
        assert stat.feature_name == "volatility_20"
        assert stat.observation_count == 100
        assert stat.mean == 0.15
        assert stat.median == 0.14
        assert stat.std == 0.03
        assert stat.min == 0.08
        assert stat.max == 0.25

    def test_feature_statistic_immutability(self) -> None:
        """FeatureStatistic is frozen and cannot be mutated."""
        stat = FeatureStatistic(
            feature_name="return_1",
            observation_count=10,
            mean=0.01,
        )
        with pytest.raises(ValidationError):
            stat.mean = 0.05  # type: ignore[misc]

    def test_feature_statistic_rejects_nan_and_inf(self) -> None:
        """FeatureStatistic rejects NaN and infinite values."""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            FeatureStatistic(
                feature_name="return_1",
                observation_count=1,
                mean=float("nan"),
            )

        with pytest.raises(ValidationError, match="cannot be infinite"):
            FeatureStatistic(
                feature_name="return_1",
                observation_count=1,
                std=float("inf"),
            )


class TestRegimeAssignmentModel:
    """Tests for RegimeAssignment domain model."""

    def test_valid_regime_assignment_creation(self) -> None:
        """Valid inputs construct a frozen RegimeAssignment."""
        assignment = RegimeAssignment(
            timestamp=_ts(0),
            regime_id=0,
            regime_label="REGIME_0",
            features={"volatility_20": 0.12, "return_1": 0.01},
            confidence=0.85,
            model_metadata={"model": "kmeans"},
        )
        assert assignment.regime_id == 0
        assert assignment.regime_label == "REGIME_0"
        assert assignment.confidence == 0.85
        assert assignment.features["volatility_20"] == 0.12

    def test_regime_assignment_immutability(self) -> None:
        """RegimeAssignment is frozen and cannot be mutated."""
        assignment = RegimeAssignment(
            timestamp=_ts(0),
            regime_id=1,
            regime_label="REGIME_1",
        )
        with pytest.raises(ValidationError):
            assignment.regime_id = 2  # type: ignore[misc]

    def test_regime_assignment_rejects_naive_datetime(self) -> None:
        """RegimeAssignment rejects naive datetimes."""
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            RegimeAssignment(
                timestamp=naive_dt,
                regime_id=0,
                regime_label="REGIME_0",
            )

    def test_regime_assignment_rejects_negative_regime_id(self) -> None:
        """RegimeAssignment rejects negative regime IDs."""
        with pytest.raises(ValidationError):
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=-1,
                regime_label="REGIME_INVALID",
            )

    def test_regime_assignment_rejects_nan_feature_values(self) -> None:
        """RegimeAssignment rejects NaN features (missing must be None)."""
        with pytest.raises(ValidationError, match="NaN value"):
            RegimeAssignment(
                timestamp=_ts(0),
                regime_id=0,
                regime_label="REGIME_0",
                features={"return_1": float("nan")},
            )


class TestRegimeProfileModel:
    """Tests for RegimeProfile domain model."""

    def test_valid_profile_creation(self) -> None:
        """Valid profile with duration invariant satisfactions."""
        profile = RegimeProfile(
            regime_id=0,
            regime_label="REGIME_0",
            observation_count=20,
            frequency=0.4,
            percentage=40.0,
            first_seen=_ts(0),
            last_seen=_ts(19),
            run_count=4,
            average_duration=5.0,
            median_duration=5.0,
            min_duration=2,
            max_duration=8,
            feature_statistics={},
        )
        assert profile.observation_count == 20
        assert profile.frequency == 0.4
        assert profile.min_duration == 2
        assert profile.max_duration == 8

    def test_profile_duration_invariants_validation(self) -> None:
        """Profile rejects min > median or median > max."""
        with pytest.raises(ValidationError, match="Duration invariant violated"):
            RegimeProfile(
                regime_id=0,
                regime_label="REGIME_0",
                observation_count=10,
                frequency=0.5,
                percentage=50.0,
                run_count=2,
                average_duration=5.0,
                median_duration=10.0,
                min_duration=6,  # min > average, invalid
                max_duration=8,
            )

    def test_profile_rejects_naive_timestamps(self) -> None:
        """Profile rejects naive first_seen or last_seen."""
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            RegimeProfile(
                regime_id=0,
                regime_label="REGIME_0",
                observation_count=1,
                frequency=1.0,
                percentage=100.0,
                first_seen=naive_dt,
                run_count=1,
                average_duration=1.0,
                median_duration=1.0,
                min_duration=1,
                max_duration=1,
            )


class TestCurrentRegimeContextModel:
    """Tests for CurrentRegimeContext domain model."""

    def test_valid_context_creation(self) -> None:
        """Valid context fields."""
        context = CurrentRegimeContext(
            current_regime_id=1,
            current_regime_label="REGIME_1",
            current_timestamp=_ts(10),
            observations_in_current_run=3,
            historical_frequency=0.25,
            historical_average_duration=4.5,
            historical_max_duration=8,
            historical_min_duration=1,
            historical_run_count=5,
            current_features={"return_1": 0.02},
        )
        assert context.current_regime_id == 1
        assert context.observations_in_current_run == 3
        assert context.historical_frequency == 0.25

    def test_context_rejects_naive_timestamp(self) -> None:
        """CurrentRegimeContext rejects naive current_timestamp."""
        naive_dt = datetime(2025, 1, 1, 12, 0, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            CurrentRegimeContext(
                current_regime_id=0,
                current_regime_label="REGIME_0",
                current_timestamp=naive_dt,
                observations_in_current_run=1,
                historical_frequency=1.0,
                historical_average_duration=1.0,
                historical_max_duration=1,
                historical_min_duration=1,
                historical_run_count=1,
            )


class TestRegimeHistorySummaryModel:
    """Tests for RegimeHistorySummary domain model."""

    def test_empty_summary_properties(self) -> None:
        """Empty summary has is_empty == True."""
        summary = RegimeHistorySummary(
            analysis_start=None,
            analysis_end=None,
            total_observations=0,
            regimes_observed=(),
            regime_profiles={},
            current_regime=None,
        )
        assert summary.is_empty is True
        assert summary.total_observations == 0
        assert summary.get_profile(0) is None


class TestModelValidationHardening:
    """Comprehensive validation and serialization hardening across all models."""

    def test_feature_statistic_nullable_when_zero_count(self) -> None:
        """FeatureStatistic with observation_count == 0 allows all stats to be None."""
        stat = FeatureStatistic(feature_name="zero_obs", observation_count=0)
        assert stat.mean is None
        assert stat.median is None
        assert stat.std is None
        assert stat.min is None
        assert stat.max is None

    def test_feature_statistic_rejects_negative_count(self) -> None:
        """FeatureStatistic rejects negative observation_count."""
        with pytest.raises(ValidationError):
            FeatureStatistic(feature_name="vol", observation_count=-1)

    def test_regime_assignment_confidence_bounds(self) -> None:
        """Confidence score must be strictly between 0.0 and 1.0."""
        # Valid bounds
        a0 = RegimeAssignment(timestamp=_ts(0), regime_id=0, regime_label="R0", confidence=0.0)
        assert a0.confidence == 0.0
        a1 = RegimeAssignment(timestamp=_ts(1), regime_id=0, regime_label="R0", confidence=1.0)
        assert a1.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            RegimeAssignment(timestamp=_ts(2), regime_id=0, regime_label="R0", confidence=-0.01)

        with pytest.raises(ValidationError):
            RegimeAssignment(timestamp=_ts(3), regime_id=0, regime_label="R0", confidence=1.01)

    def test_regime_assignment_rejects_empty_label(self) -> None:
        """RegimeAssignment rejects empty regime_label string."""
        with pytest.raises(ValidationError):
            RegimeAssignment(timestamp=_ts(0), regime_id=0, regime_label="")

    def test_profile_rejects_negative_duration_and_counts(self) -> None:
        """RegimeProfile rejects negative observation_count, run_count, or duration bounds."""
        with pytest.raises(ValidationError):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=-5,
                frequency=0.5,
                percentage=50.0,
                run_count=1,
                average_duration=1.0,
                median_duration=1.0,
                min_duration=1,
                max_duration=1,
            )

        with pytest.raises(ValidationError):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=0.5,
                percentage=50.0,
                run_count=-1,
                average_duration=1.0,
                median_duration=1.0,
                min_duration=1,
                max_duration=1,
            )

        with pytest.raises(ValidationError):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=0.5,
                percentage=50.0,
                run_count=1,
                average_duration=-1.0,
                median_duration=1.0,
                min_duration=1,
                max_duration=1,
            )

    def test_profile_rejects_invalid_frequency_bounds(self) -> None:
        """
        RegimeProfile rejects frequency outside [0.0, 1.0] and percentage
        outside [0.0, 100.0].
        """
        with pytest.raises(ValidationError):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=1.05,
                percentage=105.0,
                run_count=1,
                average_duration=10.0,
                median_duration=10.0,
                min_duration=10,
                max_duration=10,
            )

        with pytest.raises(ValidationError):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=-0.1,
                percentage=-10.0,
                run_count=1,
                average_duration=10.0,
                median_duration=10.0,
                min_duration=10,
                max_duration=10,
            )

    def test_profile_duration_invariants_exhaustive(self) -> None:
        """Verify all duration invariant failure cases."""
        # 1. min > max
        with pytest.raises(ValidationError, match="Duration invariant violated"):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=1.0,
                percentage=100.0,
                run_count=2,
                average_duration=5.0,
                median_duration=5.0,
                min_duration=8,
                max_duration=4,
            )

        # 2. median > max
        with pytest.raises(ValidationError, match="Duration invariant violated"):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=1.0,
                percentage=100.0,
                run_count=2,
                average_duration=5.0,
                median_duration=9.0,
                min_duration=2,
                max_duration=6,
            )

        # 3. average > max
        with pytest.raises(ValidationError, match="Duration invariant violated"):
            RegimeProfile(
                regime_id=0,
                regime_label="R0",
                observation_count=10,
                frequency=1.0,
                percentage=100.0,
                run_count=2,
                average_duration=7.5,
                median_duration=5.0,
                min_duration=2,
                max_duration=6,
            )

    def test_current_context_rejects_zero_or_negative_run(self) -> None:
        """CurrentRegimeContext requires observations_in_current_run >= 1."""
        with pytest.raises(ValidationError):
            CurrentRegimeContext(
                current_regime_id=0,
                current_regime_label="R0",
                current_timestamp=_ts(0),
                observations_in_current_run=0,  # Invalid! Must be >= 1
                historical_frequency=1.0,
                historical_average_duration=1.0,
                historical_max_duration=1,
                historical_min_duration=1,
                historical_run_count=1,
            )

    def test_serialization_round_trip(self) -> None:
        """All domain models can be serialized to JSON/dict and deserialized without loss."""
        # 1. FeatureStatistic
        stat = FeatureStatistic(
            feature_name="return_1",
            observation_count=50,
            mean=0.015,
            median=0.014,
            std=0.005,
            min=-0.02,
            max=0.05,
        )
        stat_dump = stat.model_dump()
        stat_restored = FeatureStatistic.model_validate(stat_dump)
        assert stat == stat_restored
        assert FeatureStatistic.model_validate_json(stat.model_dump_json()) == stat

        # 2. RegimeAssignment
        assignment = RegimeAssignment(
            timestamp=_ts(5),
            regime_id=1,
            regime_label="REGIME_1",
            features={"return_1": 0.015, "volatility_20": None},
            confidence=0.92,
            model_metadata={"model": "kmeans", "version": "1.0.0"},
        )
        asgn_restored = RegimeAssignment.model_validate(assignment.model_dump())
        assert assignment == asgn_restored
        assert RegimeAssignment.model_validate_json(assignment.model_dump_json()) == assignment

        # 3. RegimeProfile
        profile = RegimeProfile(
            regime_id=1,
            regime_label="REGIME_1",
            observation_count=25,
            frequency=0.5,
            percentage=50.0,
            first_seen=_ts(0),
            last_seen=_ts(24),
            run_count=3,
            average_duration=8.333333333333334,
            median_duration=8.0,
            min_duration=5,
            max_duration=12,
            feature_statistics={"return_1": stat},
        )
        prof_restored = RegimeProfile.model_validate(profile.model_dump())
        assert profile == prof_restored
        assert RegimeProfile.model_validate_json(profile.model_dump_json()) == profile

        # 4. CurrentRegimeContext
        ctx = CurrentRegimeContext(
            current_regime_id=1,
            current_regime_label="REGIME_1",
            current_timestamp=_ts(24),
            observations_in_current_run=5,
            historical_frequency=0.5,
            historical_average_duration=8.33,
            historical_max_duration=12,
            historical_min_duration=5,
            historical_run_count=3,
            current_features={"return_1": 0.02},
        )
        ctx_restored = CurrentRegimeContext.model_validate(ctx.model_dump())
        assert ctx == ctx_restored
        assert CurrentRegimeContext.model_validate_json(ctx.model_dump_json()) == ctx

        # 5. RegimeHistorySummary
        summary = RegimeHistorySummary(
            analysis_start=_ts(0),
            analysis_end=_ts(24),
            total_observations=50,
            regimes_observed=(0, 1),
            regime_profiles={1: profile},
            current_regime=ctx,
            model_name="kmeans-baseline",
            model_version="1.0.0",
            algorithm="kmeans_baseline",
            feature_names=("return_1",),
        )
        summary_restored = RegimeHistorySummary.model_validate(summary.model_dump())
        assert summary.total_observations == summary_restored.total_observations
        assert summary.regimes_observed == summary_restored.regimes_observed
        assert summary.model_name == summary_restored.model_name
