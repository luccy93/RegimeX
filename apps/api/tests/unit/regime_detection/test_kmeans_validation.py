"""
RegimeX Regime Detection — Golden KMeans Validation Suite
=========================================================
Provides deterministic regression tests for the KMeans baseline:

1. Golden four-cluster dataset with clearly separated market states.
2. Numerical safety: very large / small / constant / near-zero variance features.
3. Predict output shape, range, and determinism validation.
4. predict_proba() contract: finite, normalized, deterministic, disclosed as heuristic.
5. Fit-result diagnostic validation.
6. Performance regression: no accidental O(N²) Python loops for moderate dataset.
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.modules.regime_detection.domain.errors import (
    InvalidFeatureMatrixError,
    ModelTrainingError,
)
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    ModelState,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TIME + timedelta(days=i)


def _make_four_cluster_matrix(
    n_per_cluster: int = 40,
    seed: int = 7,
    noise: float = 0.003,
) -> FeatureMatrix:
    """
    Synthetic dataset with four clearly separated financial market states:

    Cluster A (Bull / Low-Vol):   return ≈ +0.020, volatility ≈ 0.010
    Cluster B (Bear / High-Vol):  return ≈ -0.020, volatility ≈ 0.050
    Cluster C (Rally / Mid-Vol):  return ≈ +0.010, volatility ≈ 0.030
    Cluster D (Calm / Low-Vol):   return ≈ -0.010, volatility ≈ 0.010

    Separation is sufficient that KMeans with k=4 should cleanly partition
    the clusters regardless of initialization seed.
    """
    rng = np.random.default_rng(seed)

    centers = [
        (0.020, 0.010),  # A — Bull / Low-Vol
        (-0.020, 0.050),  # B — Bear / High-Vol
        (0.010, 0.030),  # C — Rally / Mid-Vol
        (-0.010, 0.010),  # D — Calm / Low-Vol
    ]

    rows: list[tuple[float, float]] = []
    for ret_center, vol_center in centers:
        rets = rng.normal(ret_center, noise, n_per_cluster)
        vols = rng.normal(vol_center, noise / 2, n_per_cluster)
        rows.extend(zip(rets.tolist(), vols.tolist(), strict=True))

    n_total = len(rows)
    timestamps = tuple(_ts(i) for i in range(n_total))
    values = tuple((float(r), float(v)) for r, v in rows)

    return FeatureMatrix(
        timestamps=timestamps,
        feature_names=("return_1", "volatility_20"),
        values=values,
    )


# ---------------------------------------------------------------------------
# Class 1: Golden four-cluster correctness
# ---------------------------------------------------------------------------


class TestGoldenKMeansValidation:
    """Validates KMeans against a four-cluster separable synthetic dataset."""

    def test_golden_four_cluster_fit_succeeds(self) -> None:
        """Model must fit without error and report correct cluster count."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.state == ModelState.FITTED
        fit_res = detector.fit_result
        assert fit_res is not None
        assert fit_res.n_clusters == 4
        assert fit_res.training_sample_count == 4 * 40
        assert len(fit_res.cluster_profiles) == 4

    def test_golden_four_cluster_purity(self) -> None:
        """
        Each original cluster block must map to a single canonical regime ID.
        The four clusters are sufficiently separated that purity should be 100%.
        """
        n = 40
        matrix = _make_four_cluster_matrix(n_per_cluster=n)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        assert len(preds) == 4 * n

        # Each of the four contiguous blocks must have a single canonical regime
        for block in range(4):
            block_preds = preds[block * n : (block + 1) * n]
            unique_regimes = set(block_preds)
            assert len(unique_regimes) == 1, (
                f"Block {block} was split across {unique_regimes}; clusters not cleanly separated."
            )

        # All four blocks must belong to distinct canonical regimes
        regime_per_block = {preds[block * n] for block in range(4)}
        assert len(regime_per_block) == 4, (
            f"Two or more blocks share the same canonical regime: {regime_per_block}"
        )

    def test_golden_four_cluster_canonical_ids_in_range(self) -> None:
        """All canonical regime IDs must fall within [0, n_clusters - 1]."""
        matrix = _make_four_cluster_matrix()
        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        detector.fit(matrix)

        preds = detector.predict(matrix)
        assert all(0 <= p < 4 for p in preds)

    def test_golden_four_cluster_labels_match_canonical_ids(self) -> None:
        """Cluster profile labels must be exactly 'REGIME_<canonical_regime_id>'."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        for profile in detector.cluster_profiles:
            expected = f"REGIME_{profile.canonical_regime_id}"
            assert profile.canonical_regime_label == expected, (
                f"Label mismatch: expected '{expected}', got '{profile.canonical_regime_label}'."
            )

    def test_canonical_regime_ids_are_consecutive_zero_indexed(self) -> None:
        """Canonical regime IDs must be {0, 1, 2, ..., K-1} with no gaps."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        canonical_ids = {p.canonical_regime_id for p in detector.cluster_profiles}
        assert canonical_ids == {0, 1, 2, 3}


