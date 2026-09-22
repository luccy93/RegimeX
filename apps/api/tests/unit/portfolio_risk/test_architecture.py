"""
RegimeX Portfolio Risk — Architecture Boundary Tests
====================================================
Verifies that the portfolio_risk domain layer adheres strictly to clean architecture principles:
- Zero imports of external machine learning packages (scikit-learn, PyTorch, etc.).
- Zero imports of database / ORM packages (SQLAlchemy, Alembic, etc.).
- Zero imports of web / presentation packages (FastAPI, Starlette, etc.).
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
]


class TestArchitectureBoundaries:
    def test_domain_layer_has_zero_forbidden_imports(self) -> None:
        """Verify portfolio_risk domain layer does not import forbidden libraries."""
        # Unload any cached domain modules to inspect fresh imports
        domain_modules = [
            "app.modules.portfolio_risk.domain.models",
            "app.modules.portfolio_risk.domain.errors",
            "app.modules.portfolio_risk.domain.interfaces",
            "app.modules.portfolio_risk.domain",
        ]
        for mod in domain_modules:
            if mod in sys.modules:
                del sys.modules[mod]

        for mod_name in domain_modules:
            module = importlib.import_module(mod_name)
            for forbidden in FORBIDDEN_PACKAGES:
                assert not any(
                    m == forbidden or m.startswith(f"{forbidden}.")
                    for m in getattr(module, "__dict__", {})
                ), f"Domain module {mod_name} illegally imports {forbidden}."
