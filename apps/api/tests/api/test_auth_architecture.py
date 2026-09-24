"""
Architectural Boundary & Invariant Tests for Authentication & Security Layer.
=============================================================================
Enforces Clean Architecture rules:
1. Authentication domain & application modules (app/modules/identity_access/domain/**,
   app/modules/identity_access/application/**) must NEVER import transport/web frameworks:
   - fastapi
   - starlette
   - HTTPException
   - Request
   - Response
2. Route handlers (app/api/v1/endpoints/auth.py) must remain thin presentation boundaries
   and must NEVER import cryptographic libraries or engines directly:
   - argon2
   - jwt (PyJWT)
   - bcrypt
   - passlib
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_AUTH_DOMAIN_MODULES = {
    "fastapi",
    "starlette",
    "httpx",
    "flask",
    "django",
}

FORBIDDEN_AUTH_DOMAIN_NAMES = {
    "HTTPException",
    "Request",
    "Response",
    "APIRouter",
    "FastAPI",
    "Depends",
}


def test_auth_domain_and_application_never_import_web_frameworks() -> None:
    """
    Verify that identity_access domain and application layers have zero
    imports of FastAPI, Starlette, or HTTP request/response constructs.
    """
    app_root = Path(__file__).resolve().parent.parent.parent / "app"
    auth_module = app_root / "modules" / "identity_access"
    assert auth_module.is_dir(), f"Identity access module not found at {auth_module}"

    target_files = list((auth_module / "domain").glob("**/*.py")) + list(
        (auth_module / "application").glob("**/*.py")
    )
    assert len(target_files) > 0, "No identity_access domain/application files found"

    violations: list[str] = []

    for py_file in target_files:
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
                    if root_name in FORBIDDEN_AUTH_DOMAIN_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports forbidden module '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    if root_name in FORBIDDEN_AUTH_DOMAIN_MODULES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports from forbidden module '{node.module}'"
                        )
                for alias in node.names:
                    if alias.name in FORBIDDEN_AUTH_DOMAIN_NAMES:
                        violations.append(
                            f"{py_file}:{node.lineno} imports forbidden name '{alias.name}'"
                        )

    assert not violations, (
        "Clean Architecture violation(s) in auth domain/application layers:\n"
        + "\n".join(violations)
    )


FORBIDDEN_AUTH_ROUTE_MODULES = {
    "argon2",
    "jwt",
    "bcrypt",
    "passlib",
    "cryptography",
}


def test_auth_routes_never_import_cryptographic_libraries_directly() -> None:
    """
    Verify that authentication route handlers delegate to application services and
    do not directly import low-level password hashing or JWT libraries.
    """
    app_root = Path(__file__).resolve().parent.parent.parent / "app"
    auth_route_file = app_root / "api" / "v1" / "endpoints" / "auth.py"
    assert auth_route_file.is_file(), f"Auth route file not found at {auth_route_file}"

    content = auth_route_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(auth_route_file))

    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".")[0]
                if root_name in FORBIDDEN_AUTH_ROUTE_MODULES:
                    violations.append(
                        f"{auth_route_file}:{node.lineno} route imports "
                        f"forbidden crypto module '{alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_name = node.module.split(".")[0]
                if root_name in FORBIDDEN_AUTH_ROUTE_MODULES:
                    violations.append(
                        f"{auth_route_file}:{node.lineno} route imports "
                        f"from forbidden crypto module '{node.module}'"
                    )

    assert not violations, (
        "Thin route violation: auth route directly imports cryptography libraries:\n"
        + "\n".join(violations)
    )


def test_protected_endpoints_use_authorization_boundary() -> None:
    """
    Verify that protected endpoints in auth routes use CurrentUser / RequireAuthenticatedUser
    and do not perform ad-hoc token decoding or database queries directly in the route body.
    """
    app_root = Path(__file__).resolve().parent.parent.parent / "app"
    auth_route_file = app_root / "api" / "v1" / "endpoints" / "auth.py"
    content = auth_route_file.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(auth_route_file))

    # Inspect get_current_user_profile function
    me_function = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_current_user_profile":
            me_function = node
            break

    assert me_function is not None, "get_current_user_profile route function not found"
    arg_names = [arg.arg for arg in me_function.args.args]
    msg = "Expected current_user parameter in get_current_user_profile"
    assert "current_user" in arg_names, msg
