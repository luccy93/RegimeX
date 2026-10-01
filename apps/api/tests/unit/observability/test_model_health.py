"""Unit tests for Model Health Monitoring.

Tests cover:
- Valid KMeans, GMM, HMM, and Ensemble output evaluation
- Invalid regime ID detection (out of bounds)
- Invalid probability vector detection (sum != 1, out of bounds [0, 1])
- Non-finite (NaN / Inf) values in predictions and probabilities
- Model execution failure rate tracking
- Low confidence prediction detection and ratio computation
- Stability and regime switching frequency
- Full ModelHealthSnapshot creation
"""

import math
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from app.modules.observability.application.model_health import ModelHealthMonitor
from app.modules.observability.domain.enums import HealthStatus
from app.modules.regime_detection.domain.models import (
    RegimeDetectionResult,
    RegimeEnsembleResult,
    RegimeRecord,
)


def test_valid_kmeans_output() -> None:
    """Valid KMeans output produces healthy validity and stability snapshots."""
    monitor = ModelHealthMonitor(health_window=100)
    predictions = [0, 0, 0, 1, 1, 1, 0, 0, 1, 1] * 5

    snapshot = monitor.evaluate_prediction_validity(
        predictions=predictions,
        k_clusters=2,
        probabilities=None,
        model_id="kmeans",
    )

    assert snapshot.status == HealthStatus.HEALTHY
    assert snapshot.total_predictions == 50
    assert snapshot.valid_predictions == 50
    assert snapshot.invalid_predictions == 0
    assert snapshot.invalid_regime_ids == 0
    assert snapshot.non_finite_values == 0


def test_valid_gmm_output_with_posterior() -> None:
    """Valid GMM posterior probabilities satisfy sum == 1 and [0, 1] bounds."""
    monitor = ModelHealthMonitor()
    predictions = [0, 1, 2, 0, 1, 2]
    probabilities = [
        [0.8, 0.1, 0.1],
        [0.1, 0.8, 0.1],
        [0.05, 0.05, 0.9],
        [0.7, 0.2, 0.1],
        [0.15, 0.7, 0.15],
        [0.1, 0.1, 0.8],
    ]

    snapshot = monitor.evaluate_prediction_validity(
        predictions=predictions,
        k_clusters=3,
        probabilities=probabilities,
        model_id="gmm",
    )

    assert snapshot.status == HealthStatus.HEALTHY
    assert snapshot.valid_predictions == 6
    assert snapshot.invalid_probability_vectors == 0


def test_invalid_regime_id_out_of_bounds() -> None:
    """Regime ID outside [0, K-1] is marked UNHEALTHY without silent repair."""
    monitor = ModelHealthMonitor()
    predictions = [0, 1, 5, -1, 2]  # 5 and -1 are invalid for K=3

    snapshot = monitor.evaluate_prediction_validity(
        predictions=predictions,
        k_clusters=3,
        model_id="kmeans",
    )

    assert snapshot.status == HealthStatus.UNHEALTHY
    assert snapshot.invalid_regime_ids == 2
    assert snapshot.valid_predictions == 3
    assert len(snapshot.violations) >= 2


def test_invalid_probability_vector_sum() -> None:
    """Probability vector that does not sum to 1.0 is flagged as an invariant violation."""
    monitor = ModelHealthMonitor()
    predictions = [0, 1]
    bad_probabilities = [
        [0.5, 0.2],  # sums to 0.7 != 1.0
        [0.8, 0.8],  # sums to 1.6 != 1.0
    ]

    snapshot = monitor.evaluate_prediction_validity(
        predictions=predictions,
        k_clusters=2,
        probabilities=bad_probabilities,
        model_id="hmm",
    )

    assert snapshot.status == HealthStatus.UNHEALTHY
    assert snapshot.invalid_probability_vectors == 2


