# RegimeX Continuous Integration (CI) Guide

This document specifies the architecture, triggers, quality gates, security policies, and execution procedures for the RegimeX GitHub Actions Continuous Integration pipeline.

---

## 1. Overview & Architecture

RegimeX uses a unified, parallelized GitHub Actions workflow located at [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

The pipeline automatically validates all code contributions before changes can merge into `main`. It covers backend static analysis and tests, frontend quality gates and builds, infrastructure configuration validation, container build integrity, and secret hygiene.

```
                  ┌───────────────────────────────┐
                  │        Trigger: Push / PR     │
                  └───────────────┬───────────────┘
                                  │
         ┌──────────────┬─────────┴────────┬──────────────┬──────────────┐
         ▼              ▼                  ▼              ▼              ▼
   ┌───────────┐  ┌───────────┐      ┌───────────┐  ┌───────────┐  ┌────────────┐
   │ Security  │  │  Infra    │      │  Backend  │  │ Frontend  │  │Docker-Build│
   │ & Hygiene │  │Validation │      │ & Pytest  │  │ & Build   │  │Verification│
   └─────┬─────┘  └─────┬─────┘      └─────┬─────┘  └─────┬─────┘  └─────┬──────┘
         │              │                  │              │              │
         └──────────────┴─────────┬────────┴──────────────┴──────────────┘
                                  ▼
                         ┌─────────────────┐
                         │     CI Gate     │
                         │ (Aggregate Job) │
                         └─────────────────┘
```

---

## 2. Workflows & Trigger Policy

- **Workflow Name**: `CI`
- **File**: `.github/workflows/ci.yml`
- **Triggers**:
  - `pull_request`: Targets `main` branch.
  - `push`: Directly to `main` branch.
  - `workflow_dispatch`: Manual triggering via GitHub Actions UI or CLI.
- **Concurrency & Cancellation**:
  - `group: ${{ github.workflow }}-${{ github.ref }}`
  - `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`
  - Automatically cancels obsolete runs when newer commits are pushed to open pull requests, saving compute resources while preserving `main` deployment integrity.
- **Path Filter Policy**:
  - No path filters are applied to the workflow. This guarantees that branch protection cannot be hung or bypassed by pull requests that only touch specific subdirectories.

---

## 3. CI Quality Jobs

### 3.1 Security & Hygiene (`security`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 10 minutes
- **Checks**:
  - Scans repository tree for forbidden credential files (`.env`, `.env.production`, `*.pem`, `*.key`, `id_rsa*`).
  - Verifies that example templates (`.env.example`, `.env.production.example`) do not contain live API keys or passwords.

### 3.2 Infrastructure Validation (`infra`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 10 minutes
- **Checks**:
  - Validates development Docker Compose configuration syntax:
    ```bash
    docker compose -f infra/docker-compose.yml config --quiet
    ```
  - Validates production Docker Compose overlay syntax with required environment variable substitutions:
    ```bash
    docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config --quiet
    ```

### 3.3 Backend Quality & Tests (`backend`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 15 minutes
- **Working Directory**: `apps/api`
- **Python Version**: `3.11` (pinned via `actions/setup-python`)
- **Caching**: Pip cache keyed against `apps/api/pyproject.toml`.
- **Environment**:
  - `REGIMEX_ENV: test`
  - `SECRET_KEY: ci-test-secret-key-for-unit-and-integration-testing-000`
- **Execution Sequence**:
  1. Dependencies installed reproducibly:
     ```bash
     python -m pip install --upgrade pip setuptools wheel
     pip install -e ".[dev,database,workers,analytics,ml,observability]"
     ```
  2. Ruff format check:
     ```bash
     python -m ruff format --check app tests
     ```
  3. Ruff linting check:
     ```bash
     python -m ruff check app tests
     ```
  4. Mypy strict type checking:
     ```bash
     python -m mypy app tests
     ```
  5. Full backend test suite:
     ```bash
     python -m pytest tests/ -q --tb=short
     ```
- **External Calls**: Zero live external dependencies. All market data and AI provider integrations use deterministic mock implementations and synthetic fixtures.

### 3.4 Frontend Quality & Tests (`frontend`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 15 minutes
- **Working Directory**: `apps/web`
- **Node.js Version**: `20` (pinned via `actions/setup-node`)
- **Caching**: npm cache keyed against `apps/web/package-lock.json`.
- **Environment**:
  - `NODE_ENV: production`
  - `NEXT_TELEMETRY_DISABLED: 1`
  - `NEXT_PUBLIC_API_URL: http://localhost:8000`
- **Execution Sequence**:
  1. Dependencies installed reproducibly:
     ```bash
     npm ci
     ```
  2. Next.js ESLint:
     ```bash
     npm run lint
     ```
  3. TypeScript compiler type check:
     ```bash
     npm run type-check
     ```
  4. Unit and accessibility test suite:
     ```bash
     npm test
     ```
  5. Next.js production standalone build:
     ```bash
     npm run build
     ```

### 3.5 Docker Build Verification (`docker-build`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 15 minutes
- **Tooling**: `docker/setup-buildx-action` and `docker/build-push-action`
- **Caching**: GitHub Actions layer cache (`type=gha,mode=max`).
- **Build Targets**:
  - API Dockerfile: `infra/docker/api.Dockerfile`
  - Web Dockerfile: `infra/docker/web.Dockerfile`
- **Safety**:
  - `push: false` (images are never pushed to a container registry).
  - No deployment triggers.
  - No secrets injected into layers.

### 3.6 Pull Request Status Gate (`ci-gate`)
- **Needs**: `[security, infra, backend, frontend, docker-build]`
- **Condition**: `if: always()`
- **Purpose**: Evaluates whether all required upstream jobs succeeded. If any job was cancelled, skipped, or failed, `ci-gate` reports an actionable error and exits with code 1.
- **Branch Protection**: Repository administrators can configure `CI Gate` as the single required status check on `main`.

---

## 4. Security & Permissions Policy

1. **Least Privilege**:
   - The workflow explicitly sets top-level permissions to read-only:
     ```yaml
     permissions:
       contents: read
     ```
   - No write permissions to repository contents, packages, issues, or pull requests are granted.

2. **Immutable Action Pinning**:
   - All third-party GitHub Actions are pinned to full 40-character commit SHAs with version comments:
     - `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`
     - `actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38 # v5.4.0`
     - `actions/setup-node@1e60f63fe749454848bbdc089d892d19f6a7d519 # v4.2.0`
     - `docker/setup-buildx-action@b5ca514310bc82956671457a546cac9caac5f416 # v3.10.0`
     - `docker/build-push-action@471d1dc4e07e5cdedd4c2171150001c434f0b7a4 # v6.15.0`

3. **Fork Protection**:
   - Pull requests from forks execute in untrusted contexts with read-only repository tokens.
   - `pull_request_target` is intentionally not used.
   - No secrets are exposed to pull request jobs.

---

## 5. Reproducing CI Failures Locally

Before pushing code, run the quality gates locally:

### Full Local Quality Gate
```bash
# Using Makefile
make quality

# Or using repository script (Linux / macOS)
bash scripts/quality-check.sh

# Or using PowerShell (Windows)
.\scripts\quality-check.ps1
```

### Backend Step-by-Step
```bash
cd apps/api

# 1. Format check
python -m ruff format --check app tests

# 2. Lint check
python -m ruff check app tests

# 3. Type check
python -m mypy app tests

# 4. Run test suite
python -m pytest tests/ -q
```

### Frontend Step-by-Step
```bash
cd apps/web

# 1. Install dependencies
npm ci

# 2. ESLint
npm run lint

# 3. Type check
npm run type-check

# 4. Tests
npm test

# 5. Build
npm run build
```

### Infrastructure Validation Step-by-Step
```bash
# Development compose
docker compose -f infra/docker-compose.yml config --quiet

# Production compose overlay
REGIMEX_DB_PASSWORD="dummy" \
REGIMEX_DATABASE_URL="postgresql+asyncpg://regimex:dummy@db:5432/regimex_prod" \
REGIMEX_SECRET_KEY="dummy-secret-key-at-least-32-chars-long" \
REGIMEX_ALLOWED_ORIGINS="http://localhost:3000" \
NEXT_PUBLIC_API_URL="http://localhost:8000" \
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config --quiet
```

---

## 6. Recommended Branch Protection Settings

For the `main` branch in GitHub Repository Settings (`Settings` -> `Branches` -> `Branch protection rules`):

1. **Require a pull request before merging**: Enabled.
   - Require approvals: At least 1 review.
   - Dismiss stale pull request approvals when new commits are pushed: Enabled.
2. **Require status checks to pass before merging**: Enabled.
   - Require branches to be up to date before merging: Enabled.
   - Status check to require:
     - `CI Gate` (or `CI / CI Gate`)
3. **Do not allow bypassing the above settings**: Enabled for all contributors.
4. **Require linear history**: Recommended for clean release tracking.

---

## 7. Known Limitations & Scope Boundaries

1. **Compose Configuration vs. Runtime Testing**:
   - `docker compose config` validates schema, YAML syntax, volume definitions, and variable interpolation. It does not spin up running containers on the runner machine.
2. **Container Build Verification**:
   - Docker build verification checks that multi-stage builds succeed on Linux runners. It does not push images to a registry or perform live multi-node smoke testing.
3. **Backend Dependency Locking**:
   - `apps/web` uses `package-lock.json` for deterministic npm dependencies.
   - `apps/api` uses bounded version constraints in `pyproject.toml`. Pinned lockfiles for Python (e.g. `pip-compile` / `uv.lock`) are planned for future dependency management updates.
4. **External Services**:
   - The test suite intentionally skips live market queries (e.g. Yahoo Finance) and live OpenAI calls. Integration tests with live networks are isolated into dedicated offline mocks.
