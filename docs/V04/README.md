# V04 — Monorepo Engineering Foundation

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V04 — Monorepo Engineering Foundation  
**Commit 01:** `chore(monorepo): establish application and package structure`  
**Commit 02:** `chore(tooling): configure development quality gates`  
**Status:** ✅ Volume V04 Complete

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
│       ├── .eslintrc.json                  ← Next.js ESLint configuration
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
│       ├── ARCHITECTURE_GUARDRAILS.md
│       └── README.md               ← This file
│
├── scripts/                       ← Operational and quality-gate scripts
│   ├── quality-check.sh            ← Bash quality-gate script (Linux/macOS/Git Bash)
│   └── quality-check.ps1           ← PowerShell quality-gate script (Windows)
│
├── infra/                         ← Infrastructure configuration
│   ├── docker-compose.yml          ← Local development topology
│   └── docker/
│       ├── api.Dockerfile          ← Multi-stage FastAPI image
│       └── web.Dockerfile          ← Multi-stage Next.js image
│
├── .github/
│   ├── CODEOWNERS                  ← Review ownership assignments
│   └── PULL_REQUEST_TEMPLATE.md    ← PR checklist and guardrails
│
├── .pre-commit-config.yaml         ← Fast repository hygiene hooks
├── Makefile                        ← Cross-platform developer quality commands
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

---

## Development Quality Gates

RegimeX enforces a three-tier quality-gate system designed to catch defects as early as possible in the development lifecycle:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Local Hygiene (Pre-commit)                               │
│    Trailing whitespace, EOF, YAML/TOML, Gitleaks, Ruff fmt  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Developer Quality Gate (Local CLI / Make / Script)       │
│    Ruff lint, mypy strict, pytest, ESLint, tsc, Next build  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Pull Request Review & CI (V25)                           │
│    Enforced PR checklist, CODEOWNERS review, CI pipeline    │
└─────────────────────────────────────────────────────────────┘
```

### Quality Command Matrix

| Quality Gate | Scope | Command | Purpose |
|--------------|-------|---------|---------|
| **Backend Lint** | `apps/api/` | `ruff check app/ tests/` | PEP 8, import sorting, security & bug rules |
| **Backend Format Check** | `apps/api/` | `ruff format --check app/ tests/` | Style conformity check (no file edits) |
| **Backend Format Apply** | `apps/api/` | `ruff format app/ tests/` | Auto-format backend Python source files |
| **Backend Type Check** | `apps/api/` | `mypy app/` | Strict static type checking (no untyped defs) |
| **Backend Tests** | `apps/api/` | `python -m pytest tests/ -v` | Unit tests & module boundary verification |
| **Frontend Lint** | `apps/web/` | `npm run lint` | Next.js Core Web Vitals & ESLint rules |
| **Frontend Type Check** | `apps/web/` | `npm run type-check` | `tsc --noEmit` strict TypeScript check |
| **Frontend Build** | `apps/web/` | `npm run build` | Next.js production build validation |
| **Full Quality Gate (Make)** | Root | `make quality` | All lint, format, typecheck, and unit tests |
| **Full Quality Gate (Bash)** | Root | `bash scripts/quality-check.sh` | Cross-platform Bash quality runner |
| **Full Quality Gate (Win)** | Root | `powershell scripts/quality-check.ps1` | Native Windows PowerShell quality runner |

### Pre-commit Hooks

Pre-commit hooks execute lightweight checks locally before code is committed:

```bash
# 1. Install pre-commit (one-time setup)
pip install pre-commit

# 2. Install Git hook scripts
pre-commit install

# 3. Run against all files manually
pre-commit run --all-files
```

Configured hooks in `.pre-commit-config.yaml`:
- **Repository hygiene**: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-json`, `check-merge-conflict`, `check-added-large-files`.
- **Secret detection**: `gitleaks` (detects accidental API keys, tokens, credentials).
- **Python quality**: `ruff-format` and `ruff` linting across `apps/api/`.
- **Frontend quality**: `frontend-type-check` (`tsc --noEmit`) across `apps/web/`.

### Contributor Expectations

1. **Clean Quality Gates**: Pull requests must pass all local quality checks prior to submission.
2. **PR Template Checklist**: Every PR must complete the checklist in [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md).
3. **No Secrets or Environment Files**: `.env` and secret credentials must never be committed.
4. **Architectural Guardrails**: Changes must adhere to the modular monolith boundaries and dependency directions documented in [`ARCHITECTURE_GUARDRAILS.md`](ARCHITECTURE_GUARDRAILS.md).

### Troubleshooting Setup Issues

- **Python Virtual Environment**: Ensure your virtual environment is active before running commands (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Linux/macOS).
- **Mypy Cache Issues**: If mypy reports stale errors, clear cache with `rm -rf apps/api/.mypy_cache` or `make clean`.
- **Ruff Cache Issues**: If ruff reports unexpected results, clear cache with `rm -rf apps/api/.ruff_cache`.
- **Frontend Dependencies**: If Next.js or TypeScript fails to resolve packages, run `cd apps/web && npm install`.
- **Pre-commit Failures**: When a hook modifies files (e.g. whitespace or ruff formatting), re-stage the modified files (`git add <files>`) and run `git commit` again.
