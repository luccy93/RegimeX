"""
RegimeX Feature Engineering — Architecture Boundary Tests
=========================================================
Verifies domain layer isolation and dependency direction rules.
"""

from __future__ import annotations

import inspect

import app.modules.feature_engineering.domain.errors as domain_errors
import app.modules.feature_engineering.domain.feature_set as domain_feature_set
import app.modules.feature_engineering.domain.feature_spec as domain_feature_spec
import app.modules.feature_engineering.domain.interfaces as domain_interfaces
import app.modules.feature_engineering.domain.models as domain_models


class TestArchitectureBoundaries:
    DOMAIN_MODULES = [
        domain_models,
        domain_feature_spec,
        domain_feature_set,
        domain_errors,
        domain_interfaces,
    ]

    FORBIDDEN_DOMAIN_IMPORTS = {
        "pandas",
        "numpy",
        "scipy",
        "sklearn",
        "sqlalchemy",
        "alembic",
        "fastapi",
        "httpx",
        "celery",
        "redis",
    }

    def test_domain_layer_has_zero_forbidden_imports(self):
        for mod in self.DOMAIN_MODULES:
            source = inspect.getsource(mod)
            for forbidden in self.FORBIDDEN_DOMAIN_IMPORTS:
                assert f"import {forbidden}" not in source, (
                    f"Forbidden import '{forbidden}' found in domain module '{mod.__name__}'"
                )
                assert f"from {forbidden}" not in source, (
                    f"Forbidden import '{forbidden}' found in domain module '{mod.__name__}'"
                )