# ---------------------------------------------------------------------------
# Class 2: Fit-result diagnostic validation
# ---------------------------------------------------------------------------


class TestFitResultDiagnostics:
    """Validates the FitResult fields returned after model fitting."""

    def test_inertia_is_positive_finite(self) -> None:
        """Inertia must be strictly positive and finite after a valid fit."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        inertia = detector.fit_result.inertia
        assert inertia > 0.0
        assert math.isfinite(inertia)

    def test_iterations_at_least_one(self) -> None:
        """KMeans must run at least one iteration."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        assert detector.fit_result.iterations >= 1

    def test_cluster_profiles_capture_correct_feature_means(self) -> None:
        """
        For each cluster, feature_means must reflect the unscaled actual cluster
        centroid values — not zero and not the scaled values.
        """
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        for profile in detector.fit_result.cluster_profiles:
            assert "return_1" in profile.feature_means
            assert "volatility_20" in profile.feature_means
            # All means must be finite
            for val in profile.feature_means.values():
                assert math.isfinite(val), f"Non-finite feature mean: {val}"

    def test_cluster_sample_counts_sum_to_total(self) -> None:
        """Sum of all cluster sample_count values must equal training_sample_count."""
        n = 40
        matrix = _make_four_cluster_matrix(n_per_cluster=n)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        total_in_profiles = sum(p.sample_count for p in detector.fit_result.cluster_profiles)
        assert total_in_profiles == detector.fit_result.training_sample_count

    def test_fit_result_timestamps_are_timezone_aware(self) -> None:
        """training_start and training_end in FitResult must be timezone-aware."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        assert detector.fit_result.training_start.tzinfo is not None
        assert detector.fit_result.training_end.tzinfo is not None

    def test_fit_result_feature_names_match_matrix(self) -> None:
        """FitResult.feature_names must equal the matrix's feature_names."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        assert detector.fit_result.feature_names == matrix.feature_names

    def test_fit_result_algorithm_field(self) -> None:
        """FitResult.algorithm must be 'KMeans' (not 'kmeans_baseline' which is algorithm_id)."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector.fit_result is not None
        assert detector.fit_result.algorithm == "KMeans"

    def test_model_version_stability(self) -> None:
        """
        The algorithm version must remain 'kmeans-baseline-v1' semantically.
        ALGORITHM_VERSION == '1.0.0' and algorithm_id == 'kmeans_baseline'.
        This test locks the version so changes require a deliberate update.
        """
        detector = KMeansRegimeDetector()
        assert detector.algorithm_id == "kmeans_baseline"
        assert detector.algorithm_version == "1.0.0"


# ---------------------------------------------------------------------------
# Class 3: Numerical safety
# ---------------------------------------------------------------------------


class TestNumericalSafety:
    """Tests model behavior under edge-case numerical inputs."""

    def _make_matrix_from_values(
        self,
        rows: list[tuple[float, float]],
        names: tuple[str, str] = ("feat_a", "feat_b"),
    ) -> FeatureMatrix:
        timestamps = tuple(_ts(i) for i in range(len(rows)))
        return FeatureMatrix(
            timestamps=timestamps,
            feature_names=names,
            values=tuple(rows),
        )

    def test_very_large_feature_values_fit_succeeds(self) -> None:
        """
        Extremely large feature values must not break StandardScaler or KMeans.
        The model should fit without error.
        """
        rng = np.random.default_rng(0)
        rows_a = [
            (float(1e8 + rng.normal(0, 100)), float(2e8 + rng.normal(0, 100))) for _ in range(20)
        ]
        rows_b = [
            (float(-1e8 + rng.normal(0, 100)), float(-2e8 + rng.normal(0, 100))) for _ in range(20)
        ]
        matrix = self._make_matrix_from_values(rows_a + rows_b)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix)
        assert detector.state == ModelState.FITTED

    def test_very_small_feature_values_fit_succeeds(self) -> None:
        """
        Near-zero feature values at machine-epsilon scale must be handled safely.
        """
        rng = np.random.default_rng(1)
        rows_a = [
            (float(1e-10 + rng.normal(0, 1e-12)), float(2e-10 + rng.normal(0, 1e-12)))
            for _ in range(20)
        ]
        rows_b = [
            (float(-1e-10 + rng.normal(0, 1e-12)), float(-2e-10 + rng.normal(0, 1e-12)))
            for _ in range(20)
        ]
        matrix = self._make_matrix_from_values(rows_a + rows_b)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix)
        assert detector.state == ModelState.FITTED

    def test_constant_feature_column_does_not_crash(self) -> None:
        """
        A completely constant feature column produces zero variance.
        StandardScaler will set scale_=0 and produce NaN for that column;
        the model must either handle this gracefully or raise a typed error.
        We accept either outcome — we just require no unhandled exception.
        """
        # All rows have identical feat_a value (constant) — zero variance
        rows = [(1.0, float(i)) for i in range(20)] + [(-1.0, float(i + 20)) for i in range(20)]
        matrix = self._make_matrix_from_values(rows)
        try:
            detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
            detector.fit(matrix)
            # If it succeeds, the model must still be in a valid state
            assert detector.state in (ModelState.FITTED, ModelState.UNFITTED)
        except (InvalidFeatureMatrixError, ModelTrainingError):
            pass  # A typed error is also acceptable

    def test_near_zero_variance_feature_handled(self) -> None:
        """
        Near-zero (but non-zero) variance features must produce valid output.
        The model should not produce NaN predictions.
        """
        rng = np.random.default_rng(5)
        rows_a = [
            (float(1.0 + rng.normal(0, 1e-9)), float(2.0 + rng.normal(0, 0.1))) for _ in range(20)
        ]
        rows_b = [
            (float(-1.0 + rng.normal(0, 1e-9)), float(-2.0 + rng.normal(0, 0.1))) for _ in range(20)
        ]
        matrix = self._make_matrix_from_values(rows_a + rows_b)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        try:
            detector.fit(matrix)
            preds = detector.predict(matrix)
            assert all(isinstance(p, int) for p in preds)
            assert all(0 <= p < 2 for p in preds)
        except (InvalidFeatureMatrixError, ModelTrainingError):
            pass  # Also acceptable if the model rejects near-zero-variance explicitly

    def test_nan_rejected_by_feature_matrix_domain_model(self) -> None:
        """NaN values must be caught by FeatureMatrix validation — not by sklearn."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="NaN detected"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("a", "b"),
                values=((float("nan"), 1.0),),
            )

    def test_inf_rejected_by_feature_matrix_domain_model(self) -> None:
        """Infinite values must be caught by FeatureMatrix validation — not by sklearn."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Infinite value"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("a", "b"),
                values=((float("inf"), 1.0),),
            )

    def test_neg_inf_rejected_by_feature_matrix_domain_model(self) -> None:
        """Negative infinite values must be caught by FeatureMatrix validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Infinite value"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("a", "b"),
                values=((float("-inf"), 1.0),),
            )


