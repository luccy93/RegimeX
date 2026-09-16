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

    def test_statistics_engine_has_zero_imputation_patterns(self) -> None:
        """
        Regression guard: feature statistics implementation must never use fillna(0),
        nan_to_num with nan=0, or equivalent zero-imputation techniques.
        """
        stats_file = (
            Path(__file__).parents[3]
            / "app"
            / "modules"
            / "regime_intelligence"
            / "infrastructure"
            / "analytics"
            / "statistics.py"
        )
        code_str = stats_file.read_text(encoding="utf-8")
        tree = ast.parse(code_str)

        # 1. AST check for function/method calls to fillna or nan_to_num
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "fillna":
                    raise AssertionError("Forbidden call to 'fillna' detected in statistics.py.")
                if isinstance(node.func, ast.Name) and node.func.id in ("nan_to_num", "fillna"):
                    raise AssertionError(
                        f"Forbidden call to '{node.func.id}' detected in statistics.py."
                    )

        # 2. String pattern checks in executable statements
        forbidden_patterns = [
            "fillna(0)",
            "fillna(0.0)",
            "nan_to_num",
            "= 0 if v is None",
            "= 0.0 if v is None",
            "= 0 if math.isnan",
            "= 0.0 if math.isnan",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in code_str, (
                f"Forbidden zero-imputation pattern '{pattern}' detected in {stats_file.name}."
            )

    def test_v09_has_no_future_scope_classes(self) -> None:
        """
        Verify V09 codebase contains zero implementations or references to forbidden
        future concepts (V10 GMM/HMM, V11 Ensemble, V12 Transition, V13 Risk,
        V14 Backtesting, V21 AI).
        """
        module_dir = Path(__file__).parents[3] / "app" / "modules" / "regime_intelligence"
        forbidden_classes = {
            "TransitionMatrix",
            "MarkovChain",
            "TransitionProbability",
            "GMMRegimeDetector",
            "HMMRegimeDetector",
            "EnsembleRegimeDetector",
            "VaR",
            "BacktestEngine",
            "TradingSignal",
            "BuySignal",
            "SellSignal",
        }

        for py_file in module_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    assert node.name not in forbidden_classes, (
                        f"Forbidden class '{node.name}' defined in '{py_file.name}'."
                    )

    def test_no_economic_overclaiming_labels(self) -> None:
        """
        Ensure V09 code does not generate subjective or overclaiming economic labels
        ('bull', 'bear', 'crash', 'buy', 'sell', 'safe', 'unsafe').
        """
        module_dir = Path(__file__).parents[3] / "app" / "modules" / "regime_intelligence"
        overclaiming_tokens = {
            "bull_market",
            "bear_market",
            "market_crash",
            "buy_signal",
            "sell_signal",
        }

        for py_file in module_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8").lower()
            for token in overclaiming_tokens:
                assert token not in content, (
                    f"Forbidden overclaiming economic token '{token}' found in '{py_file.name}'."
                )
