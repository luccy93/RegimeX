# Logical Deployment Topology

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

This document specifies the logical deployment topology for RegimeX. The platform is designed from the ground up to be **self-hostable using standard open-source containerization (`docker compose`)** on commodity Linux hardware or standard virtual machines, requiring zero proprietary cloud dependencies.

> ⚠️ **Deployment Status Notice:** RegimeX is in the architecture specification phase (V03). This document specifies the *logical production and development topologies* required for subsequent implementation volumes (V04+). RegimeX does not claim to have active live production deployments, nor does it prescribe a proprietary cloud hosting vendor.

---

## 2. Component Classification Matrix

Every architectural component in the deployment topology is categorized by its network exposure, statefulness, and operational role:

| Component | Container / Process | Network Exposure | Statefulness | Primary Responsibility |
|-----------|---------------------|------------------|--------------|------------------------|
| **Edge / Reverse Proxy** | `caddy:alpine` | **Public-Facing** | Stateless | Inbound TLS 1.2+ termination, static caching, reverse proxy routing (Ports 80, 443). |
| **Web Presentation Tier** | `regimex/web` (Next.js) | **Internal (behind proxy)** | Stateless | Server-side rendering, user dashboard, chart visualization, client-side state. |
| **API Application Tier** | `regimex/api` (FastAPI) | **Internal (behind proxy)** | Stateless | REST API, authentication, RBAC, schema validation, rate-limiting, job dispatch. |
| **Compute Workers** | `regimex/worker` (Celery) | **Internal Only** | Stateless | Asynchronous execution of data ingestion, feature generation, ML training, backtests. |
| **Periodic Scheduler** | `regimex/worker` (Beat) | **Internal Only** | Stateless | Cron scheduling for market data synchronization and data freshness checks. |
| **Relational & Time-Series DB**| `timescaledb-ha:pg15` | **Internal Only** | **Stateful** | Persistent storage for canonical OHLCV, features, regime outputs, and users. |
| **In-Memory Cache & Broker** | `redis:7-alpine` | **Internal Only** | **Stateful (AOF)** | Fast transient caching, sliding-window rate limit counters, task queue messaging. |
| **External Integrations** | Outbound HTTP Adapters | **Outbound-Only** | Stateless | Secure egress connections to external market data and AI foundation APIs. |
| **Observability Sinks** | Prometheus / JSON logs | **Internal / Admin** | **Stateful** | Metrics scraping, structured log aggregation, health telemetry probes. |
| **Backup System** | Automated Backup Script | **Internal / Admin** | **Stateful** | Scheduled cryptographic database dumps and point-in-time recovery archives. |

---

## 3. Logical Production Topology

The production topology segregates services into isolated network zones within a private Docker bridge network (`regimex_net`), exposing only the reverse proxy to the public internet.

