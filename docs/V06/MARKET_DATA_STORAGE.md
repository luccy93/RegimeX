# RegimeX — Market Data Storage Engine

## 1. Overview

The **Market Data Storage Engine** is the persistence foundation of RegimeX, responsible for storing canonical, normalized, and validated financial market data. It implements a PostgreSQL and TimescaleDB-compatible time-series architecture using SQLAlchemy 2.x async, Alembic migrations, and an idempotent repository pattern.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REGIMEX INGESTION PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────────┘

   MarketDataProvider Adapter (e.g. YahooFinanceProvider)
                          │
                          ▼ (Canonical OHLCVRecord instances)
   DataQualityValidationPipeline (V06 Commit 01)
   - Schema & Price Invariants (DQ-SCHEMA-001, DQ-OHLC-001..003)
   - Timestamps & Order (DQ-TIME-001..002, DQ-ORDER-001, DQ-DUP-001)
   - Calendar & Gaps (DQ-CAL-001..002, DQ-GAP-001, DQ-STALE-001)
                          │
                          ▼ (QualityReport: PASS / WARN)
             [Strict Validation Boundary]
                          │
                          ▼
   MarketDataRepository (Domain Interface)
                          │
                          ▼
   SQLAlchemyMarketDataRepository (Infrastructure)
                          │
                          ▼ (Atomic Upsert Batch: ON CONFLICT DO UPDATE)
   PostgreSQL 16 / TimescaleDB Hypertable (`market_data_bars`)
```

> [!IMPORTANT]
> **Strict Validation Boundary**: Persisted data must flow through canonical validated records (`OHLCVRecord`). The database protects persistence invariants (uniqueness, nullability, referential integrity); the validation pipeline protects data quality.

---

## 2. Persistence Schema

The storage schema maps to the `market_data_bars` table.

### Table Definition

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT` | No | Auto-incrementing surrogate primary key. |
| `symbol` | `VARCHAR(50)` | No | Canonical uppercase instrument ticker (e.g., `AAPL`, `RELIANCE`). |
| `asset_class` | `VARCHAR(20)` | No | Asset classification (`equity_us`, `equity_in`, `crypto`, `fx`, etc.). |
| `exchange` | `VARCHAR(20)` | No | Exchange identifier (`NYSE`, `NASDAQ`, `NSE`, `BINANCE`). |
| `interval` | `VARCHAR(10)` | No | Canonical bar interval (`1d`, `1h`, `15m`, `1m`). |
| `timestamp` | `TIMESTAMPTZ` | No | UTC-aware observation timestamp (bar open time). |
| `open` | `NUMERIC(18, 6)` | No | Opening price for the period. |
| `high` | `NUMERIC(18, 6)` | No | Highest traded price during the bar. |
| `low` | `NUMERIC(18, 6)` | No | Lowest traded price during the bar. |
| `close` | `NUMERIC(18, 6)` | No | Closing price for the period. |
| `volume` | `NUMERIC(24, 6)` | No | Traded volume. Scale 6 accommodates fractional crypto units. |
| `adjustment_policy` | `VARCHAR(20)` | No | Corporate actions adjustment policy (`raw`, `split_adjusted`, `fully_adjusted`). |
| `source_provider_id` | `VARCHAR(100)` | No | Provenance identifier of the provider that supplied the data. |
| `created_at` | `TIMESTAMPTZ` | No | Audit timestamp recording ingestion time in UTC (`now()`). |
| `updated_at` | `TIMESTAMPTZ` | No | Audit timestamp recording last modification in UTC (`now()`). |

### Numeric Precision Rationale
Financial quantities must not suffer from IEEE-754 binary floating-point rounding errors. Using `NUMERIC(18, 6)` for price fields guarantees exact decimal precision up to 12 integer digits and 6 decimal places. Volume uses `NUMERIC(24, 6)` to handle both high-share traditional equities and micro-unit cryptocurrency fractions without precision degradation.

