"""
Unit tests for password hashing, verification, and security policy.
==================================================================
Verifies Argon2id password hashing, verification success/failure, salt generation,
and password policy invariants.
"""

from __future__ import annotations

import pytest
from app.modules.identity_access.domain.errors import InvalidPasswordError
from app.modules.identity_access.domain.password import PasswordHasher
from app.modules.identity_access.domain.services import (
    MIN_PASSWORD_LENGTH,
    validate_password_strength,
)


class TestPasswordHasher:
    def test_hash_creates_valid_argon2_string(self, password_hasher: PasswordHasher) -> None:
        """Verify password hasher produces a valid Argon2id hash string."""
        pw = "StrongPassword123!"
        hashed = password_hasher.hash(pw)

        assert isinstance(hashed, str)
        assert hashed.startswith("$argon2id$")
        assert hashed != pw

    def test_identical_passwords_produce_different_hashes(
        self, password_hasher: PasswordHasher
    ) -> None:
        """Verify unique salts are generated for identical plaintext passwords."""
        pw = "RepeatPassword123!"
        hash1 = password_hasher.hash(pw)
        hash2 = password_hasher.hash(pw)

        assert hash1 != hash2
        assert password_hasher.verify(pw, hash1) is True
        assert password_hasher.verify(pw, hash2) is True

    def test_verify_succeeds_for_correct_password(self, password_hasher: PasswordHasher) -> None:
        """Verify correct password verification returns True."""
        pw = "CorrectHorseBatteryStaple123"
        hashed = password_hasher.hash(pw)

        assert password_hasher.verify(pw, hashed) is True

    def test_verify_fails_for_incorrect_password(self, password_hasher: PasswordHasher) -> None:
        """Verify incorrect password verification returns False."""
        pw = "CorrectHorseBatteryStaple123"
        hashed = password_hasher.hash(pw)

        assert password_hasher.verify("WrongPassword456!", hashed) is False

    def test_verify_handles_malformed_hash_gracefully(
        self, password_hasher: PasswordHasher
    ) -> None:
        """Verify verification returns False on malformed hash without raising."""
        assert password_hasher.verify("password123", "not-a-valid-argon2-hash") is False
        assert password_hasher.verify("password123", "") is False


class TestPasswordPolicyValidation:
    def test_valid_password_passes_policy(self) -> None:
        """Verify a password meeting the minimum 12-character policy succeeds."""
        validate_password_strength("secure-password-12")
        validate_password_strength("a" * 12)
        validate_password_strength("a" * 100)

    def test_short_password_rejected(self) -> None:
        """Verify passwords under 12 characters are rejected with InvalidPasswordError."""
        for length in range(1, MIN_PASSWORD_LENGTH):
            short_pw = "a" * length
            with pytest.raises(InvalidPasswordError) as exc_info:
                validate_password_strength(short_pw)
            assert f"at least {MIN_PASSWORD_LENGTH}" in str(exc_info.value)

    def test_empty_password_rejected(self) -> None:
        """Verify empty password is rejected with InvalidPasswordError."""
        with pytest.raises(InvalidPasswordError):
            validate_password_strength("")
