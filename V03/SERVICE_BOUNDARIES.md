# Logical Service Boundaries

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

RegimeX adopts a **Modular Monolith with Asynchronous Workers** architectural style for initial production releases. This design gives developers and operators the simplicity of a single deployable unit while enforcing rigorous, decoupled logical service boundaries.

These logical boundaries ensure that as user concurrency, data ingestion volume, and analytical computational demands expand, specific high-load subcomponents (such as analytical workers or public presentation tiers) can be scaled horizontally or extracted into independent microservices without refactoring core business logic.

---

## 2. Service Boundary Map

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            1. Web Application                               │
│                         (Presentation Layer Only)                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / JSON / WebSockets
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            2. API Application                               │
│            (Auth, Request Validation, Routing, Orchestration)               │
└──────────────┬───────────────────────────────────────────────┬──────────────┘
               │ In-Process Internal Interface                 │ Async Message
               │                                               │ Queue (Redis)
┌──────────────▼──────────────────────────────┐ ┌──────────────▼──────────────┐
│               3. Core Domain                │ │       4. Worker System      │
│  (Market Data, Features, Regime, Risk,      │ │ (Model Training, Ingestion, │
│   Backtesting, Research Business Logic)     │ │  Large Backtests, Reports)  │
└──────┬──────────────────────┬───────────────┘ └──────┬──────────────┬───────┘
       │                      │                        │              │
       │ SQL / Driver         │ In-Memory Key-Value    │ SQL / Driver │ In-Memory Key-Value
┌──────▼──────────────┐ ┌─────▼───────────────┐        │              │
│     5. Storage      │ │    6. Cache         │◄───────┘              │
│ (Postgres/Timescale)│ │    (Redis)          │                       │
└─────────────────────┘ └─────────────────────┘                       │
       ▲                                                              │
       │                                                              │
┌──────┴──────────────────────────────────────────────────────────────▼───────┐
│                           7. External Providers                             │
│              (Market Data Vendors, AI / LLM Foundation Models)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ▲
                                       │ Telemetry / Logs / Metrics / Traces
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                             8. Observability                                │
│         (Prometheus Metrics, Structured JSON Logs, Distributed Tracing)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Service Boundary Specifications

### 3.1 Web Application

- **Primary Responsibility:** User presentation, data visualization, interactive charting (regime timelines, transition matrices, drawdown curves), workspace configuration forms, and AI chat interface. Presentation layer only. Strictly forbidden from executing financial calculations, direct database access, or holding long-lived application secrets.
- **Communication Mechanism:** Communicates with the API Application exclusively over standard HTTPS (RESTful JSON endpoints) and WebSockets (for live job progress and streaming AI responses).
- **Failure Behavior:** If the Web Application crashes, client browsers render offline fallback states; no data loss or corruption occurs. If the downstream API is unreachable, the web client displays structured network error notices and retries with backoff.
- **Scaling Characteristics:** Completely stateless. Can be scaled horizontally behind standard reverse proxies or CDNs. Static assets can be served directly from object storage or web servers.
- **Security Boundary:** Runs entirely in the client browser context or static SSR server. Holds ephemeral session JWTs or cookies. Has no privileged network access to databases, queues, or internal compute nodes.

---

### 3.2 API Application

- **Primary Responsibility:** Public and private API gateway. Enforces transport security, rate limiting, request validation, authentication (API keys, JWT), role-based access control (RBAC), request logging, response formatting, and task orchestration. Dispatches long-running jobs to the Worker System and queries read-optimized models from Storage/Cache.
- **Communication Mechanism:** Receives inbound client HTTPS traffic; communicates with Core Domain via internal Python module interfaces; dispatches asynchronous tasks to the Worker System via message broker (Redis/Celery); accesses Cache and Storage via connection pools.
- **Failure Behavior:** Graceful degradation. If Cache fails, falls back directly to persistent storage. If Worker queue is congested, rejects job submissions with `429 Too Many Requests` or `503 Service Unavailable` with retry headers rather than dropping jobs silently.
- **Scaling Characteristics:** Completely stateless. Instances can be scaled horizontally behind an HTTP load balancer (e.g., Caddy, Nginx, AWS ALB, Cloudflare).
- **Security Boundary:** First line of defense. Terminates or verifies TLS, validates all incoming payloads against strict Pydantic schemas, sanitizes parameters against injection attacks, enforces authorization boundaries between user roles (`public`, `researcher`, `admin`).

---

### 3.3 Core Domain

- **Primary Responsibility:** Pure business logic and mathematical computation for financial market analysis. Includes:
  - Market data normalization and canonical typing
  - Data quality gate evaluation
  - Feature engineering mathematics and point-in-time enforcement
  - Regime detection model abstractions and inference pipelines
  - Regime intelligence and transition matrix calculations
  - Regime-conditional risk metrics (VaR, CVaR, drawdowns)
  - Event-driven backtesting execution engine
  - Research workspace reproducibility and experiment lineage
- **Communication Mechanism:** Direct in-process typed function and method calls. Interacts with storage via abstract repository interfaces (`MarketDataRepository`, `RegimeRepository`, `RiskRepository`, `BacktestRepository`).
- **Failure Behavior:** Throws strongly-typed domain exceptions (`DataQualityError`, `LookAheadBiasError`, `ModelFitError`). Never crashes the host process; errors bubble cleanly to the API boundary or Worker harness.
- **Scaling Characteristics:** Scales with the host process. In the modular monolith, CPU-heavy operations are offloaded to Worker nodes to keep interactive API threads unblocked.
- **Security Boundary:** Internal application layer. Encapsulates business invariants and data integrity rules. Has no direct knowledge of HTTP headers, sessions, or raw database connection strings.

