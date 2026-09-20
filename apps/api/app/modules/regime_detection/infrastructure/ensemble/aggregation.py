"""
RegimeX Regime Detection — Ensemble Aggregation Engine
======================================================
Deterministic consensus aggregation combining aligned component model predictions.

Architectural Position:
- ``infrastructure/ensemble/aggregation.py``
- Implements weighted voting, majority voting, and plurality voting.
- Enforces deterministic tie-breaking rules and produces audit-ready observation records.

Guarantees:
- Determinism: identical predictions and weights always yield identical consensus.
- Transparency: preserves component predictions, aligned predictions, and agreement metrics.
- Zero fake confidence: discrete agreement counts only (confidence deferred to V11 Commit 02).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime

from app.modules.regime_detection.domain.errors import EnsembleExecutionError
from app.modules.regime_detection.domain.models import (
    AggregationStrategy,
    EnsembleModelConfig,
    EnsembleRecord,
    EnsembleTieBreaker,
)


class EnsembleAggregator:
    """
    Deterministic aggregator for combining aligned model predictions into a consensus regime.
    """

    @classmethod
    def aggregate(
        cls,
        timestamps: Sequence[datetime],
        component_predictions: Mapping[str, Sequence[int]],
        aligned_predictions: Mapping[str, Sequence[int]],
        weights: Mapping[str, float],
        config: EnsembleModelConfig,
    ) -> tuple[tuple[int, ...], tuple[EnsembleRecord, ...]]:
        """
        Aggregate aligned model predictions into consensus canonical regimes.

        Args:
            timestamps: Observation timestamps in chronological order.
            component_predictions: Raw/model-level predictions per model.
            aligned_predictions: Aligned canonical regime predictions per model.
            weights: Active weights per model (already validated and normalized if needed).
            config: Ensemble configuration.

        Returns:
            Tuple of (consensus_regime_ids, ensemble_records).

        Raises:
            EnsembleExecutionError: If dimensional inconsistency or aggregation error occurs.
        """
        n_samples = len(timestamps)
        participating_models = [m for m in config.enabled_models if m in aligned_predictions]

        if not participating_models:
            raise EnsembleExecutionError("No participating models available for aggregation.")

        # Verify all aligned prediction sequences match length
        for model_id in participating_models:
            preds = aligned_predictions[model_id]
            if len(preds) != n_samples:
                raise EnsembleExecutionError(
                    f"Prediction length mismatch for model '{model_id}': "
                    f"expected {n_samples}, got {len(preds)}."
                )

        strategy = config.aggregation_strategy
        tie_breaker = config.tie_breaker

        ensemble_regimes: list[int] = []
        records: list[EnsembleRecord] = []

        for idx in range(n_samples):
            ts = timestamps[idx]

            # Collect votes for this observation
            regime_votes: dict[int, float] = defaultdict(float)
            votes_by_model: dict[str, int] = {}
            raw_by_model: dict[str, int] = {}

            for model_id in participating_models:
                aligned_vote = aligned_predictions[model_id][idx]
                raw_vote = component_predictions[model_id][idx]

                votes_by_model[model_id] = aligned_vote
                raw_by_model[model_id] = raw_vote

                if strategy == AggregationStrategy.WEIGHTED_VOTING:
                    weight = weights.get(model_id, 1.0)
                    regime_votes[aligned_vote] += weight
                elif strategy in (
                    AggregationStrategy.MAJORITY_VOTING,
                    AggregationStrategy.PLURALITY_VOTING,
                ):
                    regime_votes[aligned_vote] += 1.0

            # Determine winner with deterministic tie-breaking
            max_vote = max(regime_votes.values())
            # Find all regimes achieving max_vote within float tolerance
            top_candidates = [
                regime for regime, v in regime_votes.items() if abs(v - max_vote) < 1e-12
            ]

            if len(top_candidates) == 1:
                consensus_regime = top_candidates[0]
            else:
                # Deterministic tie breaking
                if tie_breaker == EnsembleTieBreaker.LOWEST_REGIME_ID:
                    consensus_regime = min(top_candidates)
                elif tie_breaker == EnsembleTieBreaker.MODEL_PRECEDENCE:
                    # Pick the vote of the earliest participating model in config.enabled_models
                    chosen: int | None = None
                    for model_id in config.enabled_models:
                        if (
                            model_id in participating_models
                            and votes_by_model[model_id] in top_candidates
                        ):
                            chosen = votes_by_model[model_id]
                            break
                    consensus_regime = chosen if chosen is not None else min(top_candidates)
                else:
                    consensus_regime = min(top_candidates)

            # Calculate agreement metrics
            agreement_count = sum(1 for v in votes_by_model.values() if v == consensus_regime)
            total_models = len(participating_models)
            disagreeing = tuple(
                sorted(m for m, v in votes_by_model.items() if v != consensus_regime)
            )
            is_unanimous = agreement_count == total_models

            ensemble_regimes.append(consensus_regime)
            records.append(
                EnsembleRecord(
                    timestamp=ts,
                    ensemble_regime_id=consensus_regime,
                    ensemble_regime_label=f"REGIME_{consensus_regime}",
                    model_predictions=raw_by_model,
                    aligned_predictions=votes_by_model,
                    agreement_count=agreement_count,
                    total_models=total_models,
                    disagreeing_models=disagreeing,
                    is_unanimous=is_unanimous,
                )
            )

        return tuple(ensemble_regimes), tuple(records)
