# RegimeX — Deployment Guide

> **V24 Commit 01 — Containerisation reference**
> This document covers local development and production-like deployments using Docker.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Building Images](#building-images)
4. [Starting the Local Stack](#starting-the-local-stack)
5. [Database Initialisation and Migrations](#database-initialisation-and-migrations)
6. [Service URLs](#service-urls)
7. [Health-Check Verification](#health-check-verification)
8. [Logs and Troubleshooting](#logs-and-troubleshooting)
9. [Memory Diagnostics](#memory-diagnostics)
10. [Production Deployment Considerations](#production-deployment-considerations)
11. [Shutdown and Persistent-Volume Behaviour](#shutdown-and-persistent-volume-behaviour)

---

## Prerequisites

| Tool | Minimum version | Purpose |
|---|---|---|
| Docker Desktop / Engine | 24.x | Container runtime |
| Docker Compose v2 (`docker compose`) | 2.24 | Local stack orchestration |
| Python | 3.12 | Backend development |
| Node.js | 20 LTS | Frontend development |
| Git | 2.x | Source control |

> **Windows note**: commands below use PowerShell syntax.  
> On Linux/macOS use the same commands verbatim.

---

## Environment Variables

### API (`apps/api/.env`)

```bash
# Create from the committed template
cp apps/api/.env.example apps/api/.env
# Then edit apps/api/.env with real values for your environment
```

Key variables (see [`apps/api/.env.example`](../apps/api/.env.example) for the full contract):

| Variable | Required | Description |
|---|---|---|
| `REGIMEX_ENV` | Yes | `development` / `test` / `production` |
| `REGIMEX_DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REGIMEX_REDIS_URL` | Yes | `redis://host:6379/0` |
| `REGIMEX_SECRET_KEY` | Yes (production) | JWT signing key — ≥32 random characters |
| `REGIMEX_AI_PROVIDER` | No | `mock` (default) or `openai` |
| `REGIMEX_AI_API_KEY` | Only with `openai` | External AI provider key |
| `PORT` | No | API bind port (default `8000`) |

Generate a secure `REGIMEX_SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Web (`apps/web/.env.local`)

```bash
cp apps/web/.env.example apps/web/.env.local
```

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Public base URL for the API (e.g. `http://localhost:8000`) |
| `NEXT_PUBLIC_APP_NAME` | Display name (default: `RegimeX`) |
| `PORT` | Web server bind port (default `3000`) |

> **Security**: Never place backend secrets (`REGIMEX_SECRET_KEY`, database credentials, AI API keys) in `NEXT_PUBLIC_*` variables — they are exposed to the browser.

---

## Building Images

All commands are run from the **repository root**.

### API image

```bash
docker build -f infra/docker/api.Dockerfile -t regimex-api:latest .
```

### Web image

```bash
docker build -f infra/docker/web.Dockerfile -t regimex-web:latest .
```

### Both images via Compose

```bash
docker compose -f infra/docker-compose.yml build
```

---

## Starting the Local Stack

### 1. Prepare environment

```bash
# Copy environment templates
cp apps/api/.env.example apps/api/.env
# Edit apps/api/.env — at minimum, set REGIMEX_SECRET_KEY
```

### 2. Start infrastructure + application

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

This starts (in dependency order):

1. **`db`** — TimescaleDB (PostgreSQL 16), waits for `pg_isready`
2. **`redis`** — Redis 7, waits for `redis-cli ping`
3. **`api`** — FastAPI/Uvicorn, waits for `db` and `redis` to be healthy
4. **`web`** — Next.js standalone server, waits for `api` to be healthy

> **First run only**: after the stack is up, run database migrations (see below).

### 3. Check service status

```bash
docker compose -f infra/docker-compose.yml ps
```

All services should show `healthy` after their start periods elapse.

---

## Database Initialisation and Migrations

RegimeX uses [Alembic](https://alembic.sqlalchemy.org/) for schema migrations.

### Apply all migrations (fresh database)

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

### Check current migration revision

```bash
docker compose -f infra/docker-compose.yml exec api alembic current
```

### Show migration history

```bash
docker compose -f infra/docker-compose.yml exec api alembic history --verbose
```

### Create a new migration (development)

```bash
docker compose -f infra/docker-compose.yml exec api alembic revision --autogenerate -m "describe_your_change"
```

> **Important**: Migrations are **not** run automatically when the API starts.  
> Run `alembic upgrade head` once after a fresh database initialisation or after pulling new migration files.  
> The API emits a clear error at startup if the required schema is absent.

---

## Service URLs

| Service | URL | Notes |
|---|---|---|
| API root | http://localhost:8000/ | Machine-readable metadata |
| API docs (dev) | http://localhost:8000/docs | Disabled in production |
| API liveness | http://localhost:8000/health | Process-alive check |
| API readiness | http://localhost:8000/ready | Full readiness check |
| API metrics | http://localhost:8000/metrics | Prometheus text format |
| Web application | http://localhost:3000/ | Dashboard / market intelligence |

---

## Health-Check Verification

### Liveness (process alive)

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

Expected response:
```json
{"status": "ok"}
```

### Readiness (all dependencies reachable)

```bash
curl -s http://localhost:8000/ready | python -m json.tool
```

Expected response (all checks `"ok"`):
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok"
  },
  "timestamp": "2026-10-28T13:00:00.000000+00:00"
}
```

### Docker health status

```bash
docker inspect --format='{{.Name}} — {{.State.Health.Status}}' \
  regimex-db regimex-redis regimex-api regimex-web
```

---

## Logs and Troubleshooting

### Stream all logs

```bash
docker compose -f infra/docker-compose.yml logs -f
```

### Stream a single service

```bash
docker compose -f infra/docker-compose.yml logs -f api
docker compose -f infra/docker-compose.yml logs -f web
docker compose -f infra/docker-compose.yml logs -f db
```

### Open a shell inside the API container

```bash
docker compose -f infra/docker-compose.yml exec api bash
```

### Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `api` stays `starting` | Migrations not applied | Run `alembic upgrade head` after `db` is healthy |
| `web` shows `unhealthy` | `api` is not healthy yet | Wait for `api` health check to pass |
| `ConnectionRefusedError` on `db` | DB not ready | Verify `db` is `healthy` before connecting |
| `secret_key` validation error | Default key in production mode | Set `REGIMEX_SECRET_KEY` to ≥32 chars |
| Port already in use | Another process on 8000/3000 | Stop conflicting service or change port mapping |
| `ModuleNotFoundError` | Optional dep not installed | Image was built before extras were added; rebuild |

---

## Memory Diagnostics

> **Note**: Actual measurements require a running Docker environment.

### Container memory usage

```bash
docker stats regimex-api regimex-web --no-stream
```

### API process memory from inside the container

```bash
docker compose -f infra/docker-compose.yml exec api \
  python -c "import os, resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'KB RSS')"
```

### Image sizes

```bash
docker images regimex-api regimex-web
```

> To reduce image size, the API Dockerfile uses a multi-stage build: build tools (`gcc`, `libpq-dev`) stay in the builder stage and are not present in the runtime image.

---

## Production Deployment Considerations

1. **Never use this Compose file in production.**  
   Production deployments should use Kubernetes, ECS, Fly.io, or a dedicated orchestrator.

2. **Secret management**: inject `REGIMEX_SECRET_KEY`, database credentials, and AI API keys via your secret manager (AWS Secrets Manager, HashiCorp Vault, Doppler). Never commit real secrets.

3. **Database**: use a managed PostgreSQL + TimescaleDB instance. Apply migrations as a pre-deployment step, not in every API container.

4. **Scaling**: the API Dockerfile runs a single Uvicorn worker per container. Scale horizontally by increasing the replica count in your orchestrator — do not set `--workers > 1` inside the container.

5. **CORS**: set `REGIMEX_ALLOWED_ORIGINS` to your actual frontend domain in production. Wildcard (`*`) is rejected.

6. **TLS**: terminate TLS at the load balancer / ingress layer. Do not disable TLS verification.

7. **Observability**: the API exposes Prometheus metrics at `/metrics`. Scrape with your Prometheus instance and configure alerts.

8. **AI provider**: the default `REGIMEX_AI_PROVIDER=mock` requires no external credentials. Set to `openai` and provide `REGIMEX_AI_API_KEY` only in environments where AI features are needed.

---

## Shutdown and Persistent-Volume Behaviour

### Stop containers (preserve volumes)

```bash
docker compose -f infra/docker-compose.yml down
```

PostgreSQL data (`postgres_data`) and Redis data (`redis_data`) are preserved.  
The next `docker compose up` will resume from the existing state.

### Stop containers and destroy all data

```bash
docker compose -f infra/docker-compose.yml down -v
```

> ⚠️ **This permanently deletes all database content and Redis data.**  
> After running with `-v`, you must re-apply migrations on the next startup.

### Volume inspection

```bash
docker volume ls | grep regimex
docker volume inspect regimex_postgres_data
```