### Timestamps
All timestamps are stored in UTC (`TIMESTAMP WITH TIME ZONE`). Naive datetimes are strictly forbidden and rejected at the domain boundary.

---

## 3. Uniqueness and Idempotency Strategy

### Deterministic Uniqueness Boundary
A single canonical bar is uniquely identified by:
$$\text{Bar Identity} = (\text{symbol}, \text{interval}, \text{timestamp})$$

This is enforced by database constraint:
```sql
CONSTRAINT uq_market_data_symbol_interval_ts UNIQUE (symbol, interval, timestamp)
```

### Idempotent Batch Persistence
Repeated ingestion of the same canonical dataset is completely idempotent. Ingestion utilizes dialect-aware upserts (`ON CONFLICT (symbol, interval, timestamp) DO UPDATE`):
```sql
INSERT INTO market_data_bars (symbol, interval, timestamp, open, high, low, close, volume, ...)
VALUES (...)
ON CONFLICT (symbol, interval, timestamp)
DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    adjustment_policy = EXCLUDED.adjustment_policy,
    source_provider_id = EXCLUDED.source_provider_id,
    updated_at = NOW();
```
- **No duplicate accumulation**: Ingesting the same query range multiple times updates existing bars rather than inserting duplicate rows.
- **Atomic transactions**: Batches execute within an atomic transaction boundary. A failure triggers an immediate rollback, leaving no partial batches.

---

## 4. TimescaleDB Time-Series Compatibility

TimescaleDB partitions time-series tables into hypertables based on time intervals (chunks).

### Hypertable Requirements
1. The table must have a timestamp column (`TIMESTAMPTZ`).
2. Any unique constraint or primary key across the hypertable **must** include the partitioning timestamp column.

The RegimeX schema satisfies both requirements:
- Partition dimension: `timestamp`
- Unique constraint: `(symbol, interval, timestamp)` includes `timestamp`.

### Conditional Hypertable Creation
In environments with TimescaleDB enabled (such as `infra/docker-compose.yml`), the migration conditionally transforms `market_data_bars` into a hypertable:
```sql
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
    ) THEN
        PERFORM create_hypertable('market_data_bars', 'timestamp', if_not_exists => TRUE);
    END IF;
END $$;
```
Standard PostgreSQL environments (and SQLite test environments) run without modification or external plugin dependencies.

---

## 5. Repository Abstraction and Boundaries

### Domain Repository (`domain/repository.py`)
Pure Python abstract base class without any external database dependencies:
```python
class MarketDataRepository(ABC):
    async def save(self, record: OHLCVRecord, instrument: Instrument) -> None: ...
    async def save_batch(self, records: Sequence[OHLCVRecord], instrument: Instrument) -> int: ...
    async def get_range(self, symbol: str, interval: DataInterval, start: datetime, end: datetime) -> tuple[OHLCVRecord, ...]: ...
    async def get_latest(self, symbol: str, interval: DataInterval) -> OHLCVRecord | None: ...
    async def count(self, symbol: str, interval: DataInterval) -> int: ...
```

### SQLAlchemy Repository (`infrastructure/persistence/repository.py`)
- Takes an `AsyncSession`.
- Translates canonical domain entities to ORM rows on write and converts ORM rows back to canonical `OHLCVRecord` instances on read.
- Intercepts and sanitizes database exceptions into `StorageError` hierarchy (`StorageConnectionError`, `StorageIntegrityError`, `StorageNotFoundError`).

---

## 6. Database Migrations (Alembic)

Database schema evolution is managed via Alembic:

### Commands
```bash
# Apply migrations to head
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current revision
alembic current

# Create new autogenerated revision
alembic revision --autogenerate -m "description"
```

---

## 7. Local Infrastructure Setup

To launch the local TimescaleDB container:
```bash
docker compose -f infra/docker-compose.yml up -d db
```

Connection parameters:
- **Host**: `127.0.0.1:5432`
- **User**: `regimex`
- **Database**: `regimex_dev`
- **URL**: `postgresql+asyncpg://regimex:changeme@localhost:5432/regimex_dev`
