"""
RegimeX Regime Detection — Domain Interfaces
============================================
Defines the conceptual contract for market regime detection algorithms.

Conforms to V03 Architecture specifications (ADR-0003, ADR-0005, and
INTERFACE_SPECIFICATIONS.md Section 2.3).

Guarantees:
- Model agnostic: downstream systems (risk engines, transition analysis,
  backtesting attribution) interact strictly through this abstraction.
- Zero scikit-learn or vendor imports in domain contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.modules.regime_detection.domain.models import (
    DetectorMetadata,
    FeatureMatrix,
    FitResult,
    ModelState,
)


class RegimeDetector(ABC):
    """
    Conceptual interface for all market regime detection models.

    Supported model families across RegimeX:
    - KMeans / Geometric Clustering (V08 baseline)
    - Gaussian Mixture Models (future V10)
    - Hidden Markov Models (future V10)
    - Change Point Detection (future)
    """

    @property
    @abstractmethod
    def algorithm_id(self) -> str:
        """Unique algorithm identifier (e.g., 'kmeans_baseline')."""
        ...

    @property
    @abstractmethod
    def algorithm_version(self) -> str:
        """Semantic version of the detector implementation (e.g., '1.0.0')."""
        ...

    @property
    @abstractmethod
    def state(self) -> ModelState:
        """Current lifecycle state (UNFITTED or FITTED)."""
        ...

    @property
    @abstractmethod
    def fit_result(self) -> FitResult | None:
        """Summary diagnostics and provenance of the fitted model, or None if unfitted."""
        ...

    @abstractmethod
    def fit(self, feature_matrix: FeatureMatrix) -> RegimeDetector:
        """
        Fits model parameters strictly using in-sample feature data.

        Guarantees:
        - Scaler and model parameters are computed strictly from feature_matrix.
        - Must raise InsufficientTrainingDataError if sample count < n_clusters.
        - Returns self upon successful training.
        """
        ...

    @abstractmethod
    def predict(self, feature_matrix: FeatureMatrix) -> tuple[int, ...]:
        """
        Predicts discrete canonical regime states (0, 1, ..., K-1) for each observation row.

        Guarantees:
        - Output length matches len(feature_matrix.timestamps) exactly.
        - Must raise ModelNotFittedError if called before fit().
        - Output values are canonicalized regime IDs, invariant to raw cluster numbering.
        """
        ...

    @abstractmethod
    def predict_proba(
        self,
        feature_matrix: FeatureMatrix,
    ) -> tuple[tuple[float, ...], ...] | None:
        """
        Predicts continuous posterior probability distributions across all K regimes.

        Guarantees:
        - For probabilistic algorithms (GMM, HMM), outputs genuine posterior vectors where
          each row sums to 1.0 within floating-point tolerance (1e-6).
        - For non-probabilistic algorithms (such as KMeans), returns either a clearly
          disclosed deterministic distance-derived heuristic distribution or None.
        - Must raise ModelNotFittedError if called before fit().
        """
        ...

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """
        Returns the complete hyperparameter configuration for exact historical reproducibility.
        """
        ...

    @abstractmethod
    def metadata(self) -> DetectorMetadata:
        """
        Exposes algorithm documentation, assumptions, and known limitation disclosures.
        """
        ...
