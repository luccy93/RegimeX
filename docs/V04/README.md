# V04 — Monorepo Engineering Foundation

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V04 — Monorepo Engineering Foundation  
**Commit:** `chore(monorepo): establish application and package structure`  
**Status:** ✅ Commit 01 Complete

---

## Purpose of This Volume

V04 translates the V03 architecture blueprint into a working repository structure. Where V03 defined *what* to build and *why*, V04 explains *how the repository implements it*.

This document is the **V04 engineering guide** — it does not duplicate V03 architecture decisions.

> For architecture rationale, see [`V03/ARCHITECTURE.md`](../V03/ARCHITECTURE.md).  
> For module boundary specifications, see [`V03/MODULE_BOUNDARIES.md`](../V03/MODULE_BOUNDARIES.md).

---

## Repository Structure

```text
RegimeX/
│
├── apps/                          ← Deployable applications
│   ├── api/                       ← FastAPI backend (Python 3.12)
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── router.py           ← Versioned route aggregator
│   │   │   │       └── endpoints/
│   │   │   │           └── health.py       ← Liveness + readiness probes
│   │   │   ├── core/
│   │   │   │   ├── config.py               ← Pydantic settings (env-driven)
│   │   │   │   ├── dependencies.py         ← FastAPI DI foundation
│   │   │   │   └── errors.py               ← Exception hierarchy + handlers
│   │   │   ├── modules/                    ← 13 domain modules (V03-defined)
│   │   │   │   ├── market_discovery/
│   │   │   │   ├── market_data/
│   │   │   │   ├── data_quality/
│   │   │   │   ├── feature_engineering/
│   │   │   │   ├── regime_detection/
│   │   │   │   ├── regime_intelligence/
│   │   │   │   ├── risk_analytics/
│   │   │   │   ├── backtesting/
│   │   │   │   ├── research_workspace/
│   │   │   │   ├── ai_research/
│   │   │   │   ├── identity_access/
│   │   │   │   ├── administration/
│   │   │   │   └── observability/
│   │   │   ├── workers/                    ← Celery worker entry points (V05+)
│   │   │   └── main.py                     ← Application factory (create_app)
│   │   ├── tests/
│   │   │   ├── conftest.py                 ← Session fixtures, test app
│   │   │   └── test_health.py              ← Baseline foundation tests
│   │   ├── pyproject.toml                  ← Project + tool configuration
│   │   └── .env.example                    ← Required env variables (no secrets)
│   │
│   └── web/                       ← Next.js frontend (TypeScript)
│       ├── app/
│       │   ├── layout.tsx                  ← Root App Router layout + SEO
│       │   ├── page.tsx                    ← Foundation proof page
│       │   └── globals.css                 ← CSS design tokens + global styles
│       ├── components/                     ← Reusable UI components (V16+)
│       ├── lib/
│       │   └── api-client.ts               ← Backend API boundary (all calls here)
│       ├── hooks/                          ← React hooks location (V16+)
│       ├── public/                         ← Static assets
│       ├── tests/                          ← Frontend tests (V16+)
│       ├── package.json
│       ├── tsconfig.json                   ← Strict TypeScript config + path aliases
│       ├── next.config.ts                  ← Next.js configuration
│       └── .env.example                    ← Frontend env variables
│
├── packages/                      ← Shared packages (no runtime app code)
│   ├── contracts/                  ← Shared TypeScript types (backend → frontend)
│   │   ├── README.md               ← Ownership rules and what belongs here
│   │   └── src/index.ts            ← ApiEnvelope, health types, future domain types
│   └── config/                     ← Shared configuration schemas (future use)
│
├── tests/                         ← Cross-application tests
│   ├── integration/                ← Multi-service integration tests (V05+)
│   └── e2e/                        ← End-to-end browser tests (V16+)
│
├── docs/
│   └── V04/
│       └── README.md               ← This file
│
├── scripts/                       ← Operational scripts
│
├── infra/                         ← Infrastructure configuration
│   ├── docker-compose.yml          ← Local development topology
│   └── docker/
│       ├── api.Dockerfile          ← Multi-stage FastAPI image
│       └── web.Dockerfile          ← Multi-stage Next.js image
│
├── .github/
│   └── CODEOWNERS                  ← Review ownership assignments
│
├── V01/                           ← Product Foundation (documentation)
├── V02/                           ← Enterprise Requirements (documentation)
├── V03/                           ← System Architecture (documentation)
├── .gitignore                     ← Comprehensive ignore rules
├── .editorconfig                  ← Editor conventions
└── README.md                      ← Project root README
```

---

## Application Ownership

