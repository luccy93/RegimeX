"""
RegimeX Identity & Access Module
================================
Provides secure user authentication, password management, token operations,
and identity persistence.
"""

from __future__ import annotations

from app.modules.identity_access.application import (
    AuthenticationService,
    LoginResultDTO,
    UserDTO,
)
from app.modules.identity_access.domain import (
    AuthenticationRequiredError,
    DuplicateEmailError,
    ExpiredTokenError,
    IdentityAccessError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordError,
    InvalidTokenError,
    PasswordHasher,
    TokenClaims,
    TokenService,
    User,
    UserRepository,
    normalize_email,
    validate_password_strength,
)
from app.modules.identity_access.infrastructure import (
    Argon2PasswordHasher,
    JwtTokenService,
    SQLAlchemyUserRepository,
    UserModel,
)

__all__ = [
    "Argon2PasswordHasher",
    "AuthenticationRequiredError",
    "AuthenticationService",
    "DuplicateEmailError",
    "ExpiredTokenError",
    "IdentityAccessError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidEmailError",
    "InvalidPasswordError",
    "InvalidTokenError",
    "JwtTokenService",
    "LoginResultDTO",
    "PasswordHasher",
    "SQLAlchemyUserRepository",
    "TokenClaims",
    "TokenService",
    "User",
    "UserDTO",
    "UserModel",
    "UserRepository",
    "normalize_email",
    "validate_password_strength",
]
