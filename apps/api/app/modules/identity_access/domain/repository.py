"""
RegimeX Identity & Access — User Repository Protocol
====================================================
Defines the abstract interface for User entity persistence.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.identity_access.domain.models import User


class UserRepository(Protocol):
    """Protocol defining persistence operations for User identities."""

    async def create(self, user: User) -> User:
        """
        Persist a new User identity.

        Args:
            user: Canonical User domain model.

        Returns:
            The persisted User entity.

        Raises:
            DuplicateEmailError: If a user with the same normalized email already exists.
        """
        ...

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Retrieve a User identity by its unique identifier.

        Args:
            user_id: UUID primary key.

        Returns:
            The User domain entity if found, None otherwise.
        """
        ...

    async def get_by_email(self, email: str) -> User | None:
        """
        Retrieve a User identity by its canonical normalized email.

        Args:
            email: Normalized email string.

        Returns:
            The User domain entity if found, None otherwise.
        """
        ...

    async def count(self) -> int:
        """Return the total number of registered users."""
        ...
