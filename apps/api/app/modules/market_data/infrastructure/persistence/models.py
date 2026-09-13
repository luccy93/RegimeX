"""
RegimeX Market Data — Persistence ORM Models
============================================
SQLAlchemy 2.x declarative mapping for canonical market data time-series bars.

Design & Architectural Boundaries:
- Table: `market_data_bars`
- Time-series optimized: Primary access pattern is (symbol, interval, timestamp).
- TimescaleDB hypertable compatible: Unique constraint includes the partition
  time dimension (timestamp).
- Numeric precision: Uses NUMERIC(18, 6) for prices and NUMERIC(24, 6) for volume
  to preserve financial decimal precision and prevent float rounding accumulation.
- Strict timezone safety: Timestamps are stored with timezone (UTC).
- Domain isolation: Bidirectional mapping methods (`to_domain`, `from_domain`)
  convert cleanly between ORM models and canonical OHLCVRecord domain entities.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    Instrument,
    OHLCVRecord,
)


class MarketDataBarModel(Base):
    """
    SQLAlchemy ORM model representing a single canonical OHLCV bar in storage.

    Compatible with both standard PostgreSQL and TimescaleDB hypertables.
    """

    __tablename__ = "market_data_bars"

    __table_args__ = (
        # Uniqueness boundary: Exactly one canonical observation per instrument,
        # interval, and timestamp. Includes timestamp to satisfy TimescaleDB
        # hypertable unique constraint requirements.
        UniqueConstraint(
            "symbol",
            "interval",
            "timestamp",
            name="uq_market_data_symbol_interval_ts",
        ),
        # Composite index for historical range queries
        Index(
            "ix_market_data_symbol_interval_ts",
            "symbol",
            "interval",
            "timestamp",
        ),
        # Index for symbol and timestamp queries
        Index(
            "ix_market_data_symbol_ts",
            "symbol",
            "timestamp",
        ),
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # Instrument dimensions
    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    asset_class: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Time-series dimensions
    interval: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # OHLCV price & volume metrics (numeric precision)
    open: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6),
        nullable=False,
    )
    high: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6),
        nullable=False,
    )
    low: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6),
        nullable=False,
    )
    close: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6),
        nullable=False,
    )
    volume: Mapped[Decimal] = mapped_column(
        Numeric(precision=24, scale=6),
        nullable=False,
    )

    # Provenance & corporate action metadata
    adjustment_policy: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="raw",
    )
    source_provider_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_domain(self) -> OHLCVRecord:
        """Convert this persistence ORM model into a canonical OHLCVRecord domain object."""
        # Ensure timestamp is UTC-aware
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        else:
            ts = ts.astimezone(UTC)

        ingested = self.created_at
        if ingested.tzinfo is None:
            ingested = ingested.replace(tzinfo=UTC)
        else:
            ingested = ingested.astimezone(UTC)

        return OHLCVRecord(
            symbol=self.symbol,
            timestamp=ts,
            open=float(self.open),
            high=float(self.high),
            low=float(self.low),
            close=float(self.close),
            volume=float(self.volume),
            interval=DataInterval(self.interval),
            adjustment_policy=AdjustmentPolicy(self.adjustment_policy),
            source_provider_id=self.source_provider_id,
            ingested_at=ingested,
        )

    @classmethod
    def from_domain(
        cls,
        record: OHLCVRecord,
        instrument: Instrument,
    ) -> MarketDataBarModel:
        """Create a new MarketDataBarModel instance from a canonical OHLCVRecord domain object."""
        ts = record.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        else:
            ts = ts.astimezone(UTC)

        return cls(
            symbol=record.symbol,
            asset_class=instrument.asset_class.value,
            exchange=instrument.exchange,
            interval=record.interval.value,
            timestamp=ts,
            open=Decimal(str(record.open)),
            high=Decimal(str(record.high)),
            low=Decimal(str(record.low)),
            close=Decimal(str(record.close)),
            volume=Decimal(str(record.volume)),
            adjustment_policy=record.adjustment_policy.value,
            source_provider_id=record.source_provider_id,
        )
