"""
RegimeX Regime Detection — Application Service
==============================================
Coordinates the lifecycle between V07 FeatureSet outputs, FeatureMatrix preparation,
model fitting, and canonical RegimeDetectionResult generation.

Guarantees:
- Pure application orchestration: depends only on domain contracts and interfaces.
- Zero direct dependencies on scikit-learn or low-level mathematical libraries.
- Decoupled from specific ML algorithms (works with any RegimeDetector implementation).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeDetectionResult,
    RegimeRecord,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


class RegimeDetectionService:
    """
    Application facade orchestrating feature preparation, regime model fitting,
    and point-in-time regime inference.
    """

    def __init__(self, detector: RegimeDetector | None = None) -> None:
        """
        Initialize the regime detection service.

        Args:
            detector: Optional RegimeDetector implementation. Defaults to a new
                KMeansRegimeDetector baseline instance if omitted.
        """
        self._detector = detector or KMeansRegimeDetector()

    @property
    def detector(self) -> RegimeDetector:
        """Active detector instance."""
        return self._detector

    def fit_from_feature_set(
        self,
        feature_set: FeatureSet,
        feature_names: Sequence[str] | None = None,
    ) -> FeatureMatrix:
        """
        Build a validated FeatureMatrix from a FeatureSet and fit the active detector.

        Args:
            feature_set: V07 reproducible feature collection.
            feature_names: Optional specific feature names to train on.

        Returns:
            The prepared FeatureMatrix used for fitting.
        """
        matrix = FeatureMatrixBuilder.build(feature_set, feature_names=feature_names)
        self._detector.fit(matrix)
        return matrix

    def detect_from_feature_set(
        self,
        feature_set: FeatureSet,
        feature_names: Sequence[str] | None = None,
    ) -> RegimeDetectionResult:
        """
        Transform a FeatureSet and execute regime classification on the active detector.

        Args:
            feature_set: Feature observations to classify.
            feature_names: Optional subset of feature names.

        Returns:
            Structured, immutable RegimeDetectionResult.
        """
        matrix = FeatureMatrixBuilder.build(feature_set, feature_names=feature_names)
        return self.detect_from_matrix(matrix)

    def detect_from_matrix(self, matrix: FeatureMatrix) -> RegimeDetectionResult:
        """
        Execute inference directly on a pre-built FeatureMatrix using the active detector.

        Args:
            matrix: Validated numerical feature matrix.

        Returns:
            Structured, immutable RegimeDetectionResult.
        """
        canonical_preds = self._detector.predict(matrix)
        probabilities = self._detector.predict_proba(matrix)

        # Retrieve raw cluster mappings if available from cluster profiles
        raw_cluster_map: dict[int, int] = {}
        if self._detector.fit_result:
            for prof in self._detector.fit_result.cluster_profiles:
                raw_cluster_map[prof.canonical_regime_id] = prof.cluster_id

        records: list[RegimeRecord] = []
        for idx, (ts, regime_id) in enumerate(zip(matrix.timestamps, canonical_preds, strict=True)):
            raw_id = raw_cluster_map.get(regime_id, regime_id)
            prob_row = probabilities[idx] if probabilities is not None else None

            records.append(
                RegimeRecord(
                    timestamp=ts,
                    cluster_id=raw_id,
                    canonical_regime_id=regime_id,
                    canonical_regime_label=f"REGIME_{regime_id}",
                    probabilities=prob_row,
                )
            )

        return RegimeDetectionResult(
            model_version=self._detector.algorithm_version,
            algorithm=self._detector.algorithm_id,
            feature_names=matrix.feature_names,
            records=tuple(records),
        )

    def fit_and_detect(
        self,
        feature_set: FeatureSet,
        feature_names: Sequence[str] | None = None,
    ) -> tuple[RegimeDetector, RegimeDetectionResult]:
        """
        Convenience method: Fit the detector and immediately generate in-sample regime results.

        Args:
            feature_set: Feature dataset for fitting and in-sample classification.
            feature_names: Optional subset of features to train on.

        Returns:
            Tuple of (fitted detector, RegimeDetectionResult).
        """
        matrix = self.fit_from_feature_set(feature_set, feature_names=feature_names)
        result = self.detect_from_matrix(matrix)
        return self._detector, result
