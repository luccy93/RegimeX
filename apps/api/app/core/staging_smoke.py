"""RegimeX — Staging Service Qualification & Smoke-Test Suite (V27 Commit 02).

apps/api/app/core/staging_smoke.py
==================================
Provides a reusable, read-only, secret-redacted HTTP probe client, dependency
connectivity probes, live-test opt-in guard, and structured qualification stages
for verifying a real RegimeX staging deployment.

Invariants:
- Strictly read-only: never creates/deletes users, executes trades, mutates
  portfolios, modifies market data, or runs database schema downgrades.
- Never simulates successful live staging responses.
- Never retries non-idempotent HTTP methods (only GET/HEAD/OPTIONS).
- Refuses production URLs, non-staging environments, and unconfigured targets.
- Live staging tests are strictly opt-in (REGIMEX_STAGING_LIVE_TESTS=1).
- Redacts all tokens, Authorization headers, passwords, and DSNs from results.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.staging_qualification import (
    QualificationContext,
    QualificationStageRegistry,
    _is_production_environment,
    _is_production_url,
    build_default_stage_registry,
    sanitize_mapping,
    sanitize_text,
)
from app.schemas.staging_readiness import (
    QualificationCheckResult,
    QualificationStage,
    QualificationStageResult,
    QualificationStatus,
    StagingGateEvaluationReport,
)

logger = logging.getLogger("regimex.staging_smoke")

IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})


# =============================================================================
# Resilience Configuration & Live-Test Opt-In Guard
# =============================================================================


@dataclass(frozen=True)
class SmokeClientConfig:
    """Bounded timeout, retry, and target isolation policy for staging probes."""

    environment: str = "staging"
    commit_sha: str = ""
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    follow_redirects: bool = True


@dataclass(frozen=True)
class LiveTestGuardResult:
    """Outcome of the opt-in guard validating whether live staging tests may run."""

    allowed: bool
    status: QualificationStatus
    reason: str


class StagingLiveTestGuard:
    """Enforces opt-in and safety preconditions before any live staging tests execute."""

    @staticmethod
    def is_live_opted_in(env: Mapping[str, str]) -> bool:
        """Return True only when REGIMEX_STAGING_LIVE_TESTS is explicitly enabled."""
        return env.get("REGIMEX_STAGING_LIVE_TESTS", "").strip().lower() in ("1", "true", "yes")

    @classmethod
    def evaluate(
        cls,
        *,
        env: Mapping[str, str],
        environment: str | None = None,
        staging_api_url: str | None = None,
        staging_web_url: str | None = None,
        gate_report: StagingGateEvaluationReport | None = None,
        require_smoke_credentials: bool = True,
    ) -> LiveTestGuardResult:
        """Verify opt-in flag, staging identity, URLs, credentials, and V26 gate status."""
        env_dict = dict(env)
        if not cls.is_live_opted_in(env_dict):
            return LiveTestGuardResult(
                allowed=False,
                status=QualificationStatus.NOT_RUN,
                reason=(
                    "Live staging tests are opt-in and disabled "
                    "(set REGIMEX_STAGING_LIVE_TESTS=1 to enable)."
                ),
            )

        target_env = (environment or env.get("REGIMEX_STAGING_ENV") or "").strip().lower()
        if _is_production_environment(target_env):
            return LiveTestGuardResult(
                allowed=False,
                status=QualificationStatus.FAIL,
                reason=f"Production environment '{target_env}' rejected by live test guard.",
            )
        if target_env != "staging":
            return LiveTestGuardResult(
                allowed=False,
                status=QualificationStatus.BLOCKED,
                reason=(
                    f"Environment must be explicitly 'staging' for live tests (got '{target_env}')."
                ),
            )

        api_url = (staging_api_url or env.get("STAGING_API_URL") or "").strip()
        web_url = (staging_web_url or env.get("STAGING_WEB_URL") or "").strip()
        if not api_url or not web_url:
            return LiveTestGuardResult(
                allowed=False,
                status=QualificationStatus.NOT_CONFIGURED,
                reason="Missing STAGING_API_URL or STAGING_WEB_URL for live staging tests.",
            )

        for label, url in (("STAGING_API_URL", api_url), ("STAGING_WEB_URL", web_url)):
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return LiveTestGuardResult(
                    allowed=False,
                    status=QualificationStatus.FAIL,
                    reason=f"Invalid {label}: {sanitize_text(url, env_dict)}",
                )
            is_prod, prod_reason = _is_production_url(url, env_dict)
            if is_prod:
                return LiveTestGuardResult(
                    allowed=False,
                    status=QualificationStatus.FAIL,
                    reason=f"Production target rejected for {label}: {prod_reason}",
                )

        if require_smoke_credentials:
            user = (env.get("STAGING_SMOKE_USER") or env.get("SMOKE_TEST_USERNAME") or "").strip()
            pw = (env.get("STAGING_SMOKE_PASSWORD") or env.get("SMOKE_TEST_PASSWORD") or "").strip()
            if not user or not pw:
                return LiveTestGuardResult(
                    allowed=False,
                    status=QualificationStatus.NOT_CONFIGURED,
                    reason=(
                        "Missing required staging credentials "
                        "(STAGING_SMOKE_USER / STAGING_SMOKE_PASSWORD)."
                    ),
                )

        if gate_report is not None and not gate_report.is_ready:
            return LiveTestGuardResult(
                allowed=False,
                status=QualificationStatus.BLOCKED,
                reason=(
                    "V26 readiness gate failed or blocked "
                    f"(status={gate_report.overall_status.value})."
                ),
            )

        return LiveTestGuardResult(
            allowed=True,
            status=QualificationStatus.PASS,
            reason="Live staging test preconditions verified.",
        )


# =============================================================================
# Bounded, Read-Only Staging HTTP Client
# =============================================================================


@dataclass(frozen=True)
class ProbeResponse:
    """Safe, secret-redacted representation of an HTTP probe response."""

    ok: bool
    status_code: int | None
    request_id: str
    url: str
    duration_seconds: float
    attempts: int
    headers: dict[str, str]
    text: str
    json_body: Any | None
    error: str | None = None
    redirected_urls: tuple[str, ...] = ()


class StagingHttpClient:
    """Controlled HTTP client with bounded timeouts, safe GET retries, and redaction."""

    def __init__(
        self,
        base_url: str,
        *,
        config: SmokeClientConfig | None = None,
        env: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.env = env if env is not None else {}
        self.config = config or SmokeClientConfig()

        if _is_production_environment(self.config.environment):
            raise ValueError(
                f"Production environment '{self.config.environment}' rejected by StagingHttpClient."
            )
        if self.config.environment.strip().lower() != "staging":
            raise ValueError(
                f"StagingHttpClient requires explicit 'staging' environment, "
                f"got '{self.config.environment}'."
            )

        clean_base = base_url.strip().rstrip("/")
        parsed = urllib.parse.urlparse(clean_base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Malformed staging base URL: {sanitize_text(clean_base, self.env)}")
        is_prod, prod_reason = _is_production_url(clean_base, self.env)
        if is_prod:
            raise ValueError(f"Production target URL rejected: {prod_reason}")

        self.base_url = clean_base
        self._transport = transport

    def _build_client(self) -> httpx.Client:
        timeout = httpx.Timeout(
            connect=self.config.connect_timeout_seconds,
            read=self.config.read_timeout_seconds,
            write=self.config.read_timeout_seconds,
            pool=self.config.connect_timeout_seconds,
        )
        return httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=self.config.follow_redirects,
            transport=self._transport,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        read_only_override: bool = False,
    ) -> ProbeResponse:
        """Execute a bounded HTTP probe. Retries only idempotent methods."""
        upper_method = method.strip().upper()
        if upper_method not in IDEMPOTENT_METHODS and not read_only_override:
            raise ValueError(
                f"Non-idempotent HTTP method '{upper_method}' prohibited in read-only smoke suite."
            )

        req_id = f"v27-qual-{uuid.uuid4().hex[:12]}"
        req_headers = {
            "User-Agent": "RegimeX-StagingQualification/1.0",
            "X-Request-ID": req_id,
        }
        if headers:
            req_headers.update(headers)

        max_attempts = (
            (1 + max(0, self.config.max_retries)) if upper_method in IDEMPOTENT_METHODS else 1
        )
        target_path = path if path.startswith("/") else f"/{path}"
        full_url = f"{self.base_url}{target_path}"
        started = time.monotonic()
        last_error: str | None = None

        with self._build_client() as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    resp = client.request(
                        upper_method,
                        target_path,
                        headers=req_headers,
                        params=params,
                        json=json_payload,
                    )
                    # Check redirect targets for production URL leaks
                    redirect_urls = tuple(str(r.url) for r in resp.history)
                    for r_url in redirect_urls:
                        is_prod, prod_reason = _is_production_url(r_url, self.env)
                        if is_prod:
                            return ProbeResponse(
                                ok=False,
                                status_code=resp.status_code,
                                request_id=req_id,
                                url=sanitize_text(full_url, self.env),
                                duration_seconds=round(time.monotonic() - started, 4),
                                attempts=attempt,
                                headers={},
                                text="",
                                json_body=None,
                                error=f"Unexpected redirect to production host: {prod_reason}",
                                redirected_urls=tuple(
                                    sanitize_text(u, self.env) for u in redirect_urls
                                ),
                            )

                    if resp.status_code in RETRYABLE_STATUS_CODES and attempt < max_attempts:
                        last_error = f"Transient HTTP {resp.status_code}"
                        time.sleep(self.config.retry_backoff_seconds * attempt)
                        continue

                    safe_headers = {
                        k.lower(): sanitize_text(v, self.env)
                        for k, v in resp.headers.items()
                        if k.lower() not in ("set-cookie", "authorization", "cookie")
                    }
                    parsed_json: Any | None = None
                    ctype = resp.headers.get("content-type", "").lower()
                    if "json" in ctype:
                        try:
                            parsed_json = resp.json()
                        except Exception:
                            parsed_json = None

                    safe_text = sanitize_text(resp.text[:4096], self.env)
                    return ProbeResponse(
                        ok=200 <= resp.status_code < 400,
                        status_code=resp.status_code,
                        request_id=req_id,
                        url=sanitize_text(full_url, self.env),
                        duration_seconds=round(time.monotonic() - started, 4),
                        attempts=attempt,
                        headers=safe_headers,
                        text=safe_text,
                        json_body=parsed_json,
                        error=None,
                        redirected_urls=tuple(sanitize_text(u, self.env) for u in redirect_urls),
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = sanitize_text(f"{type(exc).__name__}: {exc}", self.env)
                    if attempt < max_attempts:
                        time.sleep(self.config.retry_backoff_seconds * attempt)
                        continue
                    return ProbeResponse(
                        ok=False,
                        status_code=None,
                        request_id=req_id,
                        url=sanitize_text(full_url, self.env),
                        duration_seconds=round(time.monotonic() - started, 4),
                        attempts=attempt,
                        headers={},
                        text="",
                        json_body=None,
                        error=last_error,
                    )
                except Exception as exc:
                    return ProbeResponse(
                        ok=False,
                        status_code=None,
                        request_id=req_id,
                        url=sanitize_text(full_url, self.env),
                        duration_seconds=round(time.monotonic() - started, 4),
                        attempts=attempt,
                        headers={},
                        text="",
                        json_body=None,
                        error=sanitize_text(str(exc), self.env),
                    )

        return ProbeResponse(
            ok=False,
            status_code=None,
            request_id=req_id,
            url=sanitize_text(full_url, self.env),
            duration_seconds=round(time.monotonic() - started, 4),
            attempts=max_attempts,
            headers={},
            text="",
            json_body=None,
            error=last_error or "Retry attempts exhausted",
        )

    def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ProbeResponse:
        """Execute a bounded, retry-safe HTTP GET request."""
        return self.request("GET", path, headers=headers, params=params)


# =============================================================================
# Dependency Probes (Database & Redis Read-Only Inspection)
# =============================================================================


DatabaseProbeFn = Callable[[str, float], tuple[bool, str | None, str]]
RedisProbeFn = Callable[[str, float], tuple[bool, str]]


def default_database_probe(
    database_url: str, timeout_seconds: float
) -> tuple[bool, str | None, str]:
    """Read-only database probe executing SELECT 1 and reading alembic_version."""
    try:
        import asyncio

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        async def _probe() -> tuple[bool, str | None, str]:
            engine = create_async_engine(database_url, pool_pre_ping=True)
            try:
                async with engine.connect() as conn:
                    await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=timeout_seconds)
                    try:
                        res = await asyncio.wait_for(
                            conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")),
                            timeout=timeout_seconds,
                        )
                        row = res.first()
                        version_num = str(row[0]) if row else None
                    except Exception:
                        version_num = None
                return True, version_num, "Database SELECT 1 succeeded"
            finally:
                await engine.dispose()

        return asyncio.run(_probe())
    except Exception as exc:
        return False, None, str(exc)


def default_redis_probe(redis_url: str, timeout_seconds: float) -> tuple[bool, str]:
    """Read-only Redis PING probe with bounded socket timeout."""
    try:
        import redis

        client = redis.from_url(  # type: ignore[no-untyped-call]
            redis_url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        try:
            pong = client.ping()
            if pong:
                return True, "Redis PING succeeded"
            return False, "Redis PING returned falsy response"
        finally:
            client.close()
    except Exception as exc:
        return False, str(exc)


def get_expected_alembic_heads(repo_root: Path) -> set[str]:
    """Read expected revision IDs from apps/api/alembic/versions without executing migrations."""
    versions_dir = repo_root / "apps" / "api" / "alembic" / "versions"
    if not versions_dir.is_dir():
        return set()
    revisions: set[str] = set()
    for py_file in versions_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        content = py_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'^revision(?:\s*:\s*[^=]+)?\s*=\s*["\']([^"\']+)["\']', content, re.M)
        if match:
            revisions.add(match.group(1).strip())
    return revisions


# =============================================================================
# Structured Smoke-Test Suite Runner
# =============================================================================


def _make_check(
    *,
    ctx: QualificationContext,
    check_id: str,
    stage_id: str,
    name: str,
    status: QualificationStatus,
    mandatory: bool,
    started_at: str,
    duration_seconds: float,
    message: str,
    http_status: int | None = None,
    details: dict[str, Any] | None = None,
    error: str | None = None,
    remediation: str | None = None,
) -> QualificationCheckResult:
    """Build a standardized, secret-redacted QualificationCheckResult with evidence ref."""
    return QualificationCheckResult(
        check_id=check_id,
        stage_id=stage_id,
        name=name,
        status=status,
        mandatory=mandatory,
        environment=ctx.environment,
        commit_sha=ctx.commit_sha,
        message=sanitize_text(message, ctx.env),
        started_at=started_at,
        completed_at=datetime.now(UTC).isoformat(),
        duration_seconds=round(duration_seconds, 4),
        http_status=http_status,
        evidence_ref=f"smoke:{ctx.run_id}:{check_id}",
        details=sanitize_mapping(details or {}, ctx.env),
        error=sanitize_text(error, ctx.env) if error else None,
        remediation=sanitize_text(remediation, ctx.env) if remediation else None,
    )


def _aggregate_stage_status(
    checks: list[QualificationCheckResult], *, strict: bool
) -> QualificationStatus:
    """Aggregate mandatory and optional check statuses fail-closed."""
    mandatory_checks = [c for c in checks if c.mandatory]
    if any(c.status == QualificationStatus.FAIL for c in mandatory_checks):
        return QualificationStatus.FAIL
    if any(c.status == QualificationStatus.BLOCKED for c in mandatory_checks):
        return QualificationStatus.BLOCKED
    if any(c.status == QualificationStatus.NOT_CONFIGURED for c in mandatory_checks):
        return QualificationStatus.NOT_CONFIGURED
    if any(c.status == QualificationStatus.FAIL for c in checks):
        return QualificationStatus.WARNING if not strict else QualificationStatus.FAIL
    if any(c.status == QualificationStatus.WARNING for c in checks):
        return QualificationStatus.FAIL if strict else QualificationStatus.WARNING
    if all(c.status == QualificationStatus.NOT_RUN for c in checks):
        return QualificationStatus.NOT_RUN
    return QualificationStatus.PASS


class StagingSmokeSuite:
    """Encapsulates all read-only staging qualification smoke-test stages."""

    def __init__(
        self,
        *,
        client_config: SmokeClientConfig | None = None,
        api_transport: httpx.BaseTransport | None = None,
        web_transport: httpx.BaseTransport | None = None,
        db_probe: DatabaseProbeFn | None = None,
        redis_probe: RedisProbeFn | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.client_config = client_config
        self.api_transport = api_transport
        self.web_transport = web_transport
        self.db_probe = db_probe or default_database_probe
        self.redis_probe = redis_probe or default_redis_probe
        self.repo_root = (
            repo_root or Path(__file__).resolve().parent.parent.parent.parent.parent
        ).resolve()

    def _api_client(self, ctx: QualificationContext) -> StagingHttpClient:
        if not ctx.staging_api_url:
            raise ValueError("STAGING_API_URL is not configured")
        cfg = self.client_config or SmokeClientConfig(
            environment=ctx.environment,
            commit_sha=ctx.commit_sha,
        )
        return StagingHttpClient(
            ctx.staging_api_url,
            config=cfg,
            env=ctx.env,
            transport=self.api_transport,
        )

    def _web_client(self, ctx: QualificationContext) -> StagingHttpClient:
        if not ctx.staging_web_url:
            raise ValueError("STAGING_WEB_URL is not configured")
        cfg = self.client_config or SmokeClientConfig(
            environment=ctx.environment,
            commit_sha=ctx.commit_sha,
        )
        return StagingHttpClient(
            ctx.staging_web_url,
            config=cfg,
            env=ctx.env,
            transport=self.web_transport,
        )

    # -------------------------------------------------------------------------
    # Stage 1: Backend Health & Readiness Qualification
    # -------------------------------------------------------------------------

    def run_backend_health_stage(self, ctx: QualificationContext) -> QualificationStageResult:
        """Verify /api/v1/health/live, /api/v1/health/ready, and /ready probes."""
        stage_id = "backend_health_qualification"
        stage_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()

        if not ctx.staging_api_url:
            return QualificationStageResult(
                stage_id=stage_id,
                name="Backend Health & Readiness Qualification",
                status=QualificationStatus.NOT_CONFIGURED,
                mandatory=True,
                requires_live_staging=True,
                started_at=stage_started,
                completed_at=datetime.now(UTC).isoformat(),
                message="STAGING_API_URL is not configured.",
            )

        client = self._api_client(ctx)
        checks: list[QualificationCheckResult] = []

        # 1. /api/v1/health/live
        c_start = datetime.now(UTC).isoformat()
        live_resp = client.get("/api/v1/health/live")
        if live_resp.status_code is None:
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.backend.liveness",
                    stage_id=stage_id,
                    name="Backend Liveness (/api/v1/health/live)",
                    status=QualificationStatus.BLOCKED,
                    mandatory=True,
                    started_at=c_start,
                    duration_seconds=live_resp.duration_seconds,
                    message=f"Staging backend unreachable: {live_resp.error}",
                    details={"request_id": live_resp.request_id, "attempts": live_resp.attempts},
                    error=live_resp.error,
                    remediation="Verify staging API process is running and reachable.",
                )
            )
        elif (
            live_resp.status_code == 200
            and isinstance(live_resp.json_body, dict)
            and live_resp.json_body.get("status") == "ok"
            and live_resp.json_body.get("service") == "RegimeX API"
            and bool(live_resp.json_body.get("version"))
            and bool(live_resp.json_body.get("timestamp"))
        ):
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.backend.liveness",
                    stage_id=stage_id,
                    name="Backend Liveness (/api/v1/health/live)",
                    status=QualificationStatus.PASS,
                    mandatory=True,
                    started_at=c_start,
                    duration_seconds=live_resp.duration_seconds,
                    http_status=live_resp.status_code,
                    message="Backend liveness verified (RegimeX API)",
                    details={
                        "request_id": live_resp.request_id,
                        "service": live_resp.json_body.get("service"),
                        "version": live_resp.json_body.get("version"),
                        "attempts": live_resp.attempts,
                    },
                )
            )
        else:
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.backend.liveness",
                    stage_id=stage_id,
                    name="Backend Liveness (/api/v1/health/live)",
                    status=QualificationStatus.FAIL,
                    mandatory=True,
                    started_at=c_start,
                    duration_seconds=live_resp.duration_seconds,
                    http_status=live_resp.status_code,
                    message=(
                        f"Unexpected liveness response (HTTP {live_resp.status_code}): "
                        "invalid status, service identity, or schema"
                    ),
                    details={"request_id": live_resp.request_id, "attempts": live_resp.attempts},
                    error="Liveness contract validation failed",
                )
            )

        # 2. /api/v1/health/ready
        c_start = datetime.now(UTC).isoformat()
        ready_v1 = client.get("/api/v1/health/ready")
        v1_body = ready_v1.json_body if isinstance(ready_v1.json_body, dict) else None
        v1_checks = v1_body.get("checks") if v1_body else None
        v1_ok = (
            ready_v1.status_code == 200
            and v1_body is not None
            and v1_body.get("status") == "ready"
            and isinstance(v1_checks, dict)
            and bool(v1_checks)
            and all(val == "ok" for val in v1_checks.values())
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.backend.readiness_v1",
                stage_id=stage_id,
                name="Backend V1 Readiness (/api/v1/health/ready)",
                status=(
                    QualificationStatus.PASS
                    if v1_ok
                    else (
                        QualificationStatus.BLOCKED
                        if ready_v1.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=ready_v1.duration_seconds,
                http_status=ready_v1.status_code,
                message=(
                    "Backend /api/v1/health/ready verified"
                    if v1_ok
                    else f"Backend /api/v1/health/ready failed (HTTP {ready_v1.status_code})"
                ),
                details={
                    "request_id": ready_v1.request_id,
                    "checks": v1_checks or {},
                },
                error=ready_v1.error if not v1_ok else None,
            )
        )

        # 3. /ready (deep dependency readiness including database)
        c_start = datetime.now(UTC).isoformat()
        ready_root = client.get("/ready")
        root_body = ready_root.json_body if isinstance(ready_root.json_body, dict) else None
        root_checks = root_body.get("checks") if root_body else None
        root_ok = (
            ready_root.status_code == 200
            and root_body is not None
            and root_body.get("status") == "ready"
            and isinstance(root_checks, dict)
            and root_checks.get("application") == "ok"
            and all(val == "ok" for val in root_checks.values())
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.backend.readiness_root",
                stage_id=stage_id,
                name="Backend Dependency Readiness (/ready)",
                status=(
                    QualificationStatus.PASS
                    if root_ok
                    else (
                        QualificationStatus.BLOCKED
                        if ready_root.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=ready_root.duration_seconds,
                http_status=ready_root.status_code,
                message=(
                    "Root /ready dependency checks verified"
                    if root_ok
                    else f"Root /ready dependency readiness failed (HTTP {ready_root.status_code})"
                ),
                details={
                    "request_id": ready_root.request_id,
                    "checks": root_checks or {},
                },
                error=ready_root.error if not root_ok else None,
            )
        )

        stage_status = _aggregate_stage_status(checks, strict=ctx.strict)
        return QualificationStageResult(
            stage_id=stage_id,
            name="Backend Health & Readiness Qualification",
            status=stage_status,
            mandatory=True,
            requires_live_staging=True,
            started_at=stage_started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(time.monotonic() - t0, 4),
            checks=checks,
            message=(
                "Backend liveness and dependency readiness passed"
                if stage_status == QualificationStatus.PASS
                else "Backend health or readiness qualification failed"
            ),
        )

    # -------------------------------------------------------------------------
    # Stage 2: Frontend Availability & Configuration Consistency
    # -------------------------------------------------------------------------

    def run_frontend_stage(self, ctx: QualificationContext) -> QualificationStageResult:
        """Verify staging frontend homepage, shell HTML, and API URL consistency."""
        stage_id = "frontend_availability_qualification"
        stage_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()

        if not ctx.staging_web_url:
            return QualificationStageResult(
                stage_id=stage_id,
                name="Frontend Availability Qualification",
                status=QualificationStatus.NOT_CONFIGURED,
                mandatory=True,
                requires_live_staging=True,
                started_at=stage_started,
                completed_at=datetime.now(UTC).isoformat(),
                message="STAGING_WEB_URL is not configured.",
            )

        client = self._web_client(ctx)
        checks: list[QualificationCheckResult] = []

        # 1. Homepage accessibility & content type & shell check
        c_start = datetime.now(UTC).isoformat()
        home_resp = client.get("/")
        ctype = home_resp.headers.get("content-type", "")
        has_html = "text/html" in ctype.lower()
        has_shell = any(
            marker in home_resp.text for marker in ("RegimeX", "__next", "<html", "<main")
        )
        prod_api_ref = _detect_production_reference(home_resp.text, ctx.env)

        home_ok = (
            home_resp.status_code == 200
            and has_html
            and has_shell
            and prod_api_ref is None
            and home_resp.error is None
        )
        home_status = (
            QualificationStatus.PASS
            if home_ok
            else (
                QualificationStatus.BLOCKED
                if home_resp.status_code is None
                else QualificationStatus.FAIL
            )
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.frontend.homepage",
                stage_id=stage_id,
                name="Frontend Homepage & Shell (GET /)",
                status=home_status,
                mandatory=True,
                started_at=c_start,
                duration_seconds=home_resp.duration_seconds,
                http_status=home_resp.status_code,
                message=(
                    "Frontend homepage reachable with valid HTML shell"
                    if home_ok
                    else (
                        f"Frontend homepage check failed: {prod_api_ref}"
                        if prod_api_ref
                        else f"Frontend homepage failed (HTTP {home_resp.status_code})"
                    )
                ),
                details={
                    "request_id": home_resp.request_id,
                    "content_type": ctype,
                    "has_shell": has_shell,
                    "redirects": list(home_resp.redirected_urls),
                },
                error=prod_api_ref or home_resp.error,
            )
        )

        # 2. Frontend /app/health route accessibility
        c_start = datetime.now(UTC).isoformat()
        app_health_resp = client.get("/app/health")
        ah_ctype = app_health_resp.headers.get("content-type", "")
        ah_ok = (
            app_health_resp.status_code == 200
            and "text/html" in ah_ctype.lower()
            and app_health_resp.error is None
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.frontend.health_shell",
                stage_id=stage_id,
                name="Frontend Health Route (GET /app/health)",
                status=(
                    QualificationStatus.PASS
                    if ah_ok
                    else (
                        QualificationStatus.BLOCKED
                        if app_health_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=False,
                started_at=c_start,
                duration_seconds=app_health_resp.duration_seconds,
                http_status=app_health_resp.status_code,
                message=(
                    "Frontend /app/health route accessible"
                    if ah_ok
                    else f"Frontend /app/health returned HTTP {app_health_resp.status_code}"
                ),
                details={"request_id": app_health_resp.request_id, "content_type": ah_ctype},
                error=app_health_resp.error,
            )
        )

        # 3. Frontend/Backend API URL configuration consistency
        c_start = datetime.now(UTC).isoformat()
        configured_public_api = (ctx.env.get("NEXT_PUBLIC_API_URL") or "").strip().rstrip("/")
        expected_api = (ctx.staging_api_url or "").strip().rstrip("/")
        if configured_public_api and expected_api:
            is_prod_pub, prod_reason = _is_production_url(configured_public_api, ctx.env)
            urls_match = configured_public_api.lower() == expected_api.lower() and not is_prod_pub
            cfg_msg = (
                "NEXT_PUBLIC_API_URL matches STAGING_API_URL"
                if urls_match
                else (
                    f"Production API reference rejected in NEXT_PUBLIC_API_URL: {prod_reason}"
                    if is_prod_pub
                    else (
                        f"Frontend NEXT_PUBLIC_API_URL ({configured_public_api}) mismatches "
                        f"STAGING_API_URL ({expected_api})"
                    )
                )
            )
            cfg_status = QualificationStatus.PASS if urls_match else QualificationStatus.FAIL
        else:
            cfg_msg = "NEXT_PUBLIC_API_URL not set in runner environment; HTML prod scan clean"
            cfg_status = (
                QualificationStatus.PASS if prod_api_ref is None else QualificationStatus.FAIL
            )

        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.frontend.api_config_consistency",
                stage_id=stage_id,
                name="Frontend/Backend API Config Consistency",
                status=cfg_status,
                mandatory=True,
                started_at=c_start,
                duration_seconds=0.0,
                message=cfg_msg,
                details={
                    "next_public_api_url": configured_public_api or None,
                    "staging_api_url": expected_api or None,
                },
                error=cfg_msg if cfg_status == QualificationStatus.FAIL else None,
            )
        )

        stage_status = _aggregate_stage_status(checks, strict=ctx.strict)
        return QualificationStageResult(
            stage_id=stage_id,
            name="Frontend Availability Qualification",
            status=stage_status,
            mandatory=True,
            requires_live_staging=True,
            started_at=stage_started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(time.monotonic() - t0, 4),
            checks=checks,
            message=(
                "Frontend availability and API configuration verified"
                if stage_status in (QualificationStatus.PASS, QualificationStatus.WARNING)
                else "Frontend availability or configuration check failed"
            ),
        )

    # -------------------------------------------------------------------------
    # Stage 3: Read-Only API Contract Qualification
    # -------------------------------------------------------------------------

    def run_api_contract_stage(self, ctx: QualificationContext) -> QualificationStageResult:
        """Verify auth enforcement, error envelopes, pagination, and schemas (read-only)."""
        stage_id = "api_contract_qualification"
        stage_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()

        if not ctx.staging_api_url:
            return QualificationStageResult(
                stage_id=stage_id,
                name="API Contract Qualification",
                status=QualificationStatus.NOT_CONFIGURED,
                mandatory=True,
                requires_live_staging=True,
                started_at=stage_started,
                completed_at=datetime.now(UTC).isoformat(),
                message="STAGING_API_URL is not configured.",
            )

        client = self._api_client(ctx)
        checks: list[QualificationCheckResult] = []

        # 1. Authentication enforcement (unauthenticated + invalid token -> 401)
        c_start = datetime.now(UTC).isoformat()
        unauth_resp = client.get("/api/v1/auth/me")
        bad_tok_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.staging.probe.token"},
        )
        auth_ok = unauth_resp.status_code == 401 and bad_tok_resp.status_code == 401
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.api.auth_enforcement",
                stage_id=stage_id,
                name="API Authentication Enforcement (/api/v1/auth/me)",
                status=(
                    QualificationStatus.PASS
                    if auth_ok
                    else (
                        QualificationStatus.BLOCKED
                        if unauth_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=unauth_resp.duration_seconds + bad_tok_resp.duration_seconds,
                http_status=unauth_resp.status_code,
                message=(
                    "Authentication boundary enforced (HTTP 401 on missing and invalid Bearer)"
                    if auth_ok
                    else (
                        f"Auth boundary check failed: unauth={unauth_resp.status_code}, "
                        f"invalid={bad_tok_resp.status_code}"
                    )
                ),
                details={
                    "unauth_status": unauth_resp.status_code,
                    "invalid_token_status": bad_tok_resp.status_code,
                },
                error=None if auth_ok else "Auth enforcement returned unexpected status",
            )
        )

        # 2. Invalid request handling & error envelope
        c_start = datetime.now(UTC).isoformat()
        bad_req = client.get("/api/v1/markets", params={"asset_class": "__invalid_asset_class__"})
        bad_body = bad_req.json_body if isinstance(bad_req.json_body, dict) else None
        has_err_envelope = bad_body is not None and ("error" in bad_body or "detail" in bad_body)
        invalid_ok = bad_req.status_code in (400, 422) and has_err_envelope
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.api.invalid_request_handling",
                stage_id=stage_id,
                name="API Invalid Request & Error Structure",
                status=(
                    QualificationStatus.PASS
                    if invalid_ok
                    else (
                        QualificationStatus.BLOCKED
                        if bad_req.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=bad_req.duration_seconds,
                http_status=bad_req.status_code,
                message=(
                    f"Structured validation error returned (HTTP {bad_req.status_code})"
                    if invalid_ok
                    else f"Unexpected invalid-request response (HTTP {bad_req.status_code})"
                ),
                details={
                    "request_id": bad_req.request_id,
                    "has_error_envelope": has_err_envelope,
                },
                error=None if invalid_ok else "Invalid request did not return structured 4xx error",
            )
        )

        # 3. Response schema & pagination consistency
        c_start = datetime.now(UTC).isoformat()
        pag_resp = client.get("/api/v1/markets", params={"limit": 2, "offset": 0})
        pag_body = pag_resp.json_body if isinstance(pag_resp.json_body, dict) else None
        pag_ok = (
            pag_resp.status_code == 200
            and pag_body is not None
            and isinstance(pag_body.get("items"), list)
            and len(pag_body["items"]) <= 2
            and isinstance(pag_body.get("total"), int)
            and pag_body.get("limit") == 2
            and pag_body.get("offset") == 0
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.api.pagination_and_schema",
                stage_id=stage_id,
                name="API Pagination & Schema (/api/v1/markets)",
                status=(
                    QualificationStatus.PASS
                    if pag_ok
                    else (
                        QualificationStatus.BLOCKED
                        if pag_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=pag_resp.duration_seconds,
                http_status=pag_resp.status_code,
                message=(
                    "Markets catalog schema and pagination verified"
                    if pag_ok
                    else f"Markets pagination/schema check failed (HTTP {pag_resp.status_code})"
                ),
                details={
                    "request_id": pag_resp.request_id,
                    "returned_count": len(pag_body["items"])
                    if pag_body and "items" in pag_body
                    else 0,
                    "total": pag_body.get("total") if pag_body else None,
                },
                error=None if pag_ok else "Response schema or pagination mismatch",
            )
        )

        # 4. Rate limit header inspection (non-mandatory)
        rl_headers = {
            k: v for k, v in pag_resp.headers.items() if "ratelimit" in k or k == "retry-after"
        }
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.api.rate_limit_headers",
                stage_id=stage_id,
                name="Rate-Limit Header Inspection",
                status=QualificationStatus.PASS,
                mandatory=False,
                started_at=stage_started,
                duration_seconds=0.0,
                http_status=pag_resp.status_code,
                message=(
                    f"Rate-limit headers observed: {list(rl_headers.keys())}"
                    if rl_headers
                    else "No explicit rate-limit headers configured on staging response"
                ),
                details={"rate_limit_headers": rl_headers},
            )
        )

        stage_status = _aggregate_stage_status(checks, strict=ctx.strict)
        return QualificationStageResult(
            stage_id=stage_id,
            name="API Contract Qualification",
            status=stage_status,
            mandatory=True,
            requires_live_staging=True,
            started_at=stage_started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(time.monotonic() - t0, 4),
            checks=checks,
            message=(
                "Read-only API contract checks passed"
                if stage_status == QualificationStatus.PASS
                else "API contract qualification failed"
            ),
        )

    # -------------------------------------------------------------------------
    # Stage 4: Database & Redis Dependency Qualification
    # -------------------------------------------------------------------------

    def run_dependency_stage(self, ctx: QualificationContext) -> QualificationStageResult:
        """Verify staging database connectivity, Alembic head compatibility, and Redis."""
        stage_id = "dependency_readiness_qualification"
        stage_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()
        checks: list[QualificationCheckResult] = []

        # 1. Database readiness via /ready + optional direct read-only probe
        c_start = datetime.now(UTC).isoformat()
        db_url = (
            ctx.env.get("STAGING_DATABASE_URL") or ctx.env.get("REGIMEX_DATABASE_URL") or ""
        ).strip()

        db_ok = False
        db_msg = "Database readiness not verified"
        db_err: str | None = None
        db_http_status: int | None = None
        db_details: dict[str, Any] = {}

        if ctx.staging_api_url:
            client = self._api_client(ctx)
            ready_resp = client.get("/ready")
            db_http_status = ready_resp.status_code
            body = ready_resp.json_body if isinstance(ready_resp.json_body, dict) else {}
            db_check_val = (body.get("checks") or {}).get("database")
            if ready_resp.status_code == 200 and db_check_val in ("ok", None):
                if db_check_val == "ok":
                    db_ok = True
                    db_msg = "Database dependency healthy via /ready"
                else:
                    db_ok = True
                    db_msg = "API /ready reported healthy application state"
            else:
                db_ok = False
                db_msg = f"Database readiness unhealthy via /ready (status={db_check_val})"
                db_err = ready_resp.error or db_msg
            db_details["ready_checks"] = body.get("checks") or {}

        # Optional direct read-only SQL/Alembic probe if explicitly enabled
        direct_db = ctx.env.get("REGIMEX_STAGING_DIRECT_DB_PROBE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if db_url and direct_db:
            probe_ok, live_rev, probe_msg = self.db_probe(db_url, 5.0)
            expected_heads = get_expected_alembic_heads(self.repo_root)
            db_details["alembic_live_revision"] = live_rev
            db_details["alembic_known_revisions"] = sorted(expected_heads)
            if not probe_ok:
                db_ok = False
                db_msg = f"Direct read-only DB probe failed: {probe_msg}"
                db_err = probe_msg
            elif expected_heads and live_rev and live_rev not in expected_heads:
                db_ok = False
                db_msg = f"Database migration mismatch: live revision '{live_rev}' unknown"
                db_err = db_msg
            else:
                db_ok = True
                db_msg = f"Database connectivity and schema verified (revision={live_rev or 'n/a'})"

        db_status = (
            QualificationStatus.PASS
            if db_ok
            else (
                QualificationStatus.NOT_CONFIGURED
                if not ctx.staging_api_url and not db_url
                else (
                    QualificationStatus.BLOCKED
                    if db_http_status is None and not direct_db
                    else QualificationStatus.FAIL
                )
            )
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.deps.database_readiness",
                stage_id=stage_id,
                name="Database Connectivity & Migration Readiness",
                status=db_status,
                mandatory=True,
                started_at=c_start,
                duration_seconds=time.monotonic() - t0,
                http_status=db_http_status,
                message=db_msg,
                details=db_details,
                error=db_err,
            )
        )

        # 2. Redis readiness (non-mandatory unless configured; read-only PING)
        c_start = datetime.now(UTC).isoformat()
        redis_url = (
            ctx.env.get("STAGING_REDIS_URL") or ctx.env.get("REGIMEX_REDIS_URL") or ""
        ).strip()
        if not redis_url:
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.deps.redis_readiness",
                    stage_id=stage_id,
                    name="Redis Connectivity",
                    status=QualificationStatus.NOT_CONFIGURED,
                    mandatory=False,
                    started_at=c_start,
                    duration_seconds=0.0,
                    message="STAGING_REDIS_URL not configured (optional cache/worker dependency)",
                )
            )
        else:
            r_ok, r_msg = self.redis_probe(redis_url, 4.0)
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.deps.redis_readiness",
                    stage_id=stage_id,
                    name="Redis Connectivity",
                    status=QualificationStatus.PASS if r_ok else QualificationStatus.FAIL,
                    mandatory=True,
                    started_at=c_start,
                    duration_seconds=0.0,
                    message=r_msg if r_ok else f"Redis connectivity check failed: {r_msg}",
                    error=None if r_ok else r_msg,
                )
            )

        stage_status = _aggregate_stage_status(checks, strict=ctx.strict)
        return QualificationStageResult(
            stage_id=stage_id,
            name="Database & Redis Dependency Qualification",
            status=stage_status,
            mandatory=True,
            requires_live_staging=True,
            started_at=stage_started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(time.monotonic() - t0, 4),
            checks=checks,
            message=(
                "Database and Redis dependency readiness verified"
                if stage_status in (QualificationStatus.PASS, QualificationStatus.WARNING)
                else "Dependency readiness qualification failed"
            ),
        )

    # -------------------------------------------------------------------------
    # Stage 5: Application Service Qualification (Read-Only)
    # -------------------------------------------------------------------------

    def run_service_stage(self, ctx: QualificationContext) -> QualificationStageResult:
        """Verify critical RegimeX service readiness (market data, health, models, AI)."""
        stage_id = "service_readiness_qualification"
        stage_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()

        if not ctx.staging_api_url:
            return QualificationStageResult(
                stage_id=stage_id,
                name="Application Service Qualification",
                status=QualificationStatus.NOT_CONFIGURED,
                mandatory=True,
                requires_live_staging=True,
                started_at=stage_started,
                completed_at=datetime.now(UTC).isoformat(),
                message="STAGING_API_URL is not configured.",
            )

        client = self._api_client(ctx)
        checks: list[QualificationCheckResult] = []

        # 1. System operational health summary (/api/v1/health/summary)
        c_start = datetime.now(UTC).isoformat()
        sum_resp = client.get("/api/v1/health/summary")
        sum_body = sum_resp.json_body if isinstance(sum_resp.json_body, dict) else None
        sum_ok = (
            sum_resp.status_code == 200
            and sum_body is not None
            and "status" in sum_body
            and isinstance(sum_body.get("components"), dict)
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.service.observability_summary",
                stage_id=stage_id,
                name="Observability & System Health Summary",
                status=(
                    QualificationStatus.PASS
                    if sum_ok
                    else (
                        QualificationStatus.BLOCKED
                        if sum_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=sum_resp.duration_seconds,
                http_status=sum_resp.status_code,
                message=(
                    f"System health summary operational (status={sum_body.get('status')})"
                    if sum_ok and sum_body is not None
                    else f"System health summary failed (HTTP {sum_resp.status_code})"
                ),
                details={
                    "components": list((sum_body.get("components") or {}).keys())
                    if sum_body
                    else []
                },
                error=sum_resp.error if not sum_ok else None,
            )
        )

        # 2. Regime models readiness (/api/v1/health/models)
        c_start = datetime.now(UTC).isoformat()
        mod_resp = client.get("/api/v1/health/models")
        mod_body = mod_resp.json_body if isinstance(mod_resp.json_body, dict) else None
        mod_ok = (
            mod_resp.status_code == 200
            and mod_body is not None
            and isinstance(mod_body.get("items"), list)
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.service.regime_models",
                stage_id=stage_id,
                name="Regime Inference Models Readiness",
                status=(
                    QualificationStatus.PASS
                    if mod_ok
                    else (
                        QualificationStatus.BLOCKED
                        if mod_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=mod_resp.duration_seconds,
                http_status=mod_resp.status_code,
                message=(
                    f"Regime model telemetry ready (models={mod_body.get('total')})"
                    if mod_ok and mod_body is not None
                    else f"Regime model readiness failed (HTTP {mod_resp.status_code})"
                ),
                details={"total": mod_body.get("total") if mod_body else None},
                error=mod_resp.error if not mod_ok else None,
            )
        )

        # 3. Data feeds & pipeline readiness (/api/v1/health/data, /api/v1/health/pipeline)
        c_start = datetime.now(UTC).isoformat()
        data_resp = client.get("/api/v1/health/data")
        pipe_resp = client.get("/api/v1/health/pipeline")
        dp_ok = (
            data_resp.status_code == 200
            and isinstance(data_resp.json_body, dict)
            and pipe_resp.status_code == 200
            and isinstance(pipe_resp.json_body, dict)
        )
        checks.append(
            _make_check(
                ctx=ctx,
                check_id="smoke.service.feature_and_pipeline",
                stage_id=stage_id,
                name="Market Data & Pipeline Readiness",
                status=(
                    QualificationStatus.PASS
                    if dp_ok
                    else (
                        QualificationStatus.BLOCKED
                        if data_resp.status_code is None or pipe_resp.status_code is None
                        else QualificationStatus.FAIL
                    )
                ),
                mandatory=True,
                started_at=c_start,
                duration_seconds=data_resp.duration_seconds + pipe_resp.duration_seconds,
                http_status=data_resp.status_code,
                message=(
                    "Data feed and pipeline telemetry operational"
                    if dp_ok
                    else "Data feed or pipeline readiness check failed"
                ),
                error=data_resp.error or pipe_resp.error if not dp_ok else None,
            )
        )

        # 4. Optional AI research integration readiness
        c_start = datetime.now(UTC).isoformat()
        ai_provider = (
            ctx.env.get("REGIMEX_AI_PROVIDER") or ctx.env.get("AI_PROVIDER") or ""
        ).strip()
        ai_key = (ctx.env.get("REGIMEX_AI_API_KEY") or ctx.env.get("AI_API_KEY") or "").strip()
        if ai_provider.lower() == "openai" and not ai_key:
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.service.ai_research_optional",
                    stage_id=stage_id,
                    name="AI Research Assistant Integration (Optional)",
                    status=QualificationStatus.NOT_CONFIGURED,
                    mandatory=False,
                    started_at=c_start,
                    duration_seconds=0.0,
                    message="External AI provider configured without API key (optional).",
                )
            )
        elif not ai_provider or ai_provider.lower() == "mock":
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.service.ai_research_optional",
                    stage_id=stage_id,
                    name="AI Research Assistant Integration (Optional)",
                    status=QualificationStatus.WARNING,
                    mandatory=False,
                    started_at=c_start,
                    duration_seconds=0.0,
                    message="AI Research Assistant running in offline 'mock' mode (optional).",
                )
            )
        else:
            ai_resp = client.get("/api/v1/research/context/SPY")
            ai_ok = ai_resp.status_code == 200 and isinstance(ai_resp.json_body, list)
            checks.append(
                _make_check(
                    ctx=ctx,
                    check_id="smoke.service.ai_research_optional",
                    stage_id=stage_id,
                    name="AI Research Assistant Integration (Optional)",
                    status=QualificationStatus.PASS if ai_ok else QualificationStatus.WARNING,
                    mandatory=False,
                    started_at=c_start,
                    duration_seconds=ai_resp.duration_seconds,
                    http_status=ai_resp.status_code,
                    message=(
                        "AI research evidence context endpoint verified"
                        if ai_ok
                        else (
                            f"Optional AI research context unavailable (HTTP {ai_resp.status_code})"
                        )
                    ),
                )
            )

        stage_status = _aggregate_stage_status(checks, strict=ctx.strict)
        return QualificationStageResult(
            stage_id=stage_id,
            name="Application Service Qualification",
            status=stage_status,
            mandatory=True,
            requires_live_staging=True,
            started_at=stage_started,
            completed_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(time.monotonic() - t0, 4),
            checks=checks,
            message=(
                "Critical RegimeX application services verified"
                if stage_status in (QualificationStatus.PASS, QualificationStatus.WARNING)
                else "Application service qualification failed"
            ),
        )


def _detect_production_reference(html_text: str, env: dict[str, str]) -> str | None:
    """Scan HTML/JS response for unexpected production API references."""
    if not html_text:
        return None
    lowered = html_text.lower()
    prod_urls = (
        env.get("PRODUCTION_API_URL", ""),
        env.get("PRODUCTION_WEB_URL", ""),
        "https://api.regimex.io",
        "https://app.regimex.io",
    )
    for p_url in prod_urls:
        clean = p_url.strip().rstrip("/").lower()
        if clean and clean in lowered:
            return f"Detected production URL reference '{clean}' in frontend response"
    return None


def register_smoke_stages(
    registry: QualificationStageRegistry,
    suite: StagingSmokeSuite | None = None,
) -> QualificationStageRegistry:
    """Register all V27 Commit 02 read-only staging smoke stages into a registry."""
    smoke = suite or StagingSmokeSuite()

    registry.register(
        QualificationStage(
            stage_id="backend_health_qualification",
            name="Backend Health & Readiness Qualification",
            description="Verifies /api/v1/health/live, /api/v1/health/ready, and /ready.",
            prerequisites=["qualification_policy"],
            requires_live_staging=True,
            timeout_seconds=30.0,
            mandatory=True,
            approved=True,
        ),
        smoke.run_backend_health_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="frontend_availability_qualification",
            name="Frontend Availability Qualification",
            description="Verifies staging web homepage, shell HTML, and API config consistency.",
            prerequisites=["backend_health_qualification"],
            requires_live_staging=True,
            timeout_seconds=30.0,
            mandatory=True,
            approved=True,
        ),
        smoke.run_frontend_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="api_contract_qualification",
            name="API Contract Qualification",
            description="Verifies auth enforcement, validation errors, pagination, and schemas.",
            prerequisites=["backend_health_qualification"],
            requires_live_staging=True,
            timeout_seconds=30.0,
            mandatory=True,
            approved=True,
        ),
        smoke.run_api_contract_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="dependency_readiness_qualification",
            name="Database & Redis Dependency Qualification",
            description="Verifies database readiness, migration compatibility, and Redis PING.",
            prerequisites=["backend_health_qualification"],
            requires_live_staging=True,
            timeout_seconds=30.0,
            mandatory=True,
            approved=True,
        ),
        smoke.run_dependency_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="service_readiness_qualification",
            name="Application Service Qualification",
            description=(
                "Verifies RegimeX observability, market data, model health, and AI readiness."
            ),
            prerequisites=["backend_health_qualification", "api_contract_qualification"],
            requires_live_staging=True,
            timeout_seconds=30.0,
            mandatory=True,
            approved=True,
        ),
        smoke.run_service_stage,
    )
    return registry


def build_smoke_stage_registry(
    suite: StagingSmokeSuite | None = None,
) -> QualificationStageRegistry:
    """Create a complete approved registry containing Commit 01 + Commit 02 smoke stages."""
    registry = build_default_stage_registry()
    return register_smoke_stages(registry, suite=suite)