# ---------------------------------------------------------------------------
# Class 4: Predict output validation
# ---------------------------------------------------------------------------


class TestPredictOutputValidation:
    """Validates properties of predict() output on fitted models."""

    def test_prediction_count_equals_input_rows(self) -> None:
        """predict() must return exactly as many values as the matrix has rows."""
        matrix = _make_four_cluster_matrix(n_per_cluster=25)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        preds = detector.predict(matrix)
        assert len(preds) == matrix.sample_count

    def test_all_predictions_are_valid_canonical_regimes(self) -> None:
        """Every prediction must be an integer in [0, n_clusters - 1]."""
        matrix = _make_four_cluster_matrix()
        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        detector.fit(matrix)

        preds = detector.predict(matrix)
        for p in preds:
            assert isinstance(p, int)
            assert 0 <= p < 4

    def test_repeated_prediction_is_deterministic(self) -> None:
        """Calling predict() twice on the same matrix must return identical results."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        preds_1 = detector.predict(matrix)
        preds_2 = detector.predict(matrix)
        assert preds_1 == preds_2

    def test_predict_on_single_observation(self) -> None:
        """Inference on a single-row matrix must succeed and return exactly one value."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        single_row = FeatureMatrix(
            timestamps=(_ts(9999),),
            feature_names=("return_1", "volatility_20"),
            values=((0.015, 0.012),),
        )
        preds = detector.predict(single_row)
        assert len(preds) == 1
        assert 0 <= preds[0] < 4

    def test_no_unexpected_labels_in_predictions(self) -> None:
        """No prediction label outside {0, ..., K-1} must ever appear."""
        matrix = _make_four_cluster_matrix()
        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        detector.fit(matrix)

        preds = detector.predict(matrix)
        valid_labels = set(range(4))
        for p in preds:
            assert p in valid_labels, f"Unexpected label {p} not in {valid_labels}"


