# RegimeX Platform Architecture Blueprint

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Document Status:** Authoritative Architecture Blueprint (V03 Commit 01)  

---

## 1. Executive Summary & Architectural Goals

RegimeX is an enterprise-grade, open-source market intelligence and quantitative research platform. It provides the technological foundation to ingest financial market data, compute quantitative signals with zero look-ahead bias, detect macro and micro market regimes, analyze state transition probabilities, calculate regime-conditional risk analytics, backtest trading strategies with realistic cost attribution, and deliver AI-assisted research grounded strictly in verified platform data.

### 1.1 Architecture Goals

The architecture is explicitly designed to satisfy the functional requirements (FR-001 through FR-091) and non-functional quality attributes (NFR-001 through NFR-113) established in `V02/SRS.md`:

1. **Provider Independence (`FR-005`–`FR-013`, `NFR-078`):** Complete decoupling of core business logic from any third-party market data vendor, AI provider, or cloud infrastructure vendor.
2. **Model Pluggability & Algorithmic Extensibility (`FR-022`–`FR-031`, `NFR-030`):** Standardized, modular interfaces allowing community researchers to plug in new feature transformers, regime detection algorithms, and backtesting strategies without modifying downstream consumers.
3. **Point-in-Time Correctness & Anti-Leakage (`FR-015`, `FR-054`, `NFR-032`, `NFR-088`):** Total elimination of look-ahead bias across data pipelines, feature calculations, model fitting, and backtesting.
4. **Reproducibility & Provenance (`NFR-032`, `NFR-094`–`NFR-098`):** Every analytical artifact is bit-for-bit reproducible via explicit version fingerprinting across dataset, feature set, model parameters, execution seeds, and environment metadata.
5. **Grounded AI with Anti-Hallucination Safeguards (`FR-060`–`FR-066`, `NFR-100`, `NFR-103`):** AI research assistance operating through a strictly controlled grounding pipeline that prohibits hallucinations, cites verified data, communicates uncertainty, and strictly declines personalized financial advice.
6. **Self-Hostability & Zero Vendor Lock-in (`FR-086`, `NFR-075`):** Standard containerized orchestration (`docker compose up`) executable on any standard Linux host or local workstation without mandatory commercial cloud dependencies.

---

## 2. High-Level Conceptual Architecture

The diagram below illustrates the end-to-end conceptual flow from end users through presentation, API orchestration, domain computation, regime intelligence, and underlying storage:

```text
                         ┌──────────────────────┐
                         │     Public Users     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   Next.js Web App    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │      API Layer       │
                         │       FastAPI        │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
       ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
       │ Market Data │       │   Research  │       │    AI       │
       │   Domain    │       │   Domain    │       │   Domain    │
       └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
              │                     │                     │
              ▼                     ▼                     ▼
       ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
       │ Feature      │      │ Risk /       │      │ Grounded    │
       │ Engineering  │      │ Backtesting  │      │ Retrieval   │
       └──────┬───────┘      └──────┬───────┘      └──────────────┘
              │                     │
              ▼                     ▼
       ┌─────────────────────────────────────┐
       │        Regime Intelligence          │
       │ KMeans / GMM / HMM / Future Models │
       └──────────────────┬──────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Storage / Cache │
                 └─────────────────┘
```

---

## 3. Architecture Layers

RegimeX establishes clean separation of concerns across seven distinct architectural layers:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Presentation Layer (Next.js, React, TailwindCSS/Vanilla, Charts)   │
├────────────────────────────────────────────────────────────────────────┤
│ 2. API / Application Layer (FastAPI, Auth, Rate Limit, Envelope)       │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Domain Layer (Pure Financial Business Logic, Invariants)           │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Analytics & Machine Learning Layer (Scikit-Learn, HMM, Risk Math)   │
├────────────────────────────────────────────────────────────────────────┤
│ 5. Data & Storage Layer (PostgreSQL/TimescaleDB, Redis, Repositories)  │
├────────────────────────────────────────────────────────────────────────┤
│ 6. Background Processing Layer (Celery, Redis Task Queue, Beat)        │
├────────────────────────────────────────────────────────────────────────┤
│ 7. Infrastructure Layer (Docker, Docker Compose, Caddy / Reverse Proxy)│
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Presentation Layer
- **Scope:** Web interface, interactive charting (time-series, regime heatmaps, drawdown overlays), search navigation, research workspaces, and conversational AI UI.
- **Boundaries:** Consumes the API layer via HTTPS and WebSockets. Contains zero financial math or domain rules. Never accesses the database directly.

