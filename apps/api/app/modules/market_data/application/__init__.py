"""
RegimeX Market Data — Application Package
==========================================
Public re-exports for the market_data application layer.
"""

from app.modules.market_data.application.registry import (
    ProviderRegistry,
    default_registry,
)
from app.modules.market_data.application.service import (
    DEFAULT_BENCHMARK_MARKETS,
    MarketDataService,
)

__all__ = [
    "DEFAULT_BENCHMARK_MARKETS",
    "MarketDataService",
    "ProviderRegistry",
    "default_registry",
]
