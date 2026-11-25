# RegimeX — Staging Infrastructure Readiness & Qualification Guide

> **V26 — Staging Infrastructure Readiness & Live Qualification Preparation**  
> Operational guide and runbook for evaluating staging host prerequisites, inspecting runtime configuration, verifying security boundaries, and collecting genuine qualification evidence.

---

## 1. Overview & Objectives

RegimeX establishes dedicated staging readiness verification to ensure that releases are evaluated against genuine, reproducible infrastructure evidence before any live qualification can occur.

### Scope & Invariants
- **Evidence-Only Assessment**: V26 establishes infrastructure readiness verification; it **does NOT deploy** services to staging or production, publish Docker images, or trigger automated rollouts.
- **Fail-Closed Evaluation**: All readiness gates fail closed. A missing dependency is reported as `BLOCKED`, missing secrets as `NOT_CONFIGURED`, and defects as `FAIL`. A check is never reported as `PASS` without verified evidence.
- **Secret Redaction**: Passwords, API keys, and bearer tokens are strictly masked (`***`) in reports, console logs, and metadata artifacts.
- **Forward-Only Database Lifecycle**: Staging verification honors the project's forward-only database migration policy; automated schema downgrades are prohibited.

---

## 2. Staging Preflight Architecture

The staging preflight system is structured into modular components:

```
┌────────────────────────────────────────────────────────┐
│             scripts/staging_preflight.py               │
│                 (Operator CLI Interface)               │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         app.core.staging_readiness.Inspector           │
│     - inspect_host()      - inspect_runtime()          │
│     - inspect_security()  - inspect_release()          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│        app.schemas.staging_readiness.Report            │
│  - Categories: host, runtime, security, release        │
│  - Machine-readable JSON / Human-readable Text         │
│  - Statuses: PASS, FAIL, BLOCKED, NOT_CONFIGURED,      │
│              NOT_RUN, WARNING                          │
└────────────────────────────────────────────────────────┘
```

---

## 3. Host Prerequisites

| Prerequisite | Minimum Required | Recommended | Failure Status | Remediation |
|---|---|---|---|---|
| **OS Architecture** | 64-bit OS | x86_64 or aarch64 | `WARNING` | Deploy staging host on standard 64-bit architecture |
| **Python Runtime** | `>= 3.11` | Python 3.11 | `FAIL` | Upgrade host Python version to 3.11+ |
| **Docker CLI** | `docker` on PATH | Docker Engine 24+ | `FAIL` | Install Docker Engine / Desktop CLI |
| **Docker Daemon** | Active & responding | Accessible socket | `BLOCKED` | Start Docker daemon (`systemctl start docker`) |
| **Docker Compose** | Compose v2 | `docker compose` plugin | `FAIL` | Install Docker Compose v2 plugin |
| **Available Disk** | 1.0 GB | $\ge 5.0$ GB | `FAIL` / `WARNING` | Prune unused Docker images and build caches |
| **Available RAM** | 1.0 GB | $\ge 2.0$ GB | `WARNING` | Allocate at least 2 GB RAM to host container engine |
| **Workspace Write** | Writable | Writable | `FAIL` | Correct directory file permissions for execution user |
| **Project Trees** | Complete source | `infra/`, `apps/` | `FAIL` | Verify full repository git checkout |

---

## 4. Staging Environment Variables

| Variable | Requirement | Format / Validation | Description |
|---|---|---|---|
| `REGIMEX_SECRET_KEY` | Mandatory | $\ge 32$ random characters | Cryptographic secret for JWT authentication tokens |
| `REGIMEX_DATABASE_URL` | Mandatory | `postgresql+asyncpg://...` | Connection URL for PostgreSQL / TimescaleDB |
| `REGIMEX_ALLOWED_ORIGINS` | Mandatory | Explicit domains (no `*`) | Comma-delimited CORS allowed origin URLs |
| `NEXT_PUBLIC_API_URL` | Mandatory | Client HTTP/HTTPS URL | Public base URL for browser API communication |
| `REGIMEX_REDIS_URL` | Optional | `redis://...` or `rediss://...` | Redis cache and Celery broker connection string |

---

## 5. CLI Usage: `scripts/staging_preflight.py`

Run preflight checks from the repository root:

```bash
# Standard human-readable summary
python scripts/staging_preflight.py

# Detailed evaluation per check
python scripts/staging_preflight.py --verbose

# Strict gate (treats warnings as failures)
python scripts/staging_preflight.py --strict

# Machine-readable JSON report output to file
python scripts/staging_preflight.py --format json --output staging-readiness-preflight.json
```

