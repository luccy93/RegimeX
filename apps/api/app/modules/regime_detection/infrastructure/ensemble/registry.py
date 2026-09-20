"""
RegimeX Regime Detection — Regime Model Registry
================================================
Catalog and factory registry for component regime detection algorithms.

Architectural Position:
- ``infrastructure/ensemble/registry.py``
- Pre-registers standard RegimeX detectors: KMeans (V08), GMM (V10), HMM (V10).
- Extensible: allows registering future community models and custom detectors.
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.regime_detection.domain.errors import InvalidEnsembleConfigurationError
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.hmm import (
    GaussianHMMRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)

DetectorFactory = Callable[..., RegimeDetector]


class RegimeModelRegistry:
    """
    Catalog of available regime detector algorithms for the ensemble.
    """

    _registry: dict[str, DetectorFactory] = {
        "kmeans": lambda **kw: KMeansRegimeDetector(**kw),
        "gmm": lambda **kw: GaussianMixtureRegimeDetector(**kw),
        "hmm": lambda **kw: GaussianHMMRegimeDetector(**kw),
    }

    @classmethod
    def register(cls, model_id: str, factory: DetectorFactory) -> None:
        """Register a new or custom regime detector factory."""
        if not model_id or not isinstance(model_id, str):
            raise InvalidEnsembleConfigurationError("model_id must be a non-empty string.")
        cls._registry[model_id.lower().strip()] = factory

    @classmethod
    def get_factory(cls, model_id: str) -> DetectorFactory:
        """Retrieve the factory callable for a model identifier."""
        clean_id = model_id.lower().strip()
        if clean_id not in cls._registry:
            raise InvalidEnsembleConfigurationError(
                f"Unknown model identifier '{model_id}'. "
                f"Available models: {sorted(cls._registry.keys())}."
            )
        return cls._registry[clean_id]

    @classmethod
    def create(cls, model_id: str, **kwargs: object) -> RegimeDetector:
        """Instantiate a new detector instance by model identifier."""
        factory = cls.get_factory(model_id)
        return factory(**kwargs)

    @classmethod
    def list_available(cls) -> tuple[str, ...]:
        """Return all registered model identifiers."""
        return tuple(sorted(cls._registry.keys()))