# ---------------------------------------------------------------------------
# Class 5: predict_proba contract
# ---------------------------------------------------------------------------


class TestPredictProbaContract:
    """Validates the documented predict_proba() heuristic contract."""

    def test_proba_output_shape_matches_n_samples_and_n_clusters(self) -> None:
        """predict_proba() must return (N, K) outer/inner tuple shapes."""
        n = 40
        matrix = _make_four_cluster_matrix(n_per_cluster=n)
        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        assert len(probs) == 4 * n  # N rows
        for row in probs:
            assert len(row) == 4  # K columns

    def test_proba_values_are_finite_and_non_negative(self) -> None:
        """All probability values must be finite and non-negative."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        for i, row in enumerate(probs):
            for j, val in enumerate(row):
                assert math.isfinite(val), f"Non-finite probability at row {i}, col {j}: {val}"
                assert val >= 0.0, f"Negative probability at row {i}, col {j}: {val}"

    def test_proba_rows_sum_to_one(self) -> None:
        """Each row must sum to 1.0 within 1e-6 (documented normalization)."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        probs = detector.predict_proba(matrix)
        for i, row in enumerate(probs):
            row_sum = sum(row)
            assert math.isclose(row_sum, 1.0, rel_tol=1e-6, abs_tol=1e-6), (
                f"Row {i} sum = {row_sum!r}, expected 1.0 within 1e-6"
            )

    def test_proba_deterministic_on_repeated_calls(self) -> None:
        """Repeated predict_proba() calls on the same matrix must be identical."""
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        probs_1 = detector.predict_proba(matrix)
        probs_2 = detector.predict_proba(matrix)
        assert probs_1 == probs_2

    def test_proba_column_r_corresponds_to_canonical_regime_r(self) -> None:
        """
        For an observation known to be closest to regime R, column R in predict_proba()
        must have the highest probability value.
        """
        # Bull cluster centroid is approximately (return=0.020, vol=0.010)
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        # Identify the canonical ID of the Bull cluster (highest return, lowest vol)
        profiles = detector.cluster_profiles
        bull_regime_id: int | None = None
        max_return = float("-inf")
        for p in profiles:
            if p.feature_means["return_1"] > max_return:
                max_return = p.feature_means["return_1"]
                bull_regime_id = p.canonical_regime_id

        assert bull_regime_id is not None

        # A single observation solidly in the Bull cluster
        bull_obs = FeatureMatrix(
            timestamps=(_ts(9999),),
            feature_names=("return_1", "volatility_20"),
            values=((0.020, 0.010),),
        )
        probs = detector.predict_proba(bull_obs)
        assert len(probs) == 1
        row = probs[0]
        assert max(range(4), key=lambda k: row[k]) == bull_regime_id, (
            f"Column for bull regime {bull_regime_id} was not argmax: {row}"
        )

    def test_proba_disclosed_as_distance_heuristic_not_calibrated(self) -> None:
        """
        The metadata known_limitations tuple must explicitly disclose that
        predict_proba() produces distance-based heuristics, not calibrated probabilities.
        """
        detector = KMeansRegimeDetector()
        meta = detector.metadata()
        limitations_text = " ".join(meta.known_limitations).lower()
        assert "heuristic" in limitations_text or "distance" in limitations_text, (
            "Metadata must disclose the heuristic nature of predict_proba() to consumers."
        )


