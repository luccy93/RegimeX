"""
RegimeX Regime Transition — Analytics Engine
============================================
Calculates downstream historical transition analytics, persistence properties,
destination rankings, transition concentration/entropy, and regime change matrices.

Guarantees:
- Zero scikit-learn, PyTorch, or external ML dependencies.
- Zero future lookahead leakage: operates strictly on historical transitions.
- Information-theoretic transition entropy H(i) = -sum P ln P (nats).
- Deterministic tie-breaking for rankings (prob desc, count desc, target_id asc).
- Sample-size transparency: preserves raw observation counts alongside rates.
- Invariant enforcement: persistence_rate + change_rate == 1.0.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.modules.regime_transition.domain.interfaces import (
    RegimeTransitionAnalyticsProtocol,
)
from app.modules.regime_transition.domain.models import (
    GlobalTransitionAnalytics,
    RankedDestination,
    RegimeTransitionResult,
    TransitionAnalyticsResult,
    TransitionRegimeAnalytics,
)
from app.modules.regime_transition.infrastructure.engine import (
    RegimeTransitionEngine,
)

if TYPE_CHECKING:
    from app.modules.regime_detection.domain.models import (
        RegimeDetectionResult,
        RegimeEnsembleResult,
    )
    from app.modules.regime_intelligence.domain.models import RegimeAssignment


class RegimeTransitionAnalytics(RegimeTransitionAnalyticsProtocol):
    """
    Production-grade transition analytics engine.

    Conforms to V12 Commit 02 specifications.
    """

    def __init__(
        self,
        engine: RegimeTransitionEngine | None = None,
    ) -> None:
        """
        Initialize the RegimeTransitionAnalytics service.

        Args:
            engine: Optional underlying transition engine used for convenience wrappers.
        """
        self._engine = engine or RegimeTransitionEngine()

    def analyze(
        self,
        result: RegimeTransitionResult,
    ) -> TransitionAnalyticsResult:
        """
        Generate comprehensive transition analytics from an existing RegimeTransitionResult.

        Args:
            result: Strongly typed RegimeTransitionResult from Commit 01.

        Returns:
            TransitionAnalyticsResult: Immutable container of per-regime and global analytics.
        """
        count_matrix = result.count_matrix
        prob_matrix = result.probability_matrix
        regimes = count_matrix.regimes
        k = len(regimes)

        # 1. Tabulate Incoming Counts and Distinct Sources per Regime
        incoming_counts: dict[int, int] = dict.fromkeys(regimes, 0)
        distinct_sources: dict[int, int] = dict.fromkeys(regimes, 0)

        for j, tgt_r in enumerate(regimes):
            in_sum = 0
            src_count = 0
            for i, _src_r in enumerate(regimes):
                c = count_matrix.matrix[i][j]
                in_sum += c
                if c > 0:
                    src_count += 1
            incoming_counts[tgt_r] = in_sum
            distinct_sources[tgt_r] = src_count

        # 2. Per-Regime Analytics
        regime_analytics_map: dict[int, TransitionRegimeAnalytics] = {}
        regime_change_counts_list: list[list[int]] = [[0] * k for _ in range(k)]
        regime_change_probs_list: list[list[float]] = [[0.0] * k for _ in range(k)]

        total_self_transitions = 0
        total_regime_changes = 0
        observed_edges = 0

        for i, src_r in enumerate(regimes):
            outgoing = count_matrix.row_totals.get(src_r, 0)
            incoming = incoming_counts[src_r]
            self_count = count_matrix.get_count(src_r, src_r)
            change_count = outgoing - self_count

            total_self_transitions += self_count
            total_regime_changes += change_count

            # Persistence & Change rates
            persistence_prob = prob_matrix.get_probability(src_r, src_r) if outgoing > 0 else 0.0
            change_rate = float(change_count / outgoing) if outgoing > 0 else 0.0

            # Distinct destinations, entropy, rankings
            dest_count = 0
            entropy = 0.0
            destination_candidates: list[tuple[float, int, int]] = []

            for j, tgt_r in enumerate(regimes):
                c = count_matrix.matrix[i][j]
                p = prob_matrix.matrix[i][j]

                if c > 0:
                    dest_count += 1
                    observed_edges += 1

                if p > 0.0:
                    entropy -= p * math.log(p)

                # Collect for ranking: sort key (-prob, -count, target_regime)
                destination_candidates.append((p, c, tgt_r))

                # Fill regime change matrices (zero out diagonal)
                if i != j:
                    regime_change_counts_list[i][j] = c

            # Normalize regime change probabilities
            if change_count > 0:
                for j in range(k):
                    if i != j:
                        regime_change_probs_list[i][j] = float(
                            regime_change_counts_list[i][j] / change_count
                        )

            # Sort rankings deterministically: higher prob first, higher count first,
            # tie-break on target_regime ascending
            destination_candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))

            rankings: list[RankedDestination] = [
                RankedDestination(
                    target_regime=tgt,
                    target_label=f"REGIME_{tgt}",
                    probability=p,
                    count=c,
                    rank=idx + 1,
                )
                for idx, (p, c, tgt) in enumerate(destination_candidates)
            ]

            most_likely_dest: int | None = None
            most_likely_prob: float = 0.0

            if outgoing > 0:
                most_likely_dest = rankings[0].target_regime
                most_likely_prob = rankings[0].probability

            regime_analytics_map[src_r] = TransitionRegimeAnalytics(
                regime_id=src_r,
                regime_label=f"REGIME_{src_r}",
                outgoing_transition_count=outgoing,
                incoming_transition_count=incoming,
                self_transition_count=self_count,
                regime_change_count=change_count,
                persistence_probability=persistence_prob,
                change_rate=change_rate,
                most_likely_destination=most_likely_dest,
                most_likely_destination_probability=most_likely_prob,
                destination_count=dest_count,
                source_count=distinct_sources[src_r],
                transition_entropy=max(0.0, float(entropy)),
                rankings=tuple(rankings),
            )

        # 3. Global Analytics
        total_transitions = count_matrix.total_transitions
        global_change_rate = (
            float(total_regime_changes / total_transitions) if total_transitions > 0 else 0.0
        )
        global_persistence_rate = (
            float(total_self_transitions / total_transitions) if total_transitions > 0 else 0.0
        )

        global_analytics = GlobalTransitionAnalytics(
            total_observations=result.total_observations,
            total_consecutive_transitions=total_transitions,
            total_regime_changes=total_regime_changes,
            total_self_transitions=total_self_transitions,
            global_change_rate=global_change_rate,
            global_persistence_rate=global_persistence_rate,
            number_of_regimes=k,
            number_of_observed_transition_edges=observed_edges,
        )

        change_counts_tuple = tuple(tuple(row) for row in regime_change_counts_list)
        change_probs_tuple = tuple(tuple(row) for row in regime_change_probs_list)

        return TransitionAnalyticsResult(
            transition_result=result,
            regime_analytics=regime_analytics_map,
            global_analytics=global_analytics,
            regime_change_counts=change_counts_tuple,
            regime_change_probabilities=change_probs_tuple,
            computed_at=datetime.now(tz=UTC),
        )

    def analyze_from_assignments(
        self,
        assignments: Sequence[RegimeAssignment],
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> TransitionAnalyticsResult:
        """Compute transition probabilities and analytics from RegimeAssignments."""
        trans_res = self._engine.compute_from_assignments(
            assignments=assignments,
            regimes=regimes,
            n_regimes=n_regimes,
        )
        return self.analyze(trans_res)

    def analyze_from_detection_result(
        self,
        result: RegimeDetectionResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> TransitionAnalyticsResult:
        """Compute transition probabilities and analytics from a RegimeDetectionResult."""
        trans_res = self._engine.compute_from_detection_result(
            result=result,
            regimes=regimes,
            n_regimes=n_regimes,
        )
        return self.analyze(trans_res)

    def analyze_from_ensemble_result(
        self,
        result: RegimeEnsembleResult,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> TransitionAnalyticsResult:
        """Compute transition probabilities and analytics from a RegimeEnsembleResult."""
        trans_res = self._engine.compute_from_ensemble_result(
            result=result,
            regimes=regimes,
            n_regimes=n_regimes,
        )
        return self.analyze(trans_res)

    def analyze_from_series(
        self,
        timestamps: Sequence[datetime],
        regime_ids: Sequence[int],
        labels: Sequence[str] | None = None,
        regimes: Sequence[int] | None = None,
        n_regimes: int | None = None,
    ) -> TransitionAnalyticsResult:
        """Compute transition probabilities and analytics from raw series."""
        trans_res = self._engine.compute_from_series(
            timestamps=timestamps,
            regime_ids=regime_ids,
            labels=labels,
            regimes=regimes,
            n_regimes=n_regimes,
        )
        return self.analyze(trans_res)
