"""
Unit tests for SQLAlchemyMarketDataRepository error handling and PostgreSQL branch.
==================================================================================
Verifies typed domain exceptions (StorageIntegrityError, StorageConnectionError, StorageError)
when underlying database operations encounter integrity violations, connectivity outages,
or generic database errors. Also tests the PostgreSQL on_conflict branch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.modules.market_data.domain.errors import (
    StorageConnectionError,
    StorageError,
    StorageIntegrityError,
)
from app.modules.market_data.domain.models import (
    AssetClass,
    DataInterval,
    Instrument,
    OHLCVRecord,
)
from app.modules.market_data.infrastructure.persistence.repository import (
    SQLAlchemyMarketDataRepository,
)
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError


@pytest.fixture
def sample_instrument() -> Instrument:
    return Instrument(
        symbol="AAPL", asset_class=AssetClass.EQUITY_US, exchange="NASDAQ", currency="USD"
    )


@pytest.fixture
def sample_record() -> OHLCVRecord:
    return OHLCVRecord(
        symbol="AAPL",
        timestamp=datetime(2026, 1, 1, 14, 30, tzinfo=UTC),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1_000_000,
        interval=DataInterval.ONE_DAY,
        source_provider_id="test",
    )


class TestRepositoryErrorTranslation:
    """Verifies that low-level SQLAlchemy errors are properly translated to domain exceptions."""

    @pytest.mark.asyncio
    async def test_save_batch_integrity_error(
        self, sample_instrument: Instrument, sample_record: OHLCVRecord
    ) -> None:
        mock_session = AsyncMock()
        mock_session.bind = MagicMock()
        mock_session.bind.dialect = MagicMock()
        mock_session.bind.dialect.name = "sqlite"
        mock_session.execute.side_effect = IntegrityError("statement", {}, Exception("constraint"))

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageIntegrityError) as exc_info:
            await repo.save_batch([sample_record], sample_instrument)

        assert "Integrity constraint violation" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_save_batch_operational_error(
        self, sample_instrument: Instrument, sample_record: OHLCVRecord
    ) -> None:
        mock_session = AsyncMock()
        mock_session.bind = MagicMock()
        mock_session.bind.dialect = MagicMock()
        mock_session.bind.dialect.name = "sqlite"
        mock_session.execute.side_effect = OperationalError("statement", {}, Exception("down"))

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageConnectionError) as exc_info:
            await repo.save_batch([sample_record], sample_instrument)

        assert "connectivity failure" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_save_batch_generic_sqlalchemy_error(
        self, sample_instrument: Instrument, sample_record: OHLCVRecord
    ) -> None:
        mock_session = AsyncMock()
        mock_session.bind = MagicMock()
        mock_session.bind.dialect = MagicMock()
        mock_session.bind.dialect.name = "sqlite"
        mock_session.execute.side_effect = SQLAlchemyError("Generic query error")

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageError) as exc_info:
            await repo.save_batch([sample_record], sample_instrument)

        assert "persistence error" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_save_batch_postgresql_dialect_branch(
        self, sample_instrument: Instrument, sample_record: OHLCVRecord
    ) -> None:
        """Verify PostgreSQL branch compiles and executes on_conflict statement."""
        mock_session = AsyncMock()
        mock_session.bind = MagicMock()
        mock_session.bind.dialect = MagicMock()
        mock_session.bind.dialect.name = "postgresql"

        repo = SQLAlchemyMarketDataRepository(mock_session)
        count = await repo.save_batch([sample_record], sample_instrument)

        assert count == 1
        assert mock_session.execute.called
        assert mock_session.flush.called

    @pytest.mark.asyncio
    async def test_get_range_operational_error(self) -> None:
        mock_session = AsyncMock()
        mock_session.scalars.side_effect = OperationalError(
            "statement", {}, Exception("conn error")
        )

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageConnectionError):
            await repo.get_range(
                "AAPL",
                DataInterval.ONE_DAY,
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 10, tzinfo=UTC),
            )

    @pytest.mark.asyncio
    async def test_get_range_generic_error(self) -> None:
        mock_session = AsyncMock()
        mock_session.scalars.side_effect = SQLAlchemyError("query failure")

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageError):
            await repo.get_range(
                "AAPL",
                DataInterval.ONE_DAY,
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 1, 10, tzinfo=UTC),
            )

    @pytest.mark.asyncio
    async def test_get_latest_dbapi_error(self) -> None:
        mock_session = AsyncMock()
        mock_session.scalars.side_effect = DBAPIError("statement", {}, Exception("dbapi fail"))

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageConnectionError):
            await repo.get_latest("AAPL", DataInterval.ONE_DAY)

    @pytest.mark.asyncio
    async def test_count_errors(self) -> None:
        mock_session = AsyncMock()
        mock_session.scalar.side_effect = OperationalError("statement", {}, Exception("down"))

        repo = SQLAlchemyMarketDataRepository(mock_session)

        with pytest.raises(StorageConnectionError):
            await repo.count("AAPL", DataInterval.ONE_DAY)

        mock_session.scalar.side_effect = SQLAlchemyError("generic fail")
        with pytest.raises(StorageError):
            await repo.count("AAPL", DataInterval.ONE_DAY)
