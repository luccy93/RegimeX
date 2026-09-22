"""
RegimeX Regime Transition — Domain Model Tests
==============================================
Verifies immutability, Pydantic validation, dimensional consistency,
simplex normalization invariants, and query interfaces on domain models.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_transition.domain.models import (
    RegimeTransitionResult,
    TransitionCountMatrix,
    TransitionProbability,
    TransitionProbabilityMatrix,
    TransitionRecord,
)
from pydantic import ValidationError


def _ts(offset: int = 0) -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset)


class TestTransitionRecord:
    def test_valid_record_creation(self) -> None:
        rec = TransitionRecord(
            source_regime=0,
            target_regime=1,
            timestamp=_ts(1),
            source_label="REGIME_0",
            target_label="REGIME_1",
        )
        assert rec.source_regime == 0
        assert rec.target_regime == 1
        assert rec.timestamp == _ts(1)
        assert rec.source_label == "REGIME_0"
        assert rec.target_label == "REGIME_1"
        assert rec.is_self_transition is False

    def test_self_transition_flag_auto_detected(self) -> None:
        rec = TransitionRecord(
            source_regime=2,
            target_regime=2,
            timestamp=_ts(1),
        )
        assert rec.is_self_transition is True
        assert rec.source_label == "REGIME_2"
        assert rec.target_label == "REGIME_2"

    def test_naive_timestamp_rejected(self) -> None:
        naive = datetime(2026, 1, 1, 0, 0, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            TransitionRecord(
                source_regime=0,
                target_regime=1,
                timestamp=naive,
            )

    def test_negative_regime_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TransitionRecord(
                source_regime=-1,
                target_regime=1,
                timestamp=_ts(1),
            )

    def test_immutability(self) -> None:
        rec = TransitionRecord(
            source_regime=0,
            target_regime=1,
            timestamp=_ts(1),
        )
        with pytest.raises(ValidationError):
            rec.source_regime = 2  # type: ignore[misc]


class TestTransitionProbability:
    def test_valid_probability(self) -> None:
        tp = TransitionProbability(
            source_regime=0,
            target_regime=1,
            count=2,
            total_transitions_from_source=10,
            probability=0.20,
        )
        assert tp.source_regime == 0
        assert tp.target_regime == 1
        assert tp.count == 2
        assert tp.total_transitions_from_source == 10
        assert tp.sample_size == 10
        assert abs(tp.probability - 0.20) < 1e-6

    def test_zero_total_transitions_requires_zero_probability(self) -> None:
        tp = TransitionProbability(
            source_regime=0,
            target_regime=1,
            count=0,
            total_transitions_from_source=0,
            probability=0.0,
        )
        assert tp.probability == 0.0

        with pytest.raises(ValidationError, match="Probability must be 0.0"):
            TransitionProbability(
                source_regime=0,
                target_regime=1,
                count=0,
                total_transitions_from_source=0,
                probability=0.5,
            )

    def test_count_exceeding_total_rejected(self) -> None:
        with pytest.raises(ValidationError, match="cannot exceed total transitions"):
            TransitionProbability(
                source_regime=0,
                target_regime=1,
                count=5,
                total_transitions_from_source=4,
                probability=1.0,
            )

    def test_mismatched_probability_ratio_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not match empirical ratio"):
            TransitionProbability(
                source_regime=0,
                target_regime=1,
                count=2,
                total_transitions_from_source=10,
                probability=0.50,
            )


class TestTransitionCountMatrix:
    def test_valid_count_matrix(self) -> None:
        matrix = (
            (8, 2, 0),
            (1, 6, 3),
            (0, 2, 9),
        )
        row_totals = {0: 10, 1: 10, 2: 11}
        tcm = TransitionCountMatrix(
            regimes=(0, 1, 2),
            matrix=matrix,
            total_transitions=31,
            row_totals=row_totals,
        )
        assert tcm.cardinality == 3
        assert tcm.get_count(0, 1) == 2
        assert tcm.get_count(1, 2) == 3
        assert tcm.get_count(2, 0) == 0
        assert tcm.get_row(0) == (8, 2, 0)
        assert tcm.get_column(1) == (2, 6, 2)
        assert tcm.to_dict()[0][1] == 2

    def test_mismatched_row_totals_rejected(self) -> None:
        matrix = ((5, 5), (2, 8))
        with pytest.raises(ValidationError, match="does not match computed row sum"):
            TransitionCountMatrix(
                regimes=(0, 1),
                matrix=matrix,
                total_transitions=20,
                row_totals={0: 10, 1: 9},  # 1: 9 is wrong, should be 10
            )

    def test_dimension_mismatch_rejected(self) -> None:
        matrix = ((1, 2),)  # 1 row, but 2 regimes declared
        with pytest.raises(ValidationError, match="Matrix row dimension mismatch"):
            TransitionCountMatrix(
                regimes=(0, 1),
                matrix=matrix,
                total_transitions=3,
                row_totals={0: 3, 1: 0},
            )

    def test_query_key_error_for_unknown_regime(self) -> None:
        matrix = ((5, 5), (2, 8))
        tcm = TransitionCountMatrix(
            regimes=(0, 1),
            matrix=matrix,
            total_transitions=20,
            row_totals={0: 10, 1: 10},
        )
        with pytest.raises(KeyError, match="not in matrix"):
            tcm.get_count(0, 99)


class TestTransitionProbabilityMatrix:
    def test_valid_probability_matrix(self) -> None:
        c_matrix = (
            (8, 2, 0),
            (1, 6, 3),
            (0, 2, 8),
        )
        row_totals = {0: 10, 1: 10, 2: 10}
        tcm = TransitionCountMatrix(
            regimes=(0, 1, 2),
            matrix=c_matrix,
            total_transitions=30,
            row_totals=row_totals,
        )

        p_matrix = (
            (0.8, 0.2, 0.0),
            (0.1, 0.6, 0.3),
            (0.0, 0.2, 0.8),
        )
        tpm = TransitionProbabilityMatrix(
            regimes=(0, 1, 2),
            matrix=p_matrix,
            counts=tcm,
        )
        assert tpm.cardinality == 3
        assert abs(tpm.get_probability(0, 1) - 0.2) < 1e-6
        assert abs(tpm.get_probability(1, 2) - 0.3) < 1e-6
        assert tpm.get_row(0) == (0.8, 0.2, 0.0)
        assert tpm.get_column(1) == (0.2, 0.6, 0.2)
        assert tpm.to_dict()[0][1] == 0.2

    def test_row_sum_not_equal_to_one_rejected(self) -> None:
        c_matrix = ((5, 5), (2, 8))
        tcm = TransitionCountMatrix(
            regimes=(0, 1),
            matrix=c_matrix,
            total_transitions=20,
            row_totals={0: 10, 1: 10},
        )
        invalid_p = ((0.5, 0.4), (0.2, 0.8))  # 0.5 + 0.4 = 0.9 != 1.0
        with pytest.raises(ValidationError, match="simplex invariant"):
            TransitionProbabilityMatrix(
                regimes=(0, 1),
                matrix=invalid_p,
                counts=tcm,
            )


class TestRegimeTransitionResult:
    def test_result_queries(self) -> None:
        c_matrix = ((8, 2), (3, 7))
        tcm = TransitionCountMatrix(
            regimes=(0, 1),
            matrix=c_matrix,
            total_transitions=20,
            row_totals={0: 10, 1: 10},
        )
        p_matrix = ((0.8, 0.2), (0.3, 0.7))
        tpm = TransitionProbabilityMatrix(
            regimes=(0, 1),
            matrix=p_matrix,
            counts=tcm,
        )
        t1 = TransitionRecord(source_regime=0, target_regime=1, timestamp=_ts(1))
        t2 = TransitionRecord(source_regime=1, target_regime=0, timestamp=_ts(2))

        result = RegimeTransitionResult(
            count_matrix=tcm,
            probability_matrix=tpm,
            transitions=(t1, t2),
            regimes_observed=(0, 1),
            total_observations=21,
            total_transitions=20,
            analysis_start=_ts(0),
            analysis_end=_ts(2),
        )

        prob_01 = result.get_transition_probability(0, 1)
        assert prob_01.probability == 0.2
        assert prob_01.count == 2
        assert prob_01.sample_size == 10

        assert result.get_self_transition_probability(0) == 0.8
        assert result.get_self_transition_probability(1) == 0.7

        from_0 = result.get_transitions_from(0)
        assert len(from_0) == 1
        assert from_0[0] == t1

        to_0 = result.get_transitions_to(0)
        assert len(to_0) == 1
        assert to_0[0] == t2

        assert result.get_probabilities_from(0) == {0: 0.8, 1: 0.2}
        assert result.get_probabilities_to(1) == {0: 0.2, 1: 0.7}
        assert result.get_matrix() == p_matrix
        assert result.get_count_matrix() == c_matrix