### 3.2 API / Application Layer
- **Scope:** HTTP REST request routing, JSON schema validation (Pydantic v2), authentication (JWT and long-lived API keys), role-based authorization, per-identity rate limiting, request logging, and async task dispatch.
- **Boundaries:** Delegates all computation to domain modules or the background processing layer. Formats outgoing JSON envelopes.

### 3.3 Domain Layer
- **Scope:** Core financial concepts, business entities, and calculation rules: instrument representations, trading calendars, canonical OHLCV normalization, feature definitions, and strategy backtest event loops.
- **Boundaries:** Pure Python. Independent of web frameworks, HTTP protocols, and database drivers.

### 3.4 Analytics & Machine Learning Layer
- **Scope:** Quantitative statistical computation: feature pipelines, regime model fitting and inference (HMM, GMM, KMeans, Changepoint), regime transition matrix calculations, persistence analytics, and regime-conditional risk metrics.
- **Boundaries:** Operates on standardized NumPy arrays and pandas DataFrames. Interacts with persistence strictly via abstract repository interfaces.

### 3.5 Data & Storage Layer
- **Scope:** Time-series database persistence, relational user/experiment tables, in-memory caching, and data access repositories.
- **Boundaries:** Encapsulates SQL queries and connection pools. Exposes typed domain objects to upper layers.

### 3.6 Background Processing Layer
- **Scope:** Distributed worker execution for high-compute, asynchronous tasks (multi-year historical data ingestion, bulk feature calculations, model fitting, walk-forward simulations, export generation).
- **Boundaries:** Consumes tasks from Redis queues; updates task status tables in storage; emits job progress events.

### 3.7 Infrastructure Layer
- **Scope:** Container definitions (Dockerfiles), multi-service local deployment topologies (`docker compose`), TLS termination, reverse proxying (Caddy), and volume mounting.
- **Boundaries:** Manages runtime environment and process lifecycles. Completely cloud-agnostic.

---

## 4. Architectural Style: Modular Monolith + Asynchronous Workers

RegimeX adopts a **Modular Monolith with Asynchronous Workers** architectural style (formalized in [ADR-0001](./decisions/ADR-0001-architecture-style.md)).

### Why this style fits RegimeX:
1. **Avoidance of Premature Microservices:** Distributing financial research workflows across multiple microservices from day one introduces severe network latency (transferring multi-gigabyte historical price and feature matrices over internal REST/gRPC), distributed state challenges, and high operational friction for local open-source contributors.
2. **Operational Simplicity for Self-Hosting:** Self-hosters and contributors can launch the complete platform using a single `docker compose up` command on a modest machine or VPS.
3. **Rigorous Internal Boundaries:** Code is organized into strict, decoupled domain modules under `src/regimex/`. Inward-only dependency rules and abstract repositories prevent monolithic spaghetti.
4. **Natural Evolutionary Path:** If a specific subsystem (e.g., Backtesting or Ingestion Worker) experiences massive computational demand in the future, its strict module boundaries allow it to be factored out into an independent microservice with minimal architectural friction.

### Workload Separation:
- **Interactive Workloads (Synchronous API):** Instrument search, single-symbol regime status queries, cached risk metrics, dashboard metadata, user authentication, and job status polling. Target latency: $p95 \le 500\text{ ms}$.
- **Asynchronous Workloads (Background Workers):** Multi-year historical data ingestion, comprehensive feature matrix generation, ML model fitting/cross-validation, multi-universe backtesting simulations, and analytical report compilation. Returns immediate job ID (`HTTP 202 Accepted`) for progress polling.

---

## 5. Major Domain Boundaries

RegimeX decomposes its functional capabilities into 14 logical domains (detailed in [MODULE_BOUNDARIES.md](./MODULE_BOUNDARIES.md)):

