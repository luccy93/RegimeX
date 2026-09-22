"""
RegimeX Regime Transition — Production Engine
==============================================
Production-grade Regime Transition Probability Engine.

Analyzes historical regime sequences and computes statistically grounded empirical
Maximum Likelihood Estimation (MLE) transition count and probability matrices.

Guarantees:
- Zero scikit-learn, PyTorch, or external ML dependencies.
- Zero future lookahead leakage: computes transitions strictly from historical sequence.
- Strict temporal validation: enforces timezone-aware UTC timestamps and chronological order.
- Deterministic behavior: same input produces identical output across all environments.
- Sample-size transparency: preserves observation counts alongside probabilities.
- Non-fabrication: unobserved transitions strictly yield 0.0 empirical probability.
- Seamless integration with V08/V10 RegimeDetectionResult, V09 RegimeAssignment,
  and V11 RegimeEnsembleResult.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
    InvalidRegimeValueError,
    InvalidTransitionSequenceError,
)
from app.modules.regime_transition.domain.interfaces import (
    RegimeTransitionEngineProtocol,
)
from app.modules.regime_transition.domain.models import (
    RegimeTransitionResult,
    TransitionCountMatrix,
    TransitionProbabilityMatrix,
    TransitionRecord,
)

if TYPE_CHECKING:
    from app.modules.regime_detection.domain.models import (
        RegimeDetectionResult,
        RegimeEnsembleResult,
    )
    from app.modules.regime_intelligence.domain.models import RegimeAssignment


class RegimeTransitionEngine(RegimeTransitionEngineProtocol):
    """
    Deterministic service for extracting regime transitions and computing transition matrices.

    Conforms to V12 specifications and V03 Clean Architecture guidelines.
    """

    def __init__(
        self,
        include_self_transitions: bool = True,
        numerical_tolerance: float = 1e-6,
        sort_chronologically: bool = False,
        include_self_in_records: bool = False,
    ) -> None:
        """
        Initialize the RegimeTransitionEngine.

        Args:
            include_self_transitions: Whether count/probability matrices include persistence
                transitions (i -> i). True by default for standard Markov chain matrices.
            numerical_tolerance: Floating-point tolerance for simplex row sum validation (1.0).
            sort_chronologically: If True, automatically sorts observations by timestamp.
                If False (default), strictly raises an error on unsorted input.
            include_self_in_records: If True, self-transitions (persistence) are
                included in the transition event records tuple. Default False
                (records capture state changes).
        """
        self._include_self_transitions = include_self_transitions
        self._numerical_tolerance = numerical_tolerance
        self._sort_chronologically = sort_chronologically
        self._include_self_in_records = include_self_in_records

    def compute_from_assignments(
        self,
        assignments: Sequence[RegimeAssignment],
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from a sequence of V09 RegimeAssignments.

        Args:
            assignments: Chronologically ordered regime assignments.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).

        Returns:
            RegimeTransitionResult: Complete transition analysis result.
        """
        if not assignments:
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=0,
                details={"message": "Cannot compute transitions on empty assignments list."},
            )

        timestamps = tuple(a.timestamp for a in assignments)
        regime_ids = tuple(a.regime_id for a in assignments)
        labels = tuple(a.regime_label for a in assignments)

        return self.compute_from_series(
            timestamps=timestamps,
            regime_ids=regime_ids,
            labels=labels,
            regimes=regimes,
            n_regimes=n_regimes,
        )

    def compute_from_detection_result(
        self,
        result: RegimeDetectionResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from a V08/V10 RegimeDetectionResult.

        Args:
            result: RegimeDetectionResult containing chronological RegimeRecords.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).

        Returns:
            RegimeTransitionResult: Complete transition analysis result.
        """
        records = getattr(result, "records", ())
        if not records:
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=0,
                details={"message": "Cannot compute transitions on empty RegimeDetectionResult."},
            )

        timestamps = tuple(r.timestamp for r in records)
        regime_ids = tuple(r.canonical_regime_id for r in records)
        labels = tuple(r.canonical_regime_label for r in records)

        return self.compute_from_series(
            timestamps=timestamps,
            regime_ids=regime_ids,
            labels=labels,
            regimes=regimes,
            n_regimes=n_regimes,
        )

    def compute_from_ensemble_result(
        self,
        result: RegimeEnsembleResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from a V11 consensus RegimeEnsembleResult.

        Args:
            result: RegimeEnsembleResult containing chronological EnsembleRecords.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).

        Returns:
            RegimeTransitionResult: Complete transition analysis result.
        """
        records = getattr(result, "records", ())
        if not records:
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=0,
                details={"message": "Cannot compute transitions on empty RegimeEnsembleResult."},
            )

        timestamps = tuple(r.timestamp for r in records)
        regime_ids = tuple(r.ensemble_regime_id for r in records)
        labels = tuple(r.ensemble_regime_label for r in records)

        return self.compute_from_series(
            timestamps=timestamps,
            regime_ids=regime_ids,
            labels=labels,
            regimes=regimes,
            n_regimes=n_regimes,
        )

    def compute_from_series(
        self,
        timestamps: Sequence[datetime],
        regime_ids: Sequence[int],
        labels: Sequence[str] | None = None,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> RegimeTransitionResult:
        """
        Compute transition probability matrix from raw timestamps, regime IDs, and labels.

        Args:
            timestamps: Sequence of timezone-aware timestamps.
            regime_ids: Sequence of integer regime IDs.
            labels: Optional sequence of regime string labels.
            regimes: Optional explicit tuple of canonical regime IDs.
            n_regimes: Optional cardinality K (0..K-1).

        Returns:
            RegimeTransitionResult: Strongly typed transition result container.
        """
        n_obs = len(timestamps)
        if n_obs < 2:
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=n_obs,
                details={"message": "Transition calculation requires at least 2 observations."},
            )

        if len(regime_ids) != n_obs:
            raise InvalidTransitionSequenceError(
                f"Dimension mismatch: got {n_obs} timestamps but {len(regime_ids)} regime IDs."
            )

        if labels is not None and len(labels) != n_obs:
            raise InvalidTransitionSequenceError(
                f"Dimension mismatch: got {n_obs} timestamps but {len(labels)} labels."
            )

        resolved_labels: tuple[str, ...] = (
            tuple(labels) if labels is not None else tuple(f"REGIME_{r}" for r in regime_ids)
        )

        # 1. Validate Regime IDs
        for i, r_id in enumerate(regime_ids):
            if r_id is None:
                raise InvalidRegimeValueError(
                    f"Missing regime ID at index {i}. Missing values must not be silently imputed."
                )
            # Check for non-integers, floats, NaNs, infinities
            if isinstance(r_id, bool) or not isinstance(r_id, int):
                raise InvalidRegimeValueError(
                    f"Invalid regime ID type at index {i}: got {type(r_id).__name__} ({r_id!r}). "
                    f"Regime IDs must be non-negative integers."
                )
            if r_id < 0:
                raise InvalidRegimeValueError(
                    f"Negative regime ID detected at index {i}: {r_id}. Must be >= 0."
                )

        # 2. Validate Timestamps
        for i, ts in enumerate(timestamps):
            if ts is None:
                raise InvalidTransitionSequenceError(f"Missing timestamp at index {i}.")
            if not isinstance(ts, datetime):
                raise InvalidTransitionSequenceError(
                    f"Invalid timestamp type at index {i}: got {type(ts).__name__} ({ts!r})."
                )
            if ts.tzinfo is None:
                raise InvalidTransitionSequenceError(
                    f"Timestamp at index {i} is naive ({ts!r}). Timezone-aware UTC required."
                )

        # 3. Handle Ordering / Sorting
        combined = list(zip(timestamps, regime_ids, resolved_labels, strict=True))
        if self._sort_chronologically:
            # Sort chronologically by timestamp
            combined.sort(key=lambda item: item[0])
        else:
            # Strict ordering validation
            for i in range(1, n_obs):
                prev_ts = combined[i - 1][0]
                curr_ts = combined[i][0]
                if curr_ts == prev_ts:
                    raise InvalidTransitionSequenceError(
                        f"Duplicate timestamp detected at index {i}: {curr_ts}."
                    )
                if curr_ts < prev_ts:
                    raise InvalidTransitionSequenceError(
                        f"Timestamps must be strictly ascending: index {i} ({curr_ts}) "
                        f"< index {i - 1} ({prev_ts}). Future-to-past transition prohibited."
                    )

        # Even after sorting, check for duplicates
        for i in range(1, n_obs):
            if combined[i][0] == combined[i - 1][0]:
                raise InvalidTransitionSequenceError(
                    f"Duplicate timestamp detected at index {i}: {combined[i][0]}."
                )

        sorted_timestamps = tuple(item[0] for item in combined)
        sorted_regimes = tuple(item[1] for item in combined)
        sorted_labels = tuple(item[2] for item in combined)

        # 4. Resolve Regime Universe (Cardinality)
        unique_observed = sorted(set(sorted_regimes))
        if regimes is not None:
            regime_universe = tuple(sorted(set(regimes)))
            # Verify observed regimes are within provided universe
            unmapped = set(unique_observed) - set(regime_universe)
            if unmapped:
                raise InvalidRegimeValueError(
                    f"Observed regimes {sorted(unmapped)} not present in "
                    f"configured regimes {regime_universe}."
                )
        elif n_regimes is not None:
            if n_regimes < 1:
                raise InvalidRegimeValueError(
                    f"Configured n_regimes must be >= 1, got {n_regimes}."
                )
            regime_universe = tuple(range(n_regimes))
            unmapped = set(unique_observed) - set(regime_universe)
            if unmapped:
                raise InvalidRegimeValueError(
                    f"Observed regimes {sorted(unmapped)} exceed "
                    f"configured cardinality n_regimes={n_regimes}."
                )
        else:
            # If 0 is observed, use canonical 0..max(observed)
            max_r = max(unique_observed)
            if 0 in unique_observed:
                regime_universe = tuple(range(max_r + 1))
            else:
                regime_universe = tuple(unique_observed)

        regime_to_idx = {r_id: idx for idx, r_id in enumerate(regime_universe)}
        k = len(regime_universe)

        # 5. Extract Transitions and Count Matrix
        raw_counts: list[list[int]] = [[0] * k for _ in range(k)]
        transition_records: list[TransitionRecord] = []
        total_transitions = 0

        for t in range(1, n_obs):
            src = sorted_regimes[t - 1]
            tgt = sorted_regimes[t]
            ts = sorted_timestamps[t]
            src_lbl = sorted_labels[t - 1]
            tgt_lbl = sorted_labels[t]
            is_self = src == tgt

            i = regime_to_idx[src]
            j = regime_to_idx[tgt]

            if not is_self or self._include_self_transitions:
                raw_counts[i][j] += 1
                total_transitions += 1

            if not is_self:
                transition_records.append(
                    TransitionRecord(
                        source_regime=src,
                        target_regime=tgt,
                        timestamp=ts,
                        source_label=src_lbl,
                        target_label=tgt_lbl,
                        is_self_transition=False,
                    )
                )
            elif self._include_self_in_records:
                transition_records.append(
                    TransitionRecord(
                        source_regime=src,
                        target_regime=tgt,
                        timestamp=ts,
                        source_label=src_lbl,
                        target_label=tgt_lbl,
                        is_self_transition=True,
                    )
                )

        count_matrix_tuple = tuple(tuple(row) for row in raw_counts)
        row_totals: dict[int, int] = {
            r_id: sum(raw_counts[regime_to_idx[r_id]]) for r_id in regime_universe
        }

        count_matrix = TransitionCountMatrix(
            regimes=regime_universe,
            matrix=count_matrix_tuple,
            total_transitions=total_transitions,
            row_totals=row_totals,
        )

        # 6. Compute Row-Normalized Empirical Probabilities (MLE)
        raw_probs: list[list[float]] = [[0.0] * k for _ in range(k)]

        for i, r_id in enumerate(regime_universe):
            row_sum = row_totals[r_id]
            if row_sum > 0:
                for j in range(k):
                    raw_probs[i][j] = float(raw_counts[i][j] / row_sum)

        prob_matrix_tuple = tuple(tuple(row) for row in raw_probs)

        prob_matrix = TransitionProbabilityMatrix(
            regimes=regime_universe,
            matrix=prob_matrix_tuple,
            counts=count_matrix,
        )

        return RegimeTransitionResult(
            count_matrix=count_matrix,
            probability_matrix=prob_matrix,
            transitions=tuple(transition_records),
            regimes_observed=tuple(unique_observed),
            total_observations=n_obs,
            total_transitions=total_transitions,
            analysis_start=sorted_timestamps[0],
            analysis_end=sorted_timestamps[-1],
            computed_at=datetime.now(tz=UTC),
        )
