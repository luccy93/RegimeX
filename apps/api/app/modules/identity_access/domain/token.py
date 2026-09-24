"""
RegimeX Identity & Access — Token Service Protocol
==================================================
Defines the abstract interface for signing and verifying authentication access tokens.
"""

from __future__ import annotations

from typing import Protocol

from app.modules.identity_access.domain.models import TokenClaims


class TokenService(Protocol):
    """Protocol for creating and decoding signed JWT access tokens."""

    def create_access_token(self, subject: str, email: str) -> str:
        """
        Create a signed, short-lived JWT access token for the given subject.

        Args:
            subject: Unique subject identifier (typically user UUID string).
            email: Canonical normalized user email address.

        Returns:
            Encoded, signed JWT token string.
        """
        ...

    def decode_access_token(self, token: str) -> TokenClaims:
        """
        Decode and validate a signed JWT access token.

        Validates signature, algorithm, expiration, and required claims.

        Args:
            token: Encoded JWT token string.

        Returns:
            Validated TokenClaims domain object.

        Raises:
            ExpiredTokenError: If the token has expired.
            InvalidTokenError: If the token is malformed, invalid, or forged.
        """
        ...
