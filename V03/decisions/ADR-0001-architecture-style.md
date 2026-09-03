# ADR-0001: Modular Monolith with Asynchronous Workers

**Status:** Accepted  
**Date:** 2026-09-03  
**Volume:** V03 — System Architecture  
**Deciders:** RegimeX Core Architecture Team  

---

## 1. Context

RegimeX is an open-source market intelligence and quantitative research platform designed for researchers, analysts, and developers. It requires both high-responsiveness for interactive user interfaces (dashboards, symbol queries, risk metrics) and heavy computational capabilities for long-running quantitative tasks (multi-year market data ingestion, feature generation, machine learning model training, walk-forward backtesting).

When designing the foundational system architecture, we must balance:
- Operational simplicity and single-command local setup for open-source contributors (`docker compose up`).
- Clean separation of concerns to prevent domain spaghetti.
- Horizontal scaling capability for high-compute workloads.
- Long-term viability without requiring complete architectural rewrites as platform usage and data volumes expand.

A premature microservices architecture would introduce distributed systems complexity (network latency, distributed transactions, service discovery, cross-service schema synchronization, complex debugging) that would severely hinder velocity, raise contributor barriers, and burden self-hosting operators.

---

## 2. Decision

> **RegimeX adopts a Modular Monolith with Asynchronous Workers architecture as its initial production deployment style.**

1. **Unified Application Codebase:** The entire core domain (market data, feature engineering, regime detection, risk, backtesting, research workspace) resides within a single, highly structured repository (`src/regimex/`).
2. **Strict Module Boundaries:** Logical modules communicate exclusively through well-defined internal interfaces. Cross-module imports must follow a strict acyclic dependency hierarchy. In-process dependency injection is enforced.
3. **Decoupled Asynchronous Workers:** Computationally intensive, high-latency tasks (historical ingestion, model fitting, backtest execution) are offloaded to background worker processes via an in-memory message broker (Redis / Celery).
4. **Stateless API Gateway:** The interactive API tier (FastAPI) remains strictly stateless, handling routing, authentication, request validation, and query dispatch.
5. **Future Microservices Readability:** Because all domain modules have strict boundaries, zero circular dependencies, and decoupled persistence repositories, any individual domain (e.g., Backtesting Engine or Ingestion Worker) can be extracted into an independent microservice in the future if organizational or scaling requirements warrant it.

---

## 3. Alternatives Considered

| Architecture Style | Description | Why Not Chosen |
|--------------------|-------------|----------------|
| **Premature Microservices** | Separate deployable services for Data, Features, Models, Risk, Backtest, and API from Day 1. | Excessive operational overhead; requires distributed tracing, service meshes, complex local Docker orchestration; steep barrier for open-source contributors; high latency for cross-module quantitative data transfer. |
| **Simple Monolith (Synchronous Only)** | Single web process executing all computations synchronously within request handlers. | Unacceptable user experience; long-running model fitting or backtesting would block HTTP worker threads, leading to request timeouts and severe performance degradation. |
| **Serverless Functions** | Deploying each algorithm and endpoint as cloud functions (AWS Lambda, Google Cloud Functions). | Violates open-source self-hosting and zero-vendor-lock-in principles; cold starts degrade performance; severe memory and runtime execution limits hinder long backtests. |

---

## 4. Consequences

### Positive
- **Operational Simplicity:** A single Docker Compose stack runs the entire platform locally or on a single VPS with minimal memory footprint.
- **Contributor-Friendly:** New contributors can run tests, add features, or introduce algorithms without configuring multi-service networking or external cloud dependencies.
- **Fast Internal Communication:** High-throughput feature matrices and time-series arrays are passed in-memory between modules without serialization/deserialization over internal HTTP networks.
- **Resilient Background Execution:** Long-running jobs run in isolated worker processes; job failures or memory spikes do not degrade interactive API availability.
- **Clear Evolutionary Path:** Modules are clean enough to be split into independent microservices when justified by real-world production metrics.

### Negative / Trade-offs
- **Discipline Required:** Developers must strictly adhere to module boundary rules and avoid shortcut cross-imports. Enforced via automated import linter checks in CI.
- **Shared Database:** Modules share the underlying PostgreSQL instance (though segregated by schema tables). Schema migrations require coordination.

---

## 5. Requirements Addressed

- **V01 Vision:** Democratized open-source self-hosting without proprietary cloud dependencies.
- **V02 Functional Requirements:** FR-001–FR-091 (modular domain separation across data, features, models, backtesting).
- **V02 Non-Functional Requirements:**
  - `NFR-001`, `NFR-007`: Interactive API latency and concurrency.
  - `NFR-008`: Background workload isolation.
  - `NFR-026`, `NFR-027`: Stateless API and horizontal worker scaling.
  - `NFR-064`: Modular architecture.
  - `NFR-075`: Self-hosting compatibility via standard Docker Compose.
