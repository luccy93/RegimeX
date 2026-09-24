"""
RegimeX Identity & Access — Persistence ORM Models
===================================================
SQLAlchemy 2.x declarative mapping for User identities.

Design & Architectural Boundaries:
- Table: `users`
- Primary key: UUID (`sa.Uuid`) compatible with PostgreSQL native UUID and SQLite.
- Email: Unique, indexed, normalized string.
- Password hash: Stores only salted Argon2id hashes; NEVER plaintext passwords.
- Audit timestamps: UTC timezone-aware with server defaults.
- Clean domain boundary: `to_domain()` and `from_domain()` bidirectional mappers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.modules.identity_access.domain.models import User


class UserModel(Base):
    """SQLAlchemy ORM model representing a registered User in database storage."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )

    # Primary key UUID
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identity dimensions
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_domain(self) -> User:
        """Convert this persistence ORM model into a pure User domain entity."""
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        else:
            created = created.astimezone(UTC)

        updated = self.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        else:
            updated = updated.astimezone(UTC)

        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            is_active=self.is_active,
            created_at=created,
            updated_at=updated,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserModel:
        """Construct a new UserModel persistence instance from a User domain entity."""
        created = user.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        else:
            created = created.astimezone(UTC)

        updated = user.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=UTC)
        else:
            updated = updated.astimezone(UTC)

        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            created_at=created,
            updated_at=updated,
        )