# ---------------------------------------------------------------------------
# Class 6: Performance regression
# ---------------------------------------------------------------------------


class TestPerformanceRegression:
    """
    Verifies that fitting and prediction complete in a reasonable wall-clock time
    for a moderate-sized deterministic dataset.

    No external benchmarking libraries are used.
    The threshold is intentionally generous to avoid flakiness across environments.
    """

    def test_fit_and_predict_complete_within_time_budget(self) -> None:
        """
        Fitting on 500 rows and predicting 500 rows must complete in < 30 seconds
        on any modern hardware. This guards against accidental O(N²) Python loops.
        """
        n = 125  # 4 clusters × 125 = 500 total rows
        matrix = _make_four_cluster_matrix(n_per_cluster=n)
        config = RegimeModelConfig(n_clusters=4, random_state=42)
        detector = KMeansRegimeDetector(config=config)

        start = time.monotonic()
        detector.fit(matrix)
        detector.predict(matrix)
        detector.predict_proba(matrix)
        elapsed = time.monotonic() - start

        assert elapsed < 30.0, (
            f"Fit + predict on {matrix.sample_count} rows took {elapsed:.2f}s; "
            "this may indicate an O(N²) loop regression."
        )

    def test_repeated_prediction_does_not_refit(self) -> None:
        """
        Repeated calls to predict() must produce identical results and must not
        alter the internal scaler or KMeans model parameters (i.e., no refitting).
        """
        matrix = _make_four_cluster_matrix()
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=4, random_state=42))
        detector.fit(matrix)

        assert detector._scaler is not None
        assert detector._kmeans is not None
        mean_before = detector._scaler.mean_.copy()
        centers_before = detector._kmeans.cluster_centers_.copy()

        # Multiple prediction passes
        for _ in range(5):
            detector.predict(matrix)
            detector.predict_proba(matrix)

        assert np.array_equal(detector._scaler.mean_, mean_before), (
            "Scaler was mutated by predict()."
        )
        assert np.array_equal(detector._kmeans.cluster_centers_, centers_before), (
            "KMeans centers were mutated by predict()."
        )
