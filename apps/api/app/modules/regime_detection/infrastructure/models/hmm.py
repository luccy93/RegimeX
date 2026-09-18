"""
RegimeX Regime Detection — Hidden Markov Model (HMM) Detector
==============================================================
Production-grade temporal regime detector implementing the ``RegimeDetector``
domain abstraction via ``hmmlearn.hmm.GaussianHMM``.

Architectural Position:
- ``infrastructure/models/hmm.py`` — Concrete adapter implementing ``RegimeDetector``.
- Encapsulates ``StandardScaler`` and ``hmmlearn.hmm.GaussianHMM`` inside pipeline.
- Translates hmmlearn temporal sequence outputs into strictly typed RegimeX domain models.

Guarantees:
- Temporal modeling: models first-order Markovian state transitions P(S_t | S_{t-1})
  and conditional Gaussian emissions P(X_t | S_t).
- Probabilistic rigour: genuine posterior state probabilities P(S_t | X_{1:T}) normalized
  to 1.0 within 1e-6 tolerance.
- Sequence decoding: predict() executes Viterbi path decoding across observation sequence.
- Anti-leakage preprocessing: StandardScaler is fitted strictly on in-sample training data.
  Inference transforms observations using frozen parameters without refitting.
- Deterministic state canonicalization: raw algorithmic states (0..K-1) are mapped
  to stable, sorted canonical regime IDs based on invariant emission signatures.
- Consistent remapping: predict() canonical state IDs and predict_proba() canonical
  columns adhere strictly to the identical canonical mapping.
- Complete domain isolation: domain contracts have zero dependency on vendor libraries.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

from app.modules.regime_detection.domain.errors import (
    HMMFitError,
    HMMPredictionError,
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
    HMMModelConfig,
    ModelState,
)

logger = logging.getLogger(__name__)


class GaussianHMMRegimeDetector(RegimeDetector):
    """
    Temporal Gaussian Hidden Markov Model regime detector with anti-leakage scaling,
    deterministic state canonicalization, Viterbi decoding, and genuine posterior
    probability estimation.
    """

    ALGORITHM_ID: str = "gaussian_hmm"
    ALGORITHM_VERSION: str = "1.0.0"

    def __init__(self, config: HMMModelConfig | None = None) -> None:
        """
        Initialize the Gaussian HMM regime detector.

        Args:
            config: HMM hyperparameter configuration specifying hidden states, covariance type,
                regularization, tolerance, iterations, decoding algorithm, and random seed.
                Defaults to HMMModelConfig().
        """
        self._config = config or HMMModelConfig()
        self._state = ModelState.UNFITTED

        # Model pipeline components (encapsulated in infrastructure)
        self._scaler: StandardScaler | None = None
        self._hmm: GaussianHMM | None = None

        # Trained state and canonicalization mapping
        self._feature_names: tuple[str, ...] = ()
        self._cluster_mapping: dict[int, int] = {}  # raw state_id -> canonical_regime_id
        self._canonical_to_raw: dict[int, int] = {}  # canonical_regime_id -> raw state_id
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
    def config(self) -> HMMModelConfig:
        return self._config

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    @property
    def cluster_profiles(self) -> tuple[ClusterProfile, ...]:
        return self._cluster_profiles

    def fit(self, feature_matrix: FeatureMatrix) -> GaussianHMMRegimeDetector:
        """
        Fit the standard scaler and Gaussian HMM strictly on in-sample training sequence.

        Args:
            feature_matrix: Validated, point-in-time, chronologically ordered feature observations.

        Returns:
            self: Fitted detector instance.

        Raises:
            InsufficientTrainingDataError: If sample count < n_components or < 1.
            InvalidFeatureMatrixError: If feature columns do not match configured feature subset.
            HMMFitError: If algorithmic or numerical convergence failure occurs during fitting.
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

            # 2. Gaussian Hidden Markov Model estimation via Baum-Welch (EM)
            hmm = GaussianHMM(
                n_components=n_components,
                covariance_type=self._config.covariance_type,
                min_covar=self._config.min_covar,
                algorithm=self._config.algorithm,
                random_state=self._config.random_state,
                n_iter=self._config.n_iter,
                tol=self._config.tol,
                params=self._config.params,
                init_params=self._config.init_params,
                implementation=self._config.implementation,
            )
            hmm.fit(x_scaled)

            converged = bool(hmm.monitor_.converged) if hasattr(hmm, "monitor_") else False
            n_iter_run = int(hmm.monitor_.iter) if hasattr(hmm, "monitor_") else self._config.n_iter

            if not converged:
                logger.warning(
                    "HMM did not converge within n_iter=%d (actual_iter=%d)",
                    self._config.n_iter,
                    n_iter_run,
                )

            # 3. Unscale state emission means and calculate empirical feature statistics
            unscaled_means = scaler.inverse_transform(hmm.means_)
            raw_viterbi_labels = hmm.predict(x_scaled)

            raw_profiles: list[dict[str, Any]] = []

            for state_idx in range(n_components):
                mask = raw_viterbi_labels == state_idx
                count = int(np.sum(mask))

                if count > 0:
                    state_data = x_raw[mask]
                    means = np.mean(state_data, axis=0)
                    stds = np.std(state_data, axis=0, ddof=1) if count > 1 else np.zeros_like(means)
                else:
                    means = unscaled_means[state_idx]
                    stds = np.zeros_like(means)

                feature_means = {
                    feat: float(means[col_idx]) for col_idx, feat in enumerate(self._feature_names)
                }
                feature_stds = {
                    feat: float(stds[col_idx]) for col_idx, feat in enumerate(self._feature_names)
                }

                # Deterministic signature: tuple of unscaled emission means sorted by feature name
                feat_to_col = {f: i for i, f in enumerate(self._feature_names)}
                signature = tuple(
                    float(unscaled_means[state_idx, feat_to_col[f]])
                    for f in sorted(self._feature_names)
                )

                raw_profiles.append(
                    {
                        "state_id": state_idx,
                        "center": tuple(float(v) for v in unscaled_means[state_idx]),
                        "sample_count": count,
                        "feature_means": feature_means,
                        "feature_stds": feature_stds,
                        "signature": signature,
                    }
                )

            # 4. Deterministic State Canonicalization
            # Sort states by invariant emission signature (secondary tie-breaker: state_id)
            sorted_by_signature = sorted(
                raw_profiles,
                key=lambda p: (p["signature"], p["state_id"]),
            )

            cluster_mapping: dict[int, int] = {}
            canonical_to_raw: dict[int, int] = {}
            final_profiles: list[ClusterProfile] = []

            for canonical_id, prof in enumerate(sorted_by_signature):
                raw_id = prof["state_id"]
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

            # Compute sequence log-likelihood score
            score_val = float(hmm.score(x_scaled))

            # 5. Persist fitted pipeline and diagnostics
            self._scaler = scaler
            self._hmm = hmm
            self._cluster_mapping = cluster_mapping
            self._canonical_to_raw = canonical_to_raw
            self._cluster_profiles = tuple(final_profiles)

            self._fit_result = FitResult(
                model_name=self._config.model_name,
                model_version=self._config.model_version,
                algorithm="GaussianHMM",
                n_clusters=n_components,
                random_state=self._config.random_state,
                feature_names=self._feature_names,
                training_sample_count=n_samples,
                training_start=feature_matrix.timestamps[0],
                training_end=feature_matrix.timestamps[-1],
                inertia=0.0,
                iterations=n_iter_run,
                cluster_profiles=self._cluster_profiles,
                lower_bound=score_val,
                converged=converged,
            )
            self._state = ModelState.FITTED

        except (InsufficientTrainingDataError, InvalidFeatureMatrixError):
            raise
        except Exception as exc:
            raise HMMFitError(f"Gaussian Hidden Markov Model fitting failed: {exc}") from exc

        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        """
        Predict discrete canonical regime IDs (0..K-1) for observations via sequence decoding.

        By default, uses Viterbi decoding to infer the single most likely hidden state sequence
        given the observed sequence and learned transition dynamics.

        Args:
            feature_matrix: Chronologically ordered observations to classify.

        Returns:
            Tuple of canonical regime integer identifiers.

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
            HMMPredictionError: If numerical failure occurs during sequence decoding.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._hmm is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        x_raw = np.array(feature_matrix.values, dtype=np.float64)

        try:
            # Strictly transform using the frozen, in-sample fitted scaler (zero leakage)
            x_scaled = self._scaler.transform(x_raw)
            raw_preds = self._hmm.predict(x_scaled)

            # Map raw decoded states to canonical regime IDs
            return tuple(self._cluster_mapping[int(s)] for s in raw_preds)

        except Exception as exc:
            raise HMMPredictionError(f"HMM sequence decoding failed: {exc}") from exc

    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...]:
        """
        Compute continuous Bayesian posterior state probability vectors across canonical regimes.

        Methodology:
        - Computes posterior state probabilities P(S_t=k | X_{1:T}) via forward-backward algorithm.
        - Probability columns are deterministically remapped to canonical regime order
          such that column c corresponds strictly to REGIME_c.
        - Guarantees each row sums to 1.0 within 1e-6 and every probability satisfies 0 <= p <= 1.

        Raises:
            ModelNotFittedError: If model has not been fitted.
            InvalidFeatureMatrixError: If feature columns do not match training features.
            HMMPredictionError: If numerical failure occurs during posterior inference.
        """
        if self._state != ModelState.FITTED or self._scaler is None or self._hmm is None:
            raise ModelNotFittedError(model_name=self._config.model_name)

        self._validate_inference_features(feature_matrix)

        x_raw = np.array(feature_matrix.values, dtype=np.float64)

        try:
            # Strictly transform using the frozen, in-sample fitted scaler (zero leakage)
            x_scaled = self._scaler.transform(x_raw)
            raw_probs = self._hmm.predict_proba(x_scaled)

            # Numerical validation: ensure all values are finite
            if not np.all(np.isfinite(raw_probs)):
                raise HMMPredictionError("HMM posterior probabilities contain non-finite values.")

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

            if np.any(np.abs(row_sums - 1.0) > 1e-2):
                raise HMMPredictionError(
                    "HMM posterior probabilities deviate significantly from sum=1.0."
                )

            row_sums = np.where(row_sums == 0, 1.0, row_sums)
            canonical_probs = canonical_probs / row_sums

            return tuple(tuple(float(val) for val in row) for row in canonical_probs)

        except HMMPredictionError:
            raise
        except Exception as exc:
            raise HMMPredictionError(f"HMM posterior probability estimation failed: {exc}") from exc

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
            "n_iter": self._config.n_iter,
            "tol": self._config.tol,
            "min_covar": self._config.min_covar,
            "algorithm": self._config.algorithm,
            "init_params": self._config.init_params,
            "params": self._config.params,
            "implementation": self._config.implementation,
            "feature_names": feature_names,
        }

    def metadata(self) -> DetectorMetadata:
        """Return self-describing model metadata, mathematical assumptions, and limitations."""
        return DetectorMetadata(
            algorithm_id=self.ALGORITHM_ID,
            algorithm_version=self.ALGORITHM_VERSION,
            algorithm_family="Probabilistic / Temporal Sequence Models",
            description=(
                "Temporal market regime detector utilizing Gaussian Hidden Markov Models (HMM) "
                "fitted via Baum-Welch Expectation-Maximization, featuring Viterbi sequence "
                "decoding, forward-backward posterior inference, anti-leakage standardized "
                "preprocessing, and deterministic state canonicalization."
            ),
            assumptions=(
                "Hidden market regime transitions follow a first-order stationary Markov chain.",
                (
                    "Feature observations at each time step are conditionally independent "
                    "given the current hidden regime state."
                ),
                (
                    "Feature vectors within each regime are emitted from a multivariate "
                    "Gaussian distribution."
                ),
                (
                    f"Emission covariance matrices conform to '{self._config.covariance_type}' "
                    "structure."
                ),
                "Observations must be strictly chronologically ordered without temporal gaps.",
            ),
            known_limitations=(
                (
                    "First-order Markov assumption assumes temporal memory of exactly one step; "
                    "long-term regime memory is not captured directly."
                ),
                (
                    "Baum-Welch EM converges to local likelihood maxima; parameter estimation "
                    "is sensitive to initialization and random seed."
                ),
                (
                    "Stationary transition matrix assumption may degrade during non-stationary "
                    "structural macroeconomic shifts."
                ),
                (
                    "Viterbi sequence decoding finds the globally optimal path, which may differ "
                    "from row-wise argmax of posterior marginal probabilities."
                ),
                (
                    "Posterior probabilities reflect in-sample sequence likelihoods, not "
                    "guarantees of future price direction or trading returns."
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
