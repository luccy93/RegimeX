"""Unit tests for statistical drift calculations (JSD, Total Variation, PSI).

Tests cover:
- Identical distributions
- Small distribution shift
- Large distribution shift
- Constant distributions
- Empty reference / comparison data
- Non-finite (NaN / Inf) values
- Continuous feature PSI calculation
"""

import numpy as np
import pytest
from app.modules.observability.domain.drift import (
    compute_jensen_shannon_divergence,
    compute_population_stability_index,
    compute_total_variation_distance,
    evaluate_feature_drift,
    evaluate_regime_distribution_drift,
)
from app.modules.observability.domain.enums import DriftMethod, HealthStatus


def test_jsd_identical_distributions() -> None:
    """JSD between identical distributions should be identically zero."""
    dist_a = {"0": 0.5, "1": 0.3, "2": 0.2}
    dist_b = {"0": 0.5, "1": 0.3, "2": 0.2}

    jsd = compute_jensen_shannon_divergence(dist_a, dist_b)
    assert jsd == pytest.approx(0.0, abs=1e-7)


def test_jsd_small_and_large_shift() -> None:
    """JSD increases monotonically with distribution divergence."""
    ref = {"0": 0.5, "1": 0.5}
    small_shift = {"0": 0.55, "1": 0.45}
    large_shift = {"0": 0.95, "1": 0.05}
    disjoint = {"0": 1.0, "1": 0.0}
    opposite = {"0": 0.0, "1": 1.0}

    jsd_small = compute_jensen_shannon_divergence(ref, small_shift)
    jsd_large = compute_jensen_shannon_divergence(ref, large_shift)
    jsd_disjoint = compute_jensen_shannon_divergence(disjoint, opposite)

    assert 0.0 < jsd_small < jsd_large <= 1.0
    assert jsd_disjoint == pytest.approx(1.0, abs=1e-5)


def test_jsd_empty_or_zero_distributions() -> None:
    """Empty or all-zero distributions should safely evaluate to 0.0."""
    assert compute_jensen_shannon_divergence({}, {}) == 0.0
    assert compute_jensen_shannon_divergence({"0": 0.0}, {"0": 0.0}) == 0.0
    assert compute_jensen_shannon_divergence({"0": 1.0}, {}) == 0.0


def test_jsd_mismatched_keys() -> None:
    """Mismatched categories should be smoothed and unioned correctly."""
    ref = {"0": 1.0}
    comp = {"1": 1.0}
    jsd = compute_jensen_shannon_divergence(ref, comp)
    assert 0.0 < jsd <= 1.0


def test_total_variation_distance() -> None:
    """Total variation distance is bounded in [0, 1]."""
    ref = {"0": 0.7, "1": 0.3}
    comp = {"0": 0.4, "1": 0.6}
    # TV = 0.5 * (|0.7 - 0.4| + |0.3 - 0.6|) = 0.5 * (0.3 + 0.3) = 0.3
    tv = compute_total_variation_distance(ref, comp)
    assert tv == pytest.approx(0.3, abs=1e-5)


def test_total_variation_identical_and_disjoint() -> None:
    """TV should be 0 for identical and 1 for disjoint distributions."""
    ref = {"0": 1.0, "1": 0.0}
    assert compute_total_variation_distance(ref, ref) == 0.0

    disjoint = {"0": 0.0, "1": 1.0}
    assert compute_total_variation_distance(ref, disjoint) == pytest.approx(1.0, abs=1e-5)


def test_psi_identical_distributions() -> None:
    """PSI between identical continuous samples should be near zero."""
    rng = np.random.default_rng(42)
    sample_a = [float(x) for x in rng.normal(loc=0.0, scale=1.0, size=500)]
    sample_b = [float(x) for x in rng.normal(loc=0.0, scale=1.0, size=500)]

    psi = compute_population_stability_index(sample_a, sample_b, bins=10)
    assert psi < 0.10


def test_psi_shifted_distributions() -> None:
    """PSI significantly detects distribution shift."""
    rng = np.random.default_rng(42)
    sample_a = [float(x) for x in rng.normal(loc=0.0, scale=1.0, size=500)]
    sample_b = [float(x) for x in rng.normal(loc=2.0, scale=1.0, size=500)]

    psi = compute_population_stability_index(sample_a, sample_b, bins=10)
    assert psi > 0.25


def test_psi_empty_or_small_samples() -> None:
    """Empty or undersized samples safely return 0.0."""
    assert compute_population_stability_index([], []) == 0.0


def test_psi_constant_distributions() -> None:
    """Constant values in reference do not trigger division-by-zero or crashes."""
    constant_ref = [5.0] * 50
    comparison = [5.0] * 50
    psi = compute_population_stability_index(constant_ref, comparison)
    assert psi == 0.0


def test_psi_nan_inf_handling() -> None:
    """NaNs and Infs are filtered cleanly before binning."""
    ref = [1.0, 2.0, float(np.nan), 3.0, float(np.inf), 4.0, float(-np.inf), 5.0] * 10
    comp = [1.0, 2.0, 3.0, 4.0, 5.0] * 10

    psi = compute_population_stability_index(ref, comp, bins=5)
    assert psi == pytest.approx(0.0, abs=1e-2)


def test_evaluate_regime_distribution_drift() -> None:
    """Evaluate regime distribution drift snapshot and detection flag."""
    ref_regimes = [0, 0, 1, 1, 0, 0, 1, 1]
    curr_stable = [0, 0, 1, 1, 0, 0, 1, 1]

    snapshot = evaluate_regime_distribution_drift(
        current_regimes=curr_stable,
        reference_regimes=ref_regimes,
        threshold=0.15,
        method=DriftMethod.JENSEN_SHANNON,
    )

    assert snapshot.metric_name == "regime_output"
    assert snapshot.method == DriftMethod.JENSEN_SHANNON
    assert snapshot.drift_score < 0.15
    assert not snapshot.is_drift_detected
    assert snapshot.status == HealthStatus.HEALTHY

    # Test drift detected when predictions shift to 100% regime 1
    curr_shifted = [1, 1, 1, 1, 1, 1, 1, 1]
    drifted_snapshot = evaluate_regime_distribution_drift(
        current_regimes=curr_shifted,
        reference_regimes=ref_regimes,
        threshold=0.15,
        method=DriftMethod.JENSEN_SHANNON,
    )
    assert drifted_snapshot.is_drift_detected
    assert drifted_snapshot.drift_score > 0.15
    assert drifted_snapshot.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)


def test_evaluate_feature_drift() -> None:
    """evaluate_feature_drift evaluates continuous feature sequences."""
    ref_vals = [1.0, 2.0, 3.0, 4.0, 5.0] * 20
    curr_vals = [1.0, 2.0, 3.0, 4.0, 5.0] * 20

    snapshot = evaluate_feature_drift(
        feature_name="log_volatility",
        current_values=curr_vals,
        reference_values=ref_vals,
        threshold=0.25,
    )
    assert snapshot.metric_name == "log_volatility"
    assert snapshot.method == DriftMethod.PSI
    assert not snapshot.is_drift_detected
    assert snapshot.status == HealthStatus.HEALTHY
