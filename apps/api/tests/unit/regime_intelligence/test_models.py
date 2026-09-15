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