| # | Domain | Core Responsibility | Key Invariant |
|---|--------|---------------------|---------------|
| 1 | **Market Discovery** | Catalogue instruments, exchanges, asset classes, and trading calendars | Authoritative symbol resolution |
| 2 | **Market Data** | Ingest, normalize, and store canonical OHLCV records | Provider-agnostic storage |
| 3 | **Data Quality** | Validate price/volume constraints, detect gaps, flag anomalies | Quarantine corrupt records |
| 4 | **Feature Engineering** | Compute quantitative signals with zero look-ahead bias | Strict $t \le T$ point-in-time filtering |
| 5 | **Regime Detection** | Fit statistical/ML models and infer market regime states | Unified `RegimeDetector` interface |
| 6 | **Regime Intelligence** | Compute state transition matrices and regime persistence | Probabilistic Markov analysis |
| 7 | **Risk Analytics** | Calculate unconditional and regime-conditional risk (VaR, CVaR) | Explicit confidence & assumptions |
| 8 | **Backtesting** | Chronological event-driven simulation with realistic costs | Strict bar-by-bar isolation |
| 9 | **Research Workspace** | Manage reproducible parameterized experiment runs and comparisons | Immutable provenance recording |
| 10 | **AI Research** | Grounded quantitative query assistant with data provenance | Zero hallucination, no advice |
| 11 | **Identity & Access** | Authentication, authorization (RBAC), API key management | Secure hashed credentials |
| 12 | **API Gateway** | Transport routing, validation, rate limiting, and response envelopes | Zero business logic in transport |
| 13 | **Observability** | Structured logging, metrics emission, tracing, and health probes | Non-blocking telemetry |
| 14 | **Administration** | System configuration, ingestion schedules, audit inspection | Immutable audit logs |

---

## 6. Technology Policy & Core Stack

To prevent architectural bloat, avoid premature dependencies, and maintain open-source contributor accessibility, RegimeX enforces a strict technology policy distinguishing confirmed architectural directions from proposed implementation choices and unresolved decisions.

Detailed visual specifications for all architectural layers are available in [DIAGRAMS.md](./DIAGRAMS.md).

### 6.1 Confirmed Architectural Direction
These technologies represent foundational architectural commitments established by V01 principles and V02 requirements:
- **Programming Languages:** Python 3.10+ (for analytical core, mathematical pipelines, and data processing) and TypeScript (for type-safe web platform development).
- **API Framework:** FastAPI (high-performance asynchronous ASGI routing, native typing, and OpenAPI generation).
- **Web Application:** Next.js / React (modern responsive presentation, server-side rendering for financial dashboards).
- **Primary Data Persistence:** PostgreSQL 15+ with TimescaleDB (relational ACID compliance combined with time-series hypertables).
- **In-Memory Cache & Message Broker:** Redis 7+ (ephemeral caching, sliding-window rate limiting, and task queue broker).
- **Containerization & Deployment:** Docker and Docker Compose (reproducible, vendor-agnostic local and production self-hosting).

### 6.2 Proposed Implementation Candidates
These technologies are architectural candidates selected for standard implementation, subject to empirical validation in their respective volumes:
- **Asynchronous Task Harness:** Celery (distributed background job execution; to be validated in V05/V08).
- **Reverse Proxy & TLS:** Caddy (automated TLS certificate lifecycle, reverse proxy; configurable with Nginx).
- **Numerical & ML Libraries:** NumPy, pandas, scikit-learn, hmmlearn, statsmodels, scipy.
- **Data Validation:** Pydantic v2 (strict request/response schema parsing and serialization).
- **Observability:** `structlog` (structured JSON logging) and `prometheus-client` (metrics scraping).
- **Code Quality:** Ruff (linter/formatter), mypy (static type analysis), pytest (automated testing).

### 6.3 Unresolved Technology Decisions
The following architectural decisions remain open and will be decided via formal ADRs in their designated volumes:
- **Initial Data Providers (OQ-001):** To be finalized in V05 (Market Data Engine).
- **Supported Asset Class Scope (OQ-002):** US Equities initially vs Multi-Market; to be resolved in V05.
- **Default Regime Detection Algorithm (OQ-003):** HMM vs GMM prioritized in V08.
- **AI Foundation Model Provider (OQ-004):** OpenAI vs Anthropic vs Local LLM; to be resolved in V21.
- **Open-Source License Selection (OQ-010):** Must be resolved prior to V04 implementation.

