"""
RegimeX Observability — Distribution Drift & Divergence Mathematics
===================================================================
Provides robust, mathematically documented implementations for detecting distribution
shift in categorical model outputs (regime predictions) and continuous input features.

Mathematical Definitions:
1. Jensen-Shannon Divergence (JSD):
   For discrete distributions P and Q with mixture M = 0.5 * (P + Q):
     JSD(P || Q) = 0.5 * D_KL(P || M) + 0.5 * D_KL(Q || M)
   Computed with log2 such that JSD is bounded in [0.0, 1.0].
   Symmetric: JSD(P || Q) == JSD(Q || P).
   Identity: JSD(P || P) == 0.0.

2. Total Variation (TV) Distance:
   TV(P, Q) = 0.5 * sum_i(|P_i - Q_i|)
   Bounded in [0.0, 1.0].

3. Population Stability Index (PSI):
   For binned continuous features with reference distribution P and comparison Q:
     PSI = sum_b (Q_b - P_b) * ln(Q_b / P_b)
   Standard interpretation:
     PSI < 0.10: Insignificant drift / stable
     0.10 <= PSI <= 0.25: Moderate drift
     PSI > 0.25: Significant drift

Guarantees:
- Pure mathematics: standard library + math/collections.
- Handles empty sequences, single-value constant series, and non-finite values safely.
- Deterministic and fully documented.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.modules.observability.domain.enums import DriftMethod, HealthStatus
from app.modules.observability.domain.models import DistributionDriftSnapshot


def compute_jensen_shannon_divergence(
    p: Mapping[Any, float] | Sequence[float],
    q: Mapping[Any, float] | Sequence[float],
) -> float:
    """
    Compute base-2 Jensen-Shannon Divergence between two probability distributions.

    Output is guaranteed to be in [0.0, 1.0].
    """
    p_dict: dict[Any, float]
    q_dict: dict[Any, float]

    if isinstance(p, Mapping) and isinstance(q, Mapping):
        keys = set(p.keys()) | set(q.keys())
        p_dict = {k: float(p.get(k, 0.0)) for k in keys}
        q_dict = {k: float(q.get(k, 0.0)) for k in keys}
    elif isinstance(p, Sequence) and isinstance(q, Sequence):
        n = max(len(p), len(q))
        p_dict = {i: float(p[i]) if i < len(p) else 0.0 for i in range(n)}
        q_dict = {i: float(q[i]) if i < len(q) else 0.0 for i in range(n)}
    else:
        raise TypeError("p and q must both be Mappings or both be Sequences")

    # Normalize to valid probability mass functions if sums differ from 1.0
    sum_p = sum(p_dict.values())
    sum_q = sum(q_dict.values())

    if sum_p <= 0.0 or sum_q <= 0.0:
        return 0.0

    p_norm = {k: v / sum_p for k, v in p_dict.items()}
    q_norm = {k: v / sum_q for k, v in q_dict.items()}

    jsd = 0.0
    for k in p_dict:
        pk = p_norm[k]
        qk = q_norm[k]
        m = 0.5 * (pk + qk)
        if m > 0.0:
            if pk > 0.0:
                jsd += 0.5 * pk * math.log2(pk / m)
            if qk > 0.0:
                jsd += 0.5 * qk * math.log2(qk / m)

    # Clamp floating point tolerances to [0.0, 1.0]
    return max(0.0, min(1.0, float(jsd)))


def compute_total_variation_distance(
    p: Mapping[Any, float] | Sequence[float],
    q: Mapping[Any, float] | Sequence[float],
) -> float:
    """
    Compute Total Variation distance: 0.5 * sum(|p_i - q_i|).
    """
    if isinstance(p, Mapping) and isinstance(q, Mapping):
        keys = set(p.keys()) | set(q.keys())
        p_dict = {k: float(p.get(k, 0.0)) for k in keys}
        q_dict = {k: float(q.get(k, 0.0)) for k in keys}
    elif isinstance(p, Sequence) and isinstance(q, Sequence):
        n = max(len(p), len(q))
        p_dict = {i: float(p[i]) if i < len(p) else 0.0 for i in range(n)}
        q_dict = {i: float(q[i]) if i < len(q) else 0.0 for i in range(n)}
    else:
        raise TypeError("p and q must both be Mappings or both be Sequences")

    sum_p = sum(p_dict.values())
    sum_q = sum(q_dict.values())
    if sum_p <= 0.0 or sum_q <= 0.0:
        return 0.0

    p_norm = {k: v / sum_p for k, v in p_dict.items()}
    q_norm = {k: v / sum_q for k, v in q_dict.items()}

    tv = 0.5 * sum(abs(p_norm[k] - q_norm[k]) for k in p_dict)
    return max(0.0, min(1.0, float(tv)))


def compute_population_stability_index(
    reference: Sequence[float],
    comparison: Sequence[float],
    bins: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """
    Compute Population Stability Index (PSI) between reference and comparison samples.

    Filters non-finite numbers (NaN, Inf). Returns 0.0 if either sample is empty.
    """
    clean_ref = [float(x) for x in reference if math.isfinite(x)]
    clean_comp = [float(x) for x in comparison if math.isfinite(x)]

    if not clean_ref or not clean_comp:
        return 0.0

    # If all reference values are identical (constant distribution)
    min_val = min(clean_ref)
    max_val = max(clean_ref)
    if math.isclose(min_val, max_val, abs_tol=1e-9):
        # Check if comparison values match
        comp_matches = sum(1 for x in clean_comp if math.isclose(x, min_val, abs_tol=1e-9))
        if comp_matches == len(clean_comp):
            return 0.0
        # If comparison has shifted away from the constant
        return 1.0

    # Create uniform bin edges based on reference bounds
    step = (max_val - min_val) / bins
    edges = [min_val + i * step for i in range(bins)]
    edges.append(max_val)

    def assign_bin(val: float) -> int:
        for idx in range(bins):
            if val < edges[idx + 1] or idx == bins - 1:
                return idx
        return bins - 1

    ref_counts = [0] * bins
    for v in clean_ref:
        ref_counts[assign_bin(v)] += 1

    comp_counts = [0] * bins
    for v in clean_comp:
        comp_counts[assign_bin(v)] += 1

    n_ref = len(clean_ref)
    n_comp = len(clean_comp)

    psi = 0.0
    for b in range(bins):
        # Calculate empirical frequencies with smoothing epsilon
        p = max((ref_counts[b] / n_ref), epsilon)
        q = max((comp_counts[b] / n_comp), epsilon)
        psi += (q - p) * math.log(q / p)

    return max(0.0, float(psi))


def evaluate_regime_distribution_drift(
    current_regimes: Sequence[int],
    reference_regimes: Sequence[int],
    threshold: float = 0.25,
    method: DriftMethod = DriftMethod.JENSEN_SHANNON,
) -> DistributionDriftSnapshot:
    """
    Evaluate drift between current regime output predictions and a reference baseline.
    """
    if not current_regimes or not reference_regimes:
        return DistributionDriftSnapshot(
            metric_name="regime_output",
            method=method,
            drift_score=0.0,
            threshold=threshold,
            is_drift_detected=False,
            reference_distribution={},
            comparison_distribution={},
            status=HealthStatus.UNKNOWN,
        )

    # Compute empirical frequency distributions
    curr_counts = Counter(current_regimes)
    ref_counts = Counter(reference_regimes)

    all_keys = sorted(set(curr_counts.keys()) | set(ref_counts.keys()))
    n_curr = len(current_regimes)
    n_ref = len(reference_regimes)

    p_ref = {str(k): ref_counts[k] / n_ref for k in all_keys}
    q_curr = {str(k): curr_counts[k] / n_curr for k in all_keys}

    if method == DriftMethod.TOTAL_VARIATION:
        score = compute_total_variation_distance(p_ref, q_curr)
    else:
        score = compute_jensen_shannon_divergence(p_ref, q_curr)

    is_drift = score > threshold
    if is_drift:
        status = HealthStatus.DEGRADED if score <= threshold * 1.5 else HealthStatus.UNHEALTHY
    else:
        status = HealthStatus.HEALTHY

    return DistributionDriftSnapshot(
        metric_name="regime_output",
        method=method,
        drift_score=score,
        threshold=threshold,
        is_drift_detected=is_drift,
        reference_distribution=p_ref,
        comparison_distribution=q_curr,
        status=status,
    )


def evaluate_feature_drift(
    feature_name: str,
    current_values: Sequence[float],
    reference_values: Sequence[float],
    threshold: float = 0.25,
    method: DriftMethod = DriftMethod.PSI,
) -> DistributionDriftSnapshot:
    """
    Evaluate drift for a continuous feature distribution between current and reference data.
    """
    if not current_values or not reference_values:
        return DistributionDriftSnapshot(
            metric_name=feature_name,
            method=method,
            drift_score=0.0,
            threshold=threshold,
            is_drift_detected=False,
            reference_distribution={},
            comparison_distribution={},
            status=HealthStatus.UNKNOWN,
        )

    psi_score = compute_population_stability_index(
        reference=reference_values,
        comparison=current_values,
    )

    is_drift = psi_score > threshold
    if is_drift:
        status = HealthStatus.DEGRADED if psi_score <= threshold * 1.5 else HealthStatus.UNHEALTHY
    else:
        status = HealthStatus.HEALTHY

    return DistributionDriftSnapshot(
        metric_name=feature_name,
        method=method,
        drift_score=psi_score,
        threshold=threshold,
        is_drift_detected=is_drift,
        reference_distribution={},
        comparison_distribution={},
        status=status,
    )
