"""
Pytest fixtures for market data persistence unit tests.
======================================================
Provides an in-memory asynchronous SQLite database engine and session factory
for deterministic, 100% offline persistence testing.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from app.core.database.base import Base
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    OHLCVRecord,
)
from app.modules.market_data.infrastructure.persistence.models import (
    MarketDataBarModel,  # noqa: F401
)
from app.modules.market_data.infrastructure.persistence.repository import (
    SQLAlchemyMarketDataRepository,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture
async def sqlite_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory async SQLite engine with schema initialized."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(
    sqlite_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async session for each test."""
    session_factory = async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def repository(db_session: AsyncSession) -> SQLAlchemyMarketDataRepository:
    """Provide a repository instance bound to the test session."""
    return SQLAlchemyMarketDataRepository(session=db_session)


@pytest.fixture
def sample_instrument() -> Instrument:
    """Sample canonical equity instrument."""
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Apple Inc.",
    )


@pytest.fixture
def sample_records() -> list[OHLCVRecord]:
    """Five consecutive daily canonical OHLCV bars."""
    bars: list[dict[str, Any]] = [
        {
            "ts": datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            "o": 185.0,
            "h": 187.0,
            "l": 184.0,
            "c": 186.0,
            "v": 100000.0,
        },
        {
            "ts": datetime(2024, 1, 3, 14, 30, tzinfo=UTC),
            "o": 186.0,
            "h": 188.5,
            "l": 185.5,
            "c": 187.5,
            "v": 120000.0,
        },
        {
            "ts": datetime(2024, 1, 4, 14, 30, tzinfo=UTC),
            "o": 187.5,
            "h": 189.0,
            "l": 186.0,
            "c": 188.0,
            "v": 110000.0,
        },
        {
            "ts": datetime(2024, 1, 5, 14, 30, tzinfo=UTC),
            "o": 188.0,
            "h": 190.0,
            "l": 187.0,
            "c": 189.5,
            "v": 130000.0,
        },
        {
            "ts": datetime(2024, 1, 8, 14, 30, tzinfo=UTC),
            "o": 189.5,
            "h": 191.0,
            "l": 188.5,
            "c": 190.0,
            "v": 95000.0,
        },
    ]

    return [
        OHLCVRecord(
            symbol="AAPL",
            timestamp=b["ts"],
            open=b["o"],
            high=b["h"],
            low=b["l"],
            close=b["c"],
            volume=b["v"],
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.RAW,
            source_provider_id="test_provider",
        )
        for b in bars
    ]
