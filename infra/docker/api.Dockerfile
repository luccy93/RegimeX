# =============================================================================
# RegimeX API — Dockerfile
# =============================================================================
#
# Multi-stage build for the FastAPI backend.
#
# Stages:
#   1. builder  — Install dependencies in an isolated environment
#   2. runtime  — Minimal production image
#
# V04: Foundation image. Full wiring (database, migrations) completed in V05.
#
# Build:
#   docker build -f infra/docker/api.Dockerfile -t regimex-api .
#
# Run locally:
#   docker run --env-file apps/api/.env -p 8000:8000 regimex-api
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install system build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for layer caching
COPY apps/api/pyproject.toml ./

# Install core runtime dependencies
RUN pip install --upgrade pip \
    && pip install --prefix=/install . \
    && pip install --prefix=/install "uvicorn[standard]>=0.29.0"

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user for running the application
RUN groupadd --gid 1001 regimex \
    && useradd --uid 1001 --gid regimex --shell /bin/bash --create-home regimex

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY apps/api/app ./app

# Switch to non-root user
USER regimex

EXPOSE 8000

# Health check — uses the liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')"

# Start uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
