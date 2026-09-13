"""
RegimeX Regime Detection — Baseline KMeans Detector
===================================================
Production-grade deterministic KMeans baseline implementation for unsupervised
market regime discovery.

Architectural Position:
- ``infrastructure/models/kmeans.py`` — Concrete adapter implementing ``RegimeDetector``.
- Encapsulates ``StandardScaler`` and ``sklearn.cluster.KMeans`` inside an integrated pipeline.
- Translates scikit-learn numerical outputs into strictly typed RegimeX domain models.

Guarantees:
- Deterministic reproducibility: obeys configured random_state and initialization strategy.
- Leakage-safe scaling: StandardScaler is fitted strictly on in-sample training data.
  Inference transforms observations using frozen parameters without refitting.
- Deterministic cluster canonicalization: raw algorithmic cluster IDs (0..K-1) are mapped
  to stable, sorted canonical regime IDs based on centroid feature signatures.
- Non-probabilistic uncertainty disclosure: predict_proba() provides an explicit,
  documented distance-based heuristic distribution (softmax of negative distances to centroids)
  with columns aligned to canonical regime indices.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.modules.regime_detection.domain.errors import (
    InsufficientTrainingDataError,
    InvalidFeatureMatrixError,
    ModelNotFittedError,
    ModelTrainingError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    ClusterProfile,
    DetectorMetadata,
    FeatureMatrix,
    FitResult,
    ModelState,
    RegimeModelConfig,
)


class KMeansRegimeDetector(RegimeDetector):
    """
    Deterministic KMeans baseline regime detector with anti-leakage scaling
    and deterministic cluster canonicalization.
    """

    ALGORITHM_ID: str = "kmeans_baseline"
    ALGORITHM_VERSION: str = "1.0.0"

    def __init__(self, config: RegimeModelConfig | None = None) -> None:
        """
        Initialize the KMeans regime detector.

        Args:
            config: Model configuration specifying hyperparameters, random seed,
                and feature specifications. Defaults to RegimeModelConfig().
        """
        self._config = config or RegimeModelConfig()
        self._state = ModelState.UNFITTED

        # Model pipeline components (encapsulated in infrastructure)
        self._scaler: StandardScaler | None = None
        self._kmeans: KMeans | None = None

        # Trained state and canonicalization mapping
        self._feature_names: tuple[str, ...] = ()
        self._cluster_mapping: dict[int, int] = {}  # raw cluster_id -> canonical_regime_id
        self._canonical_to_raw: dict[int, int] = {}  # canonical_regime_id -> raw cluster_id
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
    def config(self) -> RegimeModelConfig:
        return self._config

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    @property
    def cluster_profiles(self) -> tuple[ClusterProfile, ...]:
        return self._cluster_profiles

    def fit(self, feature_matrix: FeatureMatrix) -> KMeansRegimeDetector:
        """
        Fit the standard scaler and KMeans model strictly on the input training matrix.

        Args:
            feature_matrix: Validated, point-in-time feature observations.

        Returns:
            self: Fitted detector instance.

        Raises:
            InsufficientTrainingDataError: If observation count < n_clusters.
            InvalidFeatureMatrixError: If feature matrix is empty or does not contain
                the configured feature subset.
        """
        n_samples = feature_matrix.sample_count
        n_clusters = self._config.n_clusters

        if n_samples < n_clusters:
            raise InsufficientTrainingDataError(
                required_samples=n_clusters,
                available_samples=n_samples,
                requested_clusters=n_clusters,
            )

        if n_samples < 2:
            raise InsufficientTrainingDataError(
                required_samples=2,
                available_samples=n_samples,
                requested_clusters=n_clusters,
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

        # Convert to numpy float64 matrix
        x_raw = np.array(feature_matrix.values, dtype=np.float64)

        try:
            # 1. Anti-leakage standard scaling (fit ONLY on in-sample training data)
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x_raw)

            # 2. Deterministic KMeans clustering
            kmeans = KMeans(
                n_clusters=n_clusters,
                init=self._config.init,
                max_iter=self._config.max_iter,
                tol=self._config.tol,
                random_state=self._config.random_state,
                n_init=10,
            )
            raw_labels = kmeans.fit_predict(x_scaled)

            # 3. Compute unscaled cluster profiles and signatures for canonicalization
            raw_profiles: list[dict[str, Any]] = []
            unscaled_centers = scaler.inverse_transform(kmeans.cluster_centers_)

            for cluster_idx in range(n_clusters):
                mask = raw_labels == cluster_idx
                count = int(np.sum(mask))

                if count > 0:
                    cluster_data = x_raw[mask]
                    means = np.mean(cluster_data, axis=0)
                    stds = (
                        np.std(cluster_data, axis=0, ddof=1) if count > 1 else np.zeros_like(means)
                    )
                else:
                    means = unscaled_centers[cluster_idx]
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
                        "cluster_id": cluster_idx,
                        "center": tuple(float(v) for v in unscaled_centers[cluster_idx]),
                        "sample_count": count,
                        "feature_means": feature_means,
                        "feature_stds": feature_stds,
                        "signature": signature,
                    }
                )

            # 4. Deterministic Cluster Canonicalization
            # Sort clusters by their invariant feature signature.
            # This decouples arbitrary raw KMeans cluster IDs from canonical regime IDs.
            sorted_by_signature = sorted(
                raw_profiles,
                key=lambda p: p["signature"],
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

            # 5. Persist fitted state
            self._scaler = scaler
            self._kmeans = kmeans
            self._cluster_mapping = cluster_mapping
            self._canonical_to_raw = canonical_to_raw
            self._cluster_profiles = tuple(final_profiles)

            self._fit_result = FitResult(
                model_name=self._config.model_name,
                model_version=self._config.model_version,
                algorithm="KMeans",
                n_clusters=n_clusters,
                random_state=self._config.random_state,
                feature_names=self._feature_names,
                training_sample_count=n_samples,
                training_start=feature_matrix.timestamps[0],
                training_end=feature_matrix.timestamps[-1],
                inertia=float(kmeans.inertia_),
                iterations=int(kmeans.n_iter_),
                cluster_profiles=self._cluster_profiles,
            )
            self._state = ModelState.FITTED

        except (InsufficientTrainingDataError, InvalidFeatureMatrixError):
            raise
        except Exception as exc:
            raise ModelTrainingError(f"KMeans fitting failed: {exc}") from exc

        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        """
        Predict discrete canonical regime IDs (0..K-1) for each observation row.

        Args:
            feature_matrix: Observations to classify.

        Returns:
            Tuple of canonical regime integer identifiers.

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._kmeans is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        x_raw = np.array(feature_matrix.values, dtype=np.float64)
        # Strictly transform using the frozen, in-sample fitted scaler (zero leakage)
        x_scaled = self._scaler.transform(x_raw)
        raw_labels = self._kmeans.predict(x_scaled)

        # Map raw cluster IDs to canonical regime IDs
        canonical_labels = tuple(self._cluster_mapping[int(c)] for c in raw_labels)
        return canonical_labels

    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...]:
        """
        Compute continuous confidence heuristic vectors across all canonical regimes.

        Methodology:
        - KMeans is a geometric partitioning algorithm, not a generative probabilistic model.
        - As required by the RegimeX contract (ADR-0005, V03 Interface Specifications),
          this method returns a deterministic distance-derived heuristic:
          p(r) = softmax(-d_r / tau) where d_r is Euclidean distance to the scaled
          centroid of regime r.
        - Guarantees each row sums to 1.0 within 1e-6.
        - Column r corresponds strictly to canonical regime r (not raw cluster ID).

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._kmeans is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        x_raw = np.array(feature_matrix.values, dtype=np.float64)
        x_scaled = self._scaler.transform(x_raw)

        # Compute Euclidean distance to all cluster centers in scaled space
        # centers shape: (n_clusters, n_features)
        # distances shape: (n_samples, n_clusters)
        centers = self._kmeans.cluster_centers_
        diff = x_scaled[:, np.newaxis, :] - centers[np.newaxis, :, :]
        raw_distances = np.linalg.norm(diff, axis=2)

        # Temperature scaling based on mean pairwise distance or unit default
        mean_dist = float(np.mean(raw_distances))
        tau = max(mean_dist, 1e-6)

        # Softmax of negative distances
        scaled_neg_dist = -raw_distances / tau
        # Numerical stability shift
        shift = np.max(scaled_neg_dist, axis=1, keepdims=True)
        exp_vals = np.exp(scaled_neg_dist - shift)
        raw_probs = exp_vals / np.sum(exp_vals, axis=1, keepdims=True)

        # Permute probabilities so column r corresponds to canonical regime r
        n_samples = feature_matrix.sample_count
        n_clusters = self._config.n_clusters
        canonical_probs = np.zeros((n_samples, n_clusters), dtype=np.float64)

        for canonical_id in range(n_clusters):
            raw_id = self._canonical_to_raw[canonical_id]
            canonical_probs[:, canonical_id] = raw_probs[:, raw_id]

        # Ensure exact row normalization
        row_sums = np.sum(canonical_probs, axis=1, keepdims=True)
        canonical_probs = canonical_probs / row_sums

        return tuple(tuple(float(val) for val in row) for row in canonical_probs)

    def get_params(self) -> dict[str, Any]:
        """Return hyperparameter dictionary for exact reproducibility."""
        return {
            "model_name": self._config.model_name,
            "model_version": self._config.model_version,
            "n_clusters": self._config.n_clusters,
            "random_state": self._config.random_state,
            "max_iter": self._config.max_iter,
            "init": self._config.init,
            "tol": self._config.tol,
            "feature_names": list(self._feature_names),
        }

    def metadata(self) -> DetectorMetadata:
        """Return self-describing model metadata, assumptions, and limitations."""
        return DetectorMetadata(
            algorithm_id=self.ALGORITHM_ID,
            algorithm_version=self.ALGORITHM_VERSION,
            algorithm_family="Geometric Partitioning / Clustering",
            description=(
                "Deterministic baseline market regime detector utilizing standardized "
                "Euclidean KMeans partitioning with canonical cluster-to-regime sorting."
            ),
            assumptions=(
                "Clusters are spherical in standard-scaled feature space.",
                "Feature distributions have isotropic variance after StandardScaler.",
                "Observations are identically distributed over the training window.",
                "Euclidean distance represents meaningful financial dissimilarity.",
            ),
            known_limitations=(
                "Does not model temporal transitions or time-series autocorrelation (unlike HMM).",
                "Assumes equal cluster sizes and variance across all regime dimensions.",
                "Sensitive to extreme outlier feature vectors.",
                (
                    "predict_proba() provides distance-based geometric heuristics, "
                    "not calibrated Bayesian posteriors."
                ),
                "In-sample fitting does not guarantee out-of-sample regime persistence.",
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
