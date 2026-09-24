"""
Unit tests for SQLAlchemyUserRepository.
========================================
Verifies user persistence, retrieval by ID, retrieval by normalized email,
duplicate email enforcement, and transaction rollback on constraint violation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.modules.identity_access.domain.errors import DuplicateEmailError
from app.modules.identity_access.domain.models import User
from app.modules.identity_access.domain.repository import UserRepository


class TestSQLAlchemyUserRepository:
    async def test_create_and_get_by_id(self, user_repository: UserRepository) -> None:
        """Verify saving a new user and retrieving by unique ID."""
        user_id = uuid.uuid4()
        now = datetime.now(tz=UTC)
        user = User(
            id=user_id,
            email="researcher@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$hash",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        created = await user_repository.create(user)
        assert created.id == user_id
        assert created.email == "researcher@regimex.org"
        assert created.is_active is True

        retrieved = await user_repository.get_by_id(user_id)
        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "researcher@regimex.org"
        assert retrieved.password_hash == user.password_hash
        assert retrieved.is_active is True

    async def test_get_by_email_normalized(self, user_repository: UserRepository) -> None:
        """Verify retrieval by email works case-insensitively with normalized search."""
        user = User(
            id=uuid.uuid4(),
            email="quant.lead@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$hash",
            is_active=True,
        )
        await user_repository.create(user)

        # Exact match
        found = await user_repository.get_by_email("quant.lead@regimex.org")
        assert found is not None
        assert found.id == user.id

        # Uppercase query
        found_upper = await user_repository.get_by_email("QUANT.LEAD@REGIMEX.ORG")
        assert found_upper is not None
        assert found_upper.id == user.id

        # Query with whitespace
        found_ws = await user_repository.get_by_email("  quant.lead@regimex.org  ")
        assert found_ws is not None
        assert found_ws.id == user.id

    async def test_get_by_id_and_email_nonexistent_returns_none(
        self, user_repository: UserRepository
    ) -> None:
        """Verify queries for non-existent users return None."""
        assert await user_repository.get_by_id(uuid.uuid4()) is None
        assert await user_repository.get_by_email("nonexistent@regimex.org") is None

    async def test_duplicate_email_raises_duplicate_email_error(
        self, user_repository: UserRepository
    ) -> None:
        """Verify attempting to create a user with duplicate email raises DuplicateEmailError."""
        user1 = User(
            id=uuid.uuid4(),
            email="unique@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$hash1",
            is_active=True,
        )
        await user_repository.create(user1)

        user2 = User(
            id=uuid.uuid4(),
            email="unique@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$hash2",
            is_active=True,
        )

        with pytest.raises(DuplicateEmailError) as exc_info:
            await user_repository.create(user2)
        assert "unique@regimex.org" in str(exc_info.value)

    async def test_count(self, user_repository: UserRepository) -> None:
        """Verify count tracking accurately reflects created users."""
        initial_count = await user_repository.count()

        user1 = User(
            id=uuid.uuid4(),
            email="user1@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$h1",
            is_active=True,
        )
        user2 = User(
            id=uuid.uuid4(),
            email="user2@regimex.org",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake$h2",
            is_active=True,
        )

        await user_repository.create(user1)
        await user_repository.create(user2)

        assert await user_repository.count() == initial_count + 2
