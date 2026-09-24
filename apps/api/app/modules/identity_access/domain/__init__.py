"""
RegimeX Identity & Access — Domain Layer
========================================
Exports pure domain entities, repository/service protocols, and exception contracts.
"""

from __future__ import annotations

from app.modules.identity_access.domain.authorization import (
    ActiveUserPolicy,
    AuthorizationChecker,
    AuthorizationError,
    AuthorizationPolicy,
)
from app.modules.identity_access.domain.errors import (
    AuthenticationRequiredError,
    DuplicateEmailError,
    ExpiredTokenError,
    IdentityAccessError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordError,
    InvalidTokenError,
)
from app.modules.identity_access.domain.models import TokenClaims, User
from app.modules.identity_access.domain.password import PasswordHasher
from app.modules.identity_access.domain.repository import UserRepository
from app.modules.identity_access.domain.services import (
    MIN_PASSWORD_LENGTH,
    normalize_email,
    validate_password_strength,
)
from app.modules.identity_access.domain.token import TokenService

__all__ = [
    "MIN_PASSWORD_LENGTH",
    "ActiveUserPolicy",
    "AuthenticationRequiredError",
    "AuthorizationChecker",
    "AuthorizationError",
    "AuthorizationPolicy",
    "DuplicateEmailError",
    "ExpiredTokenError",
    "IdentityAccessError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidEmailError",
    "InvalidPasswordError",
    "InvalidTokenError",
    "PasswordHasher",
    "TokenClaims",
    "TokenService",
    "User",
    "UserRepository",
    "normalize_email",
    "validate_password_strength",
]
