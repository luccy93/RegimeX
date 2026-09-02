# System Architecture

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

RegimeX is designed as a **modular, layered, provider-independent platform**. The architecture separates concerns cleanly across layers, enabling components to evolve independently and third parties to extend the platform through well-defined interfaces.

The system is organized into five architectural layers:

```text
┌────────────────────────────────────────────────────────────────┐
│                        Client Layer                            │
│         Web Browser · Python SDK · Third-Party API Clients    │
└────────────────────────────────┬───────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────┐
│                        Platform Layer                          │
│         FastAPI REST API · Authentication · Rate Limiting      │
└──────┬──────────────┬──────────────┬──────────────┬───────────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│  Analytics  │ │  Research  │ │   AI    │ │  Developer  │
│   Engine    │ │ Workspace  │ │ Engine  │ │  Platform   │
└──────┬──────┘ └─────┬──────┘ └────┬────┘ └──────┬──────┘
       │              │              │              │
┌──────▼──────────────▼──────────────▼──────────────▼──────────┐
│                     Intelligence Layer                         │
│  Regime Detection · Risk Engine · Backtesting · Feature Eng.  │
└────────────────────────────────┬──────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────┐
│                        Data Layer                              │
│   Market Data Ingestion · Storage · Validation · Provider Abs │
└────────────────────────────────┬──────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────┐
│                    Infrastructure Layer                        │
│      PostgreSQL/TimescaleDB · Redis · Task Queue · Docker     │
└────────────────────────────────────────────────────────────────┘
```

---

## Architectural Principles Applied

This architecture was designed to satisfy:

- **NFR-COMPAT-001:** Self-hostable via Docker Compose
- **NFR-COMPAT-002:** No proprietary cloud service dependencies
- **NFR-SCALE-005:** New regime detection algorithms without modifying consumers
- **NFR-SCALE-006:** New data providers without modifying business logic
- **NFR-DATA-001–003:** No look-ahead bias at any layer
- **FR-DEV-006:** Full self-hosting support

---

## Layer Responsibilities

### Data Layer

The data layer is responsible for all interactions with external data sources and the internal data store.

**Components:**
- **Market Data Provider Abstraction** — abstract interface hiding provider-specific API details
- **Provider Adapters** — concrete implementations per provider (Yahoo Finance, Alpha Vantage, etc.)
- **Ingestion Pipeline** — orchestrates ingestion, validation, and storage
- **Data Validator** — detects gaps, outliers, and schema violations
- **Data Store Interface** — abstract interface to the storage backend

**Key constraint:** The data layer is the only layer allowed to interact directly with external data providers. All other layers query data through internal repository interfaces.

---

### Intelligence Layer

The intelligence layer performs all quantitative computation: feature engineering, regime detection, risk analytics, and backtesting.

**Components:**
- **Feature Registry** — catalogue of all available features
- **Feature Pipeline** — executes feature computation pipelines
- **Regime Detector Registry** — catalogue of all available detection algorithms
- **Regime Detection Pipeline** — orchestrates detection runs
- **Risk Engine** — computes regime-aware risk metrics
- **Backtesting Engine** — event-driven strategy simulation

**Key constraint:** The intelligence layer must not make direct calls to external APIs or the raw database. It interacts with data through the repository interface exposed by the data layer.

---

### Platform Layer

The platform layer exposes intelligence capabilities to external consumers via a versioned REST API.

**Components:**
- **FastAPI Application** — HTTP request handling, routing, OpenAPI generation
- **Authentication Middleware** — API key validation, JWT verification
- **Rate Limiting Middleware** — per-user rate enforcement
- **Request/Response Validation** — Pydantic schema validation
- **Job Queue Integration** — async job submission for long-running operations
- **Error Handler** — consistent error response formatting

---

### Analytics & Research Engines

Specialized engines layered on top of the intelligence layer:

- **Analytics Engine** — aggregates regime, risk, and backtest data for dashboard consumption
- **Research Workspace** — parameterized, reproducible research run management
- **AI Engine** — grounded AI assistant (LLM + RegimeX data retrieval)
- **Developer Platform** — SDK generation, plugin registry

---

### Infrastructure Layer

Self-hostable infrastructure services:

- **PostgreSQL + TimescaleDB** — primary relational + time-series database
- **Redis** — caching layer and task queue broker
- **Celery** — distributed task queue for async jobs (ingestion, detection, backtesting)
- **Docker + Docker Compose** — containerization and local orchestration

---

## Technology Stack Summary

| Layer | Technology | ADR |
|-------|-----------|-----|
| Language | Python 3.10+ | ADR-0001 |
| API Framework | FastAPI | ADR-0002 |
| Primary Database | PostgreSQL 15+ | ADR-0003 |
| Time-Series Extension | TimescaleDB | ADR-0003 |
| ORM | SQLAlchemy 2.x | ADR-0003 |
| Schema Validation | Pydantic v2 | ADR-0002 |
| Task Queue | Celery + Redis | ADR-0003 |
| Caching | Redis | ADR-0003 |
| Regime Detection ML | scikit-learn, hmmlearn, statsmodels | ADR-0001 |
| Testing | pytest | ADR-0001 |
| Formatting | Ruff | ADR-0001 |
| Type Checking | mypy | ADR-0001 |
| Containerization | Docker + Docker Compose | — |
| CI | GitHub Actions | — |

---

## Security Architecture Overview

- **API authentication:** API keys (long-lived) + JWT (session-based)
- **Authorization:** Role-based: `public` < `researcher` < `admin`
- **Secrets management:** Environment variables only — never in source
- **TLS:** Enforced in production via reverse proxy (Nginx/Caddy)
- **Input validation:** Pydantic v2 at all API boundaries
- **Rate limiting:** Per-user limits enforced in middleware
- **Dependency scanning:** Automated in CI (pip-audit)

---

## Observability Architecture

- **Structured logging:** JSON logs via `structlog`
- **Metrics:** Prometheus-compatible metrics via `prometheus-client`
- **Tracing:** OpenTelemetry instrumentation (future, V23)
- **Health endpoints:** `/health` (liveness) and `/ready` (readiness)
- **Log levels:** `DEBUG` (dev), `INFO` (production default), `WARNING`, `ERROR`