### 6.4 Technologies Explicitly Excluded for V03
The following technologies are deliberately omitted as unnecessary complexity:
- **Kafka / RabbitMQ:** Redis provides sufficient throughput without the heavy operational overhead of Kafka.
- **Kubernetes:** Self-hosting simplicity mandates Docker Compose; Kubernetes is not required for single-node or moderate-scale deployments.
- **Dedicated Vector Databases (Pinecone/Qdrant):** Grounded AI retrieval relies on structured time-series queries; vector embeddings can use PostgreSQL `pgvector` if needed in V21.
- **Graph Databases (Neo4j):** Relational tables efficiently represent transition matrices and asset correlations.

---

## 7. Security Architecture

Security boundaries are established at the outermost platform perimeter and enforced across all internal layers:

```text
               Public Internet / Untrusted Network
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 1. Edge & Transport Security (TLS 1.2+, Caddy)     │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 2. Rate Limiting & Abuse Throttling (Redis IP/Key)│
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 3. Authentication Boundary (JWT / API Key Salted) │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 4. Role-Based Access Control (Public/Researcher/  │
     │    Admin RBAC Checks)                             │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 5. Schema Validation & Sanitization (Pydantic v2) │
     └─────────────────────────┬─────────────────────────┘
                               │
                               ▼
     ┌───────────────────────────────────────────────────┐
     │ 6. Isolated Internal Network (Database, Workers)  │
     └───────────────────────────────────────────────────┘
```

- **Authentication & Sessions:** Bearer JWT tokens for web sessions (ephemeral, 1-hour expiry); cryptographically salted SHA-256 hashes for long-lived API keys (`regimex_live_...`).
- **Secrets Management:** Secrets (database passwords, API key salts, external vendor tokens) are injected strictly via environment variables; never committed to source control or logged in telemetry.
- **Network Isolation:** Internal storage (PostgreSQL, Redis) and background worker nodes listen only on the internal Docker network (`regimex_net`) and are never exposed to public internet ports in production.
- **Audit Logging:** Security events (login attempts, permission denials, key revocations, administrative configuration updates) produce immutable structured audit records.

---

## 8. Data Storage Architecture

Data persistence is partitioned logically across distinct storage domains within the PostgreSQL / TimescaleDB and Redis engines:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL + TimescaleDB                         │
├──────────────────────────────┬──────────────────────────────────────────┤
│ Relational Entities          │ Time-Series Hypertables (TimescaleDB)    │
│ (ACID, B-Tree Indexes)       │ (Time-Partitioned Chunks, Compression)   │
├──────────────────────────────┼──────────────────────────────────────────┤
│ - instruments                │ - ohlcv_records                          │
│ - exchange_calendars         │ - feature_values                         │
│ - users & api_keys           │ - regime_outputs                         │
│ - research_runs              │ - backtest_equity_curves                 │
│ - backtest_configurations    │ - data_quality_events                    │
│ - audit_logs                 │                                          │
└──────────────────────────────┴──────────────────────────────────────────┘
                               ▲
                               │
┌──────────────────────────────┴──────────────────────────────────────────┐
│                                 Redis                                   │
├──────────────────────────────┬──────────────────────────────────────────┤
│ In-Memory Caching            │ Operational State                        │
├──────────────────────────────┼──────────────────────────────────────────┤
│ - API response cache         │ - Celery task queue & worker heartbeats  │
│ - Regime timeline snapshots  │ - Rate limiting sliding-window counters  │
│ - Transition matrix cache    │ - Active user session tokens             │
└──────────────────────────────┴──────────────────────────────────────────┘
```

---

## 9. AI Research Assistant Architecture

The AI Research Assistant operates through a strictly bounded, read-only grounding pipeline designed to prevent hallucinations, protect data privacy, and enforce compliance:

```text
                  ┌──────────────────────┐
                  │    User Question     │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │   Research Context   │
                  │       Builder        │
                  └──────────┬───────────┘
                             │ Query Structured APIs
                  ┌──────────▼───────────┐
                  │    RegimeX Data /    │
                  │  Research Retrieval  │
                  └──────────┬───────────┘
                             │ Verified Grounding Payload
                  ┌──────────▼───────────┐
                  │  Grounding Context & │
                  │ System Instructions  │
                  └──────────┬───────────┘
                             │ Sanitized Prompt (No Secrets)
                  ┌──────────▼───────────┐
                  │     AI Provider      │
                  │       Adapter        │
                  └──────────┬───────────┘
                             │ Generated Response
                  ┌──────────▼───────────┐
                  │ Response Validation  │
                  │   & Anti-Advice /    │
                  │   Hallucination Gate │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │ User (with Citations │
                  │    & Disclaimers)    │
                  └──────────────────────┘
