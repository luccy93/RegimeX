"""
Unit Tests — Regime Intelligence Architectural Boundaries
=========================================================
Verifies architectural isolation, zero forbidden imports, and separation of concerns
as specified in V03 and V09 Commit 01 requirements.
"""

from __future__ import annotations

import ast
from pathlib import Path


class TestArchitectureBoundaries:
    """Automated AST checks enforcing strict architectural constraints."""

    def test_domain_layer_has_zero_forbidden_imports(self) -> None:
        """Domain models and errors must not import pandas, numpy, or scikit-learn."""
        domain_dir = (
            Path(__file__).parents[3] / "app" / "modules" / "regime_intelligence" / "domain"
        )
        forbidden = {"pandas", "numpy", "sklearn", "scipy", "statsmodels", "torch"}

        for py_file in domain_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pkg = alias.name.split(".")[0]
                        assert pkg not in forbidden, (
                            f"Domain file '{py_file.name}' imports forbidden package '{pkg}'."
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    pkg = node.module.split(".")[0]
                    assert pkg not in forbidden, (
                        f"Domain file '{py_file.name}' imports from forbidden package '{pkg}'."
                    )

    def test_application_layer_has_zero_ml_training_imports(self) -> None:
        """Application service must not import scikit-learn internals or trainers."""
        app_dir = (
            Path(__file__).parents[3] / "app" / "modules" / "regime_intelligence" / "application"
        )
        forbidden = {"sklearn", "hmmlearn"}

        for py_file in app_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pkg = alias.name.split(".")[0]
                        assert pkg not in forbidden, (
                            f"Application file '{py_file.name}' imports forbidden package '{pkg}'."
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    pkg = node.module.split(".")[0]
                    assert pkg not in forbidden, (
                        f"Application file '{py_file.name}' imports from forbidden package '{pkg}'."
                    )

    def test_v09_has_no_transition_matrix_or_markov_classes(self) -> None:
        """Commit 01 strictly excludes transition matrices and Markov engines."""
        module_dir = Path(__file__).parents[3] / "app" / "modules" / "regime_intelligence"
        forbidden_terms = {
            "transition_matrix",
            "markov_chain",
            "transition_probability",
            "TransitionMatrix",
        }

        for py_file in module_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for term in forbidden_terms:
                assert term not in content, (
                    f"File '{py_file.name}' contains forbidden term '{term}'. "
                    "Transition modeling is strictly reserved for future volumes."
                )