```text
                                  Public Internet
                                         │
                                         ▼ HTTPS (443) / HTTP (80)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Zone 1: Edge Perimeter Tier                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Caddy Reverse Proxy / TLS Termination                                          │   │
│   │ - Automatic Let's Encrypt / ZeroSSL TLS certificates                          │   │
│   │ - HTTP -> HTTPS redirection                                                    │   │
│   │ - Reverse proxy pass to Web (:3000) and API (:8000)                            │   │
│   └───────────────────────┬────────────────────────────────┬───────────────────────┘   │
└───────────────────────────┼────────────────────────────────┼───────────────────────────┘
                            │                                │
┌───────────────────────────┼────────────────────────────────┼───────────────────────────┐
│ Zone 2: Application Tier  │ (Internal HTTP)                │ (Internal HTTP)           │
│   ┌───────────────────────▼────────┐              ┌────────▼───────────────────────┐   │
│   │ Web Presentation Application   │              │ FastAPI REST API Server        │   │
│   │ - Next.js SSR / Static React   │              │ - Pydantic v2 Request Validation│  │
│   │ - Port: 3000 (Internal Only)   │              │ - Auth & Rate Limiting Engine  │   │
│   └────────────────────────────────┘              │ - Port: 8000 (Internal Only)   │   │
│                                                   └───────┬────────────────────────┘   │
└───────────────────────────────────────────────────────────┼────────────────────────────┘
                                                            │
┌───────────────────────────────────────────────────────────┼────────────────────────────┐
│ Zone 3: Asynchronous Compute & Queue Tier                 │                            │
│   ┌────────────────────────┐      Redis Protocol          │ Redis Protocol             │
│   │ Celery Beat Scheduler  │ ──────────────────────┐      │                            │
│   │ - Periodic Data Ingest │                       │      │                            │
│   └────────────────────────┘                       │      │                            │
│                                                    ▼      ▼                            │
│   ┌────────────────────────┐             ┌─────────────────────────────────────────┐   │
│   │ Celery Worker Nodes    │◄───────────►│ Redis In-Memory Cache & Message Broker  │   │
│   │ - Data Ingestion       │             │ - Task Queue (Celery Broker)            │   │
│   │ - Feature Generation   │             │ - Rate Limit Counters                   │   │
│   │ - Regime ML Fitting    │             │ - API Response Cache                    │   │
│   │ - Strategy Backtesting │             │ - Port: 6379 (Internal Only)            │   │
│   └───────────┬────────────┘             └─────────────────────────────────────────┘   │
└───────────────┼───────────────────────────────────────────┬────────────────────────────┘
                │                                           │
┌───────────────┼───────────────────────────────────────────┼────────────────────────────┐
│ Zone 4: Persistence Tier                                  │ (AsyncPG Pool)             │
│               │ (AsyncPG Pool)                            │                            │
│               └───────────────────────────┬───────────────┘                            │
│                                           │                                            │
│                                           ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ PostgreSQL 15+ & TimescaleDB                                                   │   │
│   │ - Time-Series Hypertables (ohlcv_records, feature_values, regime_outputs)      │   │
│   │ - Relational Tables (users, api_keys, research_runs, audit_logs)               │   │
│   │ - Volume: regimex_postgres_data (Persistent Disk Mount)                        │   │
│   │ - Port: 5432 (Internal Only, strictly blocked from host/public)                │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Network Boundaries & Port Isolation

Security boundaries are strictly enforced through Docker virtual network isolation:

| Service | Internal Port | Host Port (Dev) | Host Port (Prod) | Exposure Rule |
|---------|:-------------:|:---------------:|:----------------:|---------------|
| `proxy` | 80, 443 | 80, 443 | **80, 443** | **Public Facing:** Only service directly bound to host interface. |
| `web` | 3000 | 3000 | *None* | **Internal:** Accessible only via Caddy proxy. |
| `api` | 8000 | 8000 | *None* | **Internal:** Accessible only via Caddy proxy. |
| `worker`| *None* | *None* | *None* | **Internal Only:** No listening TCP socket; egress to Redis and DB. |
| `redis` | 6379 | 6379 (localhost) | *None* | **Internal Only:** Protected by Redis password; no host port mapping in prod. |
| `db` | 5432 | 5432 (localhost) | *None* | **Internal Only:** Accessible only from internal `regimex_net`. |

---

## 5. Local Development Topology

For local software development, the edge proxy is bypassed to enable direct developer inspection and hot reloading:

```text
Developer Localhost
        │
        ├── localhost:3000 ──► Next.js Web Dev Server (npm run dev)
        ├── localhost:8000 ──► FastAPI API Server (uvicorn --reload)
        ├── localhost:5432 ──► PostgreSQL + TimescaleDB Container
        └── localhost:6379 ──► Redis Container
```

---

## 6. Observability, Health & Telemetry Topology

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Observability Framework                         │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Health Probes (HTTP Pull)                                           │
│    - GET /api/v1/health -> 200 OK (Process liveness, instant response) │
│    - GET /api/v1/ready  -> 200 OK (Database & Redis connection check)  │
│                                                                        │
│ 2. Metrics Scraping (Prometheus Pull)                                  │
│    - GET /metrics       -> Standard Prometheus formatted metrics      │
│      (API latencies, active worker counts, queue depths, error rates)  │
│                                                                        │
│ 3. Structured Logging (Stdout / Stderr Pipeline)                       │
│    - JSON formatted structlog logs emitted to container streams        │
│    - Tagged with request_id, user_id, run_id, and service name         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Disaster Recovery & Backup Topology

To guarantee business continuity without relying on proprietary cloud snapshots, RegimeX establishes an automated, file-based backup architecture:

```text
           Cron Scheduled Backup Daemon
                         │
                         ▼
     ┌───────────────────────────────────────┐
     │ 1. Logical PostgreSQL Dump (pg_dump)  │
     │    - Consistent, non-blocking snapshot│
     │    - Compresses relational & hypertables
     └───────────────────┬───────────────────┘
                         │
                         ▼
     ┌───────────────────────────────────────┐
     │ 2. Cryptographic Checksum & Gzip      │
     │    - Generates SHA-256 integrity hash │
     └───────────────────┬───────────────────┘
                         │
                         ▼
     ┌───────────────────────────────────────┐
     │ 3. Secure Storage Mount (Backup Vol)  │
     │    - Local volume or operator rsync   │
     │    - Retained according to NFR-081/082│
     └───────────────────────────────────────┘
```

- **Target RPO (Recovery Point Objective):** $\le 24$ hours (configurable via backup frequency; production target TBD in capacity planning).
- **Target RTO (Recovery Time Objective):** $\le 2$ hours (tested via automated restoration procedure).
- **Integrity Validation:** Every backup verification run executes an automated container restore to a temporary test database, asserting table record counts and foreign key constraints.

---

## 8. Horizontal Scaling Architecture

When platform workload scales beyond a single-node host:

1. **API Scalability:** Deploy multiple stateless `api` containers behind an external load balancer (HAProxy, AWS ALB, Cloudflare). No sticky sessions required.
2. **Worker Scalability:** Spawn additional `worker` containers across one or more compute nodes consuming from the centralized Redis task queue.
3. **Database Scalability:** TimescaleDB chunk compression reduces disk space by up to 90%; read-replicas can be added for read-heavy historical backtest queries.