```

### AI Safeguards & Mandates:
1. **No Direct Database Access:** The LLM cannot execute arbitrary SQL queries or interact with persistence layers. It receives structured, sanitized JSON representations of verified platform analytics.
2. **Provenance & Citation:** Every assertion concerning market regimes, transition probabilities, or risk metrics must cite the underlying `run_id`, instrument symbol, and date range.
3. **No Financial Advice Enforcement (`FR-064`, `NFR-100`):** System prompts strictly instruct the model to decline personalized investment recommendations, portfolio allocations, or profit guarantees. A response validation filter scans output for advisory language.
4. **Uncertainty Communication (`NFR-101`):** Responses must convey model confidence scores, sample window limitations, and probabilistic caveats.

---

---

## 10. Requirements Traceability

The RegimeX architecture blueprint establishes an unbroken chain of traceability from the original product vision through requirements, architecture components, and formal architecture decisions:

```text
V01 Product Vision (V01/PRODUCT_FOUNDATION.md, V01/PRINCIPLES.md)
        ↓
V02 Functional Requirements (V02/SRS.md FR-001–FR-091)
        ↓
V02 Non-Functional Requirements (V02/SRS.md NFR-001–NFR-113)
        ↓
V03 Architecture Blueprint (V03/ARCHITECTURE.md, V03/MODULE_BOUNDARIES.md)
        ↓
