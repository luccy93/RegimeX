"""
RegimeX Identity & Access — Argon2id Password Hasher
=====================================================
Concrete implementation of PasswordHasher protocol using memory-hard Argon2id.
"""

from __future__ import annotations

import logging

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerificationError

from app.modules.identity_access.domain.password import PasswordHasher

logger = logging.getLogger(__name__)


class Argon2PasswordHasher(PasswordHasher):
    """
    Argon2id password hasher providing memory-hard, salt-salted password hashing
    and constant-time verification.
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = Argon2Hasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash(self, password: str) -> str:
        """Hash a plaintext password using Argon2id with an auto-generated salt."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """
        Verify that a plaintext password matches an Argon2id hash.

        Returns False on verification mismatch or malformed hash; never raises
        verification errors to prevent timing/oracle leaks.
        """
        try:
            return bool(self._hasher.verify(password_hash, password))
        except VerificationError:
            return False
        except Exception:
            logger.warning("Unexpected error during password hash verification")
            return False