| Application | Path | Language | Framework | Owner Volume |
|-------------|------|----------|-----------|-------------|
| **API Backend** | `apps/api/` | Python 3.12 | FastAPI | V04 foundation → V05+ |
| **Web Frontend** | `apps/web/` | TypeScript | Next.js 14 | V04 foundation → V16+ |

---

## Backend Structure

### Module Anatomy

Every domain module follows this four-layer structure:

```text
module_name/
├── __init__.py          ← Public module interface
├── domain/              ← Pure business logic, entities, value objects
│   └── __init__.py
├── application/         ← Use cases, command/query handlers, orchestration
│   └── __init__.py
├── infrastructure/      ← Database repos, external adapters, caches
│   └── __init__.py
└── api/                 ← FastAPI routers specific to this module
    └── __init__.py
```

### Dependency Direction

```text
api/ → application/ → domain/
                        ↑
infrastructure/ ────────┘
```

- `domain/` must never import from `infrastructure/`, `api/`, or `application/`.
- `application/` may import from `domain/` only.
- `infrastructure/` implements interfaces defined in `domain/`.
- `api/` calls `application/` use cases only — never domain directly, never infrastructure directly.

### Module Implementation Timeline

| Module | Path | Designated Volume |
|--------|------|------------------|
| `market_discovery` | `apps/api/app/modules/market_discovery/` | V05 |
| `market_data` | `apps/api/app/modules/market_data/` | V05 |
| `data_quality` | `apps/api/app/modules/data_quality/` | V06 |
| `feature_engineering` | `apps/api/app/modules/feature_engineering/` | V07 |
| `regime_detection` | `apps/api/app/modules/regime_detection/` | V08 |
| `regime_intelligence` | `apps/api/app/modules/regime_intelligence/` | V09 |
| `risk_analytics` | `apps/api/app/modules/risk_analytics/` | V10 |
| `backtesting` | `apps/api/app/modules/backtesting/` | V11 |
| `research_workspace` | `apps/api/app/modules/research_workspace/` | V12 |
| `ai_research` | `apps/api/app/modules/ai_research/` | V21 |
| `identity_access` | `apps/api/app/modules/identity_access/` | V15 |
| `administration` | `apps/api/app/modules/administration/` | V16 |
| `observability` | `apps/api/app/modules/observability/` | V05 |

---

## Frontend Structure

### API Client Boundary

All backend communication goes through `apps/web/lib/api-client.ts`.

**Rules:**
- The frontend NEVER accesses the database.
- The frontend NEVER imports from `apps/api/`.
- All API calls go through `apiFetch()` in `api-client.ts`.
- Authentication tokens are managed in `api-client.ts` (V15+).

### Component Organization

```text
apps/web/
├── app/               ← Next.js App Router pages and layouts
├── components/        ← Reusable, dumb UI components (no data fetching)
├── lib/               ← Utilities, API client, data transformation
└── hooks/             ← React hooks (data fetching, state management)
```

---

## Shared Contracts

The `packages/contracts/` package contains TypeScript types shared between the backend API and the frontend.

**Rule:** Backend Pydantic schemas are the source of truth. TypeScript types mirror them.

See [`packages/contracts/README.md`](../packages/contracts/README.md) for ownership rules.

---

## Configuration Strategy

All configuration is environment-driven. No secrets are hardcoded.

| Variable Prefix | Scope | Example |
|-----------------|-------|---------|
| `REGIMEX_` | Backend (Python) | `REGIMEX_DATABASE_URL` |
| `NEXT_PUBLIC_` | Frontend browser | `NEXT_PUBLIC_API_URL` |
| (no prefix) | Frontend server-only | `INTERNAL_API_SECRET` |

Copy `.env.example` files to get started:
```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

---

## Local Development Entry Points

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

### 1. Start infrastructure services

```bash
# Start PostgreSQL/TimescaleDB and Redis only (no app containers)
docker compose -f infra/docker-compose.yml up -d db redis
```

### 2. Run the backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"
cp .env.example .env            # Edit .env with your values
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://localhost:8000/api/docs  
Health check: http://localhost:8000/api/v1/health/live

### 3. Run the frontend

```bash
cd apps/web
npm install
cp .env.example .env.local      # Edit .env.local if needed
npm run dev
```

Web app: http://localhost:3000

### 4. Run backend tests

```bash
cd apps/api
pytest tests/ -v
```

---

## Testing Structure

| Test Type | Location | Requires Infrastructure |
|-----------|----------|------------------------|
| Unit tests | `apps/api/tests/` | No |
| Integration tests | `tests/integration/` | Yes (db + redis) |
| E2E tests | `tests/e2e/` | Yes (full stack) |

---

## Architectural Guardrails

See [`ARCHITECTURE_GUARDRAILS.md`](ARCHITECTURE_GUARDRAILS.md) for the full set of rules preventing architectural drift.
