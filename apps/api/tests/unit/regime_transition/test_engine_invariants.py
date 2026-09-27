"""
RegimeX Regime Transition — Engine Invariants & Edge Cases
==========================================================
Verifies transition matrix computation, mathematical properties, and input validation:
- Empty inputs to compute_from_assignments, compute_from_detection_result,
  and compute_from_ensemble_result
- Missing, non-datetime, or timezone-naive timestamps
- Duplicate timestamps after sorting
- Regime universe validation (explicit regimes vs observed, invalid n_regimes < 1, overflow)
- Invariant: each row of transition matrix sums to 1.0 (or 0.0 for unobserved regimes)
- Invariant: self-transition inclusion in transition_records when configured
- Single observation handling (< 2 observations raises InsufficientTransitionDataError)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
    InvalidRegimeValueError,
    InvalidTransitionSequenceError,
)
from app.modules.regime_transition.infrastructure.engine import (
    RegimeTransitionEngine,
)


class TestMarkovTransitionEngineInvariants:
    @pytest.fixture
    def engine(self) -> RegimeTransitionEngine:
        return RegimeTransitionEngine()

    def test_empty_assignments_raises_insufficient_data(
        self, engine: RegimeTransitionEngine
    ) -> None:
        with pytest.raises(InsufficientTransitionDataError):
            engine.compute_from_assignments([])

    def test_single_observation_raises_insufficient_data(
        self, engine: RegimeTransitionEngine
    ) -> None:
        ts = [datetime(2026, 1, 1, tzinfo=UTC)]
        with pytest.raises(InsufficientTransitionDataError):
            engine.compute_from_series(timestamps=ts, regime_ids=[0])

    def test_naive_timestamp_raises_invalid_sequence(self, engine: RegimeTransitionEngine) -> None:
        ts = [datetime(2026, 1, 1), datetime(2026, 1, 2)]  # naive
        with pytest.raises(InvalidTransitionSequenceError, match="naive"):
            engine.compute_from_series(timestamps=ts, regime_ids=[0, 1])

    def test_none_or_non_datetime_raises_invalid_sequence(
        self, engine: RegimeTransitionEngine
    ) -> None:
        ts_with_none: Any = [datetime(2026, 1, 1, tzinfo=UTC), None]
        with pytest.raises(InvalidTransitionSequenceError, match="Missing timestamp"):
            engine.compute_from_series(timestamps=ts_with_none, regime_ids=[0, 1])

        ts_with_str: Any = [datetime(2026, 1, 1, tzinfo=UTC), "2026-01-02"]
        with pytest.raises(InvalidTransitionSequenceError, match="Invalid timestamp type"):
            engine.compute_from_series(timestamps=ts_with_str, regime_ids=[0, 1])

    def test_duplicate_timestamp_raises_invalid_sequence(
        self, engine: RegimeTransitionEngine
    ) -> None:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        ts = [t0, t0]  # duplicate
        with pytest.raises(InvalidTransitionSequenceError, match="Duplicate timestamp"):
            engine.compute_from_series(timestamps=ts, regime_ids=[0, 1])

    def test_unmapped_regimes_in_explicit_universe_raises(
        self, engine: RegimeTransitionEngine
    ) -> None:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        ts = [t0, t0 + timedelta(days=1), t0 + timedelta(days=2)]
        # Observed regime 2, but explicit universe is (0, 1)
        with pytest.raises(InvalidRegimeValueError, match="not present in configured regimes"):
            engine.compute_from_series(timestamps=ts, regime_ids=[0, 1, 2], regimes=(0, 1))

    def test_invalid_n_regimes_cardinality_raises(self, engine: RegimeTransitionEngine) -> None:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        ts = [t0, t0 + timedelta(days=1)]
        with pytest.raises(InvalidRegimeValueError, match="n_regimes must be >= 1"):
            engine.compute_from_series(timestamps=ts, regime_ids=[0, 0], n_regimes=0)

        # Observed regime 2, but n_regimes=2 (universe 0..1)
        with pytest.raises(InvalidRegimeValueError, match="exceed configured cardinality"):
            engine.compute_from_series(timestamps=ts, regime_ids=[0, 2], n_regimes=2)

    def test_matrix_row_stochastic_invariant(self, engine: RegimeTransitionEngine) -> None:
        """Every row of transition probability matrix with outgoing transitions sums to 1.0."""
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        ts = [t0 + timedelta(days=i) for i in range(20)]
        # Regimes alternating 0, 1, 2
        r_ids = [(i % 3) for i in range(20)]

        res = engine.compute_from_series(timestamps=ts, regime_ids=r_ids, n_regimes=3)
        matrix = res.probability_matrix

        for i, row in enumerate(matrix.matrix):
            row_sum = sum(row)
            assert abs(row_sum - 1.0) < 1e-6, f"Row {i} sum {row_sum} != 1.0"

    def test_include_self_in_records_configuration(self) -> None:
        engine = RegimeTransitionEngine(
            include_self_transitions=True,
            include_self_in_records=True,
        )
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        ts = [t0, t0 + timedelta(days=1), t0 + timedelta(days=2)]
        # Constant regime 0 -> 0 -> 0 (all self-transitions)
        res = engine.compute_from_series(timestamps=ts, regime_ids=[0, 0, 0])

        assert len(res.transitions) == 2
        assert all(rec.is_self_transition for rec in res.transitions)
