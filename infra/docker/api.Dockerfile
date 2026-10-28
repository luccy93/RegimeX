# =============================================================================
# RegimeX API — Dockerfile
# =============================================================================
#
# Multi-stage build for the FastAPI backend.
#
# Stages:
#   1. builder  — Install Python dependencies in an isolated environment
#   2. runtime  — Minimal production image
#
# Build (from repository root):
#   docker build -f infra/docker/api.Dockerfile -t regimex-api .
#
# Run locally:
#   docker run --env-file apps/api/.env -p 8000:8000 regimex-api
#
# Environment:
#   PORT  — TCP port the server binds to (default: 8000)
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevents Python from writing .pyc files and buffers stdout/stderr.
# PIP_NO_CACHE_DIR reduces layer size.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build-time system dependencies.
# gcc and libpq-dev are required for asyncpg/psycopg2 compilation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the package manifest first to maximise layer cache reuse.
COPY apps/api/pyproject.toml ./

# Install all runtime optional groups in one pip invocation.
# Extras: database (SQLAlchemy/asyncpg/alembic), workers (Celery/Redis),
#         analytics (numpy/pandas/scikit-learn/scipy/statsmodels),
#         ml (hmmlearn), observability (structlog/prometheus-client).
# The trailing pip install ensures uvicorn[standard] is present even if it
# is already satisfied transitively.
RUN pip install --upgrade pip \
    && pip install --prefix=/install \
        ".[database,workers,analytics,ml,observability]" \
    && pip install --prefix=/install "uvicorn[standard]>=0.29.0"

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Default port; override via PORT environment variable at runtime.
    PORT=8000

# Create a dedicated non-root user and group before writing any files.
RUN groupadd --gid 1001 regimex \
    && useradd --uid 1001 --gid regimex --shell /bin/bash --create-home regimex

WORKDIR /app

# Install only the runtime shared libraries required at import time.
# libpq5 is needed by asyncpg; curl is used by the health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built Python packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source into the working directory.
# alembic/ and alembic.ini are included so that migrations can be run
# from within the container via:
#   docker exec regimex-api alembic upgrade head
# Migrations are NOT run automatically on every worker start.
COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini

# Ensure the non-root user owns the application files.
RUN chown -R regimex:regimex /app

USER regimex

EXPOSE 8000

# Liveness probe:
#   GET /health — lightweight process-alive check, no external dependencies.
#   curl is used rather than wget because it provides better timeout control.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" > /dev/null || exit 1

# Production startup command.
#
# Design decisions:
#   --workers 1   — Single Uvicorn worker per container.  Horizontal scaling
#                   is delegated to the container orchestrator (Docker Compose
#                   replicas, Kubernetes deployments).  Multiple in-process
#                   workers complicate shared state and inflate memory.
#   --host        — Always bind to 0.0.0.0 so the container network interface
#                   is reachable.  Port isolation is enforced by Docker.
#   --port        — Sourced from the PORT environment variable (default 8000).
#   --no-access-log — Structured request logging is handled by the application
#                     middleware (structlog); uvicorn's default log is redundant.
#
# Startup does NOT run database migrations.  Run migrations separately:
#   docker exec regimex-api alembic upgrade head
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
