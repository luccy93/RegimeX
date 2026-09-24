"""
RegimeX Identity & Access — Domain Services & Policy Validation
===============================================================
Encapsulates domain-level policies for email canonical normalization
and password security validation.
"""

from __future__ import annotations

import re

from app.modules.identity_access.domain.errors import (
    InvalidEmailError,
    InvalidPasswordError,
)

# Standard basic email RFC syntax regex
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

MIN_PASSWORD_LENGTH = 12


def normalize_email(email: str) -> str:
    """
    Apply canonical normalization to an email address.

    Policy:
      1. Trim surrounding whitespace.
      2. Normalize to lowercase.
      3. Validate email format against standard RFC syntax.

    This identical normalization is applied uniformly during:
      - Registration
      - Login
      - Account lookup

    Raises:
        InvalidEmailError: If the email is empty or malformed.
    """
    if not email:
        raise InvalidEmailError("Email address cannot be empty.")

    trimmed = email.strip()
    if not trimmed:
        raise InvalidEmailError("Email address cannot be blank.")

    # Canonical case normalization
    normalized = trimmed.lower()

    if not EMAIL_REGEX.match(normalized):
        raise InvalidEmailError(f"Email address '{trimmed}' is not a valid format.")

    return normalized


def validate_password_strength(password: str) -> None:
    """
    Validate that a password complies with the RegimeX baseline security policy.

    Policy:
      - Minimum length: 12 characters.
      - Reject empty or whitespace-only passwords.

    Never logs passwords or includes plaintext passwords in exception messages.

    Raises:
        InvalidPasswordError: If the password violates policy.
    """
    if not password:
        raise InvalidPasswordError("Password cannot be empty.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters in length."
        )
