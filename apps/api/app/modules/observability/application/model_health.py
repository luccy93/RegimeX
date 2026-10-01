"""
RegimeX Observability — Model Health Monitor
============================================
Evaluates operational health, prediction validity, confidence, stability, and
distribution drift across KMeans, GMM, HMM, and Ensemble regime models.

Guarantees:
- Never silently modifies or repairs invalid model outputs.
- Invariants checked: valid regime IDs in [0, K-1], finite values, valid probability
  distributions summing to 1.0 within floating point tolerance.
- Evaluates operational stability and regime switching dynamics.
- Emits Prometheus telemetry metrics with strictly bounded labels.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence

from app.modules.observability.domain.drift import (
    evaluate_regime_distribution_drift,
)
from app.modules.observability.domain.enums import DriftMethod, HealthStatus
from app.modules.observability.domain.models import (
    DistributionDriftSnapshot,
    ModelConfidenceSnapshot,
    ModelExecutionSnapshot,
    ModelHealthSnapshot,
    ModelStabilitySnapshot,
    PredictionValiditySnapshot,
    RegimeDistributionSnapshot,
)
from app.modules.observability.infrastructure.metrics import metrics
from app.modules.regime_detection.domain.models import (
    RegimeDetectionResult,
    RegimeEnsembleResult,
)


class ModelExecutionAccumulator:
    """Tracks latency and failure statistics for a specific model."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.prediction_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0.0

    def record(self, success: bool, latency_ms: float = 0.0) -> None:
        self.prediction_count += 1
        self.total_latency_ms += max(0.0, latency_ms)
        if not success:
            self.failure_count += 1

    def to_snapshot(self) -> ModelExecutionSnapshot:
        if self.prediction_count == 0:
            return ModelExecutionSnapshot(
                prediction_count=0,
                failure_count=0,
                failure_rate=0.0,
                avg_latency_ms=0.0,
                status=HealthStatus.UNKNOWN,
            )

        fail_rate = float(self.failure_count / self.prediction_count)
        avg_lat = float(self.total_latency_ms / self.prediction_count)

        if fail_rate >= 0.10:
            status = HealthStatus.UNHEALTHY
        elif fail_rate > 0.02 or avg_lat > 2000.0:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return ModelExecutionSnapshot(
            prediction_count=self.prediction_count,
            failure_count=self.failure_count,
            failure_rate=fail_rate,
            avg_latency_ms=avg_lat,
            status=status,
        )