### Exit Codes:
- `0`: All required checks passed (`PASS`). Staging environment is ready for Stage 2 evidence collection.
- `1`: One or more checks failed (`FAIL`) or warning in strict mode.
- `2`: One or more required checks are blocked (`BLOCKED`, e.g. Docker daemon unreachable).
- `3`: One or more mandatory checks are not configured (`NOT_CONFIGURED`, e.g. database URL or secrets missing).

---

## 6. Check Status Definitions

- **`PASS`**: The check was evaluated with concrete evidence and meets all staging criteria.
- **`FAIL`**: The check was evaluated and failed compliance (e.g. invalid commit SHA, wildcard CORS, insufficient disk space).
- **`BLOCKED`**: The check could not proceed because a prerequisite dependency is missing or unresponsive (e.g. Docker daemon unreachable).
- **`NOT_CONFIGURED`**: Mandatory configuration or credentials have not been supplied in the environment.
- **`NOT_RUN`**: Check was intentionally bypassed or depends on absent metadata (e.g. manifest integrity check when manifest is absent).
- **`WARNING`**: Non-mandatory advisory condition detected (e.g. low available memory or non-primary git branch). In strict mode, warnings escalate to failures.

---

## 7. Security & Redaction Guarantees

1. **Zero Credential Exposure**: `redact_secrets()` sanitizes all connection strings, tokens, and authorization headers before logging or serializing to JSON.
2. **Non-Root Containers**: Both `api.Dockerfile` and `web.Dockerfile` enforce dedicated non-root users (`regimex` and `nextjs`).
3. **No World-Writable Configurations**: Sensitive files and `.env` credentials are restricted and untracked from version control.

---

## 8. Infrastructure Readiness Evidence Collection

`scripts/staging_evidence.py` collects concrete, auditable infrastructure readiness evidence from the staging execution host:

```
┌────────────────────────────────────────────────────────┐
│              scripts/staging_evidence.py               │
│               (Evidence CLI Collector)                 │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         app.core.staging_evidence.Collector            │
│     - collect_docker_evidence()                        │
│     - collect_github_evidence()                        │
│     - collect_ghcr_evidence()                          │
│     - validate_release_manifest()                      │
│     - validate_smoke_credentials()                     │
│     - assess_rollback_and_backup()                     │
│     - detect_gpu_capability()                          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│     app.schemas.staging_readiness.EvidenceReport       │
│  - Fail-closed evaluation                              │
│  - live_qualification_authorized: false (strictly)    │
│  - production_deployment_authorized: false (strictly) │
│  - Immutable digest pins (@sha256:...) enforcement     │
│  - Staging smoke-test vs prod secret isolation         │
│  - Honest optional GPU detection (CPU fallback)        │
└────────────────────────────────────────────────────────┘
```

### Component Evidence Gates

| Component | Target Check | Strict Invariant | Failure Status |
|---|---|---|---|
| **Docker Staging Host** | Engine 24+, Compose v2, storage $\ge 1$ GB, ports (8000, 3000, 5432, 6379) | Daemon socket must respond; non-root execution | `BLOCKED` / `FAIL` |
| **GitHub Access** | `gh` CLI or `GITHUB_TOKEN` | Read access to `luccy93/RegimeX`; zero token logging | `NOT_CONFIGURED` / `FAIL` |
| **GHCR Registry** | `ghcr.io` pull authorization | Verified via token or docker config | `NOT_CONFIGURED` / `FAIL` |
| **Release Manifest** | `release-manifest.json` | Exact 40-char SHA match; immutable `@sha256:` digest pins; `:latest` rejected | `FAIL` |
| **Smoke Credentials** | `STAGING_SMOKE_USER`, `STAGING_SMOKE_PASSWORD` | Strictly isolated; fails if matching production secrets | `FAIL` / `NOT_CONFIGURED` |
| **Rollback & Backup** | Backup dir, `docs/deployment.md`, `docs/staging.md` | Forward-only DB lifecycle; no automated downgrades | `FAIL` / `WARNING` |
| **GPU Compute** | NVIDIA GPU & container toolkit | Non-mandatory (`mandatory=False`); CPU fallback supported | `WARNING` (Advisory) |

### CLI Usage: `scripts/staging_evidence.py`

```bash
# Output evidence summary in JSON format
python scripts/staging_evidence.py --format json

# Write JSON evidence report to disk
python scripts/staging_evidence.py --format json --output staging-infrastructure-evidence.json

# Human-readable formatted text breakdown
python scripts/staging_evidence.py --format text --verbose

# Strict evaluation gate (treats warnings as failures)
python scripts/staging_evidence.py --strict
```

### Authorization Boundaries

In accordance with Volume V26 governance:
- `live_qualification_authorized` is **always `false`**.
- `production_deployment_authorized` is **always `false`**.
- V26 prepares readiness evidence; live qualification and production rollouts remain strictly gated.

