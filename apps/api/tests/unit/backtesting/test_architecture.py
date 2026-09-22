"""
RegimeX Backtesting — Architecture Boundary Tests
=================================================
Verifies that the backtesting module adheres strictly to clean architecture principles:
- Zero imports of external machine learning packages (scikit-learn, PyTorch, etc.).
- Zero imports of database / ORM packages (SQLAlchemy, Alembic, etc.).
- Zero imports of web / presentation packages (FastAPI, Starlette, etc.).
- Zero imports of external broker or network clients.
"""

from __future__ import annotations

import importlib
import sys

FORBIDDEN_PACKAGES = [
    "sklearn",
    "torch",
    "torchvision",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "scipy",
    "httpx",
    "requests",
]


class TestBacktestingArchitectureBoundaries:
    def test_backtesting_layers_have_zero_forbidden_imports(self) -> None:
        """Verify backtesting domain and infrastructure layers do not import forbidden libraries."""
        backtest_modules = [
            "app.modules.backtesting.domain.models",
            "app.modules.backtesting.domain.errors",
            "app.modules.backtesting.domain.interfaces",
            "app.modules.backtesting.domain",
            "app.modules.backtesting.infrastructure.execution",
            "app.modules.backtesting.infrastructure.portfolio",
            "app.modules.backtesting.infrastructure.engine",
            "app.modules.backtesting.infrastructure",
            "app.modules.backtesting",
        ]
        for mod in backtest_modules:
            if mod in sys.modules:
                del sys.modules[mod]

        for mod_name in backtest_modules:
            module = importlib.import_module(mod_name)
            for forbidden in FORBIDDEN_PACKAGES:
                assert not any(
                    m == forbidden or m.startswith(f"{forbidden}.")
                    for m in getattr(module, "__dict__", {})
                ), f"Backtesting module {mod_name} illegally imports {forbidden}."
