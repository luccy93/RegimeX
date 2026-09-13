"""
RegimeX Feature Engineering — Infrastructure Calculators
========================================================
Exports all concrete feature calculators implementing the domain FeatureCalculator interface.
"""

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

__all__ = [
    "EMARatioCalculator",
    "HighLowRangeCalculator",
    "MomentumCalculator",
    "NormalizedTrueRangeCalculator",
    "RollingVolatilityCalculator",
    "SMARatioCalculator",
    "SimpleReturnCalculator",
    "TrueRangeCalculator",
    "VolumeChangeCalculator",
    "VolumeRatioCalculator",
]
