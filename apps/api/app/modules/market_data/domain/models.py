"""
RegimeX Market Data — Canonical Domain Models
==============================================
This module defines the internal, provider-independent data structures used
throughout the RegimeX platform.

Design decisions:
- All models are *frozen* Pydantic v2 dataclasses or BaseModel subclasses so
  that domain objects are effectively immutable after construction.
- Timestamps are always timezone-aware UTC.  Naive datetimes are rejected at
  construction time to guarantee deterministic ordering across providers.
- Numeric fields use Python ``Decimal`` types only where exact decimal
  semantics are mandated by downstream calculations.  Price/volume fields
  remain ``float`` here because downstream feature calculations will use
  NumPy/Pandas; the conversion boundary is explicit.
- No provider-specific fields are present.  The ``source_provider_id`` field
  records *which* provider produced the record for provenance purposes only;
  it does not carry vendor-specific metadata.

Architectural position: ``domain/``  — no imports from infrastructure or
  application layers, no HTTP clients, no ORM, no vendor SDKs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Enumerated domain types
# =============================================================================


class AssetClass(StrEnum):
    """Canonical asset classification supported by RegimeX."""

    EQUITY_US = "equity_us"
    EQUITY_IN = "equity_in"
    INDEX = "index"
    CRYPTO = "crypto"
    FX = "fx"
    COMMODITY = "commodity"


class DataInterval(StrEnum):
    """
    Canonical representation of market-data bar intervals.

    Not every provider supports every interval.  A ``ProviderCapabilities``
    object (see ``provider.py``) declares which intervals a given adapter
    actually supports.
    """

    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN = "30m"
    ONE_HOUR = "1h"
    FOUR_HOUR = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class AdjustmentPolicy(StrEnum):
    """
    Corporate-action adjustment policy for price series.

    RAW              — No adjustments applied.
    SPLIT_ADJUSTED   — Prices adjusted for stock splits only.
    FULLY_ADJUSTED   — Prices adjusted for splits and dividends.
    """

    RAW = "raw"
    SPLIT_ADJUSTED = "split_adjusted"
    FULLY_ADJUSTED = "fully_adjusted"


# =============================================================================
# Instrument / Symbol model
# =============================================================================


class Instrument(BaseModel):
    """
    Canonical representation of a tradeable instrument.

    The ``symbol`` field uses the provider-neutral internal identifier used by
    RegimeX (e.g. ``"RELIANCE"``, ``"AAPL"``, ``"BTC-USD"``).  Provider-
    specific symbol mappings (e.g. ``"RELIANCE.NS"`` for Yahoo Finance) are
    an adapter concern and must not appear here.
    """

    model_config = {"frozen": True}

    symbol: Annotated[
        str,
        Field(min_length=1, max_length=50, description="RegimeX canonical symbol identifier"),
    ]
    asset_class: AssetClass
    exchange: Annotated[
        str,
        Field(
            min_length=1,
            max_length=20,
            description="Exchange/market identifier (e.g. 'NSE', 'NYSE', 'BINANCE')",
        ),
    ]
    currency: Annotated[
        str,
        Field(
            min_length=2,
            max_length=10,
            description=(
                "Currency code — ISO 4217 for traditional assets (e.g. 'USD', 'INR'), "
                "or crypto quote currency (e.g. 'USDT', 'BTC')"
            ),
        ),
    ]
    description: str = Field(
        default="",
        max_length=200,
        description="Human-readable instrument name",
    )

    @field_validator("symbol", "exchange", mode="before")
    @classmethod
    def strip_and_upper(cls, v: str) -> str:
        """Normalise symbol and exchange to uppercase, stripped."""
        return v.strip().upper()

    @field_validator("currency", mode="before")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.strip().upper()


# =============================================================================
# OHLCV Record — canonical bar model
# =============================================================================


class OHLCVRecord(BaseModel):
    """
    Canonical single-bar OHLCV record.

    Invariants enforced at construction:
    - ``timestamp`` must be timezone-aware (UTC expected; adapters must convert).
    - ``open``, ``high``, ``low``, ``close`` must be strictly positive.
    - ``volume`` must be non-negative (some instruments have 0-volume bars).
    - ``high >= low`` always.
    - ``high >= open`` and ``high >= close``.
    - ``low <= open`` and ``low <= close``.

    Note: full data-quality pipeline (gap repair, duplicate removal, calendar
    validation) is NOT part of this model.  That belongs to V06 (regimex.quality).
    This model validates structural correctness only.
    """

    model_config = {"frozen": True}

    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    timestamp: datetime
    open: Annotated[float, Field(gt=0.0, description="Opening price of the bar")]
    high: Annotated[float, Field(gt=0.0, description="Highest price of the bar")]
    low: Annotated[float, Field(gt=0.0, description="Lowest price of the bar")]
    close: Annotated[float, Field(gt=0.0, description="Closing price of the bar")]
    volume: Annotated[float, Field(ge=0.0, description="Volume traded during the bar")]
    interval: DataInterval
    adjustment_policy: AdjustmentPolicy = AdjustmentPolicy.RAW
    source_provider_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="ID of the provider that produced this record",
        ),
    ]
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when this record was ingested into RegimeX",
    )

    @field_validator("timestamp", "ingested_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes — all timestamps must carry timezone info."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(
                f"Datetime value must be timezone-aware (got naive datetime: {v!r}). "
                "All RegimeX timestamps must be UTC-aware."
            )
        return v

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> OHLCVRecord:
        """Enforce price consistency invariants across OHLC fields."""
        errors: list[str] = []

        if self.high < self.low:
            errors.append(f"high ({self.high}) must be >= low ({self.low})")
        if self.high < self.open:
            errors.append(f"high ({self.high}) must be >= open ({self.open})")
        if self.high < self.close:
            errors.append(f"high ({self.high}) must be >= close ({self.close})")
        if self.low > self.open:
            errors.append(f"low ({self.low}) must be <= open ({self.open})")
        if self.low > self.close:
            errors.append(f"low ({self.low}) must be <= close ({self.close})")

        if errors:
            raise ValueError(f"OHLCV price relationship violations: {'; '.join(errors)}")

        return self


# =============================================================================
# Market Data Query model
# =============================================================================


class MarketDataQuery(BaseModel):
    """
    Canonical query/request model for historical OHLCV retrieval.

    The provider contract requires that adapters respect all fields here.
    Adapters translate this into their vendor-specific parameters.

    Validation rules:
    - ``start`` and ``end`` must both be timezone-aware.
    - ``end`` must be strictly after ``start``.
    - ``symbol`` / ``instrument`` must be non-empty.
    """

    model_config = {"frozen": True}

    instrument: Instrument
    start: datetime = Field(description="Query start datetime (inclusive), must be timezone-aware")
    end: datetime = Field(description="Query end datetime (exclusive), must be timezone-aware")
    interval: DataInterval = DataInterval.ONE_DAY
    adjustment_policy: AdjustmentPolicy = AdjustmentPolicy.SPLIT_ADJUSTED

    @field_validator("start", "end", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(
                f"Query datetime must be timezone-aware (got naive datetime: {v!r}). "
                "Use datetime(..., tzinfo=timezone.utc) or an aware datetime."
            )
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> MarketDataQuery:
        """Ensure end > start."""
        if self.end <= self.start:
            raise ValueError(
                f"Query end ({self.end.isoformat()}) must be strictly after "
                f"start ({self.start.isoformat()})."
            )
        return self


# =============================================================================
# Market Data Result model
# =============================================================================


class MarketDataResult(BaseModel):
    """
    Canonical result returned by a ``MarketDataProvider.get_ohlcv()`` call.

    The provider is responsible for returning records sorted in ascending
    chronological order.  This model does NOT sort or deduplicate records —
    that is the provider adapter's responsibility and will be further enforced
    by the V06 data quality pipeline.

    Fields:
    - ``query``       — echo of the original request (for result correlation).
    - ``provider_id`` — stable identifier of the provider that produced results.
    - ``fetched_at``  — UTC timestamp of the data fetch (for freshness tracking).
    - ``records``     — ordered list of canonical OHLCV bars.
    """

    model_config = {"frozen": True}

    query: MarketDataQuery
    provider_id: Annotated[str, Field(min_length=1, max_length=100)]
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when the provider returned this result",
    )
    records: tuple[OHLCVRecord, ...] = Field(
        default=(),
        description="OHLCV bars in ascending chronological order",
    )

    @field_validator("fetched_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware.")
        return v

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """Return True when the provider returned no records."""
        return len(self.records) == 0

    @property
    def record_count(self) -> int:
        """Number of OHLCV bars in this result."""
        return len(self.records)

    @property
    def symbol(self) -> str:
        """Convenience accessor for the queried symbol."""
        return self.query.instrument.symbol

    def price_range(self) -> tuple[Decimal, Decimal] | None:
        """
        Return (min_low, max_high) across all records, or None for empty result.

        Uses Decimal to avoid floating-point accumulation across bars.
        """
        if self.is_empty:
            return None
        lows = [Decimal(str(r.low)) for r in self.records]
        highs = [Decimal(str(r.high)) for r in self.records]
        return min(lows), max(highs)
