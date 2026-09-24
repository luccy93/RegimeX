"""
RegimeX Identity & Access — Password Hashing Protocol
=====================================================
Defines the abstract interface for cryptographic password hashing and verification.
"""

from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    """Protocol for secure password hashing and constant-time verification."""

    def hash(self, password: str) -> str:
        """
        Generate a secure cryptographic hash for the given plaintext password.

        Must automatically generate a cryptographically strong, unique salt.
        """
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify that a plaintext password matches the given password hash.

        Must use constant-time verification behavior to prevent timing attacks.
        """
        ...
