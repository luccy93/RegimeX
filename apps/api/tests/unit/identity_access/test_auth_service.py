"""
Unit tests for AuthenticationService application orchestration.
================================================================
Verifies registration, login, timing mitigation on unknown accounts,
token resolution, active status validation, and error semantics.
"""

from __future__ import annotations

import uuid

import pytest
from app.modules.identity_access.application.service import AuthenticationService
from app.modules.identity_access.domain.errors import (
    AuthenticationRequiredError,
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordError,
)
from app.modules.identity_access.domain.models import User
from app.modules.identity_access.domain.repository import UserRepository


class TestAuthenticationServiceRegistration:
    async def test_successful_registration(self, auth_service: AuthenticationService) -> None:
        """Verify standard user registration returns safe UserDTO."""
        user_dto = await auth_service.register(
            email="new.user@regimex.org",
            password="StrongPassword123!",
        )

        assert isinstance(user_dto.id, uuid.UUID)
        assert user_dto.email == "new.user@regimex.org"
        assert user_dto.is_active is True
        assert not hasattr(user_dto, "password")
        assert not hasattr(user_dto, "password_hash")

    async def test_duplicate_registration_rejected(
        self, auth_service: AuthenticationService
    ) -> None:
        """Verify registering existing email raises DuplicateEmailError."""
        await auth_service.register(
            email="duplicate@regimex.org",
            password="StrongPassword123!",
        )

        with pytest.raises(DuplicateEmailError):
            await auth_service.register(
                email="duplicate@regimex.org",
                password="AnotherPassword123!",
            )

    async def test_duplicate_registration_with_case_and_whitespace_differences(
        self, auth_service: AuthenticationService
    ) -> None:
        """Verify normalization catches duplicate email despite case/whitespace variation."""
        await auth_service.register(
            email="case.test@regimex.org",
            password="StrongPassword123!",
        )

        with pytest.raises(DuplicateEmailError):
            await auth_service.register(
                email="  CASE.TEST@REGIMEX.ORG  ",
                password="StrongPassword123!",
            )

    async def test_short_password_rejected(self, auth_service: AuthenticationService) -> None:
        """Verify registration with password under 12 characters raises InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            await auth_service.register(
                email="short.pw@regimex.org",
                password="short",
            )

    async def test_invalid_email_format_rejected(self, auth_service: AuthenticationService) -> None:
        """Verify registration with invalid email raises InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            await auth_service.register(
                email="not-an-email",
                password="StrongPassword123!",
            )


class TestAuthenticationServiceLogin:
    async def test_successful_login(self, auth_service: AuthenticationService) -> None:
        """Verify valid credentials return signed access token and safe UserDTO."""
        await auth_service.register(
            email="login.test@regimex.org",
            password="StrongPassword123!",
        )

        result = await auth_service.login(
            email="login.test@regimex.org",
            password="StrongPassword123!",
        )

        assert isinstance(result.access_token, str)
        assert result.token_type == "bearer"
        assert result.expires_in == 3600
        assert result.user.email == "login.test@regimex.org"
        assert not hasattr(result.user, "password_hash")

    async def test_login_with_case_and_whitespace_variations(
        self, auth_service: AuthenticationService
    ) -> None:
        """Verify login succeeds when email has different case or whitespace."""
        await auth_service.register(
            email="canonical.login@regimex.org",
            password="StrongPassword123!",
        )

        result = await auth_service.login(
            email="  CANONICAL.LOGIN@REGIMEX.ORG  ",
            password="StrongPassword123!",
        )
        assert result.user.email == "canonical.login@regimex.org"

    async def test_login_incorrect_password_raises_invalid_credentials(
        self, auth_service: AuthenticationService
    ) -> None:
        """Verify wrong password raises InvalidCredentialsError with generic message."""
        await auth_service.register(
            email="wrong.pw@regimex.org",
            password="StrongPassword123!",
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            await auth_service.login(
                email="wrong.pw@regimex.org",
                password="IncorrectPassword999!",
            )
        assert str(exc_info.value) == "Invalid email or password."

    async def test_login_unknown_email_raises_identical_generic_error(
        self, auth_service: AuthenticationService
    ) -> None:
        """
        Anti-enumeration invariant: unknown email produces the identical generic
        InvalidCredentialsError message as an incorrect password.
        """
        with pytest.raises(InvalidCredentialsError) as exc_info:
            await auth_service.login(
                email="unknown.account@regimex.org",
                password="AnyPassword123!",
            )
        assert str(exc_info.value) == "Invalid email or password."

    async def test_login_inactive_user_rejected(
        self,
        auth_service: AuthenticationService,
        user_repository: UserRepository,
    ) -> None:
        """Verify inactive account is rejected during login."""
        # Create an inactive user directly
        user = User(
            id=uuid.uuid4(),
            email="inactive.user@regimex.org",
            password_hash=auth_service._password_hasher.hash("StrongPassword123!"),
            is_active=False,
        )
        await user_repository.create(user)

        with pytest.raises(InactiveUserError) as exc_info:
            await auth_service.login(
                email="inactive.user@regimex.org",
                password="StrongPassword123!",
            )
        assert "inactive" in str(exc_info.value).lower()


class TestAuthenticationServiceTokenResolution:
    async def test_resolve_current_user_from_valid_token(
        self, auth_service: AuthenticationService
    ) -> None:
        """Verify resolving authenticated user identity from a valid issued token."""
        await auth_service.register(
            email="resolve.test@regimex.org",
            password="StrongPassword123!",
        )
        login_result = await auth_service.login(
            email="resolve.test@regimex.org",
            password="StrongPassword123!",
        )

        resolved_user = await auth_service.get_current_user_from_token(login_result.access_token)
        assert resolved_user.email == "resolve.test@regimex.org"
        assert resolved_user.id == login_result.user.id

    async def test_resolve_unknown_user_from_valid_token_raises_error(
        self, auth_service: AuthenticationService
    ) -> None:
        """
        Verify valid token referencing deleted/nonexistent user raises
        AuthenticationRequiredError.
        """
        fake_user_id = str(uuid.uuid4())
        token = auth_service._token_service.create_access_token(
            subject=fake_user_id,
            email="ghost@regimex.org",
        )

        with pytest.raises(AuthenticationRequiredError):
            await auth_service.get_current_user_from_token(token)
