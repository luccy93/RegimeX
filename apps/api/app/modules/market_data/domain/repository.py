"""
RegimeX Market Data — Domain Repository Abstraction
===================================================
Defines the canonical repository interface for market data storage and
retrieval operations.

Architectural boundaries:
- Pure domain interface: Zero imports from SQLAlchemy, ORM, or database drivers.
- Canonical models only: Operates exclusively on canonical domain models
  (OHLCVRecord, Instrument, DataInterval).
- Async interface: Native coroutine signatures for asynchronous I/O.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from app.modules.market_data.domain.models import (
    DataInterval,
    Instrument,
    OHLCVRecord,
)


class MarketDataRepository(ABC):
    """
    Abstract interface for persisting and querying canonical market data.

    All implementations must guarantee:
    1. Idempotency: Persisting the same canonical bar multiple times must
       not produce duplicate records.
    2. Atomicity: Batch operations must be atomic (all records persist or
       none do).
    3. Type safety: Returns canonical OHLCVRecord domain objects, never ORM
       or raw driver models.
    """

    @abstractmethod
    async def save(self, record: OHLCVRecord, instrument: Instrument) -> None:
        """
        Persist a single canonical OHLCV bar.

        Must be idempotent. If the bar already exists, it is updated or
        silently ignored according to conflict policy.
        """

    @abstractmethod
    async def save_batch(
        self,
        records: Sequence[OHLCVRecord],
        instrument: Instrument,
    ) -> int:
        """
        Persist a sequence of canonical OHLCV bars in a single atomic transaction.

        Returns the count of records persisted/upserted.
        Must handle empty batches gracefully (returns 0).
        """

    @abstractmethod
    async def get_range(
        self,
        symbol: str,
        interval: DataInterval,
        start: datetime,
        end: datetime,
    ) -> tuple[OHLCVRecord, ...]:
        """
        Retrieve canonical OHLCV bars for an instrument within a time range.

        Parameters:
        - symbol: Canonical instrument symbol identifier (e.g. 'AAPL', 'RELIANCE').
        - interval: Bar interval (e.g. 1d, 1h).
        - start: Start datetime (inclusive), must be timezone-aware.
        - end: End datetime (exclusive), must be timezone-aware.

        Returns:
        - Ordered tuple of OHLCVRecord objects sorted ascending by timestamp.
        """

    @abstractmethod
    async def get_latest(
        self,
        symbol: str,
        interval: DataInterval,
    ) -> OHLCVRecord | None:
        """
        Retrieve the latest available canonical bar for an instrument and interval.

        Returns None if no records exist.
        """

    @abstractmethod
    async def count(
        self,
        symbol: str,
        interval: DataInterval,
    ) -> int:
        """Return the total number of persisted bars for an instrument and interval."""
