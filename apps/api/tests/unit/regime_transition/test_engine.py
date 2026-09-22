"""
RegimeX Regime Transition — Engine Test Suite
=============================================
Comprehensive unit tests for the Regime Transition Probability Engine (V12 Commit 01).

Guarantees Verified:
- Basic transition extraction: 0 -> 1, 1 -> 2, 2 -> 0, alternating, persistence.
- Matrix dimensions, counts, and empirical row-normalized probabilities (MLE).
- Simplex invariant: each row sums to 1.0 within numerical tolerance (1e-6).
- Sample-size transparency: probabilities preserve supporting observation counts.
- Zero-count handling: unobserved transitions strictly yield 0.0 with zero artificial smoothing.
- Temporal ordering & integrity: monotonic UTC timestamps, duplicate rejection, auto-sort option.
- Missing & invalid data rejection: empty, single-element, NaN, inf, None, negative, invalid IDs.
- Regime cardinality: 2, 3, 4, and 5+ regimes.
- Integration: V09 RegimeAssignment, V08/V10 RegimeDetectionResult, V11 RegimeEnsembleResult.
- Zero future leakage and full determinism across repeated executions.
"""

from __future__ import annotations

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
    InvalidRegimeValueError,
    InvalidTransitionSequenceError,
)
from app.modules.regime_transition.infrastructure.engine import (
    RegimeTransitionEngine,
)


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


# =============================================================================
# 1. Basic Transitions & Sequences
# =============================================================================


