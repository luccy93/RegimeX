"""
RegimeX Regime Transition — Analytics Test Suite
================================================
Exhaustive tests verifying regime persistence, change rates, deterministic rankings,
transition entropy H(i), diversity metrics, regime change matrices, and global invariants.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.models import (
    EnsembleConfidence,
    EnsembleRecord,
    RegimeDetectionResult,
    RegimeEnsembleResult,
    RegimeRecord,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment
from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
)
from app.modules.regime_transition.infrastructure.analytics import (
    RegimeTransitionAnalytics,
)


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


# =============================================================================
# 1. Persistence Tests
# =============================================================================


class TestPersistence:
    def test_all_self_transitions(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = tuple(_ts(i) for i in range(5))
        regimes = (0, 0, 0, 0, 0)

        result = analytics.analyze_from_series(timestamps, regimes)

        r0 = result.get_regime_analytics(0)
        assert r0.persistence_probability == 1.0
        assert r0.change_rate == 0.0
        assert r0.self_transition_count == 4
        assert r0.regime_change_count == 0
        assert result.get_persistence(0) == 1.0
        assert result.get_persistence_rate() == 1.0
        assert result.get_change_rate() == 0.0

    def test_zero_self_transitions(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = tuple(_ts(i) for i in range(4))
        regimes = (0, 1, 2, 0)  # 0->1, 1->2, 2->0 (no persistence)

        result = analytics.analyze_from_series(timestamps, regimes)

        for r_id in (0, 1, 2):
            r_stat = result.get_regime_analytics(r_id)
            assert r_stat.persistence_probability == 0.0
            assert r_stat.change_rate == 1.0
            assert r_stat.self_transition_count == 0

        assert result.get_persistence_rate() == 0.0
        assert result.get_change_rate() == 1.0

    def test_mixed_persistence(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # 0->0, 0->0, 0->1 (out of 0: 2 self, 1 change -> P(0->0) = 2/3)
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3))
        regimes = (0, 0, 0, 1)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=2)

        r0 = result.get_regime_analytics(0)
        assert r0.self_transition_count == 2
        assert r0.regime_change_count == 1
        assert abs(r0.persistence_probability - 2 / 3) < 1e-6
        assert abs(r0.change_rate - 1 / 3) < 1e-6


# =============================================================================
# 2. Change Rate & Invariant Tests
# =============================================================================


class TestChangeRateAndInvariants:
    def test_global_rate_invariants(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = tuple(_ts(i) for i in range(10))
        regimes = (0, 0, 1, 1, 2, 2, 0, 1, 2, 0)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        ga = result.global_analytics

        assert (
            ga.total_self_transitions + ga.total_regime_changes == ga.total_consecutive_transitions
        )
        assert abs((ga.global_persistence_rate + ga.global_change_rate) - 1.0) < 1e-6
        assert result.get_persistence_rate() == ga.global_persistence_rate
        assert result.get_change_rate() == ga.global_change_rate

    def test_unobserved_regime_has_zero_rates(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = (_ts(0), _ts(1), _ts(2))
        regimes = (0, 0, 0)

        # Regimes 0, 1 configured, but regime 1 never observed
        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=2)

        r1 = result.get_regime_analytics(1)
        assert r1.outgoing_transition_count == 0
        assert r1.incoming_transition_count == 0
        assert r1.persistence_probability == 0.0
        assert r1.change_rate == 0.0
        assert r1.most_likely_destination is None
        assert r1.most_likely_destination_probability == 0.0


# =============================================================================
# 3. Destination Rankings & Tie-Breaking Tests
# =============================================================================


class TestRankingsAndMostLikelyDestination:
    def test_unique_maximum_ranking(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # From 0: 0->0 (3 times), 0->1 (1 time), 0->2 (0 times)
        timestamps = tuple(_ts(i) for i in range(5))
        regimes = (0, 0, 0, 0, 1)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        rankings = result.get_rankings(0)

        assert len(rankings) == 3
        # Rank 1: regime 0 (p = 0.75, c = 3)
        assert rankings[0].target_regime == 0
        assert rankings[0].probability == 0.75
        assert rankings[0].count == 3
        assert rankings[0].rank == 1

        # Rank 2: regime 1 (p = 0.25, c = 1)
        assert rankings[1].target_regime == 1
        assert rankings[1].probability == 0.25
        assert rankings[1].count == 1
        assert rankings[1].rank == 2

        # Rank 3: regime 2 (p = 0.0, c = 0)
        assert rankings[2].target_regime == 2
        assert rankings[2].probability == 0.0
        assert rankings[2].count == 0
        assert rankings[2].rank == 3

        assert result.get_most_likely_destination(0) == 0

    def test_deterministic_tie_breaking_by_target_id(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # From 0: 0->1 (1 time), 0->2 (1 time). Exactly equal support!
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3))
        regimes = (0, 1, 0, 2)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        rankings = result.get_rankings(0)

        # Both have prob = 0.50, count = 1.
        # Tie breaker: target_regime ascending -> regime 1 comes before regime 2!
        assert rankings[0].target_regime == 1
        assert rankings[0].probability == 0.50
        assert rankings[0].rank == 1

        assert rankings[1].target_regime == 2
        assert rankings[1].probability == 0.50
        assert rankings[1].rank == 2

        assert result.get_most_likely_destination(0) == 1

    def test_external_transition_higher_than_self(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # From 0: 0->1 (2 times), 0->0 (1 time)
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3), _ts(4))
        regimes = (0, 0, 1, 0, 1)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=2)

        assert result.get_most_likely_destination(0) == 1
        most_likely_p = result.get_regime_analytics(0).most_likely_destination_probability
        assert abs(most_likely_p - 2 / 3) < 1e-6


# =============================================================================
# 4. Transition Entropy & Concentration Tests
# =============================================================================


class TestTransitionEntropy:
    def test_deterministic_transition_has_zero_entropy(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = tuple(_ts(i) for i in range(5))
        regimes = (0, 0, 0, 0, 0)  # P(0->0) = 1.0

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        r0 = result.get_regime_analytics(0)

        assert r0.transition_entropy == 0.0

    def test_two_equal_destinations_entropy(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # From 0: 0->1 (1 time), 0->2 (1 time) -> P=0.5, 0.5
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3))
        regimes = (0, 1, 0, 2)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        r0 = result.get_regime_analytics(0)

        # Expected entropy: - 0.5*ln(0.5) - 0.5*ln(0.5) = ln(2)
        expected_h = math.log(2.0)
        assert abs(r0.transition_entropy - expected_h) < 1e-6

    def test_three_equal_destinations_entropy(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # From 0: 0->0 (1), 0->1 (1), 0->2 (1) -> P=1/3, 1/3, 1/3
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3), _ts(4))
        # Transitions from 0: 0->0, 0->1, 0->2
        regimes = (0, 0, 1, 0, 2)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        r0 = result.get_regime_analytics(0)

        # Expected entropy: ln(3)
        expected_h = math.log(3.0)
        assert abs(r0.transition_entropy - expected_h) < 1e-6

    def test_unobserved_regime_zero_entropy(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, 0)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        # Regimes 1 and 2 unobserved
        assert result.get_regime_analytics(1).transition_entropy == 0.0
        assert result.get_regime_analytics(2).transition_entropy == 0.0


# =============================================================================
# 5. Transition Diversity Tests
# =============================================================================


class TestTransitionDiversity:
    def test_destination_and_source_counts(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # Transitions: 0->1, 1->2, 2->1
        # Regime 1:
        #   Outgoing destinations: {2} (destination_count = 1)
        #   Incoming sources: {0, 2} (source_count = 2)
        timestamps = (_ts(0), _ts(1), _ts(2), _ts(3))
        regimes = (0, 1, 2, 1)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)
        r1 = result.get_regime_analytics(1)

        assert r1.destination_count == 1
        assert r1.source_count == 2


# =============================================================================
# 6. Regime Change Matrix Tests
# =============================================================================


class TestRegimeChangeMatrix:
    def test_change_matrix_zeroes_out_diagonal(self) -> None:
        analytics = RegimeTransitionAnalytics()
        # Transitions: 0->0, 0->1, 1->1, 1->2
        timestamps = tuple(_ts(i) for i in range(5))
        regimes = (0, 0, 1, 1, 2)

        result = analytics.analyze_from_series(timestamps, regimes, n_regimes=3)

        change_counts = result.regime_change_counts
        # Diagonal must be strictly 0
        assert change_counts[0][0] == 0
        assert change_counts[1][1] == 0
        assert change_counts[2][2] == 0

        # Off-diagonal preserved: 0->1 count = 1, 1->2 count = 1
        assert change_counts[0][1] == 1
        assert change_counts[1][2] == 1

        # Conditional shift probabilities:
        # Row 0: shift to 1 is 100% of shifts (P_shift(0->1) = 1.0)
        assert result.regime_change_probabilities[0][1] == 1.0
        assert result.regime_change_probabilities[0][0] == 0.0


# =============================================================================
# 7. Integration Tests
# =============================================================================


class TestIntegration:
    def test_integration_with_v09_assignments(self) -> None:
        analytics = RegimeTransitionAnalytics()
        assignments = [
            RegimeAssignment(timestamp=_ts(0), regime_id=0, regime_label="REGIME_0"),
            RegimeAssignment(timestamp=_ts(1), regime_id=0, regime_label="REGIME_0"),
            RegimeAssignment(timestamp=_ts(2), regime_id=1, regime_label="REGIME_1"),
            RegimeAssignment(timestamp=_ts(3), regime_id=1, regime_label="REGIME_1"),
        ]

        result = analytics.analyze_from_assignments(assignments)
        assert result.global_analytics.total_observations == 4
        assert result.global_analytics.total_consecutive_transitions == 3
        assert result.global_analytics.total_self_transitions == 2
        assert result.global_analytics.total_regime_changes == 1

    def test_integration_with_v08_detection_result(self) -> None:
        analytics = RegimeTransitionAnalytics()
        records = (
            RegimeRecord(
                timestamp=_ts(0),
                cluster_id=0,
                canonical_regime_id=0,
                canonical_regime_label="R0",
            ),
            RegimeRecord(
                timestamp=_ts(1),
                cluster_id=0,
                canonical_regime_id=0,
                canonical_regime_label="R0",
            ),
            RegimeRecord(
                timestamp=_ts(2),
                cluster_id=1,
                canonical_regime_id=1,
                canonical_regime_label="R1",
            ),
        )
        det_result = RegimeDetectionResult(
            model_version="1.0.0",
            algorithm="kmeans_baseline",
            feature_names=("f1",),
            records=records,
        )

        result = analytics.analyze_from_detection_result(det_result)
        assert result.get_persistence(0) == 0.5

    def test_integration_with_v11_ensemble_result(self) -> None:
        analytics = RegimeTransitionAnalytics()
        confidence = EnsembleConfidence(
            score=1.0,
            supporting_model_count=2,
            active_model_count=2,
            supporting_weight=1.0,
            total_active_weight=1.0,
            agreement_ratio=1.0,
            is_unanimous=True,
            disagreeing_models=(),
        )
        records = (
            EnsembleRecord(
                timestamp=_ts(0),
                ensemble_regime_id=0,
                ensemble_regime_label="REGIME_0",
                model_predictions={"kmeans": 0, "gmm": 0},
                aligned_predictions={"kmeans": 0, "gmm": 0},
                agreement_count=2,
                total_models=2,
                is_unanimous=True,
                confidence=1.0,
                confidence_breakdown=confidence,
            ),
            EnsembleRecord(
                timestamp=_ts(1),
                ensemble_regime_id=1,
                ensemble_regime_label="REGIME_1",
                model_predictions={"kmeans": 1, "gmm": 1},
                aligned_predictions={"kmeans": 1, "gmm": 1},
                agreement_count=2,
                total_models=2,
                is_unanimous=True,
                confidence=1.0,
                confidence_breakdown=confidence,
            ),
            EnsembleRecord(
                timestamp=_ts(2),
                ensemble_regime_id=1,
                ensemble_regime_label="REGIME_1",
                model_predictions={"kmeans": 1, "gmm": 1},
                aligned_predictions={"kmeans": 1, "gmm": 1},
                agreement_count=2,
                total_models=2,
                is_unanimous=True,
                confidence=1.0,
                confidence_breakdown=confidence,
            ),
        )
        ens_result = RegimeEnsembleResult(
            model_version="1.0.0",
            algorithm="ensemble",
            feature_names=("f1",),
            records=records,
            models_used=("kmeans", "gmm"),
            component_predictions={"kmeans": (0, 1, 1), "gmm": (0, 1, 1)},
            aligned_predictions={"kmeans": (0, 1, 1), "gmm": (0, 1, 1)},
            ensemble_regimes=(0, 1, 1),
            weights_used={"kmeans": 0.5, "gmm": 0.5},
            aggregation_strategy="weighted_voting",
            alignment_policy="canonical_label",
            failure_policy="fail_fast",
            confidence_scores=(1.0, 1.0, 1.0),
        )

        result = analytics.analyze_from_ensemble_result(ens_result)
        assert result.get_persistence(1) == 1.0
        assert result.get_change_rate() == 0.5


# =============================================================================
# 8. Determinism & Error Handling Tests
# =============================================================================


class TestDeterminismAndEdgeCases:
    def test_repeated_runs_deterministic(self) -> None:
        analytics = RegimeTransitionAnalytics()
        timestamps = tuple(_ts(i) for i in range(25))
        regimes = tuple((i * 3 + 1) % 4 for i in range(25))

        results = [analytics.analyze_from_series(timestamps, regimes) for _ in range(5)]
        first = results[0]

        for other in results[1:]:
            assert other.global_analytics == first.global_analytics
            assert other.regime_change_counts == first.regime_change_counts
            assert other.regime_change_probabilities == first.regime_change_probabilities
            for r_id in (0, 1, 2, 3):
                assert other.get_regime_analytics(r_id) == first.get_regime_analytics(r_id)

    def test_insufficient_data_raises_error(self) -> None:
        analytics = RegimeTransitionAnalytics()
        with pytest.raises(InsufficientTransitionDataError):
            analytics.analyze_from_series((_ts(0),), (0,))
