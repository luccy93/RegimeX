"""
RegimeX Identity & Access — Domain Models
=========================================
Pure Python domain models representing user identity, security credentials,
and token claims.

Architectural Rules:
- Pure Python and framework-independent (no FastAPI/Starlette imports).
- Plaintext passwords are never modeled, stored, or persisted.
- Timestamps must be timezone-aware (UTC).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """
    Durable User identity domain model.

    Represents an authenticated principal in RegimeX.
    Plaintext passwords are never held in this model.
    """

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Immutable unique primary identifier",
    )
    email: str = Field(
        description="Canonical normalized email address",
    )
    password_hash: str = Field(
        description="Cryptographic password hash (Argon2id)",
    )
    is_active: bool = Field(
        default=True,
        description="Flag indicating whether account is active and permitted to authenticate",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Timestamp when the user account was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Timestamp when the user account was last updated (UTC)",
    )

    @field_validator("email")
    @classmethod
    def validate_email_not_empty(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if not trimmed or "@" not in trimmed:
            raise ValueError("Email must be a valid non-empty email address.")
        return trimmed

    @field_validator("password_hash")
    @classmethod
    def validate_password_hash_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Password hash must not be empty.")
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a dictionary representation omitting sensitive credential data."""
        return {
            "id": str(self.id),
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TokenClaims(BaseModel):
    """
    Decoded JWT access token claims.

    Only contains necessary identification claims; never contains secrets or passwords.
    """

    model_config = ConfigDict(frozen=True)

    sub: str = Field(description="Subject identifier (User UUID)")
    email: str = Field(description="User email address")
    iat: datetime = Field(description="Issued at timestamp (UTC)")
    exp: datetime = Field(description="Expiration timestamp (UTC)")
    jti: str = Field(description="Unique token identifier for replay protection")
    iss: str | None = Field(default=None, description="Token issuer identifier")
    aud: str | None = Field(default=None, description="Token audience identifier")

    @field_validator("iat", "exp")
    @classmethod
    def validate_claim_timestamps(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
