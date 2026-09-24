"""
RegimeX Identity & Access — Persistence Infrastructure
======================================================
"""

from __future__ import annotations

from app.modules.identity_access.infrastructure.persistence.models import UserModel
from app.modules.identity_access.infrastructure.persistence.repository import (
    SQLAlchemyUserRepository,
)

__all__ = ["SQLAlchemyUserRepository", "UserModel"]
