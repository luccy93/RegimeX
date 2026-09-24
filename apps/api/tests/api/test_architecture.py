"""
Architectural Boundary & Invariant Tests for RegimeX Platform.
==============================================================
Enforces Clean Architecture rules:
1. Domain modules (app/modules/*/domain/**) must NEVER import transport/web frameworks:
   - fastapi
   - starlette
   - HTTPException
   - Request
   - Response
2. Domain modules must remain pure Python and framework-independent.
3. API endpoints must reside exclusively under app/api/.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_DOMAIN_MODULES = {
    "fastapi",
    "starlette",
    "httpx",
    "flask",
    "django",
}

FORBIDDEN_DOMAIN_NAMES = {
    "HTTPException",
    "Request",
    "Response",
    "APIRouter",
    "FastAPI",
}


def test_domain_modules_never_import_web_frameworks() -> None:
    """
    Verify that all domain modules across all application modules have zero
    imports of FastAPI, Starlette, or HTTP request/response constructs.
    """
    app_root = Path(__file__).resolve().parent.parent.parent / "app"
    modules_dir = app_root / "modules"
    assert modules_dir.is_dir(), f"Modules directory not found at {modules_dir}"

    domain_files = list(modules_dir.glob("*/domain/**/*.py"))
    assert len(domain_files) > 0, "No domain files found to inspect"

    violations: list[str] = []

    for py_file in domain_files:
        content = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"{py_file}: Syntax error during AST parse: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name in FORBIDDEN_DOMAIN_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports forbidden module '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    if root_name in FORBIDDEN_DOMAIN_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports from forbidden module '{node.module}'"
                        )
                for alias in node.names:
                    if alias.name in FORBIDDEN_DOMAIN_NAMES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports forbidden name '{alias.name}'"
                        )

    assert not violations, (
        "Clean Architecture violation(s) detected in domain layers:\n" + "\n".join(violations)
    )


FORBIDDEN_ROUTE_MODULES = {
    "sklearn",
    "scipy",
    "numpy",
    "torch",
}

FORBIDDEN_ROUTE_NAMES = {
    "KMeansRegimeDetector",
    "GaussianMixtureRegimeDetector",
    "GaussianHMMRegimeDetector",
    "PortfolioRiskEngine",
    "BacktestingEngine",
}


def test_routes_never_import_heavy_ml_or_engines() -> None:
    """
    Verify that API route handlers remain thin orchestration boundaries and
    do not directly import low-level ML libraries, detectors, or execution engines.
    """
    app_root = Path(__file__).resolve().parent.parent.parent / "app"
    endpoints_dir = app_root / "api" / "v1" / "endpoints"
    assert endpoints_dir.is_dir(), f"Endpoints directory not found at {endpoints_dir}"

    route_files = list(endpoints_dir.glob("**/*.py"))
    assert len(route_files) > 0, "No endpoint route files found"

    violations: list[str] = []

    for py_file in route_files:
        content = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"{py_file}: Syntax error during AST parse: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    if root_name in FORBIDDEN_ROUTE_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} route imports forbidden module '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    if root_name in FORBIDDEN_ROUTE_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} route imports "
                            f"from forbidden module '{node.module}'"
                        )
                for alias in node.names:
                    if alias.name in FORBIDDEN_ROUTE_NAMES:
                        violations.append(
                            f"{py_file}:{node.lineno} route imports "
                            f"forbidden engine/model '{alias.name}'"
                        )

    assert not violations, "Thin route violation(s) detected in endpoint layer:\n" + "\n".join(
        violations
    )
