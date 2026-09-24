"""
RegimeX Identity & Access — Authentication Application Service
==============================================================
Orchestrates user registration, authentication (login), and access-token
validation across domain entities and persistence protocols.

Architectural Boundaries:
- Pure Python; zero imports of FastAPI, Starlette, or HTTP request/response classes.
- Completely framework-independent.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.modules.identity_access.application.dto import LoginResultDTO, UserDTO
from app.modules.identity_access.domain.errors import (
    AuthenticationRequiredError,
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.modules.identity_access.domain.models import User
from app.modules.identity_access.domain.password import PasswordHasher
from app.modules.identity_access.domain.repository import UserRepository
from app.modules.identity_access.domain.services import (
    normalize_email,
    validate_password_strength,
)
from app.modules.identity_access.domain.token import TokenService

logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Application service managing user registration, credential authentication,
    and current-user resolution.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        access_token_expire_minutes: int = 60,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._access_token_expire_minutes = access_token_expire_minutes

        # Pre-compute a dummy hash at initialization for constant-time mitigation
        # when an unknown email is submitted during login.
        self._dummy_hash = self._password_hasher.hash("RegimeX_timing_mitigation_token_2026")

    async def register(self, email: str, password: str) -> UserDTO:
        """
        Register a new user account.

        Steps:
          1. Canonical email normalization.
          2. Password policy validation.
          3. Uniqueness verification.
          4. Memory-hard Argon2id hashing.
          5. Persistent storage.
          6. Return safe public user DTO.

        Raises:
            InvalidEmailError: If the email format is invalid.
            InvalidPasswordError: If the password violates policy.
            DuplicateEmailError: If the email is already registered.
        """
        normalized_email = normalize_email(email)
        validate_password_strength(password)

        existing_user = await self._user_repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise DuplicateEmailError(f"An account with email '{normalized_email}' already exists.")

        password_hash = self._password_hasher.hash(password)
        now = datetime.now(tz=UTC)

        user = User(
            id=uuid.uuid4(),
            email=normalized_email,
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        persisted = await self._user_repository.create(user)
        logger.info("User registered successfully: id=%s", persisted.id)

        return UserDTO(
            id=persisted.id,
            email=persisted.email,
            is_active=persisted.is_active,
            created_at=persisted.created_at,
        )

    async def login(self, email: str, password: str) -> LoginResultDTO:
        """
        Authenticate a user by credentials and issue an access token.

        Steps:
          1. Canonical email normalization.
          2. User lookup.
          3. Constant-time password verification (with dummy hash on missing user).
          4. Active account validation.
          5. Issue signed access token.
          6. Return login result.

        Raises:
            InvalidCredentialsError: On unknown email or incorrect password.
            InactiveUserError: If the account is deactivated.
        """
        normalized_email = normalize_email(email)
        user = await self._user_repository.get_by_email(normalized_email)

        if user is None:
            # Timing attack mitigation: Execute verify against dummy hash so
            # response duration is indistinguishable from valid user lookup.
            self._password_hasher.verify(password, self._dummy_hash)
            raise InvalidCredentialsError("Invalid email or password.")

        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            logger.warning("Authentication rejected for inactive user: id=%s", user.id)
            raise InactiveUserError("User account is inactive.")

        token = self._token_service.create_access_token(
            subject=str(user.id),
            email=user.email,
        )
        expires_in = self._access_token_expire_minutes * 60

        logger.info("User authenticated successfully: id=%s", user.id)

        return LoginResultDTO(
            access_token=token,
            token_type="bearer",  # noqa: S106
            expires_in=expires_in,
            user=UserDTO(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )

    async def get_current_user_from_token(self, token: str) -> UserDTO:
        """
        Decode access token, load user from repository, and verify active status.

        Raises:
            ExpiredTokenError: If token has expired.
            InvalidTokenError: If token is malformed, invalid, or subject is invalid.
            AuthenticationRequiredError: If user no longer exists.
            InactiveUserError: If account is inactive.
        """
        claims = self._token_service.decode_access_token(token)

        try:
            user_id = uuid.UUID(claims.sub)
        except ValueError as exc:
            raise InvalidTokenError("Invalid token subject format.") from exc

        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationRequiredError("Authenticated user not found.")

        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

        return UserDTO(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
        )
