"""
RegimeX Market Data — Domain Package
=====================================
Public re-exports for the market_data domain layer.

Import surface is intentionally minimal.  Downstream modules should
import from this package, not from individual sub-modules, to keep
the internal layout flexible.
"""

from app.modules.market_data.domain.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderDataError,
    ProviderError,
    ProviderRateLimitError,
    ProviderSymbolNotFoundError,
    ProviderUnavailableError,
    StorageConnectionError,
    StorageError,
    StorageIntegrityError,
    StorageNotFoundError,
)
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from app.modules.market_data.domain.repository import MarketDataRepository

__all__ = [
    # Enums
    "AssetClass",
    "AdjustmentPolicy",
    "DataInterval",
    # Models
    "Instrument",
    "OHLCVRecord",
    "MarketDataQuery",
    "MarketDataResult",
    # Provider interface
    "MarketDataProvider",
    "ProviderCapabilities",
    "ProviderMetadata",
    # Repository interface
    "MarketDataRepository",
    # Errors
    "ProviderError",
    "ProviderConfigurationError",
    "ProviderUnavailableError",
    "ProviderRateLimitError",
    "ProviderAuthenticationError",
    "ProviderDataError",
    "ProviderSymbolNotFoundError",
    "StorageError",
    "StorageConnectionError",
    "StorageIntegrityError",
    "StorageNotFoundError",
]
