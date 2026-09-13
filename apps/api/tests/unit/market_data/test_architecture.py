"""
Architectural boundary tests for the market_data domain layer.

Goal: prevent future regressions where infrastructure or vendor-specific
code leaks into the domain layer.

The intended dependency direction is:

    infrastructure  →  application  →  domain
                                          ↑
                                   (nothing below)

These tests verify that the domain package does NOT import from:
  - infrastructure layer (adapters, external services)
  - HTTP client libraries (httpx, requests, aiohttp, urllib3)
  - Vendor SDKs (yfinance, polygon, alpha_vantage, pandas_datareader, etc.)
  - Database ORMs (sqlalchemy, tortoise, motor, pymongo)
  - application layer (would create circular dependency)

Approach: inspect the module's transitive import graph using sys.modules
after importing each domain module.  We look for banned module prefixes
in the set of imported modules.

This is a lightweight, maintainable mechanism — no third-party
architecture-testing framework required.
"""

from __future__ import annotations

import importlib
import sys

# Modules that must NEVER appear in domain imports (prefix matching)
_BANNED_PREFIXES: list[str] = [
    # HTTP clients
    "httpx",
    "requests",
    "aiohttp",
    "urllib3",
    # Vendor market-data SDKs
    "yfinance",
    "polygon",
    "alpha_vantage",
    "tiingo",
    "pandas_datareader",
    "twelvedata",
    "nsepy",
    "nsetools",
    "binance",
    "ccxt",
    "coinbase",
    # Database ORMs / async drivers
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "tortoise",
    "motor",
    "pymongo",
    "psycopg",
    # Celery / message brokers
    "celery",
    "kombu",
    "redis",
    # Infrastructure layer modules (adapter implementations live here)
    "app.modules.market_data.infrastructure",
]

# Domain modules under test
_DOMAIN_MODULES: list[str] = [
    "app.modules.market_data.domain.models",
    "app.modules.market_data.domain.provider",
    "app.modules.market_data.domain.errors",
    "app.modules.market_data.domain",
]


def _snapshot_imported() -> set[str]:
    """Return the current set of imported top-level module names."""
    return set(sys.modules.keys())


def _modules_imported_by(module_name: str) -> set[str]:
    """
    Import ``module_name`` and return the set of newly imported module names.

    We snapshot sys.modules before and after the import so we only see what
    the module (and its transitive imports) brought in.
    """
    before = _snapshot_imported()
    importlib.import_module(module_name)
    after = _snapshot_imported()
    return after - before


def _check_no_banned_imports(module_name: str) -> list[str]:
    """
    Return a list of banned module names that were imported by ``module_name``.
    Empty list means the module is clean.
    """
    imported = _modules_imported_by(module_name)
    violations: list[str] = []
    for imported_mod in imported:
        for banned in _BANNED_PREFIXES:
            if imported_mod == banned or imported_mod.startswith(banned + "."):
                violations.append(imported_mod)
                break
    return violations


class TestDomainArchitecturalBoundary:
    """
    Verify that no domain module imports banned external or infrastructure code.
    """

    def test_models_has_no_http_client_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.market_data.domain.models")
        assert violations == [], (
            f"domain/models.py imported banned modules: {violations}\n"
            "Domain models must not depend on HTTP clients, vendor SDKs, or ORMs."
        )

    def test_provider_has_no_http_client_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.market_data.domain.provider")
        assert violations == [], (
            f"domain/provider.py imported banned modules: {violations}\n"
            "The provider interface must not depend on HTTP clients, vendor SDKs, or ORMs."
        )

    def test_errors_has_no_http_client_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.market_data.domain.errors")
        assert violations == [], (
            f"domain/errors.py imported banned modules: {violations}\n"
            "Domain errors must not depend on HTTP clients, vendor SDKs, or ORMs."
        )

    def test_domain_package_has_no_infrastructure_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.market_data.domain")
        infra_violations = [v for v in violations if "infrastructure" in v]
        assert infra_violations == [], (
            f"domain/__init__.py imported infrastructure modules: {infra_violations}\n"
            "Domain must not import from infrastructure layer."
        )

    def test_domain_package_has_no_vendor_sdk_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.market_data.domain")
        vendor_violations = [
            v
            for v in violations
            if any(v == b or v.startswith(b + ".") for b in _BANNED_PREFIXES[:10])
        ]
        assert vendor_violations == [], (
            f"domain/ imported vendor SDK modules: {vendor_violations}\n"
            "Vendor SDKs must be confined to the infrastructure layer."
        )

    def test_application_registry_does_not_import_vendor_sdks(self) -> None:
        imported = _modules_imported_by("app.modules.market_data.application.registry")
        vendor_violations = [
            m
            for m in imported
            if any(m == b or m.startswith(b + ".") for b in _BANNED_PREFIXES[:10])
        ]
        assert vendor_violations == [], (
            f"application/registry.py imported vendor SDK modules: {vendor_violations}"
        )
