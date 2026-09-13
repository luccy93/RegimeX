"""
RegimeX Market Data — SQLAlchemy Repository Implementation
==========================================================
Production-grade repository implementation persisting canonical market data
into PostgreSQL / TimescaleDB and SQLite.

Key Guarantees:
- Idempotent persistence: Native dialect-aware upserts (ON CONFLICT DO UPDATE)
  prevent duplicate canonical bars on repeated ingestion.
- Atomic transactions: Multi-record batches execute within the session transaction.
- Zero ORM leakage: Repository receives and returns only canonical domain models
  (OHLCVRecord, Instrument, DataInterval).
- Safe error mapping: Lower-level database errors are sanitized and translated
  into the platform's StorageError hierarchy.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_data.domain.errors import (
    StorageConnectionError,
    StorageError,
    StorageIntegrityError,
)
from app.modules.market_data.domain.models import (
    DataInterval,
    Instrument,
    OHLCVRecord,
)
from app.modules.market_data.domain.repository import MarketDataRepository
from app.modules.market_data.infrastructure.persistence.models import MarketDataBarModel

logger = logging.getLogger(__name__)


class SQLAlchemyMarketDataRepository(MarketDataRepository):
    """
    SQLAlchemy-backed implementation of the MarketDataRepository interface.

    Supports both PostgreSQL (production / TimescaleDB) and SQLite (testing).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _get_dialect_name(self) -> str:
        """Inspect the active session bind dialect."""
        bind = self._session.bind
        if bind is not None:
            return bind.dialect.name
        return "postgresql"

    async def save(self, record: OHLCVRecord, instrument: Instrument) -> None:
        """Persist a single canonical OHLCV bar."""
        await self.save_batch([record], instrument)

    async def save_batch(
        self,
        records: Sequence[OHLCVRecord],
        instrument: Instrument,
    ) -> int:
        """
        Persist a sequence of canonical OHLCV bars in a single atomic operation.

        Performs an idempotent upsert: existing bars with matching
        (symbol, interval, timestamp) are updated with new metrics and
        source metadata.
        """
        if not records:
            return 0

        # Prepare normalized row dictionaries
        values_list: list[dict[str, object]] = []
        for r in records:
            ts = (
                r.timestamp.astimezone(UTC)
                if r.timestamp.tzinfo
                else r.timestamp.replace(tzinfo=UTC)
            )
            values_list.append(
                {
                    "symbol": r.symbol.upper(),
                    "asset_class": instrument.asset_class.value,
                    "exchange": instrument.exchange.upper(),
                    "interval": r.interval.value,
                    "timestamp": ts,
                    "open": Decimal(str(r.open)),
                    "high": Decimal(str(r.high)),
                    "low": Decimal(str(r.low)),
                    "close": Decimal(str(r.close)),
                    "volume": Decimal(str(r.volume)),
                    "adjustment_policy": r.adjustment_policy.value,
                    "source_provider_id": r.source_provider_id,
                }
            )

        dialect = self._get_dialect_name()

        try:
            if dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                sq_insert = sqlite_insert(MarketDataBarModel).values(values_list)
                sq_upsert = sq_insert.on_conflict_do_update(
                    index_elements=["symbol", "interval", "timestamp"],
                    set_={
                        "open": sq_insert.excluded.open,
                        "high": sq_insert.excluded.high,
                        "low": sq_insert.excluded.low,
                        "close": sq_insert.excluded.close,
                        "volume": sq_insert.excluded.volume,
                        "adjustment_policy": sq_insert.excluded.adjustment_policy,
                        "source_provider_id": sq_insert.excluded.source_provider_id,
                        "updated_at": func.now(),
                    },
                )
                await self._session.execute(sq_upsert)
            else:
                # Default to PostgreSQL
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                pg_insert_stmt = pg_insert(MarketDataBarModel).values(values_list)
                pg_upsert = pg_insert_stmt.on_conflict_do_update(
                    index_elements=["symbol", "interval", "timestamp"],
                    set_={
                        "open": pg_insert_stmt.excluded.open,
                        "high": pg_insert_stmt.excluded.high,
                        "low": pg_insert_stmt.excluded.low,
                        "close": pg_insert_stmt.excluded.close,
                        "volume": pg_insert_stmt.excluded.volume,
                        "adjustment_policy": pg_insert_stmt.excluded.adjustment_policy,
                        "source_provider_id": pg_insert_stmt.excluded.source_provider_id,
                        "updated_at": func.now(),
                    },
                )
                await self._session.execute(pg_upsert)

            await self._session.flush()
            return len(values_list)

        except IntegrityError as exc:
            logger.error("Database integrity error during batch save: %s", exc)
            raise StorageIntegrityError(
                message=f"Integrity constraint violation saving records for {instrument.symbol}.",
                details={"symbol": instrument.symbol, "count": len(records)},
            ) from exc

        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection error during batch save: %s", exc)
            raise StorageConnectionError(
                message="Database connectivity failure during market data save.",
                details={"symbol": instrument.symbol},
            ) from exc

        except SQLAlchemyError as exc:
            logger.error("Database error during batch save: %s", exc)
            raise StorageError(
                message="Unexpected persistence error saving market data records.",
                details={"symbol": instrument.symbol},
            ) from exc

    async def get_range(
        self,
        symbol: str,
        interval: DataInterval,
        start: datetime,
        end: datetime,
    ) -> tuple[OHLCVRecord, ...]:
        """Retrieve canonical bars within a time range, ordered chronologically ascending."""
        # Ensure query bounds are UTC
        start_utc = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
        end_utc = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)

        stmt = (
            select(MarketDataBarModel)
            .where(
                MarketDataBarModel.symbol == symbol.upper(),
                MarketDataBarModel.interval == interval.value,
                MarketDataBarModel.timestamp >= start_utc,
                MarketDataBarModel.timestamp < end_utc,
            )
            .order_by(MarketDataBarModel.timestamp.asc())
        )

        try:
            result = await self._session.scalars(stmt)
            bars = result.all()
            return tuple(b.to_domain() for b in bars)

        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection error during get_range: %s", exc)
            raise StorageConnectionError(
                message=f"Database connectivity failure querying range for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc

        except SQLAlchemyError as exc:
            logger.error("Database error during get_range: %s", exc)
            raise StorageError(
                message=f"Failed to query market data range for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc

    async def get_latest(
        self,
        symbol: str,
        interval: DataInterval,
    ) -> OHLCVRecord | None:
        """Retrieve the latest bar for an instrument and interval."""
        stmt = (
            select(MarketDataBarModel)
            .where(
                MarketDataBarModel.symbol == symbol.upper(),
                MarketDataBarModel.interval == interval.value,
            )
            .order_by(MarketDataBarModel.timestamp.desc())
            .limit(1)
        )

        try:
            result = await self._session.scalars(stmt)
            bar = result.first()
            return bar.to_domain() if bar is not None else None

        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection error during get_latest: %s", exc)
            raise StorageConnectionError(
                message=f"Database connectivity failure querying latest bar for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc

        except SQLAlchemyError as exc:
            logger.error("Database error during get_latest: %s", exc)
            raise StorageError(
                message=f"Failed to query latest market data bar for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc

    async def count(
        self,
        symbol: str,
        interval: DataInterval,
    ) -> int:
        """Return total count of persisted bars for an instrument and interval."""
        stmt = (
            select(func.count())
            .select_from(MarketDataBarModel)
            .where(
                MarketDataBarModel.symbol == symbol.upper(),
                MarketDataBarModel.interval == interval.value,
            )
        )

        try:
            result = await self._session.scalar(stmt)
            return int(result or 0)

        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection error during count: %s", exc)
            raise StorageConnectionError(
                message=f"Database connectivity failure counting bars for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc

        except SQLAlchemyError as exc:
            logger.error("Database error during count: %s", exc)
            raise StorageError(
                message=f"Failed to count market data bars for {symbol}.",
                details={"symbol": symbol, "interval": interval.value},
            ) from exc