class ModelHealthMonitor:
    """
    Evaluator for regime model prediction validity, confidence, stability, and drift.
    """

    def __init__(
        self,
        health_window: int = 100,
        low_confidence_threshold: float = 0.5,
        drift_threshold: float = 0.25,
    ) -> None:
        self.health_window = max(10, health_window)
        self.low_confidence_threshold = low_confidence_threshold
        self.drift_threshold = drift_threshold
        self._execution_trackers: dict[str, ModelExecutionAccumulator] = {}

    def _get_tracker(self, model_id: str) -> ModelExecutionAccumulator:
        mid = model_id.lower()
        if mid not in self._execution_trackers:
            self._execution_trackers[mid] = ModelExecutionAccumulator(mid)
        return self._execution_trackers[mid]

    def record_execution(self, model_id: str, success: bool, latency_ms: float = 0.0) -> None:
        """Record model execution invocation."""
        tracker = self._get_tracker(model_id)
        tracker.record(success=success, latency_ms=latency_ms)

    def evaluate_prediction_validity(
        self,
        predictions: Sequence[int],
        k_clusters: int,
        probabilities: Sequence[Sequence[float] | None] | None = None,
        model_id: str = "regime_model",
    ) -> PredictionValiditySnapshot:
        """
        Verify mathematical invariants of model outputs.
        """
        total = len(predictions)
        if total == 0:
            return PredictionValiditySnapshot(
                total_predictions=0,
                valid_predictions=0,
                invalid_predictions=0,
                invalid_regime_ids=0,
                non_finite_values=0,
                invalid_probability_vectors=0,
                status=HealthStatus.UNKNOWN,
                violations=("No predictions provided for evaluation",),
            )

        invalid_regime_ids = 0
        non_finite_values = 0
        invalid_probability_vectors = 0
        violations: list[str] = []

        for idx, r_id in enumerate(predictions):
            # Check integer / finite
            if not isinstance(r_id, (int,)) or isinstance(r_id, bool) or not math.isfinite(r_id):
                non_finite_values += 1
                violations.append(
                    f"Observation {idx}: non-finite or non-integer regime ID: {r_id!r}"
                )
            elif r_id < 0 or r_id >= k_clusters:
                invalid_regime_ids += 1
                violations.append(
                    f"Observation {idx}: regime ID {r_id} out of bounds [0, {k_clusters - 1}]"
                )

        if probabilities is not None:
            for idx, prob_vec in enumerate(probabilities):
                if prob_vec is not None:
                    if len(prob_vec) != k_clusters:
                        invalid_probability_vectors += 1
                        violations.append(
                            f"Observation {idx}: vector len ({len(prob_vec)}) != K ({k_clusters})"
                        )
                        continue

                    # Check probabilities in [0, 1] and sum ≈ 1.0
                    has_non_finite = any(not math.isfinite(p) for p in prob_vec)
                    if has_non_finite:
                        non_finite_values += 1
                        invalid_probability_vectors += 1
                        violations.append(f"Observation {idx}: non-finite probability in vector")
                        continue

                    any_out_of_bounds = any(p < -1e-6 or p > 1.0 + 1e-6 for p in prob_vec)
                    prob_sum = sum(prob_vec)
                    if any_out_of_bounds or not math.isclose(prob_sum, 1.0, abs_tol=1e-3):
                        invalid_probability_vectors += 1
                        violations.append(
                            f"Observation {idx}: invalid prob vector "
                            f"(sum={prob_sum:.4f}, min={min(prob_vec):.4f})"
                        )

        invalid_total = invalid_regime_ids + non_finite_values + invalid_probability_vectors
        valid_count = max(0, total - invalid_total)

        if invalid_total > 0:
            status = HealthStatus.UNHEALTHY
            metrics.record_prediction_failure(
                model_id=model_id, reason="validity_invariant_violation"
            )
        else:
            status = HealthStatus.HEALTHY

        return PredictionValiditySnapshot(
            total_predictions=total,
            valid_predictions=valid_count,
            invalid_predictions=invalid_total,
            invalid_regime_ids=invalid_regime_ids,
            non_finite_values=non_finite_values,
            invalid_probability_vectors=invalid_probability_vectors,
            status=status,
            violations=tuple(violations[:20]),  # Bounded sample of violations
        )

    def evaluate_confidence(
        self,
        confidences: Sequence[float | None],
        threshold: float | None = None,
        model_id: str = "regime_model",
    ) -> ModelConfidenceSnapshot:
        """
        Evaluate confidence score distribution and low-confidence prediction frequency.
        """
        low_thresh = threshold if threshold is not None else self.low_confidence_threshold
        valid_scores = [float(c) for c in confidences if c is not None and math.isfinite(c)]
        missing_count = sum(1 for c in confidences if c is None or not math.isfinite(c))

        if not valid_scores:
            return ModelConfidenceSnapshot(
                mean_confidence=None,
                min_confidence=None,
                max_confidence=None,
                std_confidence=None,
                low_confidence_count=0,
                low_confidence_ratio=0.0,
                missing_confidence_count=missing_count,
                status=HealthStatus.UNKNOWN,
            )

        mean_c = float(sum(valid_scores) / len(valid_scores))
        min_c = float(min(valid_scores))
        max_c = float(max(valid_scores))

        variance = (
            sum((x - mean_c) ** 2 for x in valid_scores) / len(valid_scores)
            if len(valid_scores) > 1
            else 0.0
        )
        std_c = float(math.sqrt(variance))

        low_count = sum(1 for c in valid_scores if c < low_thresh)
        low_ratio = float(low_count / len(valid_scores))

        if low_ratio >= 0.50:
            status = HealthStatus.UNHEALTHY
        elif low_ratio >= 0.25 or mean_c < low_thresh:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        if low_count > 0:
            metrics.record_model_health(
                model_id=model_id,
                status=status.value,
                low_confidence_count=low_count,
            )

        return ModelConfidenceSnapshot(
            mean_confidence=mean_c,
            min_confidence=min_c,
            max_confidence=max_c,
            std_confidence=std_c,
            low_confidence_count=low_count,
            low_confidence_ratio=low_ratio,
            missing_confidence_count=missing_count,
            status=status,
        )

    def evaluate_stability(
        self,
        predictions: Sequence[int],
        confidences: Sequence[float | None] | None = None,
    ) -> ModelStabilitySnapshot:
        """
        Evaluate regime switching frequency and sequence persistence.
        """
        total = len(predictions)
        if total <= 1:
            return ModelStabilitySnapshot(
                regime_switching_frequency=0.0,
                consecutive_stable_bars=total,
                confidence_variability=0.0,
                status=HealthStatus.HEALTHY if total == 1 else HealthStatus.UNKNOWN,
            )

        switches = 0
        longest_streak = 1
        current_streak = 1

        for i in range(1, total):
            if predictions[i] != predictions[i - 1]:
                switches += 1
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
            else:
                current_streak += 1
        longest_streak = max(longest_streak, current_streak)

        switch_freq = float(switches / (total - 1))

        # Confidence variability
        conf_std = 0.0
        if confidences:
            valid_c = [float(c) for c in confidences if c is not None and math.isfinite(c)]
            if len(valid_c) > 1:
                mean_c = sum(valid_c) / len(valid_c)
                conf_std = math.sqrt(sum((x - mean_c) ** 2 for x in valid_c) / len(valid_c))

        # Operational stability thresholds:
        # If switching every bar or two (> 65% switching frequency), model is chattering/unstable
        if switch_freq >= 0.70:
            status = HealthStatus.UNHEALTHY
        elif switch_freq >= 0.45:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return ModelStabilitySnapshot(
            regime_switching_frequency=switch_freq,
            consecutive_stable_bars=longest_streak,
            confidence_variability=conf_std,
            status=status,
        )

    def evaluate_regime_distribution(
        self, predictions: Sequence[int]
    ) -> RegimeDistributionSnapshot:
        """
        Calculate descriptive empirical regime distribution and entropy.
        """
        total = len(predictions)
        if total == 0:
            return RegimeDistributionSnapshot(
                sample_count=0,
                regime_counts={},
                regime_percentages={},
                entropy=0.0,
            )

        counts = Counter(predictions)
        percentages = {k: float(counts[k] / total) * 100.0 for k in sorted(counts.keys())}

        # Shannon entropy: H = - sum(p * ln(p))
        entropy = 0.0
        for p_pct in percentages.values():
            p = p_pct / 100.0
            if p > 0.0:
                entropy -= p * math.log(p)

        return RegimeDistributionSnapshot(
            sample_count=total,
            regime_counts={k: counts[k] for k in sorted(counts.keys())},
            regime_percentages=percentages,
            entropy=float(entropy),
        )

    def evaluate_model_health(
        self,
        model_id: str,
        predictions: Sequence[int],
        k_clusters: int,
        probabilities: Sequence[Sequence[float] | None] | None = None,
        confidences: Sequence[float | None] | None = None,
        reference_predictions: Sequence[int] | None = None,
    ) -> ModelHealthSnapshot:
        """
        Comprehensive evaluation of model health producing an immutable ModelHealthSnapshot.
        """
        validity = self.evaluate_prediction_validity(
            predictions=predictions,
            k_clusters=k_clusters,
            probabilities=probabilities,
            model_id=model_id,
        )
        execution = self._get_tracker(model_id).to_snapshot()

        # Derive confidences if not explicitly provided
        effective_confidences: list[float | None] = []
        if confidences:
            effective_confidences = list(confidences)
        elif probabilities:
            for p_vec in probabilities:
                if p_vec:
                    effective_confidences.append(max(p_vec))
                else:
                    effective_confidences.append(None)
        else:
            effective_confidences = [None] * len(predictions)

        confidence_snap = self.evaluate_confidence(
            confidences=effective_confidences,
            model_id=model_id,
        )
        stability = self.evaluate_stability(
            predictions=predictions,
            confidences=effective_confidences,
        )
        regime_dist = self.evaluate_regime_distribution(predictions=predictions)

        # Drift evaluation against reference
        drift_snap: DistributionDriftSnapshot | None = None
        if reference_predictions:
            drift_snap = evaluate_regime_distribution_drift(
                current_regimes=predictions,
                reference_regimes=reference_predictions,
                threshold=self.drift_threshold,
                method=DriftMethod.JENSEN_SHANNON,
            )

        # Synthesize overall status: UNHEALTHY > DEGRADED > UNKNOWN > HEALTHY
        statuses = [validity.status, stability.status]
        if execution.status != HealthStatus.UNKNOWN:
            statuses.append(execution.status)
        if confidence_snap.status != HealthStatus.UNKNOWN:
            statuses.append(confidence_snap.status)
        if drift_snap is not None and drift_snap.status != HealthStatus.UNKNOWN:
            statuses.append(drift_snap.status)

        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNKNOWN for s in statuses):
            overall = HealthStatus.UNKNOWN
        else:
            overall = HealthStatus.HEALTHY

        summary = (
            f"Model {model_id}: status={overall.value} | "
            f"validity={validity.status.value} "
            f"(valid={validity.valid_predictions}/{validity.total_predictions}) | "
            f"switching_freq={stability.regime_switching_frequency:.2f} | "
            f"mean_confidence={(confidence_snap.mean_confidence or 0.0):.2f}"
        )

        # Record metrics telemetry
        metrics.record_model_health(
            model_id=model_id,
            status=overall.value,
            drift_score=drift_snap.drift_score if drift_snap else None,
            low_confidence_count=confidence_snap.low_confidence_count,
        )

        return ModelHealthSnapshot(
            model_id=model_id,
            status=overall,
            validity=validity,
            execution=execution,
            confidence=confidence_snap,
            stability=stability,
            regime_distribution=regime_dist,
            drift=drift_snap,
            summary=summary,
        )

    def evaluate_detection_result(
        self,
        result: RegimeDetectionResult,
        k_clusters: int = 4,
        reference_predictions: Sequence[int] | None = None,
    ) -> ModelHealthSnapshot:
        """Convenience method evaluating a RegimeDetectionResult."""
        preds = result.get_regime_series()
        probs = [r.probabilities for r in result.records]
        return self.evaluate_model_health(
            model_id=result.algorithm,
            predictions=preds,
            k_clusters=k_clusters,
            probabilities=probs,
            reference_predictions=reference_predictions,
        )

    def evaluate_ensemble_result(
        self,
        result: RegimeEnsembleResult,
        k_clusters: int = 4,
        reference_predictions: Sequence[int] | None = None,
    ) -> ModelHealthSnapshot:
        """Convenience method evaluating a RegimeEnsembleResult."""
        preds = (
            result.ensemble_regimes
            if getattr(result, "ensemble_regimes", None)
            else tuple(r.ensemble_regime_id for r in result.records)
        )
        confs = (
            list(result.confidence_scores)
            if getattr(result, "confidence_scores", None)
            else [r.confidence for r in result.records]
        )
        return self.evaluate_model_health(
            model_id="ensemble",
            predictions=preds,
            k_clusters=k_clusters,
            confidences=confs,
            reference_predictions=reference_predictions,
        )
