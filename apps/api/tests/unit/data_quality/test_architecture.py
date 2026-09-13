"""
Architectural boundary tests for the data_quality domain layer.
Ensures that data_quality.domain does NOT import banned external libraries or infrastructure.
"""

from __future__ import annotations

import importlib
import sys

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
    # Database ORMs / async drivers
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "tortoise",
    "motor",
    # Data manipulation libraries in pure domain
    "pandas",
    # Infrastructure layer
    "app.modules.data_quality.infrastructure",
]

_DOMAIN_MODULES: list[str] = [
    "app.modules.data_quality.domain.models",
    "app.modules.data_quality.domain.calendar",
    "app.modules.data_quality.domain.rules",
    "app.modules.data_quality.domain",
]


def _snapshot_imported() -> set[str]:
    return set(sys.modules.keys())


def _modules_imported_by(module_name: str) -> set[str]:
    before = _snapshot_imported()
    importlib.import_module(module_name)
    after = _snapshot_imported()
    return after - before


def _check_no_banned_imports(module_name: str) -> list[str]:
    imported = _modules_imported_by(module_name)
    violations: list[str] = []
    for imported_mod in imported:
        for banned in _BANNED_PREFIXES:
            if imported_mod == banned or imported_mod.startswith(banned + "."):
                violations.append(imported_mod)
                break
    return violations


class TestDataQualityDomainArchitecturalBoundary:
    def test_domain_models_has_no_banned_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.data_quality.domain.models")
        assert violations == [], f"data_quality.domain.models imported banned modules: {violations}"

    def test_domain_rules_has_no_banned_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.data_quality.domain.rules")
        assert violations == [], f"data_quality.domain.rules imported banned modules: {violations}"

    def test_domain_calendar_has_no_banned_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.data_quality.domain.calendar")
        assert violations == [], (
            f"data_quality.domain.calendar imported banned modules: {violations}"
        )

    def test_domain_package_has_no_infrastructure_imports(self) -> None:
        violations = _check_no_banned_imports("app.modules.data_quality.domain")
        infra_violations = [v for v in violations if "infrastructure" in v]
        assert infra_violations == [], (
            f"data_quality.domain imported infrastructure: {infra_violations}"
        )
