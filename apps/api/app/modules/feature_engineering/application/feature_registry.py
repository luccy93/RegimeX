"""
RegimeX Feature Engineering — Feature Registry
==============================================
Central catalogue and discovery registry for feature calculators.

Architectural position: ``application/feature_registry.py``
Ensures unique registration, deterministic discovery, and typed error handling.
"""

from __future__ import annotations

from app.modules.feature_engineering.domain.errors import (
    DuplicateFeatureError,
    FeatureNotFoundError,
)
from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.infrastructure.calculators.momentum import (
    MomentumCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.range import (
    HighLowRangeCalculator,
    NormalizedTrueRangeCalculator,
    TrueRangeCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.returns import (
    SimpleReturnCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.trend import (
    EMARatioCalculator,
    SMARatioCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.volatility import (
    RollingVolatilityCalculator,
)
from app.modules.feature_engineering.infrastructure.calculators.volume import (
    VolumeChangeCalculator,
    VolumeRatioCalculator,
)


class FeatureRegistry:
    """
    Thread-safe registry for discovering, cataloguing, and retrieving feature calculators.
    """

    def __init__(self) -> None:
        self._calculators: dict[str, FeatureCalculator] = {}

    def register(self, calculator: FeatureCalculator) -> None:
        """
        Register a new feature calculator.

        Raises:
            DuplicateFeatureError: if a calculator with the same name is already registered.
        """
        name = calculator.name
        if name in self._calculators:
            raise DuplicateFeatureError(
                name,
                details={"registered_features": sorted(self._calculators.keys())},
            )
        self._calculators[name] = calculator

    def get(self, name: str) -> FeatureCalculator:
        """
        Retrieve a registered calculator by name.

        Raises:
            FeatureNotFoundError: if no calculator with the given name is registered.
        """
        if name not in self._calculators:
            raise FeatureNotFoundError(
                name,
                details={"registered_features": sorted(self._calculators.keys())},
            )
        return self._calculators[name]

    def contains(self, name: str) -> bool:
        """Return True if the feature name is registered."""
        return name in self._calculators

    def list(self) -> list[FeatureDefinition]:
        """Return definitions of all registered features sorted deterministically by name."""
        return [self._calculators[name].definition for name in sorted(self._calculators.keys())]

    def unregister(self, name: str) -> None:
        """
        Remove a feature calculator by name.

        Raises:
            FeatureNotFoundError: if the feature is not registered.
        """
        if name not in self._calculators:
            raise FeatureNotFoundError(name)
        del self._calculators[name]

    def __len__(self) -> int:
        return len(self._calculators)

    @property
    def calculator_count(self) -> int:
        """Number of currently registered calculators."""
        return len(self._calculators)


def get_default_registry(annualization_factor: float = 252.0) -> FeatureRegistry:
    """
    Construct and populate a FeatureRegistry containing the complete baseline feature set.
    """
    registry = FeatureRegistry()

    # Returns
    registry.register(SimpleReturnCalculator(1))
    registry.register(SimpleReturnCalculator(5))
    registry.register(SimpleReturnCalculator(10))
    registry.register(SimpleReturnCalculator(20))

    # Volatility
    registry.register(RollingVolatilityCalculator(10, annualized=False))
    registry.register(RollingVolatilityCalculator(20, annualized=False))
    registry.register(
        RollingVolatilityCalculator(
            20,
            annualized=True,
            annualization_factor=annualization_factor,
        )
    )

    # Momentum
    registry.register(MomentumCalculator(10))
    registry.register(MomentumCalculator(20))

    # Trend
    registry.register(SMARatioCalculator(10))
    registry.register(SMARatioCalculator(20))
    registry.register(EMARatioCalculator(20))

    # Volume
    registry.register(VolumeChangeCalculator())
    registry.register(VolumeRatioCalculator(20))

    # Range
    registry.register(HighLowRangeCalculator())
    registry.register(TrueRangeCalculator())
    registry.register(NormalizedTrueRangeCalculator())

    return registry
