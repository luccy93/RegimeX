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

To prevent architectural bloat and maintain contributor accessibility, RegimeX enforces a strict technology policy:

### Confirmed Architectural Stack
- **Language:** Python 3.10+ (type-annotated domain engine, scientific stack) and TypeScript (frontend web application).
- **API Framework:** FastAPI (high-performance asynchronous REST routing, automatic OpenAPI specification generation).
- **Presentation Framework:** Next.js / React (modern, responsive web dashboards, SSR capabilities).
- **Primary Persistence:** PostgreSQL 15+ with TimescaleDB extension (relational ACID integrity combined with high-performance time-series hypertables).
- **In-Memory Cache & Message Broker:** Redis 7+ (ephemeral cache, rate-limiting store, and Celery task broker).
- **Task Execution Harness:** Celery (robust, distributed background task processing).
- **Numerical & ML Core:** NumPy, pandas, scikit-learn, hmmlearn, statsmodels, scipy.
- **Code Quality & Verification:** Ruff (formatting and linting), mypy (static type checking), pytest (unit, integration, and compliance testing).
- **Containerization:** Docker and Docker Compose (single-command local deployment).

### Technologies Explicitly Excluded for V03
The following technologies are deliberately omitted as unnecessary complexity for current requirements:
- **Kafka / RabbitMQ:** Redis provides sufficient throughput and simplicity for current task queue and caching needs.
- **Kubernetes:** Imposes excessive operational complexity for self-hosters; Docker Compose fulfills all current deployment requirements.
- **Dedicated Vector Databases (e.g., Pinecone, Qdrant, Milvus):** Grounded AI retrieval in RegimeX relies on structured SQL/time-series metadata querying, not unstructured semantic similarity search. PostgreSQL with `pgvector` can be introduced in V21 if semantic document retrieval is required.
- **Graph Databases (Neo4j):** Relational tables cleanly model asset correlations and transition matrices.

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

## 10. Traceability Matrix

The architecture blueprint directly satisfies the requirements defined in V02:

| Architecture Component | Addressed Functional Requirements | Addressed Non-Functional Requirements |
|------------------------|-----------------------------------|---------------------------------------|
| **Market Discovery Domain** | FR-001 – FR-004 | NFR-029 (Scalability), NFR-091 (Symbol Validity) |
| **Market Data Domain & Abstraction** | FR-005 – FR-013 | NFR-002 (Perf), NFR-023 (Availability), NFR-034 (Idempotency), NFR-078 (Compatibility), NFR-085–088 (Data Quality) |
| **Data Quality Gate** | FR-009, FR-011 | NFR-038 (Silent Corruption Prevention), NFR-085–093 (Data Quality) |
| **Feature Engineering Pipeline** | FR-014 – FR-021 | NFR-003 (Perf), NFR-030 (Scale), NFR-032 (Reproducibility), NFR-093 (Quality Gate) |
| **Regime Detection & Model Abstraction** | FR-022 – FR-031 | NFR-004 (Perf), NFR-030 (Scale), NFR-032 (Reproducibility), NFR-078 (Compatibility), NFR-101 (Uncertainty) |
| **Regime Intelligence** | FR-032 – FR-037 | NFR-001 (Perf), NFR-032 (Reproducibility) |
| **Risk Analytics Engine** | FR-038 – FR-044 | NFR-001 (Perf), NFR-032 (Reproducibility), NFR-099 (No Guarantees), NFR-101 (Uncertainty) |
| **Strategy Backtesting Engine** | FR-045 – FR-055 | NFR-005 (Perf), NFR-032 (Reproducibility), NFR-098 (Audit), NFR-099 (No Guarantees) |
| **Research Workspace** | FR-056 – FR-059 | NFR-032 (Reproducibility), NFR-058 (Privacy), NFR-094, 097 (Auditability) |
| **Grounded AI Architecture** | FR-060 – FR-066 | NFR-022 (Graceful Degradation), NFR-059 (Privacy), NFR-100 (No Advice), NFR-103 (No Hallucination) |
| **Identity, Security & API Gateway** | FR-067 – FR-081 | NFR-001 (Perf), NFR-009–020 (Security), NFR-026 (Scale), NFR-076 (API Compatibility) |
| **Background Worker Harness** | FR-008, FR-045, FR-075 | NFR-008 (Workload Isolation), NFR-031 (Scalability), NFR-037 (Job Recovery) |
| **Observability Infrastructure** | FR-079, FR-085 | NFR-039–048 (Structured Logging, Metrics, Tracing, Health Endpoints) |
| **Open-Source Self-Hosting** | FR-086 – FR-091 | NFR-075 (OS Compatibility), NFR-105 (License Compliance) |

---

## 11. Architecture Risks & Mitigations

| Risk | Impact | Mitigation Strategy | Residual Uncertainty |
|------|--------|---------------------|----------------------|
| **1. Upstream Data Feed Instability / Rate Limits** | Ingestion failures, stale market data | Provider Abstraction with circuit breakers, exponential backoff, and multi-provider fallback adapters | Vendor API pricing or terms of service changes |
| **2. Look-Ahead Bias Contamination** | Invalidated quantitative research, false strategy confidence | Automated CI bias checking, strict $t \le T$ slice validation, immutable historical dataset versioning | Subtle temporal leaks in complex corporate action re-indexing |
| **3. High Computational Load During Backtests** | Server resource exhaustion, API unresponsiveness | Asynchronous worker isolation (Celery), per-user concurrency quotas, resource limits | Sizing hardware requirements for extreme multi-asset Monte Carlo runs |
| **4. Regime Model Non-Convergence / Numerical Instability** | Model fitting exceptions, infinite loops | Enforced iteration timeouts, fallback initializations, standard covariance regularization | Solver convergence quirks on near-singular feature covariance matrices |
| **5. AI Assistant Hallucination / Unsupported Claims** | Misleading research interpretations, reputational damage | Strict grounding retrieval pipelines, structured prompt templates, output validation filters | Non-deterministic edge cases in foundation model reasoning |
| **6. Market Data Storage Bloat** | High disk consumption, degraded query latency | Hypertables with automated chunking, columnar data compression, data retention policies | Multi-decade tick-level storage capacity planning |
| **7. Contributor Architecture Drift** | Architectural fragmentation, leaking module boundaries | Automated import linters in CI, interface compliance test suites, strict code review against ADRs | Community contributor onboarding friction |
| **8. External Data Redistribution Restrictions** | Legal / licensing violations for self-hosters | Strict platform terms, raw export restrictions, clear user-provided API key architecture | Evolving intellectual property policies of commercial market exchanges |

---

## 12. Disclaimer

RegimeX is an open-source research and analytics platform. It does not provide financial advice, investment recommendations, or guarantees of profit. All architecture and systems described herein are designed solely for quantitative market research and educational intelligence.
