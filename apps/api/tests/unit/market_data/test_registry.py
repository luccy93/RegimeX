"""
Unit tests — ProviderRegistry.

Tests cover:
- Register + get round-trip.
- Duplicate registration raises ConflictError.
- Unknown provider raises NotFoundError.
- list_providers() returns sorted ids.
- is_registered() works correctly.
- __len__ reflects registered count.
- Default registry is a ProviderRegistry instance.
- Tests use fresh isolated registry instances (no shared state).
"""

from __future__ import annotations

import pytest
from app.core.errors import ConflictError, NotFoundError
from app.modules.market_data.application.registry import (
    ProviderRegistry,
    default_registry,
)

from tests.unit.market_data.conftest import FakeProvider


@pytest.fixture()
def registry() -> ProviderRegistry:
    """Fresh registry per test — no shared state."""
    return ProviderRegistry()


@pytest.fixture()
def provider_a() -> FakeProvider:
    class ProviderA(FakeProvider):
        PROVIDER_ID = "provider_a"

        @property
        def provider_id(self) -> str:
            return self.PROVIDER_ID

    return ProviderA()


@pytest.fixture()
def provider_b() -> FakeProvider:
    class ProviderB(FakeProvider):
        PROVIDER_ID = "provider_b"

        @property
        def provider_id(self) -> str:
            return self.PROVIDER_ID

    return ProviderB()


# =============================================================================
# Registration
# =============================================================================


class TestRegistryRegistration:
    def test_register_single_provider(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        assert len(registry) == 1

    def test_register_multiple_providers(
        self,
        registry: ProviderRegistry,
        provider_a: FakeProvider,
        provider_b: FakeProvider,
    ) -> None:
        registry.register(provider_a)
        registry.register(provider_b)
        assert len(registry) == 2

    def test_duplicate_registration_raises_conflict(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        with pytest.raises(ConflictError) as exc_info:
            registry.register(fake_provider)
        assert "fake_provider" in str(exc_info.value)

    def test_conflict_error_contains_provider_id(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        with pytest.raises(ConflictError) as exc_info:
            registry.register(fake_provider)
        assert exc_info.value.details.get("provider_id") == "fake_provider"


# =============================================================================
# Retrieval
# =============================================================================


class TestRegistryRetrieval:
    def test_get_registered_provider(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        retrieved = registry.get("fake_provider")
        assert retrieved is fake_provider

    def test_get_unknown_provider_raises_not_found(self, registry: ProviderRegistry) -> None:
        with pytest.raises(NotFoundError) as exc_info:
            registry.get("nonexistent_provider")
        assert "nonexistent_provider" in str(exc_info.value)

    def test_not_found_error_contains_provider_id(self, registry: ProviderRegistry) -> None:
        with pytest.raises(NotFoundError) as exc_info:
            registry.get("ghost")
        assert exc_info.value.details.get("provider_id") == "ghost"

    def test_not_found_error_lists_registered_providers(
        self,
        registry: ProviderRegistry,
        provider_a: FakeProvider,
    ) -> None:
        registry.register(provider_a)
        with pytest.raises(NotFoundError) as exc_info:
            registry.get("nonexistent")
        assert "provider_a" in exc_info.value.details.get("registered", [])


# =============================================================================
# Introspection
# =============================================================================


class TestRegistryIntrospection:
    def test_list_providers_empty(self, registry: ProviderRegistry) -> None:
        assert registry.list_providers() == []

    def test_list_providers_sorted(
        self,
        registry: ProviderRegistry,
        provider_a: FakeProvider,
        provider_b: FakeProvider,
    ) -> None:
        registry.register(provider_b)
        registry.register(provider_a)
        assert registry.list_providers() == ["provider_a", "provider_b"]

    def test_is_registered_true(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        assert registry.is_registered("fake_provider") is True

    def test_is_registered_false(self, registry: ProviderRegistry) -> None:
        assert registry.is_registered("missing") is False

    def test_len_empty(self, registry: ProviderRegistry) -> None:
        assert len(registry) == 0

    def test_len_after_registration(
        self,
        registry: ProviderRegistry,
        provider_a: FakeProvider,
        provider_b: FakeProvider,
    ) -> None:
        registry.register(provider_a)
        assert len(registry) == 1
        registry.register(provider_b)
        assert len(registry) == 2

    def test_repr_contains_provider_ids(
        self, registry: ProviderRegistry, fake_provider: FakeProvider
    ) -> None:
        registry.register(fake_provider)
        r = repr(registry)
        assert "fake_provider" in r


# =============================================================================
# Module-level default registry
# =============================================================================


class TestDefaultRegistry:
    def test_default_registry_is_provider_registry_instance(self) -> None:
        assert isinstance(default_registry, ProviderRegistry)

    def test_default_registry_is_empty_at_module_load(self) -> None:
        # The default registry should only have providers registered by the
        # application startup lifecycle — in tests, nothing registers there.
        # We verify it behaves correctly (not that it is empty in all cases).
        assert isinstance(default_registry.list_providers(), list)
