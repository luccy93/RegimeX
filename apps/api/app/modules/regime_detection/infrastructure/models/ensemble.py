"""
RegimeX Regime Detection — Regime Model Ensemble
================================================
Production-grade deterministic ensemble combining heterogeneous regime detectors
(KMeans baseline from V08, GMM from V10, and Gaussian HMM from V10).

Architectural Position:
- ``infrastructure/models/ensemble.py`` — Concrete implementation conforming to ``RegimeDetector``.
- Integrates ``RegimeAlignmentEngine``, ``EnsembleAggregator``, and ``RegimeModelRegistry``.
- Pure consensus aggregation; confidence scoring is explicitly deferred to V11 Commit 02.

Guarantees:
- Fully deterministic: reproducible consensus across identical inputs and configurations.
- Explainability: exposes component predictions, aligned predictions, and agreement metrics.
- Anti-leakage: fits strictly on in-sample data; inference does not mutate or refit components.
- Configurable failure policies: supports FAIL_FAST, SKIP_UNAVAILABLE, and BEST_EFFORT.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from app.modules.regime_detection.domain.errors import (
    EnsembleModelUnavailableError,
    InsufficientTrainingDataError,
    InsufficientUsableModelsError,
    InvalidFeatureMatrixError,
    ModelNotFittedError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    DetectorMetadata,
    EnsembleModelConfig,
    FailurePolicy,
    FeatureMatrix,
    FitResult,
    ModelState,
    RegimeEnsembleResult,
)
from app.modules.regime_detection.infrastructure.ensemble.aggregation import (
    EnsembleAggregator,
)
from app.modules.regime_detection.infrastructure.ensemble.alignment import (
    RegimeAlignmentEngine,
)
from app.modules.regime_detection.infrastructure.ensemble.registry import (
    RegimeModelRegistry,
)

logger = logging.getLogger(__name__)


class RegimeModelEnsemble(RegimeDetector):
    """
    Deterministic regime model ensemble combining KMeans, GMM, and HMM detectors.
    """

    ALGORITHM_ID: str = "regime_ensemble"
    ALGORITHM_VERSION: str = "1.0.0"

    def __init__(
        self,
        config: EnsembleModelConfig | None = None,
        models: Mapping[str, RegimeDetector] | None = None,
    ) -> None:
        """
        Initialize the regime model ensemble.

        Args:
            config: Ensemble configuration specifying weights, failure policies,
                alignment policies, and minimum model counts. Defaults to standard configuration.
            models: Optional pre-instantiated component detectors. If omitted, detectors
                are instantiated via the RegimeModelRegistry.
        """
        self._config = config or EnsembleModelConfig()
        self._state = ModelState.UNFITTED

        # Component models
        if models is not None:
            self._models: dict[str, RegimeDetector] = dict(models)
        else:
            self._models = {
                model_id: RegimeModelRegistry.create(model_id)
                for model_id in self._config.enabled_models
            }

        # Trained state and alignment mappings
        self._alignment_maps: dict[str, dict[int, int]] = {}
        self._feature_names: tuple[str, ...] = ()
        self._fit_result: FitResult | None = None
        self._failed_at_fit: set[str] = set()

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
    def config(self) -> EnsembleModelConfig:
        return self._config

    @property
    def models(self) -> dict[str, RegimeDetector]:
        return dict(self._models)

    @property
    def alignment_maps(self) -> dict[str, dict[int, int]]:
        return dict(self._alignment_maps)

    @property
    def fit_result(self) -> FitResult | None:
        return self._fit_result

    def fit(self, feature_matrix: FeatureMatrix) -> RegimeModelEnsemble:
        """
        Fit all enabled component models strictly on in-sample training data and align regimes.

        Args:
            feature_matrix: Validated, point-in-time feature observations.

        Returns:
            self: Fitted ensemble instance.

        Raises:
            InsufficientTrainingDataError: If observation count is insufficient.
            InvalidFeatureMatrixError: If feature matrix is invalid.
            EnsembleModelUnavailableError: If a model fails under FAIL_FAST.
            InsufficientUsableModelsError: If usable models fall below minimum_required_models.
        """
        if feature_matrix.is_empty:
            raise InvalidFeatureMatrixError("Feature matrix cannot be empty for ensemble fitting.")

        if feature_matrix.sample_count < 2:
            raise InsufficientTrainingDataError(
                required_samples=2,
                available_samples=feature_matrix.sample_count,
                requested_clusters=2,
            )

        # Validate feature column consistency
        if self._config.feature_names:
            if feature_matrix.feature_names != self._config.feature_names:
                raise InvalidFeatureMatrixError(
                    f"Feature matrix columns ({feature_matrix.feature_names}) do not match "
                    f"configured ensemble features ({self._config.feature_names})."
                )
            self._feature_names = self._config.feature_names
        else:
            self._feature_names = feature_matrix.feature_names

        usable_models: dict[str, RegimeDetector] = {}
        failed_models: set[str] = set()

        for model_id in self._config.enabled_models:
            if model_id not in self._models:
                if self._config.failure_policy == FailurePolicy.FAIL_FAST:
                    raise EnsembleModelUnavailableError(
                        model_name=model_id,
                        reason=f"Model '{model_id}' is not registered in ensemble.",
                    )
                failed_models.add(model_id)
                continue

            detector = self._models[model_id]
            try:
                # Fit detector if not already fitted on this matrix
                if detector.state != ModelState.FITTED:
                    detector.fit(feature_matrix)
                usable_models[model_id] = detector
            except Exception as exc:
                if self._config.failure_policy == FailurePolicy.FAIL_FAST:
                    raise EnsembleModelUnavailableError(
                        model_name=model_id,
                        reason=f"Fit failed for model '{model_id}': {exc}",
                    ) from exc
                logger.warning("Component model '%s' failed during fit: %s", model_id, exc)
                failed_models.add(model_id)

        # Enforce minimum usable models constraint
        if len(usable_models) < self._config.minimum_required_models:
            raise InsufficientUsableModelsError(
                required_models=self._config.minimum_required_models,
                usable_models=len(usable_models),
                details={"failed_models": list(failed_models)},
            )

        # Construct canonical alignment across all usable models
        alignment_maps = RegimeAlignmentEngine.build_alignment(
            models=usable_models,
            config=self._config,
        )

        # Select reference profiles for FitResult summary
        ref_id = self._config.reference_model
        if ref_id is None or ref_id not in usable_models:
            for enabled_id in self._config.enabled_models:
                if enabled_id in usable_models:
                    ref_id = enabled_id
                    break

        ref_model = usable_models[ref_id] if ref_id else next(iter(usable_models.values()))
        ref_fit = ref_model.fit_result
        cluster_profiles = ref_fit.cluster_profiles if ref_fit else ()
        n_clusters = ref_fit.n_clusters if ref_fit else 4

        self._alignment_maps = alignment_maps
        self._failed_at_fit = failed_models
        self._fit_result = FitResult(
            model_name=self._config.model_name,
            model_version=self._config.model_version,
            algorithm="RegimeModelEnsemble",
            n_clusters=n_clusters,
            random_state=42,
            feature_names=self._feature_names,
            training_sample_count=feature_matrix.sample_count,
            training_start=feature_matrix.timestamps[0],
            training_end=feature_matrix.timestamps[-1],
            inertia=0.0,
            iterations=1,
            cluster_profiles=cluster_profiles,
        )
        self._state = ModelState.FITTED
        return self

    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        """
        Predict discrete canonical consensus regime states (0..K-1) for each observation row.

        Args:
            feature_matrix: Feature matrix to classify.

        Returns:
            Tuple of canonical regime integer identifiers.

        Raises:
            ModelNotFittedError: If ensemble has not been fitted.
        """
        result = self.predict_ensemble(feature_matrix)
        return result.get_regime_series()

    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...] | None:
        """
        Compute continuous consensus support probability vectors across all K canonical regimes.

        Guarantees:
        - Pure consensus support distribution: P(k) = W_k / W_total.
        - Each observation vector sums to 1.0 within floating-point tolerance (1e-6).
        - Point-in-time calculation with zero future leakage.
        - Supports downstream consumers requiring continuous probabilistic distributions.

        Raises:
            ModelNotFittedError: If ensemble has not been fitted.
            InvalidFeatureMatrixError: If feature matrix columns do not match fitted columns.
        """
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._config.model_name)

        result = self.predict_ensemble(feature_matrix)
        if not result.records:
            return ()

        # Determine canonical regime space size K
        n_clusters = self._fit_result.n_clusters if self._fit_result else 4
        max_aligned = (
            max(max(preds) for preds in result.aligned_predictions.values() if preds)
            if result.aligned_predictions
            else 0
        )
        k_regimes = max(n_clusters, max_aligned + 1)

        weights = result.weights_used
        prob_matrix: list[tuple[float, ...]] = []

        for record in result.records:
            row_weights = [0.0] * k_regimes
            for model_id, aligned_regime in record.aligned_predictions.items():
                w = weights.get(model_id, 1.0)
                if 0 <= aligned_regime < k_regimes:
                    row_weights[aligned_regime] += w

            total_w = sum(row_weights)
            if total_w > 0.0:
                row_probs = tuple(float(w / total_w) for w in row_weights)
            else:
                row_probs = tuple(1.0 / k_regimes for _ in range(k_regimes))
            prob_matrix.append(row_probs)

        return tuple(prob_matrix)

    def predict_ensemble(self, feature_matrix: FeatureMatrix) -> RegimeEnsembleResult:
        """
        Execute ensemble inference producing full auditability output with component
        predictions, canonical alignment, agreement metrics, and confidence scoring.

        Args:
            feature_matrix: Feature matrix to classify.

        Returns:
            RegimeEnsembleResult: Complete, immutable ensemble output.

        Raises:
            ModelNotFittedError: If ensemble has not been fitted.
            EnsembleModelUnavailableError: If a required model fails under FAIL_FAST.
            InsufficientUsableModelsError: If usable models fall below minimum_required_models.
        """
        if self._state != ModelState.FITTED:
            raise ModelNotFittedError(model_name=self._config.model_name)

        if self._feature_names and feature_matrix.feature_names != self._feature_names:
            raise InvalidFeatureMatrixError(
                f"Feature matrix columns ({feature_matrix.feature_names}) do not match "
                f"ensemble fitted features ({self._feature_names})."
            )

        component_predictions: dict[str, tuple[int, ...]] = {}
        unavailable_models: list[str] = list(self._failed_at_fit)

        for model_id in self._config.enabled_models:
            if model_id in self._failed_at_fit or model_id not in self._models:
                if model_id not in unavailable_models:
                    unavailable_models.append(model_id)
                continue

            detector = self._models[model_id]
            try:
                preds = detector.predict(feature_matrix)
                component_predictions[model_id] = tuple(int(p) for p in preds)
            except Exception as exc:
                if self._config.failure_policy == FailurePolicy.FAIL_FAST:
                    raise EnsembleModelUnavailableError(
                        model_name=model_id,
                        reason=f"Prediction failed for model '{model_id}': {exc}",
                    ) from exc
                logger.warning("Model '%s' failed during ensemble prediction: %s", model_id, exc)
                unavailable_models.append(model_id)

        # Check usable models count
        usable_count = len(component_predictions)
        if usable_count < self._config.minimum_required_models:
            raise InsufficientUsableModelsError(
                required_models=self._config.minimum_required_models,
                usable_models=usable_count,
                details={"unavailable_models": unavailable_models},
            )

        # Normalize weights for participating models
        active_weights: dict[str, float] = {}
        total_active_weight = sum(
            self._config.model_weights.get(m, 1.0) for m in component_predictions
        )
        if total_active_weight <= 0.0:
            total_active_weight = 1.0

        for m in component_predictions:
            raw_w = self._config.model_weights.get(m, 1.0)
            active_weights[m] = float(raw_w / total_active_weight)

        # Align predictions into canonical space
        aligned_predictions = RegimeAlignmentEngine.align_predictions(
            predictions=component_predictions,
            alignment_maps=self._alignment_maps,
        )

        # Aggregate aligned predictions and compute confidence scores
        consensus_regimes, records = EnsembleAggregator.aggregate(
            timestamps=feature_matrix.timestamps,
            component_predictions=component_predictions,
            aligned_predictions=aligned_predictions,
            weights=active_weights,
            config=self._config,
        )

        confidence_scores = tuple(r.confidence for r in records)

        return RegimeEnsembleResult(
            model_version=self.ALGORITHM_VERSION,
            algorithm=self.ALGORITHM_ID,
            feature_names=feature_matrix.feature_names,
            records=records,
            models_used=tuple(sorted(component_predictions.keys())),
            models_unavailable=tuple(sorted(set(unavailable_models))),
            component_predictions=component_predictions,
            aligned_predictions=aligned_predictions,
            ensemble_regimes=consensus_regimes,
            weights_used=active_weights,
            aggregation_strategy=str(self._config.aggregation_strategy),
            alignment_policy=str(self._config.alignment_policy),
            failure_policy=str(self._config.failure_policy),
            confidence_scores=confidence_scores,
        )

    def get_params(self) -> dict[str, Any]:
        """Return hyperparameter configuration dictionary for historical auditability."""
        return {
            "model_name": self._config.model_name,
            "model_version": self._config.model_version,
            "enabled_models": list(self._config.enabled_models),
            "model_weights": dict(self._config.model_weights),
            "aggregation_strategy": str(self._config.aggregation_strategy),
            "minimum_required_models": self._config.minimum_required_models,
            "failure_policy": str(self._config.failure_policy),
            "alignment_policy": str(self._config.alignment_policy),
            "tie_breaker": str(self._config.tie_breaker),
            "reference_model": self._config.reference_model,
        }

    def metadata(self) -> DetectorMetadata:
        """Expose self-describing documentation, assumptions, and limitations."""
        return DetectorMetadata(
            algorithm_id=self.ALGORITHM_ID,
            algorithm_version=self.ALGORITHM_VERSION,
            algorithm_family="Ensemble Consensus",
            description=(
                "Multi-model regime ensemble combining KMeans geometric clustering, "
                "Gaussian Mixture Model density estimation, and Hidden Markov Model "
                "temporal dynamics into a unified consensus regime with confidence scoring."
            ),
            assumptions=(
                "Component models capture complementary geometric, density, and temporal views.",
                "Observations are aligned in chronological order across all models.",
                "Cluster profiles provide a reliable basis for canonical identity alignment.",
                "Model confidence reflects consensus support, not future return probability.",
            ),
            known_limitations=(
                "Confidence score reflects model agreement, not future returns or certainty.",
                "Consensus quality depends on the diversity and calibration of component models.",
                "Extreme market disruptions outside training data may yield model disagreement.",
                "Transition analytics and regime switching probabilities belong to Volume 12.",
            ),
            hyperparameters=self.get_params(),
        )
