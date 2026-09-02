# ADR-0003: PostgreSQL + TimescaleDB for Storage

**Status:** Accepted
**Date:** 2026-09-02
**Volume:** V03 — System Architecture

---

## Context

RegimeX requires persistent storage for:
1. OHLCV time-series data (potentially 50M+ bars per NFR-SCALE-002)
2. Computed feature values (one record per feature × symbol × timestamp)
3. Regime detection outputs (one record per algorithm × symbol × timestamp × run)
4. Risk metrics
5. Backtest results
6. User/auth data, job status, instrument metadata

Requirements:
- Time-series query performance (range scans by timestamp are the dominant access pattern)
- ACID compliance for data integrity
- Self-hostable without proprietary licensing
- Open-source
- Strong SQLAlchemy ORM support

Additionally, a **task queue** is needed for async regime detection and backtesting jobs (FR-API async job requirement). A **cache** is needed for API response caching and rate limiting state.

## Decision

> We will use **PostgreSQL 15+** as the primary relational database, with **TimescaleDB** as the time-series extension for OHLCV and feature data.
>
> We will use **Celery** as the distributed task queue, with **Redis** as both the Celery broker and the caching layer.
>
> We will use **SQLAlchemy 2.x** as the ORM.

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| InfluxDB | Strong time-series support but lacks relational capabilities needed for metadata, users, jobs |
| QuestDB | Excellent time-series performance but smaller ecosystem, limited ORM support |
| MongoDB | Document model less suited to tabular financial time-series; joins more complex |
| MySQL | Less mature time-series extension ecosystem than PostgreSQL |
| SQLite | Not suitable for production multi-user deployments |
| RabbitMQ (for queue) | More complex ops than Redis; Redis is already used for caching |
| Dramatiq (for queue) | Smaller ecosystem than Celery; Celery has broader third-party integration |

## Consequences

### Positive
- PostgreSQL + TimescaleDB gives ACID guarantees + time-series performance in one database
- TimescaleDB hypertables provide automatic partitioning for time-series data (satisfies NFR-SCALE-002)
- SQLAlchemy 2.x provides async ORM support compatible with FastAPI's async model
- Redis is lightweight and well-understood; single dependency for both caching and task queuing
- All components are fully open-source and self-hostable (satisfies NFR-COMPAT-002)

### Negative / Trade-offs
- TimescaleDB is a PostgreSQL extension — requires a TimescaleDB-enabled PostgreSQL image in Docker
- Celery adds operational complexity; workers must be managed separately from the API
- Redis must be available for both caching and task queuing; it is an additional infrastructure dependency

### Risks
- TimescaleDB license: TimescaleDB Community Edition (Timescale License) is free for self-hosting. This is acceptable. The Apache 2.0 licensed core (`timescaledb-apache`) may be used if license restrictions become a concern.

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-09-02 | Accepted | Best self-hostable combination for time-series + relational + async workloads |
