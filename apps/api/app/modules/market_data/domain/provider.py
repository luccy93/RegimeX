"""
RegimeX Market Data — Provider Interface & Capability Model
============================================================
This module defines the abstract ``MarketDataProvider`` interface and the
associated capability/metadata models.

Design decisions — async interface:
  The entire RegimeX backend is built on FastAPI (async I/O) and will use
  Celery workers for background ingestion.  All provider methods that perform
  I/O (HTTP requests to vendor APIs, file reads for local flat-file providers)
  MUST be ``async``.  This prevents any blocking I/O from reaching the event
  loop in FastAPI handlers.

  Synchronous adapters (e.g. libraries that do not support async) must wrap
  their I/O in ``asyncio.to_thread()`` inside their ``async`` adapter method
  implementations — never here in the base interface.

Provider isolation:
  This file is pure domain — no HTTP, no database, no vendor SDK imports.
  Only standard library and pydantic are allowed here.

Architectural position: ``domain/`` — no imports from infrastructure or
  application layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated

from pydantic import BaseModel, Field

from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
)

# =============================================================================
# Provider Capability Model
# =============================================================================


class ProviderCapabilities(BaseModel):
    """
    Declares the operational capabilities of a specific provider adapter.

    The capability model allows the platform to make routing decisions
    (e.g. "which provider supports intraday BTC data?") without inspecting
    adapter internals.  All fields are optional/defaulted to conservative
    values so that minimally capable adapters can be registered safely.

    Capability differences between providers are explicit and discoverable
    through the registry — no hard-coded per-provider logic in the domain.
    """

    model_config = {"frozen": True}

    supported_asset_classes: frozenset[AssetClass] = Field(
        default=frozenset(),
        description="Set of asset classes this provider can serve.",
    )
    supported_intervals: frozenset[DataInterval] = Field(
        default=frozenset(),
        description="Set of data intervals this provider can serve.",
    )
    supported_exchanges: frozenset[str] = Field(
        default=frozenset(),
        description="Set of exchange/market identifiers this provider covers.",
    )
    supported_adjustment_policies: frozenset[AdjustmentPolicy] = Field(
        default=frozenset({AdjustmentPolicy.RAW}),
        description="Adjustment policies supported by this provider.",
    )
    supports_intraday: bool = Field(
        default=False,
        description="True when the provider can serve sub-daily bars.",
    )
    supports_symbol_search: bool = Field(
        default=False,
        description="True when the provider's get_supported_symbols() returns real results.",
    )
    max_history_days: int | None = Field(
        default=None,
        description=(
            "Maximum historical depth in calendar days.  None means the provider "
            "does not declare a cap (but may still have one in practice)."
        ),
    )
    rate_limit_per_minute: int | None = Field(
        default=None,
        description="Declared API rate limit in requests per minute.  None = unknown.",
    )


# =============================================================================
# Provider Metadata Model
# =============================================================================


class ProviderMetadata(BaseModel):
    """
    Identifies a provider adapter and exposes its self-declared capabilities.

    The platform uses this for provider discovery without coupling business
    logic to any concrete adapter class.
    """

    model_config = {"frozen": True}

    provider_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            pattern=r"^[a-z][a-z0-9_]*$",
            description=(
                "Stable snake_case identifier for this provider.  "
                "Must be unique within the registry.  "
                "Examples: 'yahoo_finance', 'alpha_vantage', 'fake_provider'."
            ),
        ),
    ]
    display_name: Annotated[str, Field(min_length=1, max_length=200)]
    version: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Semantic version of the adapter implementation (e.g. '1.0.0').",
        ),
    ]
    capabilities: ProviderCapabilities


# =============================================================================
# Abstract Provider Interface
# =============================================================================


class MarketDataProvider(ABC):
    """
    Abstract base class for all RegimeX market data provider adapters.

    All concrete providers (future) must implement this interface.  The
    rest of the platform interacts exclusively with this abstraction —
    never with vendor-specific adapter classes directly.

    Contract guarantees (all methods):
    - Methods that perform I/O are ``async``; adapters may use
      ``asyncio.to_thread()`` to wrap synchronous vendor SDKs.
    - Vendor-specific exceptions MUST be caught at the adapter boundary and
      translated into ``ProviderError`` subclasses (see ``errors.py``).
    - No vendor-specific types, raw HTTP responses, or SDK objects must
      leak into return values.

    Extension guide (see V05/MARKET_DATA_PROVIDER_ARCHITECTURE.md):
      class MyProvider(MarketDataProvider):
          async def metadata(self) -> ProviderMetadata: ...
          async def capabilities(self) -> ProviderCapabilities: ...
          async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult: ...
          async def supports(self, instrument: Instrument) -> bool: ...
          async def get_supported_symbols(
              self, asset_class: AssetClass | None = None
          ) -> list[Instrument]: ...
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """
        Stable snake_case identifier for this provider.

        Must match ``ProviderMetadata.provider_id``.  Used as the registry key.
        """
        ...

    # ------------------------------------------------------------------
    # Discovery / capability introspection
    # ------------------------------------------------------------------

    @abstractmethod
    async def metadata(self) -> ProviderMetadata:
        """
        Return identification metadata for this provider adapter.

        The registry calls this on startup to index the provider's capabilities.
        Implementations should return a constant or cheaply computed object —
        this method must not perform network I/O.
        """
        ...

    @abstractmethod
    async def capabilities(self) -> ProviderCapabilities:
        """
        Return the capability declaration for this provider.

        Must be consistent with the ``capabilities`` embedded in ``metadata()``.
        May be derived from the same constant object.
        """
        ...

    @abstractmethod
    async def supports(self, instrument: Instrument) -> bool:
        """
        Return True if this provider can supply data for the given instrument.

        Implementations should check against ``capabilities()`` and any
        provider-specific symbol catalogue.  This method should avoid
        making live API calls if possible; prefer checking a local index.
        """
        ...

    @abstractmethod
    async def get_supported_symbols(
        self,
        asset_class: AssetClass | None = None,
    ) -> list[Instrument]:
        """
        Return the list of instruments discoverable from this provider.

        If ``asset_class`` is provided, filter to that class only.
        Providers where ``capabilities().supports_symbol_search is False``
        should return an empty list.

        Raises:
            ProviderError: If the provider is unavailable or the search fails.
        """
        ...

    # ------------------------------------------------------------------
    # Data retrieval
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        """
        Fetch historical OHLCV bars satisfying the given query.

        Contract:
        - Records must be sorted in ascending chronological order.
        - Records must not fall outside [query.start, query.end].
        - All vendor-specific errors must be translated into the
          ``ProviderError`` hierarchy (see ``errors.py``).
        - The returned ``MarketDataResult.provider_id`` must equal
          ``self.provider_id``.

        Args:
            query: The canonical market data query.

        Returns:
            A ``MarketDataResult`` containing zero or more OHLCV records.

        Raises:
            ProviderUnavailableError: Provider endpoint unreachable.
            ProviderAuthenticationError: Credentials missing or invalid.
            ProviderRateLimitError: Provider rate limit exceeded.
            ProviderSymbolNotFoundError: Instrument not found in provider.
            ProviderDataError: Provider returned malformed or unexpected data.
            ProviderConfigurationError: Adapter is misconfigured.
        """
        ...
