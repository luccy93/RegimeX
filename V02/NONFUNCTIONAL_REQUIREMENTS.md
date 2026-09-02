# Non-Functional Requirements

**RegimeX — Open-Source Market Intelligence Platform**

> Non-functional requirements define how the system behaves, not what it does. These requirements constrain all implementation decisions from V04 onward.

---

## NFR-PERF — Performance

| ID | Requirement | Target | Priority |
|----|------------|--------|---------|
| NFR-PERF-001 | API response time (p95) for regime query endpoints shall be ≤ 500ms under normal load. | ≤ 500ms | High |
| NFR-PERF-002 | API response time (p95) for market data retrieval (1 year OHLCV) shall be ≤ 1000ms. | ≤ 1s | High |
| NFR-PERF-003 | Feature computation for a single instrument over 5 years of daily data shall complete in ≤ 10 seconds. | ≤ 10s | Medium |
| NFR-PERF-004 | Regime detection (HMM, 5 years daily, 3 regimes) shall complete in ≤ 30 seconds. | ≤ 30s | Medium |
| NFR-PERF-005 | Backtesting a daily strategy over 10 years of data shall complete in ≤ 60 seconds. | ≤ 60s | Medium |
| NFR-PERF-006 | Market data ingestion shall process ≥ 1,000 OHLCV bars per second. | ≥ 1,000 bars/s | Medium |
| NFR-PERF-007 | Web platform initial page load (LCP) shall be ≤ 2.5 seconds on a standard broadband connection. | ≤ 2.5s | High |
| NFR-PERF-008 | The API shall support ≥ 100 concurrent authenticated users without degradation beyond p95 targets. | 100 concurrent users | Medium |

---

## NFR-REL — Reliability

| ID | Requirement | Target | Priority |
|----|------------|--------|---------|
| NFR-REL-001 | The platform API shall target 99.5% uptime for production deployments. | 99.5% uptime | High |
| NFR-REL-002 | The platform shall recover automatically from transient upstream data provider failures using retry-with-backoff. | Automatic retry | Critical |
| NFR-REL-003 | A data ingestion failure shall not corrupt previously ingested data. | Atomic writes | Critical |
| NFR-REL-004 | All write operations to persistent storage shall be atomic and idempotent. | Atomic + idempotent | Critical |
| NFR-REL-005 | The platform shall produce deterministic outputs given the same inputs, software version, and configuration. | Deterministic | Critical |
| NFR-REL-006 | The platform shall generate structured error messages with sufficient context for diagnosis without access to production systems. | Structured errors | High |
| NFR-REL-007 | Database backups shall be automated and tested at regular intervals in production deployments. | Automated backups | High |

---

## NFR-SCALE — Scalability

| ID | Requirement | Target | Priority |
|----|------------|--------|---------|
| NFR-SCALE-001 | The platform architecture shall support horizontal scaling of the API layer (stateless services). | Horizontal scaling | High |
| NFR-SCALE-002 | The market data storage layer shall support at least 50 million OHLCV bars without performance degradation. | 50M bars | High |
| NFR-SCALE-003 | The feature computation pipeline shall be parallelizable across instruments and date ranges. | Parallel execution | Medium |
| NFR-SCALE-004 | The platform shall support adding new instruments without schema migrations. | Schema-extensible | High |
| NFR-SCALE-005 | The platform shall support adding new regime detection algorithms without modifying core regime detection consumers. | Plugin architecture | Critical |
| NFR-SCALE-006 | The platform shall support adding new market data providers without modifying business logic. | Provider abstraction | Critical |

---

## NFR-SEC — Security

