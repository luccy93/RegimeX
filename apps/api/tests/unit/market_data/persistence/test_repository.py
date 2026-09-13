"""
Unit tests for SQLAlchemyMarketDataRepository.
==============================================
Verifies CRUD operations, idempotent upsert behavior, range queries,
latest bar queries, transaction safety, and provenance preservation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    Instrument,
    OHLCVRecord,
)
from app.modules.market_data.infrastructure.persistence.repository import (
    SQLAlchemyMarketDataRepository,
)


class TestSQLAlchemyMarketDataRepository:
    async def test_save_single_record(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify saving a single canonical bar."""
        record = sample_records[0]
        await repository.save(record, sample_instrument)

        count = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert count == 1

        latest = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert latest is not None
        assert latest.symbol == "AAPL"
        assert latest.timestamp == record.timestamp
        assert latest.close == record.close

    async def test_save_batch(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify bulk inserting multiple bars in one atomic call."""
        saved_count = await repository.save_batch(sample_records, sample_instrument)
        assert saved_count == 5

        total = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert total == 5

    async def test_save_empty_batch(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
    ) -> None:
        """Verify empty sequence persists nothing without error."""
        saved_count = await repository.save_batch([], sample_instrument)
        assert saved_count == 0

        total = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert total == 0

    async def test_idempotent_save_same_records_twice(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """
        Critical invariant: persisting identical records repeatedly must NOT
        produce duplicate bars or inflate counts.
        """
        # First ingestion
        first_save = await repository.save_batch(sample_records, sample_instrument)
        assert first_save == 5
        count_after_first = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert count_after_first == 5

        # Repeated ingestion of identical records
        second_save = await repository.save_batch(sample_records, sample_instrument)
        assert second_save == 5
        count_after_second = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert count_after_second == 5

    async def test_idempotent_save_updates_modified_fields(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify upsert updates price metrics if same bar is re-ingested with revised prices."""
        initial = sample_records[0]
        await repository.save(initial, sample_instrument)

        latest_initial = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert latest_initial is not None
        assert latest_initial.close == 186.0

        # Revised record with same (symbol, interval, timestamp) but revised close
        revised = initial.model_copy(update={"close": 186.75, "volume": 105000.0})
        await repository.save(revised, sample_instrument)

        total = await repository.count("AAPL", DataInterval.ONE_DAY)
        assert total == 1

        latest_revised = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert latest_revised is not None
        assert latest_revised.close == 186.75
        assert latest_revised.volume == 105000.0

    async def test_get_range_filters_and_orders_ascending(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify range query filters bounds correctly and sorts chronologically ascending."""
        await repository.save_batch(sample_records, sample_instrument)

        # Query range: Jan 3 00:00 to Jan 6 00:00 (covers Jan 3, 4, 5)
        start = datetime(2024, 1, 3, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 6, 0, 0, tzinfo=UTC)

        bars = await repository.get_range("AAPL", DataInterval.ONE_DAY, start=start, end=end)
        assert len(bars) == 3

        # Assert ascending order
        assert bars[0].timestamp < bars[1].timestamp < bars[2].timestamp
        assert bars[0].timestamp == sample_records[1].timestamp
        assert bars[1].timestamp == sample_records[2].timestamp
        assert bars[2].timestamp == sample_records[3].timestamp

    async def test_get_range_empty_result(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify query outside available window returns empty tuple."""
        await repository.save_batch(sample_records, sample_instrument)

        start = datetime(2023, 1, 1, 0, 0, tzinfo=UTC)
        end = datetime(2023, 1, 10, 0, 0, tzinfo=UTC)

        bars = await repository.get_range("AAPL", DataInterval.ONE_DAY, start=start, end=end)
        assert bars == ()

    async def test_get_latest_returns_highest_timestamp(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify get_latest returns the most recent observation."""
        await repository.save_batch(sample_records, sample_instrument)

        latest = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert latest is not None
        # Latest record in sample_records is Jan 8
        assert latest.timestamp == sample_records[4].timestamp
        assert latest.close == sample_records[4].close

    async def test_get_latest_empty(
        self,
        repository: SQLAlchemyMarketDataRepository,
    ) -> None:
        """Verify get_latest returns None when no data exists."""
        latest = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert latest is None

    async def test_count_filters_by_symbol_and_interval(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
        sample_records: list[OHLCVRecord],
    ) -> None:
        """Verify count differentiates between symbols and intervals."""
        await repository.save_batch(sample_records, sample_instrument)

        # Save 1 bar with different interval
        hourly_bar = sample_records[0].model_copy(update={"interval": DataInterval.ONE_HOUR})
        await repository.save(hourly_bar, sample_instrument)

        assert await repository.count("AAPL", DataInterval.ONE_DAY) == 5
        assert await repository.count("AAPL", DataInterval.ONE_HOUR) == 1
        assert await repository.count("MSFT", DataInterval.ONE_DAY) == 0

    async def test_provenance_metadata_preserved(
        self,
        repository: SQLAlchemyMarketDataRepository,
        sample_instrument: Instrument,
    ) -> None:
        """Verify source provider ID and adjustment policy are stored and returned."""
        bar = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=185.0,
            high=187.0,
            low=184.0,
            close=186.0,
            volume=50000.0,
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.SPLIT_ADJUSTED,
            source_provider_id="custom_provenance_feed_v1",
        )
        await repository.save(bar, sample_instrument)

        retrieved = await repository.get_latest("AAPL", DataInterval.ONE_DAY)
        assert retrieved is not None
        assert retrieved.source_provider_id == "custom_provenance_feed_v1"
        assert retrieved.adjustment_policy == AdjustmentPolicy.SPLIT_ADJUSTED