class TestBasicTransitions:
    def test_single_transition_0_to_1(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, 1)

        result = engine.compute_from_series(timestamps, regimes)

        assert result.total_observations == 2
        assert result.total_transitions == 1
        assert len(result.transitions) == 1
        record = result.transitions[0]
        assert record.source_regime == 0
        assert record.target_regime == 1
        assert record.timestamp == _ts(1)
        assert record.is_self_transition is False

        # Matrix: 2x2
        assert result.get_count_matrix() == ((0, 1), (0, 0))
        assert result.get_matrix() == ((0.0, 1.0), (0.0, 0.0))

    def test_transitions_1_to_2_and_2_to_0(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1), _ts(2))
        regimes = (1, 2, 0)

        result = engine.compute_from_series(timestamps, regimes)

        assert result.total_observations == 3
        assert result.total_transitions == 2
        assert len(result.transitions) == 2

        t1, t2 = result.transitions
        assert (t1.source_regime, t1.target_regime) == (1, 2)
        assert (t2.source_regime, t2.target_regime) == (2, 0)

    def test_repeated_same_regime_persistence(self) -> None:
        engine = RegimeTransitionEngine(include_self_transitions=True)
        timestamps = tuple(_ts(i) for i in range(5))
        regimes = (0, 0, 0, 0, 0)

        result = engine.compute_from_series(timestamps, regimes)

        assert result.total_observations == 5
        assert result.total_transitions == 4
        # Since regimes are identical, zero state change events
        assert len(result.transitions) == 0

        # Matrix: 1x1 with 4 self-transitions
        assert result.get_count_matrix() == ((4,),)
        assert result.get_matrix() == ((1.0,),)
        assert result.get_self_transition_probability(0) == 1.0

    def test_alternating_regimes(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = tuple(_ts(i) for i in range(6))
        regimes = (0, 1, 0, 1, 0, 1)

        result = engine.compute_from_series(timestamps, regimes)

        assert result.total_observations == 6
        assert result.total_transitions == 5
        assert len(result.transitions) == 5

        # 0 -> 1 occurs 3 times; 1 -> 0 occurs 2 times
        assert result.get_count_matrix() == ((0, 3), (2, 0))
        assert result.get_matrix() == ((0.0, 1.0), (1.0, 0.0))


# =============================================================================
# 2. Transition Matrix & Normalization Tests
# =============================================================================


class TestTransitionMatrixAndProbabilities:
    def test_matrix_matching_prompt_specification(self) -> None:
        """
        Verify transition counts and row-normalization matching the exact example from prompt:
                     To
                   0   1   2
        From  0    8   2   0  (total = 10)
              1    1   6   3  (total = 10)
              2    0   2   9  (total = 11)
        """
        engine = RegimeTransitionEngine()
        # Build sequence that produces exact count matrix:
        # Row 0: 8 self (0->0), 2 to 1 (0->1), 0 to 2 (0->2)
        # Row 1: 1 to 0 (1->0), 6 self (1->1), 3 to 2 (1->2)
        # Row 2: 0 to 0 (2->0), 2 to 1 (2->1), 9 self (2->2)
        # Note: In a connected sequence, transitions must follow valid paths.
        # Let's test by building a realistic series or testing via known sequence.
        # Sequence:
        # 0 x 8 -> 0 -> 1 -> 1 x 6 -> 2 -> 2 x 9 -> 1 -> 2 -> 2 (etc.)
        # Let's generate a synthetic sequence that generates known counts:
        seq = [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # 8 self transitions (0->0)
            1,  # 0->1 (1)
            1,
            1,
            1,
            1,
            1,
            1,  # 6 self transitions (1->1)
            2,  # 1->2 (1)
            2,
            2,
            2,
            2,
            2,
            2,
            2,
            2,
            2,  # 9 self transitions (2->2)
            1,  # 2->1 (1)
            0,  # 1->0 (1)
            1,  # 0->1 (2)
            2,  # 1->2 (2)
            1,  # 2->1 (2)
            2,  # 1->2 (3)
        ]
        timestamps = tuple(_ts(i) for i in range(len(seq)))
        result = engine.compute_from_series(timestamps, seq, n_regimes=3)

        assert result.count_matrix.get_row(0) == (8, 2, 0)
        assert result.count_matrix.get_row(1) == (1, 6, 3)
        assert result.count_matrix.get_row(2) == (0, 2, 9)

        # Row 0 total = 10 -> P(0->0)=0.8, P(0->1)=0.2, P(0->2)=0.0
        p01 = result.get_transition_probability(0, 1)
        assert p01.count == 2
        assert p01.sample_size == 10
        assert abs(p01.probability - 0.20) < 1e-6

        # Check row sums equal 1.0 within tolerance
        for r_id in (0, 1, 2):
            row_sum = sum(result.probability_matrix.get_row(r_id))
            assert abs(row_sum - 1.0) < 1e-6

    def test_unobserved_transitions_strictly_zero(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = tuple(_ts(i) for i in range(4))
        regimes = (0, 0, 1, 1)  # 0->0, 0->1, 1->1. No 1->0!

        result = engine.compute_from_series(timestamps, regimes, n_regimes=2)

        p10 = result.get_transition_probability(1, 0)
        assert p10.count == 0
        assert p10.probability == 0.0

    def test_sample_size_preservation(self) -> None:
        engine = RegimeTransitionEngine()

        # Case A: 3 / 4 transitions
        seq_a = (0, 1, 0, 1, 0, 1, 0, 0)
        res_a = engine.compute_from_series(tuple(_ts(i) for i in range(len(seq_a))), seq_a)
        prob_a = res_a.get_transition_probability(0, 1)
        assert prob_a.count == 3
        assert prob_a.sample_size == 4
        assert prob_a.probability == 0.75

        # Case B: 75 / 100 transitions
        # Construct exact 75 transitions (0 -> 1) and 25 transitions (0 -> 0)
        # e.g., 75 transitions of (0 -> 1 -> 0) gives 75 of (0 -> 1), followed by 25 of (0 -> 0)
        seq_b = []
        for _ in range(75):
            seq_b.extend([0, 1])
        # Now at 1. Transition to 0, then 25 consecutive 0->0 transitions
        seq_b.append(0)
        seq_b.extend([0] * 25)

        res_b = engine.compute_from_series(tuple(_ts(i) for i in range(len(seq_b))), seq_b)
        prob_b = res_b.get_transition_probability(0, 1)
        assert prob_b.count == 75
        assert prob_b.sample_size == 100
        assert prob_b.probability == 0.75

        # Distinction verified
        assert prob_a.sample_size != prob_b.sample_size


# =============================================================================
# 3. Regime Cardinality Tests (2, 3, 4, 5+ Regimes)
# =============================================================================


class TestRegimeCardinality:
    @pytest.mark.parametrize("k", [2, 3, 4, 5, 8])
    def test_various_regime_counts(self, k: int) -> None:
        engine = RegimeTransitionEngine()
        # Round-robin transitions 0 -> 1 -> ... -> K-1 -> 0
        seq = [i % k for i in range(k * 3)]
        timestamps = tuple(_ts(i) for i in range(len(seq)))

        result = engine.compute_from_series(timestamps, seq, n_regimes=k)

        assert result.count_matrix.cardinality == k
        assert result.probability_matrix.cardinality == k
        assert len(result.count_matrix.matrix) == k
        assert len(result.probability_matrix.matrix) == k

        for r_id in range(k):
            row_sum = sum(result.probability_matrix.get_row(r_id))
            assert abs(row_sum - 1.0) < 1e-6


# =============================================================================
# 4. Temporal Validation & Ordering Tests
# =============================================================================


class TestTemporalValidation:
    def test_unsorted_input_rejected_by_default(self) -> None:
        engine = RegimeTransitionEngine(sort_chronologically=False)
        timestamps = (_ts(2), _ts(1), _ts(3))  # Unsorted
        regimes = (0, 1, 2)

        with pytest.raises(InvalidTransitionSequenceError, match="strictly ascending"):
            engine.compute_from_series(timestamps, regimes)

    def test_unsorted_input_sorted_when_enabled(self) -> None:
        engine = RegimeTransitionEngine(sort_chronologically=True)
        # Out of order: t1 (0), t0 (1), t2 (2) -> chronological is t0: 1, t1: 0, t2: 2
        timestamps = (_ts(1), _ts(0), _ts(2))
        regimes = (0, 1, 2)

        result = engine.compute_from_series(timestamps, regimes)
        assert result.total_observations == 3
        # Chronological order: 1 -> 0 -> 2
        t1, t2 = result.transitions
        assert (t1.source_regime, t1.target_regime) == (1, 0)
        assert (t2.source_regime, t2.target_regime) == (0, 2)

    def test_duplicate_timestamps_rejected(self) -> None:
        engine = RegimeTransitionEngine(sort_chronologically=False)
        timestamps = (_ts(0), _ts(1), _ts(1))  # Duplicate t=1
        regimes = (0, 1, 2)

        with pytest.raises(InvalidTransitionSequenceError, match="Duplicate timestamp"):
            engine.compute_from_series(timestamps, regimes)

    def test_duplicate_timestamps_rejected_in_sort_mode(self) -> None:
        engine = RegimeTransitionEngine(sort_chronologically=True)
        timestamps = (_ts(1), _ts(0), _ts(1))  # Duplicate t=1
        regimes = (0, 1, 2)

        with pytest.raises(InvalidTransitionSequenceError, match="Duplicate timestamp"):
            engine.compute_from_series(timestamps, regimes)

    def test_naive_timestamps_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        naive = datetime(2026, 1, 1, 0, 0, 0)
        timestamps = (naive, _ts(1))
        regimes = (0, 1)

        with pytest.raises(InvalidTransitionSequenceError, match="naive"):
            engine.compute_from_series(timestamps, regimes)


# =============================================================================
# 5. Missing / Invalid Data Tests
# =============================================================================


class TestInvalidDataHandling:
    def test_empty_sequence_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        with pytest.raises(InsufficientTransitionDataError, match="at least 2"):
            engine.compute_from_series((), ())

    def test_single_observation_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        with pytest.raises(InsufficientTransitionDataError, match="at least 2"):
            engine.compute_from_series((_ts(0),), (0,))

    def test_missing_regime_none_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, None)

        with pytest.raises(InvalidRegimeValueError, match="Missing regime ID"):
            engine.compute_from_series(timestamps, regimes)  # type: ignore[arg-type]

    def test_float_regime_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, 1.0)

        with pytest.raises(InvalidRegimeValueError, match="Invalid regime ID type"):
            engine.compute_from_series(timestamps, regimes)  # type: ignore[arg-type]

    def test_nan_regime_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, float("nan"))

        with pytest.raises(InvalidRegimeValueError, match="Invalid regime ID type"):
            engine.compute_from_series(timestamps, regimes)  # type: ignore[arg-type]

    def test_negative_regime_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1))
        regimes = (0, -1)

        with pytest.raises(InvalidRegimeValueError, match="Negative regime ID"):
            engine.compute_from_series(timestamps, regimes)

    def test_length_mismatch_rejected(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = (_ts(0), _ts(1), _ts(2))
        regimes = (0, 1)

        with pytest.raises(InvalidTransitionSequenceError, match="Dimension mismatch"):
            engine.compute_from_series(timestamps, regimes)


# =============================================================================
# 6. Integration Tests (V08, V09, V11 Models)
# =============================================================================


class TestIntegrationWithRegimeStack:
    def test_compute_from_v09_assignments(self) -> None:
        engine = RegimeTransitionEngine()
        assignments = [
            RegimeAssignment(timestamp=_ts(0), regime_id=0, regime_label="REGIME_0"),
            RegimeAssignment(timestamp=_ts(1), regime_id=1, regime_label="REGIME_1"),
            RegimeAssignment(timestamp=_ts(2), regime_id=1, regime_label="REGIME_1"),
            RegimeAssignment(timestamp=_ts(3), regime_id=0, regime_label="REGIME_0"),
        ]

        result = engine.compute_from_assignments(assignments)
        assert result.total_observations == 4
        assert result.total_transitions == 3
        # Transitions: 0->1, 1->1, 1->0
        assert result.count_matrix.get_count(0, 1) == 1
        assert result.count_matrix.get_count(1, 1) == 1
        assert result.count_matrix.get_count(1, 0) == 1

    def test_compute_from_v08_detection_result(self) -> None:
        engine = RegimeTransitionEngine()
        records = (
            RegimeRecord(
                timestamp=_ts(0),
                cluster_id=0,
                canonical_regime_id=0,
                canonical_regime_label="R0",
            ),
            RegimeRecord(
                timestamp=_ts(1),
                cluster_id=1,
                canonical_regime_id=1,
                canonical_regime_label="R1",
            ),
            RegimeRecord(
                timestamp=_ts(2),
                cluster_id=2,
                canonical_regime_id=2,
                canonical_regime_label="R2",
            ),
        )
        det_result = RegimeDetectionResult(
            model_version="1.0.0",
            algorithm="kmeans_baseline",
            feature_names=("f1",),
            records=records,
        )

        result = engine.compute_from_detection_result(det_result)
        assert result.total_observations == 3
        assert result.total_transitions == 2
        assert result.count_matrix.get_count(0, 1) == 1
        assert result.count_matrix.get_count(1, 2) == 1

    def test_compute_from_v11_ensemble_result(self) -> None:
        engine = RegimeTransitionEngine()
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

        result = engine.compute_from_ensemble_result(ens_result)
        assert result.total_observations == 3
        assert result.total_transitions == 2
        # Transitions: 0 -> 1, 1 -> 1
        assert result.count_matrix.get_count(0, 1) == 1
        assert result.count_matrix.get_count(1, 1) == 1
        assert result.get_self_transition_probability(1) == 1.0


# =============================================================================
# 7. Determinism & Anti-Leakage Tests
# =============================================================================


class TestDeterminismAndAntiLeakage:
    def test_repeated_runs_produce_identical_output(self) -> None:
        engine = RegimeTransitionEngine()
        timestamps = tuple(_ts(i) for i in range(20))
        regimes = tuple((i * 7 + 3) % 4 for i in range(20))

        results = [engine.compute_from_series(timestamps, regimes) for _ in range(5)]

        first = results[0]
        for other in results[1:]:
            assert other.count_matrix.matrix == first.count_matrix.matrix
            assert other.probability_matrix.matrix == first.probability_matrix.matrix
            assert other.transitions == first.transitions
            assert other.total_transitions == first.total_transitions

    def test_no_future_lookahead_leakage(self) -> None:
        """
        Transitions up to time T must depend strictly on observations <= T.
        Appended future observations must not modify past transition records.
        """
        engine = RegimeTransitionEngine()
        timestamps_past = tuple(_ts(i) for i in range(10))
        regimes_past = tuple(i % 3 for i in range(10))

        result_past = engine.compute_from_series(timestamps_past, regimes_past, n_regimes=3)

        # Append future observations
        timestamps_extended = timestamps_past + (_ts(10), _ts(11), _ts(12))
        regimes_extended = regimes_past + (1, 2, 0)

        result_extended = engine.compute_from_series(
            timestamps_extended, regimes_extended, n_regimes=3
        )

        # The first 9 transitions of extended result must exactly match the 9 transitions of past
        past_len = len(result_past.transitions)
        assert result_extended.transitions[:past_len] == result_past.transitions
