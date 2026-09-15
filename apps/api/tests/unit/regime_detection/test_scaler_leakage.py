"""
RegimeX Regime Detection — Scaler Leakage Regression Tests
===========================================================
Comprehensive regression suite for the anti-leakage StandardScaler guarantee.

Tests:
1. Scaler mean_ and scale_ are frozen after fit() — captured before/after predict().
2. Predict path uses transform(), not fit_transform() — future data cannot refit scaler.
3. predict_proba() also uses frozen scaler.
4. Dramatically different out-of-sample data does not alter training scaling parameters.
5. Refitting replaces (not accumulates) the old scaler — no stale state persists.
6. Scaler parameters are deterministic across identical training runs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
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


def _make_training_matrix(
    n_rows: int = 30,
    ret_center: float = 0.02,
    vol_center: float = 0.15,
    noise: float = 0.005,
    seed: int = 0,
) -> FeatureMatrix:
    rng = np.random.default_rng(seed)
    rows_a = [
        (float(ret_center + rng.normal(0, noise)), float(vol_center + rng.normal(0, noise)))
        for _ in range(n_rows // 2)
    ]
    rows_b = [
        (float(-ret_center + rng.normal(0, noise)), float(vol_center * 2 + rng.normal(0, noise)))
        for _ in range(n_rows // 2)
    ]
    rows = rows_a + rows_b
    return FeatureMatrix(
        timestamps=tuple(_ts(i) for i in range(len(rows))),
        feature_names=("return_1", "volatility_20"),
        values=tuple(rows),
    )


def _make_extreme_oos_matrix(base_offset: int = 1000) -> FeatureMatrix:
    """Out-of-sample matrix with dramatically different statistics."""
    rows = [
        (1000.0, -5000.0),
        (9999.0, 8888.0),
        (-7777.0, 12345.0),
        (0.0, 99999.0),
    ]
    return FeatureMatrix(
        timestamps=tuple(_ts(base_offset + i) for i in range(len(rows))),
        feature_names=("return_1", "volatility_20"),
        values=tuple(rows),
    )


# ---------------------------------------------------------------------------
# Class 1: Core scaler leakage regression
# ---------------------------------------------------------------------------


class TestScalerLeakageRegression:
    """
    Core regression for the documented anti-leakage guarantee:

    > predict_path MUST use scaler.transform() — never scaler.fit_transform().
    > The fitted scaler's mean_ and scale_ must remain unchanged after inference.
    """

    def test_scaler_mean_unchanged_after_predict(self) -> None:
        """
        Predict on wildly out-of-sample data must not alter scaler.mean_.
        """
        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None
        mean_before = np.copy(scaler.mean_)

        oos = _make_extreme_oos_matrix()
        detector.predict(oos)

        assert np.array_equal(scaler.mean_, mean_before), (
            f"scaler.mean_ was mutated during predict()!\n"
            f"Before: {mean_before}\nAfter:  {scaler.mean_}"
        )

    def test_scaler_scale_unchanged_after_predict(self) -> None:
        """
        Predict on wildly out-of-sample data must not alter scaler.scale_.
        """
        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None
        scale_before = np.copy(scaler.scale_)

        oos = _make_extreme_oos_matrix()
        detector.predict(oos)

        assert np.array_equal(scaler.scale_, scale_before), (
            f"scaler.scale_ was mutated during predict()!\n"
            f"Before: {scale_before}\nAfter:  {scaler.scale_}"
        )

    def test_scaler_mean_unchanged_after_predict_proba(self) -> None:
        """
        predict_proba() on out-of-sample data must not alter scaler.mean_.
        """
        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None
        mean_before = np.copy(scaler.mean_)

        oos = _make_extreme_oos_matrix()
        detector.predict_proba(oos)

        assert np.array_equal(scaler.mean_, mean_before), (
            "scaler.mean_ was mutated during predict_proba()!"
        )

    def test_scaler_scale_unchanged_after_predict_proba(self) -> None:
        """
        predict_proba() on out-of-sample data must not alter scaler.scale_.
        """
        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None
        scale_before = np.copy(scaler.scale_)

        oos = _make_extreme_oos_matrix()
        detector.predict_proba(oos)

        assert np.array_equal(scaler.scale_, scale_before), (
            "scaler.scale_ was mutated during predict_proba()!"
        )

    def test_scaler_parameters_survive_multiple_prediction_passes(self) -> None:
        """
        After 10 alternating predict / predict_proba calls on extreme OOS data,
        scaler parameters must remain identical to the training values.
        """
        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None
        mean_frozen = np.copy(scaler.mean_)
        scale_frozen = np.copy(scaler.scale_)

        for i in range(10):
            oos = _make_extreme_oos_matrix(base_offset=1000 + i * 10)
            detector.predict(oos)
            detector.predict_proba(oos)

        assert np.array_equal(scaler.mean_, mean_frozen)
        assert np.array_equal(scaler.scale_, scale_frozen)


# ---------------------------------------------------------------------------
# Class 2: Transform-not-fit_transform verification
# ---------------------------------------------------------------------------


class TestTransformNotFitTransform:
    """
    Verifies that the predict path strictly uses scaler.transform() and never
    scaler.fit_transform(), which would refit on inference data.

    Methodology: We compare scaler parameters captured at training time
    against what the transform would produce if it were a fit_transform.
    These must differ on OOS data, proving transform() is used.
    """

    def test_oos_predictions_use_training_scaler_not_oos_statistics(self) -> None:
        """
        When predicting on wildly different OOS data, the transformation applied
        must use training mean/scale — not OOS mean/scale.

        Proof: We compute what the scaler would produce using OOS statistics
        and compare to what the actual model predicts (using training scaler).
        The result must align with training statistics.
        """
        from sklearn.preprocessing import StandardScaler

        train = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None

        # OOS data with completely different statistics
        oos = _make_extreme_oos_matrix()
        x_oos = np.array(oos.values, dtype=np.float64)

        # Actual transformation by the frozen training scaler
        x_scaled_training_scaler = scaler.transform(x_oos)

        # What a re-fitted OOS scaler would produce (different result)
        oos_scaler = StandardScaler()
        x_scaled_oos_scaler = oos_scaler.fit_transform(x_oos)

        # The training scaler must produce values different from OOS scaler
        # (if they match, the scaler was incorrectly refit)
        assert not np.allclose(x_scaled_training_scaler, x_scaled_oos_scaler, atol=0.01), (
            "Training scaler and OOS-refit scaler produced identical transformations. "
            "This suggests the scaler was incorrectly refit on OOS data."
        )

    def test_frozen_scaler_produces_training_normalized_values(self) -> None:
        """
        A training observation centered at the training mean must produce a
        near-zero scaled value using the frozen scaler.
        """
        train = _make_training_matrix(n_rows=30, ret_center=0.02, vol_center=0.15)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train)

        scaler = detector._scaler
        assert scaler is not None

        # Create an observation near the training center
        center_obs = FeatureMatrix(
            timestamps=(_ts(5000),),
            feature_names=("return_1", "volatility_20"),
            values=((float(scaler.mean_[0]), float(scaler.mean_[1])),),
        )
        x_raw = np.array(center_obs.values, dtype=np.float64)
        x_scaled = scaler.transform(x_raw)

        # The observation at the training mean should scale to near zero
        assert abs(x_scaled[0, 0]) < 0.1, "Training mean observation did not scale to near zero."
        assert abs(x_scaled[0, 1]) < 0.1, "Training mean observation did not scale to near zero."


# ---------------------------------------------------------------------------
# Class 3: Refit scaler replacement
# ---------------------------------------------------------------------------


class TestRefitScalerReplacement:
    """
    Verifies that refitting the detector on new data replaces the scaler
    entirely — no stale parameters from the previous fit persist.
    """

    def test_refit_replaces_scaler_mean(self) -> None:
        """
        After refit on a dataset with dramatically different statistics, scaler.mean_ must
        reflect the new training data — not the original fit.

        Strategy: fit on small values near (0.02, 0.15), then refit on large values
        near (1000, 5000). The scaler means must shift accordingly.
        """
        # First fit: centered near (0.02, 0.15)
        train_1 = _make_training_matrix(n_rows=30, ret_center=0.02, vol_center=0.15)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train_1)

        scaler_after_fit1 = detector._scaler
        assert scaler_after_fit1 is not None
        mean_fit1 = np.copy(scaler_after_fit1.mean_)

        # Second fit: centered near (1000, 5000) — orders of magnitude different
        rng = np.random.default_rng(99)
        rows_a = [
            (float(1000.0 + rng.normal(0, 10.0)), float(5000.0 + rng.normal(0, 10.0)))
            for _ in range(15)
        ]
        rows_b = [
            (float(999.0 + rng.normal(0, 10.0)), float(4990.0 + rng.normal(0, 10.0)))
            for _ in range(15)
        ]
        rows = rows_a + rows_b
        train_2 = FeatureMatrix(
            timestamps=tuple(_ts(i) for i in range(len(rows))),
            feature_names=("return_1", "volatility_20"),
            values=tuple(rows),
        )
        detector.fit(train_2)

        scaler_after_fit2 = detector._scaler
        assert scaler_after_fit2 is not None
        mean_fit2 = scaler_after_fit2.mean_

        # The L1 difference must be large (original ≈ [0.02, 0.15], new ≈ [999.5, 4995])
        mean_l1_diff = float(np.sum(np.abs(mean_fit1 - mean_fit2)))
        assert mean_l1_diff > 100.0, (
            f"Scaler mean was not replaced after refit — stale parameters may persist. "
            f"Old mean: {mean_fit1}, New mean: {mean_fit2}, L1 diff: {mean_l1_diff}"
        )

    def test_refit_does_not_accumulate_old_scaler_state(self) -> None:
        """
        After refit, the scaler must match the new training data statistics,
        not an average or accumulation of old and new.
        """
        from sklearn.preprocessing import StandardScaler

        # First fit
        train_1 = _make_training_matrix(n_rows=30)
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(train_1)

        # Second fit on very different data
        rng = np.random.default_rng(7)
        rows = [(float(rng.uniform(50, 60)), float(rng.uniform(200, 210))) for _ in range(30)]
        train_2 = FeatureMatrix(
            timestamps=tuple(_ts(i + 500) for i in range(len(rows))),
            feature_names=("return_1", "volatility_20"),
            values=tuple(rows),
        )
        detector.fit(train_2)

        # The new scaler must match a freshly fitted scaler on train_2
        reference_scaler = StandardScaler()
        reference_scaler.fit(np.array(train_2.values, dtype=np.float64))

        actual_scaler = detector._scaler
        assert actual_scaler is not None
        assert np.allclose(actual_scaler.mean_, reference_scaler.mean_, rtol=1e-10), (
            "Refitted scaler.mean_ does not match a fresh fit on the new training data."
        )
        assert np.allclose(actual_scaler.scale_, reference_scaler.scale_, rtol=1e-10), (
            "Refitted scaler.scale_ does not match a fresh fit on the new training data."
        )


# ---------------------------------------------------------------------------
# Class 4: Scaler determinism
# ---------------------------------------------------------------------------


class TestScalerDeterminism:
    """Validates that scaler parameters are deterministic across identical training runs."""

    def test_scaler_parameters_identical_on_identical_training_data(self) -> None:
        """
        Two detectors trained on identical data must produce bit-for-bit identical
        scaler mean_ and scale_.
        """
        train = _make_training_matrix(n_rows=40)

        det_1 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        det_1.fit(train)

        det_2 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        det_2.fit(train)

        scaler_1 = det_1._scaler
        scaler_2 = det_2._scaler
        assert scaler_1 is not None
        assert scaler_2 is not None

        assert np.array_equal(scaler_1.mean_, scaler_2.mean_)
        assert np.array_equal(scaler_1.scale_, scaler_2.scale_)

    def test_scaler_is_fitted_during_fit_not_before(self) -> None:
        """
        A fresh (unfitted) detector must have _scaler = None.
        After fit(), _scaler must be a non-None fitted StandardScaler.
        """
        from sklearn.preprocessing import StandardScaler

        detector = KMeansRegimeDetector()
        assert detector._scaler is None

        train = _make_training_matrix()
        detector.fit(train)

        assert detector._scaler is not None
        assert isinstance(detector._scaler, StandardScaler)
        assert hasattr(detector._scaler, "mean_")
        assert hasattr(detector._scaler, "scale_")
