"""
RegimeX Identity & Access — Application DTOs
============================================
Data transfer objects passed across the application service boundary.
Never contains passwords or password hashes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserDTO(BaseModel):
    """Safe public representation of a User identity."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(description="Unique user primary identifier")
    email: str = Field(description="Canonical normalized user email")
    is_active: bool = Field(description="Account active status")
    created_at: datetime = Field(description="Account creation timestamp (UTC)")


class LoginResultDTO(BaseModel):
    """Result of successful user authentication containing access credentials."""

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(description="Signed JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserDTO = Field(description="Authenticated user identity")