| ID | Requirement | Constraint | Priority |
|----|------------|-----------|---------|
| NFR-SEC-001 | No credentials, API keys, or secrets shall appear in source code or git history. | Hard constraint | Critical |
| NFR-SEC-002 | All API endpoints (except public read-only) shall require authentication. | Hard constraint | Critical |
| NFR-SEC-003 | Authentication tokens shall have configurable expiry and support revocation. | Hard constraint | Critical |
| NFR-SEC-004 | All API inputs shall be validated and sanitized before processing. | Hard constraint | Critical |
| NFR-SEC-005 | The API shall enforce rate limiting to prevent abuse. | Hard constraint | Critical |
| NFR-SEC-006 | All data in transit shall be encrypted using TLS 1.2 or later in production. | Hard constraint | Critical |
| NFR-SEC-007 | Dependency vulnerability scanning shall run in CI and block merges for high/critical severity CVEs. | Hard constraint | High |
| NFR-SEC-008 | Container images shall run as non-root users. | Hard constraint | High |
| NFR-SEC-009 | Security audit logs shall record authentication events, permission denials, and administrative actions. | Hard constraint | High |
| NFR-SEC-010 | The platform shall have a documented security vulnerability disclosure process. | Procedural | High |

---

## NFR-OBS — Observability

| ID | Requirement | Target | Priority |
|----|------------|--------|---------|
| NFR-OBS-001 | All services shall emit structured JSON logs. | Structured logs | Critical |
| NFR-OBS-002 | All API requests shall be logged with: method, path, status, latency, and user identity. | Per-request logs | Critical |
| NFR-OBS-003 | The platform shall emit metrics for: API request rate, error rate, latency percentiles, ingestion throughput. | Key metrics | High |
| NFR-OBS-004 | Distributed traces shall link API requests to downstream database and computation operations. | Distributed tracing | Medium |
| NFR-OBS-005 | Alerting rules shall be defined for: error rate > 1%, p95 latency > 2x SLO, ingestion failures. | Alerting | High |
| NFR-OBS-006 | The platform shall expose a `/health` endpoint and a `/ready` endpoint at the service level. | Health endpoints | Critical |

---

## NFR-MAINT — Maintainability

| ID | Requirement | Constraint | Priority |
|----|------------|-----------|---------|
| NFR-MAINT-001 | Core module unit test coverage shall be ≥ 85% (line coverage). | ≥ 85% coverage | High |
| NFR-MAINT-002 | All public interfaces shall be type-annotated. | Hard constraint | Critical |
| NFR-MAINT-003 | All public functions, classes, and modules shall have docstrings. | Hard constraint | Critical |
| NFR-MAINT-004 | Code shall pass the configured formatter, linter, and type checker without errors before merge. | Hard constraint | Critical |
| NFR-MAINT-005 | Breaking changes to public API contracts shall be versioned and documented with a migration guide. | Hard constraint | Critical |
| NFR-MAINT-006 | All dependency upgrades shall be tested against the full test suite before merge. | Hard constraint | High |
| NFR-MAINT-007 | A new developer shall be able to set up a local development environment in under 15 minutes following the setup guide. | ≤ 15 minutes | High |

---

## NFR-DATA — Data Integrity

| ID | Requirement | Constraint | Priority |
|----|------------|-----------|---------|
| NFR-DATA-001 | No feature computation shall use data from timestamps later than the computation timestamp (no look-ahead bias). | Hard constraint | Critical |
| NFR-DATA-002 | No regime detection output shall be generated using future data relative to the detection timestamp. | Hard constraint | Critical |
| NFR-DATA-003 | No backtest strategy shall receive data not available at the time of the simulated trading decision. | Hard constraint | Critical |
| NFR-DATA-004 | Data quality violations (gaps, outliers) shall be logged and surfaced to operators — never silently ignored. | Hard constraint | Critical |
| NFR-DATA-005 | All stored datasets shall have a version fingerprint that changes when underlying data changes. | Hard constraint | Critical |
| NFR-DATA-006 | The platform shall not mix adjusted and unadjusted price data within a computation without explicit documentation. | Hard constraint | Critical |

---

## NFR-COMPAT — Compatibility and Portability

| ID | Requirement | Target | Priority |
|----|------------|--------|---------|
| NFR-COMPAT-001 | The platform shall be self-hostable on any Linux host with Docker and Docker Compose installed. | Self-hosting | Critical |
| NFR-COMPAT-002 | The platform shall not depend on any proprietary cloud service for core functionality. | Open-source stack | Critical |
| NFR-COMPAT-003 | The Python SDK shall support Python 3.10 and later. | Python ≥ 3.10 | High |
| NFR-COMPAT-004 | The web platform shall support the latest two major versions of Chrome, Firefox, and Safari. | Modern browsers | High |