---

### 3.4 Worker System

- **Primary Responsibility:** Asynchronous, non-blocking execution of long-running, batch, or high-compute workloads:
  - Bulk historical market data ingestion and multi-year backfilling
  - Full-universe feature matrix calculations
  - Regime detection model training and historical sequence fitting
  - Multi-parameter backtest simulations and walk-forward optimizations
  - Research report compilation and analytical export generation
- **Communication Mechanism:** Consumes tasks from Redis message queues (via Celery/task runner); writes intermediate and final computation outputs to Storage and Cache; updates task status records in the database.
- **Failure Behavior:** Isolated worker process model. A worker thread or sub-process crashing due to out-of-memory (OOM) or unhandled computation exceptions does not bring down the API service. Tasks automatically retry using configured backoff strategies or move to dead-letter queues after exceeding maximum attempts.
- **Scaling Characteristics:** Horizontally scalable compute workers. Worker concurrency can be dynamically increased by launching additional container replicas pointing to the shared message broker.
- **Security Boundary:** Internal secure subnet. Does not expose open HTTP/listening ports to the public internet. Accesses persistent storage and external provider APIs using isolated internal service credentials.

---

### 3.5 Storage

- **Primary Responsibility:** Reliable, durable, ACID-compliant persistence of all structured platform data:
  - Canonical OHLCV historical time-series market data
  - Validated financial features and feature metadata
  - Fitted regime model weights, parameters, and historical regime classification timelines
  - Risk engine outputs and portfolio analytics
  - Backtest trade logs, equity curves, and performance attribution records
  - User accounts, authentication credentials (hashed), API keys, and audit logs
- **Communication Mechanism:** Interacts with API and Worker services via async database connection pools over standard PostgreSQL wire protocols (TCP/TLS).
- **Failure Behavior:** Relies on relational ACID guarantees, write-ahead logging (WAL), and automated scheduled backups. Connection pooling layers handle transient connection drops with connection recycling and retries.
- **Scaling Characteristics:** Scaled vertically for high compute/memory workloads; partitioned/chunked across time-series dimensions using hypertable abstractions (TimescaleDB); read replicas can be added for read-heavy analytical queries.
- **Security Boundary:** Isolated database network tier. Never accessible directly from public networks or client applications. Enforces encrypted storage at rest and encrypted transit (TLS).

---

### 3.6 Cache

- **Primary Responsibility:** High-speed in-memory data store for low-latency operational data:
  - API response caching for immutable historical analytical outputs
  - Rate limiting bucket counters and IP throttling state
  - Task queue messaging and worker job state tracking
  - Ephemeral user session state and authentication tokens
- **Communication Mechanism:** TCP connections over standard Redis serialization protocols.
- **Failure Behavior:** Soft-failure degradation. If the cache becomes unavailable, the API layer bypasses cached reads and queries persistent storage directly. Rate limiting fails closed or open depending on configured security posture.
- **Scaling Characteristics:** In-memory horizontal clustering or vertical memory expansion. Redis replication / Sentinel support for high-availability failover.
- **Security Boundary:** Internal network tier. Protected with authentication credentials and isolated from public access.

---

### 3.7 External Providers

- **Primary Responsibility:** External data feeds and third-party foundation services:
  - Upstream market data vendors (Yahoo Finance, Alpha Vantage, Polygon, local exchange feeds)
  - External AI / LLM foundation model APIs (OpenAI, Anthropic, or self-hosted local LLMs)
- **Communication Mechanism:** Outbound HTTPS calls executed strictly through internal adapter classes (`MarketDataProvider`, `AIProviderAdapter`).
- **Failure Behavior:** External outages are handled using circuit breakers, exponential backoff retries, and fallback to cached/historical data. An external provider outage must never cause internal data corruption or service crashes.
- **Scaling Characteristics:** Constrained by third-party rate limits and quota tiers. Internal rate limiters ensure RegimeX does not exceed external vendor limits.
- **Security Boundary:** Outbound egress only. Third-party provider API keys are stored in secure environment secrets and never exposed to clients or logged in telemetry.

---

### 3.8 Observability

- **Primary Responsibility:** Cross-cutting platform telemetry, monitoring, and operational visibility:
  - Centralized structured JSON application logs with correlated `request_id` and `run_id`
  - Prometheus-compatible metrics scraping endpoints (`/metrics`)
  - Distributed request tracing and span propagation
  - Health check endpoints (`/health` for process liveness, `/ready` for end-to-end dependency verification)
  - Real-time performance degradation alerts and threshold monitors
- **Communication Mechanism:** Scraped via HTTP pulls or pushed over UDP/TCP telemetry pipelines.
- **Failure Behavior:** Asynchronous, non-blocking telemetry emission. A failure in the logging aggregator or metrics collector must never block or degrade primary financial computation or API request serving.
- **Scaling Characteristics:** Scales independently via time-series metric databases and log aggregation clusters.
- **Security Boundary:** Read access to internal metrics and structured logs is restricted to authorized operators and administrators. All sensitive customer tokens, passwords, and secrets are redacted prior to log emission.
