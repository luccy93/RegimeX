"""
RegimeX Identity & Access — Authorization Abstraction & Policies
================================================================
Defines domain abstractions and policy checkers for authorization boundaries.
Maintains a strict architectural separation between Authentication
(identity verification) and Authorization (access-control / permissions).

Architectural Rules:
- Pure Python and framework-independent (zero FastAPI / Starlette imports).
- Reusable across any transport layer.
- Extensible for future role-based (RBAC) and permission-based policies.
"""

from __future__ import annotations

from typing import Protocol

from app.modules.identity_access.application.dto import UserDTO
from app.modules.identity_access.domain.errors import (
    IdentityAccessError,
    InactiveUserError,
)


class AuthorizationError(IdentityAccessError):
    """Base exception for authorization and access-control failures."""

    http_status = 403
    error_code = "FORBIDDEN"

    def __init__(
        self,
        message: str = "Access denied: insufficient permissions.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class AuthorizationPolicy(Protocol):
    """
    Protocol for evaluating whether an authenticated user is authorized.

    Designed for clean extensibility in future volumes without route changes:
    - RolePolicy(allowed_roles={"admin", "analyst"})
    - PermissionPolicy(required_permissions={"read:market_data"})
    - ResourceOwnershipPolicy(...)
    - ScopePolicy(...)
    """

    def check(self, user: UserDTO) -> None:
        """
        Evaluate authorization for the given authenticated user.

        Raises:
            AuthorizationError / InactiveUserError: If authorization check fails.
        """
        ...


class ActiveUserPolicy:
    """
    Default authorization policy:
    Enforces that the authenticated user account is active and not deactivated.
    """

    def check(self, user: UserDTO) -> None:
        if not user.is_active:
            raise InactiveUserError("User account is inactive.")


class AuthorizationChecker:
    """
    Orchestrates authorization evaluation across one or more policies.

    Default configuration enforces active user account policy.
    """

    def __init__(self, policies: list[AuthorizationPolicy] | None = None) -> None:
        self._policies: list[AuthorizationPolicy] = (
            policies if policies is not None else [ActiveUserPolicy()]
        )

    def authorize(self, user: UserDTO) -> None:
        """
        Evaluate all configured policies in sequence against the user.

        Raises:
            IdentityAccessError: If any policy check fails.
        """
        for policy in self._policies:
            policy.check(user)
