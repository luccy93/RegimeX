"""
RegimeX Regime Detection — Architecture Boundary Tests
======================================================
Verifies domain layer isolation, dependency directions, and absence
of premature model or engine components.
"""

from __future__ import annotations

import inspect

import app.modules.regime_detection.domain.errors as domain_errors
import app.modules.regime_detection.domain.interfaces as domain_interfaces
import app.modules.regime_detection.domain.models as domain_models


class TestArchitectureBoundaries:
    DOMAIN_MODULES = [
        domain_models,
        domain_errors,
        domain_interfaces,
    ]

    FORBIDDEN_DOMAIN_IMPORTS = {
        "sklearn",
        "pandas",
        "numpy",
        "scipy",
        "fastapi",
        "httpx",
        "sqlalchemy",
        "alembic",
        "celery",
        "redis",
    }

    FORBIDDEN_FUTURE_MODULES = {
        "hmmlearn",
        "xgboost",
        "lightgbm",
        "torch",
        "tensorflow",
    }

    def test_domain_layer_has_zero_forbidden_imports(self) -> None:
        """Domain layer must not import scikit-learn, numpy, pandas, or external frameworks."""
        for mod in self.DOMAIN_MODULES:
            source = inspect.getsource(mod)
            for forbidden in self.FORBIDDEN_DOMAIN_IMPORTS:
                assert f"import {forbidden}" not in source, (
                    f"Forbidden import '{forbidden}' found in domain module '{mod.__name__}'"
                )
                assert f"from {forbidden}" not in source, (
                    f"Forbidden import '{forbidden}' found in domain module '{mod.__name__}'"
                )

    def test_domain_has_zero_future_ml_libraries(self) -> None:
        """Domain and infrastructure in V08 Commit 01 must not import future ML libraries."""
        for mod in self.DOMAIN_MODULES:
            source = inspect.getsource(mod)
            for future_lib in self.FORBIDDEN_FUTURE_MODULES:
                assert future_lib not in source, (
                    f"Premature library '{future_lib}' referenced in '{mod.__name__}'"
                )

    def test_application_does_not_import_sklearn_internals(self) -> None:
        """Application layer must not directly import scikit-learn modules."""
        import app.modules.regime_detection.application.feature_matrix_builder as fmb
        import app.modules.regime_detection.application.services as srv

        for mod in [fmb, srv]:
            source = inspect.getsource(mod)
            assert "from sklearn" not in source, (
                f"Application module '{mod.__name__}' directly imports from scikit-learn."
            )
            assert "import sklearn" not in source, (
                f"Application module '{mod.__name__}' directly imports scikit-learn."
            )

    def test_no_transition_or_risk_engine_imported(self) -> None:
        """V08 Commit 01 must not import or introduce transition engines or risk engines."""
        import app.modules.regime_detection as rd

        source = inspect.getsource(rd)
        assert "transition" not in source.lower(), "Transition engine referenced in V08 Commit 01."
        assert "risk" not in source.lower(), "Risk engine referenced in V08 Commit 01."
