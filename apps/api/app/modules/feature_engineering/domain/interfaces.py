"""
RegimeX Feature Engineering — Domain Interfaces
==============================================
Defines the abstract contract for feature calculators.

Architectural position: ``domain/interfaces.py`` — pure Python, no external libraries.
Concrete calculators in ``infrastructure/calculators/`` implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.models import FeatureInputData


class FeatureCalculator(ABC):
    """
    Abstract contract for a quantitative feature calculation.

    Design Principles:
    - Pure point-in-time calculation: result at index t depends ONLY on observations <= t.
    - Zero look-ahead bias: future observations must never be used.
    - Deterministic: identical inputs produce identical outputs.
    - Missing value policy: warm-up periods return None rather than artificial zeros.
    - Thread-safe: calculators should be stateless.
    """

    @property
    @abstractmethod
    def definition(self) -> FeatureDefinition:
        """Return the immutable metadata and parameter specification of this feature."""
        ...

    @property
    def name(self) -> str:
        """Convenience property for the feature's unique identifier."""
        return self.definition.name

    @abstractmethod
    def calculate(self, data: FeatureInputData) -> list[float | None]:
        """
        Execute calculation over the provided market time series.

        Args:
            data: Pure domain container with validated, ordered price and volume series.

        Returns:
            List of calculated float values or None (for warm-up observations).
            Length of the return list MUST strictly equal ``data.length``.

        Raises:
            FeatureCalculationError: On unexpected numerical or calculation failure.
        """
        ...
