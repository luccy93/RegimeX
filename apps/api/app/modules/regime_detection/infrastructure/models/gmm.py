"""
RegimeX Regime Detection — Gaussian Mixture Model (GMM) Detector
===============================================================
Production-grade probabilistic regime detector implementing the ``RegimeDetector``
domain abstraction via ``sklearn.mixture.GaussianMixture``.

Architectural Position:
- ``infrastructure/models/gmm.py`` — Concrete adapter implementing ``RegimeDetector``.
- Encapsulates ``StandardScaler`` and ``sklearn.mixture.GaussianMixture`` inside pipeline.
- Translates scikit-learn numerical outputs into strictly typed RegimeX domain models.

Guarantees:
- Probabilistic rigour: genuine posterior probabilities normalized to 1.0 within 1e-6.
- Anti-leakage preprocessing: StandardScaler is fitted strictly on in-sample training data.
  Inference transforms observations using frozen parameters without refitting.
- Deterministic component canonicalization: raw algorithmic components (0..K-1) are mapped
  to stable, sorted canonical regime IDs based on invariant feature signatures.
- Consistent hard assignment: predict(X)[i] == argmax(predict_proba(X)[i]) guaranteed.
- Complete domain isolation: domain contracts have zero dependency on vendor libraries.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from app.modules.regime_detection.domain.errors import (
    GMMFitError,
    GMMPredictionError,
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    ClusterProfile,
    DetectorMetadata,
    FeatureMatrix,
    FitResult,
    GMMModelConfig,
    ModelState,
)

logger = logging.getLogger(__name__)


class GaussianMixtureRegimeDetector(RegimeDetector):
    """
    Probabilistic Gaussian Mixture Model regime detector with anti-leakage scaling,
    deterministic component canonicalization, and genuine posterior probability estimation.
    """

    ALGORITHM_ID: str = "gaussian_mixture"
    ALGORITHM_VERSION: str = "1.0.0"

    def __init__(self, config: GMMModelConfig | None = None) -> None:
        """
        Initialize the Gaussian Mixture Model regime detector.

        Args:
            config: GMM hyperparameter configuration specifying components, covariance type,
                regularization, tolerance, and random seed. Defaults to GMMModelConfig().
        """
        self._config = config or GMMModelConfig()
        self._state = ModelState.UNFITTED

        # Model pipeline components (encapsulated in infrastructure)
        self._scaler: StandardScaler | None = None
        self._gmm: GaussianMixture | None = None

        # Trained state and canonicalization mapping
        self._feature_names: tuple[str, ...] = ()
        self._cluster_mapping: dict[int, int] = {}  # raw component_id -> canonical_regime_id
        self._canonical_to_raw: dict[int, int] = {}  # canonical_regime_id -> raw component_id
        self._cluster_profiles: tuple[ClusterProfile, ...] = ()
        self._fit_result: FitResult | None = None

    @property
    def algorithm_id(self) -> str:
        return self.ALGORITHM_ID

    @property
    def algorithm_version(self) -> str:
        return self.ALGORITHM_VERSION

    @property
    def state(self) -> ModelState:
        return self._state

    @property
    def config(self) -> GMMModelConfig:
        return self._config

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    @property
    def cluster_profiles(self) -> tuple[ClusterProfile, ...]:
        return self._cluster_profiles

    def fit(self, feature_matrix: FeatureMatrix) -> GaussianMixtureRegimeDetector:
        """
        Fit the standard scaler and Gaussian Mixture Model strictly on in-sample training data.

        Args:
            feature_matrix: Validated, point-in-time feature observations.

        Returns:
            self: Fitted detector instance.

        Raises:
            InsufficientTrainingDataError: If sample count < n_components or < 1.
            InvalidFeatureMatrixError: If feature columns do not match configured feature subset.
            GMMFitError: If algorithmic or numerical convergence failure occurs during fitting.
        """
        n_samples = feature_matrix.sample_count
        n_components = self._config.n_components

        if n_samples < n_components:
            raise InsufficientTrainingDataError(
                required_samples=n_components,
                available_samples=n_samples,
                requested_clusters=n_components,
            )

        if n_samples < 1:
            raise InsufficientTrainingDataError(
                required_samples=1,
                available_samples=n_samples,
                requested_clusters=n_components,
            )

        # Validate feature column consistency
        if self._config.feature_names:
            if feature_matrix.feature_names != self._config.feature_names:
                raise InvalidFeatureMatrixError(
                    f"Feature matrix columns ({feature_matrix.feature_names}) do not match "
                    f"configured features ({self._config.feature_names})."
                )
            self._feature_names = self._config.feature_names
        else:
            self._feature_names = feature_matrix.feature_names

        # Convert to float64 numpy array
        x_raw = np.array(feature_matrix.values, dtype=np.float64)

        try:
            # 1. Anti-leakage standard scaling (fit ONLY on in-sample training data)
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_raw)

            # 2. Gaussian Mixture Model estimation via EM
            gmm = GaussianMixture(
                n_components=n_components,
                covariance_type=self._config.covariance_type,
                tol=self._config.tol,
                reg_covar=self._config.reg_covar,
                max_iter=self._config.max_iter,
                init_params=self._config.init_params,
                random_state=self._config.random_state,
            )
            gmm.fit(x_scaled)

            if not gmm.converged_:
                logger.warning(
                    "GMM did not converge within max_iter=%d (lower_bound=%.6f)",
                    self._config.max_iter,
                    gmm.lower_bound_,
                )

            # 3. Unscale component centers and calculate empirical feature statistics
            unscaled_centers = scaler.inverse_transform(gmm.means_)
            raw_probs = gmm.predict_proba(x_scaled)
            raw_labels = np.argmax(raw_probs, axis=1)

            raw_profiles: list[dict[str, Any]] = []

            for comp_idx in range(n_components):
                mask = raw_labels == comp_idx
                count = int(np.sum(mask))

                if count > 0:
                    comp_data = x_raw[mask]
                    means = np.mean(comp_data, axis=0)
                    stds = np.std(comp_data, axis=0, ddof=1) if count > 1 else np.zeros_like(means)
                else:
                    means = unscaled_centers[comp_idx]
                    stds = np.zeros_like(means)

                feature_means = {
                    feat: float(means[col_idx]) for col_idx, feat in enumerate(self._feature_names)
                }
                feature_stds = {
                    feat: float(stds[col_idx]) for col_idx, feat in enumerate(self._feature_names)
                }

                # Deterministic signature: tuple of feature means sorted by feature name
                signature = tuple(feature_means[f] for f in sorted(self._feature_names))

                raw_profiles.append(
                    {
                        "cluster_id": comp_idx,
                        "center": tuple(float(v) for v in unscaled_centers[comp_idx]),
                        "sample_count": count,
                        "feature_means": feature_means,
                        "feature_stds": feature_stds,
                        "signature": signature,
                    }
                )

            # 4. Deterministic Component Canonicalization
            # Sort components by invariant feature signature (secondary tie-breaker: cluster_id)
            sorted_by_signature = sorted(
                raw_profiles,
                key=lambda p: (p["signature"], p["cluster_id"]),
            )

            cluster_mapping: dict[int, int] = {}
            canonical_to_raw: dict[int, int] = {}
            final_profiles: list[ClusterProfile] = []

            for canonical_id, prof in enumerate(sorted_by_signature):
                raw_id = prof["cluster_id"]
                cluster_mapping[raw_id] = canonical_id
                canonical_to_raw[canonical_id] = raw_id

                final_profiles.append(
                    ClusterProfile(
                        cluster_id=raw_id,
                        canonical_regime_id=canonical_id,
                        canonical_regime_label=f"REGIME_{canonical_id}",
                        center=prof["center"],
                        sample_count=prof["sample_count"],
                        feature_means=prof["feature_means"],
                        feature_stds=prof["feature_stds"],
                    )
                )

            # 5. Persist fitted pipeline and diagnostics
            self._scaler = scaler
            self._gmm = gmm
            self._cluster_mapping = cluster_mapping
            self._canonical_to_raw = canonical_to_raw
            self._cluster_profiles = tuple(final_profiles)

            self._fit_result = FitResult(
                model_name=self._config.model_name,
                model_version=self._config.model_version,
                algorithm="GaussianMixture",
                n_clusters=n_components,
                random_state=self._config.random_state,
                feature_names=self._feature_names,
                training_sample_count=n_samples,
                training_start=feature_matrix.timestamps[0],
                training_end=feature_matrix.timestamps[-1],
                inertia=0.0,
                iterations=int(gmm.n_iter_),
                cluster_profiles=self._cluster_profiles,
                lower_bound=float(gmm.lower_bound_),
                converged=bool(gmm.converged_),
            )
            self._state = ModelState.FITTED

        except (InsufficientTrainingDataError, InvalidFeatureMatrixError):
            raise
        except Exception as exc:
            raise GMMFitError(f"Gaussian Mixture Model fitting failed: {exc}") from exc

        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        """
        Predict discrete canonical regime IDs (0..K-1) for each observation row.

        Hard regime assignment is strictly determined by argmax of canonical posterior
        probabilities, ensuring 100% mathematical consistency with predict_proba().

        Args:
            feature_matrix: Observations to classify.

        Returns:
            Tuple of canonical regime integer identifiers.

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
            GMMPredictionError: If numerical error occurs during prediction.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._gmm is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        probs = self.predict_proba(feature_matrix)
        # argmax across canonical probability columns
        return tuple(int(np.argmax(row)) for row in probs)

    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...]:
        """
        Compute continuous Bayesian posterior probability vectors across all canonical regimes.

        Methodology:
        - GMM provides genuine posterior probabilities P(z=k | x).
        - Probability columns are deterministically remapped to canonical regime order
          such that column c corresponds strictly to REGIME_c.
        - Guarantees each row sums to 1.0 within 1e-6 and every probability satisfies 0 <= p <= 1.

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
            GMMPredictionError: If numerical failure occurs during inference.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._gmm is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        x_raw = np.array(feature_matrix.values, dtype=np.float64)

        try:
            # Strictly transform using the frozen, in-sample fitted scaler (zero leakage)
            x_scaled = self._scaler.transform(x_raw)
            raw_probs = self._gmm.predict_proba(x_scaled)

            n_samples = feature_matrix.sample_count
            n_components = self._config.n_components
            canonical_probs = np.zeros((n_samples, n_components), dtype=np.float64)

            # Permute probabilities so column c corresponds to canonical regime c
            for canonical_id in range(n_components):
                raw_id = self._canonical_to_raw[canonical_id]
                canonical_probs[:, canonical_id] = raw_probs[:, raw_id]

            # Numerical stability: enforce non-negative and row normalization to 1.0
            canonical_probs = np.clip(canonical_probs, 0.0, 1.0)
            row_sums = np.sum(canonical_probs, axis=1, keepdims=True)
            row_sums = np.where(row_sums == 0, 1.0, row_sums)
            canonical_probs = canonical_probs / row_sums

            return tuple(tuple(float(val) for val in row) for row in canonical_probs)

        except Exception as exc:
            raise GMMPredictionError(f"GMM posterior probability estimation failed: {exc}") from exc

    def get_params(self) -> dict[str, Any]:
        """Return hyperparameter dictionary for exact historical reproducibility."""
        feature_names = (
            list(self._feature_names) if self._feature_names else list(self._config.feature_names)
        )
        return {
            "model_name": self._config.model_name,
            "model_version": self._config.model_version,
            "n_components": self._config.n_components,
            "covariance_type": self._config.covariance_type,
            "random_state": self._config.random_state,
            "max_iter": self._config.max_iter,
            "tol": self._config.tol,
            "reg_covar": self._config.reg_covar,
            "init_params": self._config.init_params,
            "feature_names": feature_names,
        }

    def metadata(self) -> DetectorMetadata:
        """Return self-describing model metadata, mathematical assumptions, and limitations."""
        return DetectorMetadata(
            algorithm_id=self.ALGORITHM_ID,
            algorithm_version=self.ALGORITHM_VERSION,
            algorithm_family="Probabilistic / Mixture Models",
            description=(
                "Probabilistic market regime detector utilizing Gaussian Mixture Models (GMM) "
                "fitted with the Expectation-Maximization (EM) algorithm, equipped with "
                "anti-leakage standardized preprocessing and deterministic component "
                "canonicalization."
            ),
            assumptions=(
                (
                    "Market feature vectors within each regime are conditionally generated "
                    "from a multivariate Gaussian distribution."
                ),
                (
                    f"Covariance matrix geometry conforms to '{self._config.covariance_type}' "
                    "structure."
                ),
                (
                    "Observations are independently and identically distributed conditional "
                    "on latent regime assignment."
                ),
                "Prior regime probabilities are stationary over the fitting window.",
            ),
            known_limitations=(
                (
                    "Does not model Markovian temporal state transitions or temporal persistence "
                    "(HMM required for state dynamics)."
                ),
                (
                    "EM algorithm converges to local maxima; solution is sensitive to "
                    "initialization and random seed."
                ),
                (
                    "High-dimensional feature spaces with 'full' covariance may experience "
                    "singularity without adequate reg_covar."
                ),
                "Stationary mixture assumption may fail during non-stationary structural shifts.",
                (
                    "Posterior probabilities reflect in-sample component likelihoods, "
                    "not certainty about future returns."
                ),
            ),
            hyperparameters=self.get_params(),
        )

    def _validate_inference_features(self, feature_matrix: FeatureMatrix) -> None:
        """Ensure inference matrix columns align with training features."""
        if feature_matrix.feature_names != self._feature_names:
            raise InvalidFeatureMatrixError(
                f"Feature mismatch: model was fitted on {self._feature_names}, "
                f"but received {feature_matrix.feature_names}."
            )
