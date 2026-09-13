"""
RegimeX Market Data — Provider Registry
=========================================
A lightweight, in-process registry for ``MarketDataProvider`` implementations.

Design goals:
- Register provider instances by their stable ``provider_id``.
- Retrieve a provider by id with clear error messages.
- Prevent accidental duplicate registration.
- Support dependency injection (callers supply the registry instance).
- Remain testable in isolation — no global side-effects on import.

What this is NOT:
- A general service locator.  Only market-data providers are stored here.
- A persistent registry.  Providers are registered at application startup
  and held in memory for the process lifetime.
- Thread-safe beyond Python's GIL guarantees.  Registration is expected to
  happen at startup, not concurrently.

Module-level singleton:
  A ``default_registry`` is provided for the main application.  Tests and
  alternative application factories should construct their own
  ``ProviderRegistry()`` instance and inject it via FastAPI dependencies.
"""

from __future__ import annotations

from app.core.errors import ConflictError, NotFoundError
from app.modules.market_data.domain.provider import MarketDataProvider


class ProviderRegistry:
    """
    Registry that maps provider identifiers to ``MarketDataProvider`` instances.

    Usage::

        registry = ProviderRegistry()
        registry.register(my_provider)
        provider = registry.get("my_provider_id")

    The registry is injected into application services via FastAPI's dependency
    injection system.  See ``app/core/dependencies.py`` for the binding.
    """

    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: MarketDataProvider) -> None:
        """
        Register a provider instance.

        Args:
            provider: A concrete ``MarketDataProvider`` implementation.

        Raises:
            ConflictError: If a provider with the same ``provider_id`` is
                           already registered.  Duplicate registration is
                           almost always a programming error (e.g. an adapter
                           registered twice during startup).
        """
        pid = provider.provider_id
        if pid in self._providers:
            raise ConflictError(
                f"A provider with id {pid!r} is already registered.  "
                "Each provider_id must be unique within a registry instance.",
                details={"provider_id": pid},
            )
        self._providers[pid] = provider

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, provider_id: str) -> MarketDataProvider:
        """
        Retrieve a registered provider by its stable identifier.

        Args:
            provider_id: The snake_case provider identifier.

        Returns:
            The registered ``MarketDataProvider`` instance.

        Raises:
            NotFoundError: If no provider with ``provider_id`` is registered.
        """
        if provider_id not in self._providers:
            registered = list(self._providers.keys())
            raise NotFoundError(
                f"No market data provider with id {provider_id!r} is registered.  "
                f"Registered providers: {registered}",
                details={"provider_id": provider_id, "registered": registered},
            )
        return self._providers[provider_id]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_providers(self) -> list[str]:
        """Return a sorted list of all registered provider identifiers."""
        return sorted(self._providers.keys())

    def is_registered(self, provider_id: str) -> bool:
        """Return True if a provider with the given id is registered."""
        return provider_id in self._providers

    def __len__(self) -> int:
        """Number of registered providers."""
        return len(self._providers)

    def __repr__(self) -> str:
        return f"ProviderRegistry(providers={self.list_providers()!r})"


# =============================================================================
# Module-level default registry
# =============================================================================

#: Default ``ProviderRegistry`` for the main application process.
#:
#: Providers are registered here during application startup (lifespan).
#: Tests should construct a fresh ``ProviderRegistry()`` instance to avoid
#: cross-test pollution.
default_registry: ProviderRegistry = ProviderRegistry()