Architecture Decisions (ADR-0001 through ADR-0005)
```

### Traceability Mapping Matrix

| Architecture Component | Addressed Functional Requirements | Addressed Non-Functional Requirements | Governing ADRs |
|------------------------|-----------------------------------|---------------------------------------|:--------------:|
| **Modular System Style** | All modules | NFR-001, NFR-008, NFR-026, NFR-064, NFR-075 | [ADR-0001](./decisions/ADR-0001-architecture-style.md) |
| **Market Discovery Domain** | FR-001 – FR-004 | NFR-029 (Scalability), NFR-091 (Symbol Validity) | — |
| **Market Data Domain & Abstraction** | FR-005 – FR-013 | NFR-002 (Perf), NFR-023 (Availability), NFR-034 (Idempotency), NFR-078 (Compatibility), NFR-085–088 (Data Quality) | [ADR-0002](./decisions/ADR-0002-data-provider-abstraction.md), [ADR-0004](./decisions/ADR-0004-provider-abstraction-pattern.md) |
| **Data Quality Gate** | FR-009, FR-011 | NFR-038 (Silent Corruption Prevention), NFR-085–093 (Data Quality) | [ADR-0004](./decisions/ADR-0004-provider-abstraction-pattern.md) |
| **Feature Engineering Pipeline** | FR-014 – FR-021 | NFR-003 (Perf), NFR-030 (Scale), NFR-032 (Reproducibility), NFR-093 (Quality Gate) | — |
| **Regime Detection & Model Abstraction** | FR-022 – FR-031 | NFR-004 (Perf), NFR-030 (Scale), NFR-032 (Reproducibility), NFR-078 (Compatibility), NFR-101 (Uncertainty) | [ADR-0003](./decisions/ADR-0003-regime-model-abstraction.md), [ADR-0005](./decisions/ADR-0005-regime-detector-interface-design.md) |
| **Regime Intelligence** | FR-032 – FR-037 | NFR-001 (Perf), NFR-032 (Reproducibility) | [ADR-0005](./decisions/ADR-0005-regime-detector-interface-design.md) |
| **Risk Analytics Engine** | FR-038 – FR-044 | NFR-001 (Perf), NFR-032 (Reproducibility), NFR-099 (No Guarantees), NFR-101 (Uncertainty) | — |
| **Strategy Backtesting Engine** | FR-045 – FR-055 | NFR-005 (Perf), NFR-032 (Reproducibility), NFR-098 (Audit), NFR-099 (No Guarantees) | — |
| **Research Workspace** | FR-056 – FR-059 | NFR-032 (Reproducibility), NFR-058 (Privacy), NFR-094, 097 (Auditability) | [ADR-0001](./decisions/ADR-0001-architecture-style.md) |
| **Grounded AI Architecture** | FR-060 – FR-066 | NFR-022 (Graceful Degradation), NFR-059 (Privacy), NFR-100 (No Advice), NFR-103 (No Hallucination) | — |
| **Identity, Security & API Gateway** | FR-067 – FR-081 | NFR-001 (Perf), NFR-009–020 (Security), NFR-026 (Scale), NFR-076 (API Compatibility) | [ADR-0001](./decisions/ADR-0001-architecture-style.md) |
| **Background Worker Harness** | FR-008, FR-045, FR-075 | NFR-008 (Workload Isolation), NFR-031 (Scalability), NFR-037 (Job Recovery) | [ADR-0001](./decisions/ADR-0001-architecture-style.md) |
| **Observability Infrastructure** | FR-079, FR-085 | NFR-039–048 (Structured Logging, Metrics, Tracing, Health Endpoints) | — |
| **Open-Source Self-Hosting** | FR-086 – FR-091 | NFR-075 (OS Compatibility), NFR-105 (License Compliance) | [ADR-0001](./decisions/ADR-0001-architecture-style.md) |

---

## 11. Architecture Risk Register

The following register documents the architectural risks identified for RegimeX, their evaluated impact, mitigation strategies, and residual uncertainties. These risks are managed proactively through automated verification gates, modular contracts, and ADR constraints:

| Risk | Impact | Mitigation Strategy | Residual Uncertainty |
|------|:------:|---------------------|----------------------|
| **Provider instability** | High | Adapter abstraction ([ADR-0002](./decisions/ADR-0002-data-provider-abstraction.md), [ADR-0004](./decisions/ADR-0004-provider-abstraction-pattern.md)) with circuit breakers and fallback adapters | Upstream vendor service availability & rate quota limits |
| **Historical data quality** | High | Multi-gate validation pipeline (Gates 1 & 2 in [DATA_FLOW.md](./DATA_FLOW.md)) and quarantine store | Source vendor reporting anomalies & calendar adjustments |
| **ML instability** | Medium / High | Common model abstraction ([ADR-0003](./decisions/ADR-0003-regime-model-abstraction.md), [ADR-0005](./decisions/ADR-0005-regime-detector-interface-design.md)) & convergence timeouts | Model-specific numerical quirks & covariance singularity |
| **AI hallucination** | High | Read-only grounding retrieval, zero raw database access, and automated anti-advisory output validation | Non-deterministic behaviors in commercial foundation LLMs |
| **Backtest computational cost** | Medium / High | Asynchronous Celery worker pools ([ADR-0001](./decisions/ADR-0001-architecture-style.md)) and per-user concurrency limits | Resource demand growth during deep multi-asset simulations |
| **Storage growth** | Medium | TimescaleDB hypertable chunking, columnar compression, and data retention policies | Long-term dataset expansion across high-frequency tick data |
| **Licensing restrictions** | High | Provider licensing metadata tracking, user-provided API key model, and raw redistribution blocks | Evolving intellectual property rules of commercial exchanges |
| **Architecture drift** | Medium | Mandatory ADR process, import boundary linters in CI, and interface compliance suites | Contributor discipline as open-source participation expands |

---

## 12. Disclaimer

RegimeX is an open-source research and analytics platform. It does not provide financial advice, investment recommendations, or guarantees of profit. All architecture and systems described herein are designed solely for quantitative market research and educational intelligence.

