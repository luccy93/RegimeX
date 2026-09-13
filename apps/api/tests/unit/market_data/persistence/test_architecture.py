"""
Architectural boundary tests for market data persistence layer.
==============================================================
Enforces strict domain independence:
- Domain repository abstraction must not import SQLAlchemy or database drivers.
- Domain package must not import persistence infrastructure models.
"""

from __future__ import annotations

import ast
import importlib
import inspect

BANNED_DOMAIN_IMPORTS: frozenset[str] = frozenset(
    [
        "sqlalchemy",
        "alembic",
        "asyncpg",
        "psycopg",
        "sqlite3",
        "aiosqlite",
        "databases",
        "app.core.database",
        "app.modules.market_data.infrastructure",
    ]
)


def _check_no_banned_imports(module_name: str) -> list[str]:
    """Parse module source with AST and detect any forbidden imports."""
    mod = importlib.import_module(module_name)
    source = inspect.getsource(mod)
    tree = ast.parse(source)

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for banned in BANNED_DOMAIN_IMPORTS:
                    if alias.name == banned or alias.name.startswith(f"{banned}."):
                        violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for banned in BANNED_DOMAIN_IMPORTS:
                if node.module == banned or node.module.startswith(f"{banned}."):
                    violations.append(node.module)
    return violations


class TestPersistenceArchitecturalBoundary:
    def test_domain_repository_has_no_database_imports(self) -> None:
        """Domain repository abstraction must be pure Python without DB or ORM imports."""
        violations = _check_no_banned_imports("app.modules.market_data.domain.repository")
        assert violations == [], f"MarketDataRepository imported forbidden modules: {violations}"

    def test_domain_package_has_no_persistence_imports(self) -> None:
        """Domain package must not import persistence infrastructure models."""
        violations = _check_no_banned_imports("app.modules.market_data.domain")
        persistence_violations = [v for v in violations if "persistence" in v]
        assert persistence_violations == [], (
            f"Domain package imported persistence: {persistence_violations}"
        )
