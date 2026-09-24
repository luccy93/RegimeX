"""
RegimeX Identity & Access — SQLAlchemy User Repository
======================================================
Asynchronous persistence adapter implementing the UserRepository protocol.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity_access.domain.errors import DuplicateEmailError
from app.modules.identity_access.domain.models import User
from app.modules.identity_access.domain.repository import UserRepository
from app.modules.identity_access.infrastructure.persistence.models import UserModel

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    """
    SQLAlchemy-backed implementation of UserRepository.

    Manages transaction safety, database uniqueness constraint translation,
    and bidirectional ORM-domain mapping.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        """
        Persist a new User entity.

        Handles unique constraint violations gracefully by performing rollback
        and raising DuplicateEmailError.
        """
        model = UserModel.from_domain(user)
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.info("Duplicate user registration attempted for email=%s", user.email)
            raise DuplicateEmailError(
                f"An account with email '{user.email}' already exists."
            ) from exc

        return model.to_domain()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Retrieve a User by unique primary key identifier."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    async def get_by_email(self, email: str) -> User | None:
        """Retrieve a User by normalized email address."""
        stmt = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model is not None else None

    async def count(self) -> int:
        """Return the count of registered users."""
        stmt = select(func.count(UserModel.id))
        result = await self._session.execute(stmt)
        count_val = result.scalar()
        return int(count_val) if count_val is not None else 0
