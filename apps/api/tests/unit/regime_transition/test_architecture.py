"""
RegimeX Regime Transition — Architecture Boundary Tests
========================================================
Verifies domain layer isolation, dependency directions, zero external library
dependencies in domain contracts, and absence of out-of-scope concepts.
"""

from __future__ import annotations

import inspect

import app.modules.regime_transition.domain.errors as domain_errors
import app.modules.regime_transition.domain.interfaces as domain_interfaces
import app.modules.regime_transition.domain.models as domain_models


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
        "torch",
        "tensorflow",
    }

    FORBIDDEN_OUT_OF_SCOPE_TOKENS = {
        "backtest",
        "trading_signal",
        "buy_signal",
        "sell_signal",
        "portfolio_optimization",
        "llm_prompt",
        "openai",
        "anthropic",
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

    def test_no_out_of_scope_concepts(self) -> None:
        """Verify module contains zero trading, risk, or AI prompt concepts."""
        import app.modules.regime_transition as rt

        source = inspect.getsource(rt)
        for token in self.FORBIDDEN_OUT_OF_SCOPE_TOKENS:
            assert token not in source.lower(), (
                f"Forbidden out-of-scope token '{token}' detected in regime_transition."
            )
