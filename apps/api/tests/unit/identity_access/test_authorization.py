"""
Unit tests for Domain Authorization abstractions and policies.
==============================================================
Verifies:
1. ActiveUserPolicy permits active users and rejects inactive users with InactiveUserError.
2. AuthorizationChecker executes policies in sequence.
3. AuthorizationError provides standard code 'FORBIDDEN' and HTTP 403 status.
4. Custom AuthorizationPolicy can be plugged into AuthorizationChecker.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.modules.identity_access.application.dto import UserDTO
from app.modules.identity_access.domain.authorization import (
    ActiveUserPolicy,
    AuthorizationChecker,
    AuthorizationError,
    AuthorizationPolicy,
)
from app.modules.identity_access.domain.errors import InactiveUserError


def _make_user(is_active: bool = True) -> UserDTO:
    return UserDTO(
        id=uuid.uuid4(),
        email="test.user@regimex.org",
        is_active=is_active,
        created_at=datetime.now(tz=UTC),
    )


class TestActiveUserPolicy:
    def test_active_user_passes_policy(self) -> None:
        policy = ActiveUserPolicy()
        user = _make_user(is_active=True)
        # Should not raise
        policy.check(user)

    def test_inactive_user_raises_inactive_user_error(self) -> None:
        policy = ActiveUserPolicy()
        user = _make_user(is_active=False)
        with pytest.raises(InactiveUserError) as exc_info:
            policy.check(user)
        assert "inactive" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "AUTHENTICATION_REQUIRED"
        assert exc_info.value.http_status == 401


class TestAuthorizationChecker:
    def test_default_checker_authorizes_active_user(self) -> None:
        checker = AuthorizationChecker()
        user = _make_user(is_active=True)
        # Should not raise
        checker.authorize(user)

    def test_default_checker_rejects_inactive_user(self) -> None:
        checker = AuthorizationChecker()
        user = _make_user(is_active=False)
        with pytest.raises(InactiveUserError):
            checker.authorize(user)

    def test_custom_policy_integration(self) -> None:
        class RolePolicy(AuthorizationPolicy):
            def __init__(self, allowed_email_domains: list[str]) -> None:
                self.allowed_domains = allowed_email_domains

            def check(self, user: UserDTO) -> None:
                domain = user.email.split("@")[-1]
                if domain not in self.allowed_domains:
                    raise AuthorizationError(f"Email domain '{domain}' is not authorized.")

        checker = AuthorizationChecker(
            policies=[
                ActiveUserPolicy(),
                RolePolicy(allowed_email_domains=["regimex.org"]),
            ]
        )

        valid_user = _make_user(is_active=True)
        checker.authorize(valid_user)

        unauthorized_domain_user = UserDTO(
            id=uuid.uuid4(),
            email="intruder@external.com",
            is_active=True,
            created_at=datetime.now(tz=UTC),
        )
        with pytest.raises(AuthorizationError) as exc_info:
            checker.authorize(unauthorized_domain_user)
        assert exc_info.value.error_code == "FORBIDDEN"
        assert exc_info.value.http_status == 403


class TestAuthorizationError:
    def test_error_attributes(self) -> None:
        err = AuthorizationError("Custom forbidden message")
        assert err.error_code == "FORBIDDEN"
        assert err.http_status == 403
        assert "Custom forbidden message" in err.message
