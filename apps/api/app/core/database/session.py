"""
RegimeX Database Foundation — Engine and Session Factory
=========================================================
Provides asynchronous SQLAlchemy 2.x engine creation, connection pooling,
session factory management, and transaction boundary utilities.

Architecture:
- Async-first: Uses SQLAlchemy asyncio extension.
- Clean lifecycle: Engine singleton with explicit disposal for shutdown/tests.
- Dialect-aware: Adapts pool configuration for PostgreSQL vs. SQLite (tests).
- Safe sessions: `get_db_session` provides request-scoped transactional sessions
  with automatic commit on success and rollback on failure.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_session_factory(
    database_url: str | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    echo: bool = False,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Create a new async SQLAlchemy engine and session factory.

    Configures connection pooling for PostgreSQL while adapting cleanly
    for SQLite test environments.
    """
    settings = get_settings()
    url = database_url or settings.database_url
    engine_kwargs: dict[str, Any] = {
        "echo": echo or settings.debug,
        "future": True,
    }

    if url.startswith("sqlite"):
        # SQLite-specific configuration for in-memory or file-based tests
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL / asyncpg configuration
        engine_kwargs["pool_size"] = (
            pool_size if pool_size is not None else settings.database_pool_size
        )
        engine_kwargs["max_overflow"] = (
            max_overflow if max_overflow is not None else settings.database_max_overflow
        )
        engine_kwargs["pool_pre_ping"] = True

    engine = create_async_engine(url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine, session_factory


def get_engine() -> AsyncEngine:
    """Return or initialize the global async engine singleton."""
    global _engine, _session_factory
    if _engine is None:
        _engine, _session_factory = create_engine_and_session_factory()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return or initialize the global async session factory singleton."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine, _session_factory = create_engine_and_session_factory()
    return _session_factory


async def dispose_engine() -> None:
    """Dispose of the global async engine and reset singletons."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed successfully")


@asynccontextmanager
async def transaction_context(
    session: AsyncSession | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager providing an atomic transaction boundary.

    If an active session is provided, wraps operations in its transaction.
    Otherwise, creates a short-lived session, commits on success, and
    rolls back on error.
    """
    if session is not None:
        yield session
    else:
        factory = get_session_factory()
        async with factory() as new_session:
            try:
                yield new_session
                await new_session.commit()
            except Exception:
                await new_session.rollback()
                raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async SQLAlchemy session.

    Transaction is committed if route completes successfully; rolled back
    on any unhandled exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