def test_non_finite_predictions_and_probabilities() -> None:
    """NaN or Inf in predictions or probabilities triggers health failure."""
    monitor = ModelHealthMonitor()
    predictions: list[Any] = [0, float("nan"), 1]
    probabilities = [
        [0.5, 0.5],
        [float("nan"), 0.5],
        [0.2, 0.8],
    ]

    snapshot = monitor.evaluate_prediction_validity(
        predictions=predictions,
        k_clusters=2,
        probabilities=probabilities,
        model_id="hmm",
    )

    assert snapshot.status == HealthStatus.UNHEALTHY
    assert snapshot.non_finite_values >= 1


def test_model_execution_tracking() -> None:
    """Execution tracker tracks failure counts and calculates failure rate."""
    monitor = ModelHealthMonitor()

    monitor.record_execution("kmeans", success=True, latency_ms=10.0)
    monitor.record_execution("kmeans", success=True, latency_ms=20.0)
    monitor.record_execution("kmeans", success=False, latency_ms=5.0)

    snap = monitor._get_tracker("kmeans").to_snapshot()
    assert snap.prediction_count == 3
    assert snap.failure_count == 1
    assert math.isclose(snap.failure_rate, 1 / 3, abs_tol=1e-3)
    assert snap.status == HealthStatus.UNHEALTHY  # fail_rate >= 0.10


def test_confidence_monitoring() -> None:
    """Evaluates mean confidence and low-confidence prediction frequency."""
    monitor = ModelHealthMonitor(low_confidence_threshold=0.60)
    confidences = [0.95, 0.85, 0.40, 0.35, 0.90]

    snap = monitor.evaluate_confidence(confidences, model_id="ensemble")
    assert snap.low_confidence_count == 2
    assert snap.low_confidence_ratio == 0.40
    assert snap.status == HealthStatus.DEGRADED  # low_ratio >= 0.25


def test_stability_regime_switching_frequency() -> None:
    """Tracks switching frequency and longest consecutive stable streaks."""
    monitor = ModelHealthMonitor()

    # Stable run
    stable_preds = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    stable_snap = monitor.evaluate_stability(stable_preds)
    assert stable_snap.regime_switching_frequency == 1 / 9
    assert stable_snap.consecutive_stable_bars == 5
    assert stable_snap.status == HealthStatus.HEALTHY

    # Chattering unstable run (switches every bar)
    chattering_preds = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    unstable_snap = monitor.evaluate_stability(chattering_preds)
    assert unstable_snap.regime_switching_frequency == 1.0
    assert unstable_snap.status == HealthStatus.UNHEALTHY


def test_evaluate_detection_result_integration() -> None:
    """Integrates with RegimeDetectionResult domain model."""
    monitor = ModelHealthMonitor()
    now = datetime.now(tz=UTC)
    records = tuple(
        RegimeRecord(
            timestamp=now,
            cluster_id=i % 2,
            canonical_regime_id=i % 2,
            canonical_regime_label=f"REGIME_{i % 2}",
            probabilities=(0.8, 0.2) if i % 2 == 0 else (0.2, 0.8),
        )
        for i in range(20)
    )
    result = RegimeDetectionResult(
        model_version="1.0.0",
        algorithm="kmeans",
        feature_names=("volatility",),
        records=records,
        computed_at=now,
    )

    snapshot = monitor.evaluate_detection_result(result, k_clusters=2)
    assert snapshot.model_id == "kmeans"
    assert snapshot.validity.status == HealthStatus.HEALTHY
    assert snapshot.validity.total_predictions == 20


def test_evaluate_ensemble_result_integration() -> None:
    """Integrates with RegimeEnsembleResult domain model."""
    monitor = ModelHealthMonitor()

    mock_ensemble = MagicMock(spec=RegimeEnsembleResult)
    mock_ensemble.ensemble_regimes = (0, 0, 0, 1, 1, 0, 0, 1)
    mock_ensemble.confidence_scores = (0.85, 0.90, 0.88, 0.92, 0.80, 0.85, 0.87, 0.89)

    snapshot = monitor.evaluate_ensemble_result(mock_ensemble, k_clusters=2)
    assert snapshot.model_id == "ensemble"
    assert snapshot.status == HealthStatus.HEALTHY
    assert snapshot.confidence.mean_confidence is not None
    assert snapshot.confidence.mean_confidence > 0.80
    assert snapshot.validity.valid_predictions == 8
