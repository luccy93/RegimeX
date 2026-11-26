"""Unit tests for RegimeX staging service qualification & smoke suite (V27 Commit 02).

Verifies:
1. Backend health success and failure (/api/v1/health/live).
2. Backend readiness failure (/api/v1/health/ready and /ready).
3. Frontend availability and HTML shell verification.
4. Frontend/backend URL mismatch and production URL reference detection.
5. API authentication enforcement (401 on missing/invalid Bearer).
6. Invalid response schemas and malformed JSON handling.
7. Database readiness and Alembic revision compatibility.
8. Redis readiness (PASS, FAIL, and NOT_CONFIGURED).
9. Request timeout handling.
10. Retry exhaustion on transient 503/network errors.
11. Secret redaction in smoke test diagnostics and headers.
12. Production target rejection.
13. Live-test opt-in enforcement (StagingLiveTestGuard).
14. Read-only behavior (prohibiting non-idempotent methods).
15. Missing optional integrations (AI research mock/unconfigured).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.core.staging_qualification import StagingQualificationOrchestrator
from app.core.staging_smoke import (
    SmokeClientConfig,
    StagingHttpClient,
    StagingLiveTestGuard,
    StagingSmokeSuite,
    build_smoke_stage_registry,
)
from app.schemas.staging_readiness import (
    AuthStatus,
    CategorySummary,
    CheckStatus,
    DockerReadinessEvidence,
    GHCRAccessEvidence,
    GitHubAccessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
    QualificationStatus,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
    StagingGateEvaluationReport,
    StagingPreflightReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "7cd7701a6c51205cab70271c857c1609e68d7b01"
STAGING_ENV = {
    "STAGING_API_URL": "https://api.staging.regimex.example.com",
    "STAGING_WEB_URL": "https://staging.regimex.example.com",
    "NEXT_PUBLIC_API_URL": "https://api.staging.regimex.example.com",
    "STAGING_DATABASE_URL": "postgresql+asyncpg://stage:StageSecret99!@db.staging.internal:5432/regimex_stage",
    "STAGING_REDIS_URL": "redis://:StageRedis99!@redis.staging.internal:6379/0",
    "STAGING_SMOKE_USER": "staging_smoke",
    "STAGING_SMOKE_PASSWORD": "IsolatedSmokePassword2026!",
    "REGIMEX_SECRET_KEY": "staging-jwt-secret-key-at-least-32-characters-long",
    "REGIMEX_AI_PROVIDER": "mock",
}


def make_preflight() -> StagingPreflightReport:
    summary = CategorySummary(
        category="host",
        status=CheckStatus.PASS,
        total_checks=1,
        passed_checks=1,
        failed_checks=0,
        blocked_checks=0,
        warning_checks=0,
        not_configured_checks=0,
        not_run_checks=0,
        checks=[],
    )
    return StagingPreflightReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        branch="main",
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        host=summary,
        runtime=summary,
        security=summary,
        release=summary,
    )


def make_evidence() -> InfrastructureEvidenceReport:
    return InfrastructureEvidenceReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        live_qualification_authorized=False,
        production_deployment_authorized=False,
        docker=DockerReadinessEvidence(
            status=CheckStatus.PASS,
            engine_accessible=True,
            compose_available=True,
            available_storage_gb=20.0,
            ports_available={8000: True, 3000: True, 5432: True, 6379: True},
        ),
        github=GitHubAccessEvidence(
            status=CheckStatus.PASS,
            cli_available=True,
            auth_status=AuthStatus.AUTHENTICATED,
            repository_accessible=True,
            read_permission=True,
        ),
        ghcr=GHCRAccessEvidence(
            status=CheckStatus.PASS,
            registry_url="ghcr.io",
            auth_status=AuthStatus.AUTHENTICATED,
            pull_capability_verified=True,
        ),
        release_manifest=ReleaseManifestEvidence(
            status=CheckStatus.PASS,
            commit_sha=VALID_SHA,
            repository="luccy93/RegimeX",
            images={"api": f"ghcr.io/luccy93/regimex-api@sha256:{'a' * 64}"},
            immutable_digests_verified=True,
            provenance_verified=True,
        ),
        smoke_credentials=SmokeCredentialEvidence(
            status=CheckStatus.PASS,
            username_configured=True,
            password_configured=True,
            credentials_masked=True,
        ),
        rollback=RollbackReadinessEvidence(
            status=CheckStatus.PASS,
            backup_configured=True,
            backup_directory_ready=True,
            recovery_runbook_verified=True,
        ),
        gpu=GPUCapabilityEvidence(
            status=CheckStatus.WARNING,
            mandatory=False,
            gpu_available=False,
        ),
    )


def make_gate_report(*, is_ready: bool = True) -> StagingGateEvaluationReport:
    return StagingGateEvaluationReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        evaluated_at=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS if is_ready else CheckStatus.FAIL,
        is_ready=is_ready,
        live_qualification_authorized=False,
        production_deployment_authorized=False,
        preflight_evaluated=True,
        evidence_evaluated=True,
        evidence_is_fresh=True,
    )


def build_healthy_api_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/health/live":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "service": "RegimeX API",
                    "version": "1.0.0",
                },
            )
        if path == "/api/v1/health/ready":
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "checks": {"api": "ok"},
                },
            )
        if path == "/ready":
            return httpx.Response(
                200,
                json={
                    "status": "ready",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "checks": {"application": "ok", "database": "ok"},
                },
            )
        if path == "/api/v1/auth/me":
            return httpx.Response(401, json={"error": {"code": "AUTH_REQUIRED"}})
        if path == "/api/v1/markets":
            if request.url.params.get("asset_class") == "__invalid_asset_class__":
                return httpx.Response(
                    422,
                    json={"error": {"code": "VALIDATION_ERROR", "message": "Invalid asset_class"}},
                )
            return httpx.Response(
                200,
                json={
                    "items": [{"symbol": "SPY", "asset_class": "equity_us"}],
                    "total": 1,
                    "limit": 2,
                    "offset": 0,
                },
            )
        if path == "/api/v1/health/summary":
            return httpx.Response(
                200,
                json={"status": "healthy", "components": {"market_data": {"status": "healthy"}}},
            )
        if path == "/api/v1/health/models":
            return httpx.Response(200, json={"items": [], "total": 0})
        if path in ("/api/v1/health/data", "/api/v1/health/pipeline"):
            return httpx.Response(200, json={"items": [], "overall_status": "healthy"})
        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


def build_healthy_web_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><body><main>RegimeX Platform</main></body></html>",
        )

    return httpx.MockTransport(handler)


def _run_suite_with_transports(
    *,
    api_transport: httpx.BaseTransport,
    web_transport: httpx.BaseTransport,
    env: dict[str, str] | None = None,
    db_probe: Any = None,
    redis_probe: Any = None,
    config: SmokeClientConfig | None = None,
) -> Any:
    suite = StagingSmokeSuite(
        client_config=config,
        api_transport=api_transport,
        web_transport=web_transport,
        db_probe=db_probe or (lambda _u, _t: (True, "0002_create_users_table", "OK")),
        redis_probe=redis_probe or (lambda _u, _t: (True, "Redis PING succeeded")),
        repo_root=REPO_ROOT,
    )
    registry = build_smoke_stage_registry(suite)
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        stage_registry=registry,
        env=env if env is not None else dict(STAGING_ENV),
    )
    return orch.run_qualification()


def test_full_smoke_suite_passes_against_healthy_mock_staging() -> None:
    """All 8 stages pass when mocked staging API, Web, DB, and Redis respond healthily."""
    report = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=build_healthy_web_transport(),
    )
    assert report.overall_status == QualificationStatus.WARNING  # optional AI mock advisory
    assert report.qualification_passed is True
    assert len(report.stages) == 8
    backend_stage = next(s for s in report.stages if s.stage_id == "backend_health_qualification")
    assert backend_stage.status == QualificationStatus.PASS
    smoke_checks = [c for c in report.checks if c.check_id.startswith("smoke.")]
    assert len(smoke_checks) >= 10
    assert all(c.evidence_ref and c.commit_sha == VALID_SHA for c in smoke_checks)


def test_backend_health_failure_reported() -> None:
    """HTTP 500 or wrong service identity on /api/v1/health/live fails backend stage."""

    def bad_live(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/health/live":
            return httpx.Response(500, json={"status": "error"})
        return httpx.Response(200, json={"status": "ready", "checks": {"application": "ok"}})

    report = _run_suite_with_transports(
        api_transport=httpx.MockTransport(bad_live),
        web_transport=build_healthy_web_transport(),
    )
    assert report.overall_status == QualificationStatus.FAIL
    live_chk = next(c for c in report.checks if c.check_id == "smoke.backend.liveness")
    assert live_chk.status == QualificationStatus.FAIL
    assert live_chk.http_status == 500


def test_backend_readiness_failure_reported() -> None:
    """503 or database unavailable on /ready fails backend readiness even if /live is 200."""

    def unready(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/health/live":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "service": "RegimeX API",
                    "version": "1.0.0",
                },
            )
        if request.url.path == "/api/v1/health/ready":
            return httpx.Response(200, json={"status": "ready", "checks": {"api": "ok"}})
        if request.url.path == "/ready":
            return httpx.Response(
                503,
                json={
                    "status": "not_ready",
                    "checks": {"application": "ok", "database": "unavailable"},
                },
            )
        return httpx.Response(200, json={"items": [], "total": 0, "limit": 2, "offset": 0})

    report = _run_suite_with_transports(
        api_transport=httpx.MockTransport(unready),
        web_transport=build_healthy_web_transport(),
    )
    assert report.overall_status == QualificationStatus.FAIL
    root_ready = next(c for c in report.checks if c.check_id == "smoke.backend.readiness_root")
    assert root_ready.status == QualificationStatus.FAIL
    assert root_ready.http_status == 503


def test_frontend_availability_and_url_mismatch() -> None:
    """Frontend/backend URL mismatch and leaked production URL fail frontend qualification."""
    mismatched_env = dict(STAGING_ENV)
    mismatched_env["NEXT_PUBLIC_API_URL"] = "https://other.staging.example.com"

    report = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=build_healthy_web_transport(),
        env=mismatched_env,
    )
    assert report.overall_status == QualificationStatus.FAIL
    cfg_chk = next(
        c for c in report.checks if c.check_id == "smoke.frontend.api_config_consistency"
    )
    assert cfg_chk.status == QualificationStatus.FAIL
    assert "mismatches" in cfg_chk.message

    prod_leak_web = httpx.MockTransport(
        lambda _req: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html>RegimeX <script>window.API='https://api.regimex.io'</script></html>",
        )
    )
    report_leak = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=prod_leak_web,
    )
    assert report_leak.overall_status == QualificationStatus.FAIL
    home_chk = next(c for c in report_leak.checks if c.check_id == "smoke.frontend.homepage")
    assert home_chk.status == QualificationStatus.FAIL
    assert "production URL reference" in home_chk.message


def test_api_authentication_enforcement_and_invalid_schemas() -> None:
    """Missing 401 on /auth/me or invalid schema on /markets fails API contract stage."""

    def broken_api(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/me":
            return httpx.Response(200, json={"email": "leaked@example.com"})
        if request.url.path == "/api/v1/markets":
            return httpx.Response(200, text="not-json")
        return build_healthy_api_transport().handle_request(request)

    report = _run_suite_with_transports(
        api_transport=httpx.MockTransport(broken_api),
        web_transport=build_healthy_web_transport(),
    )
    auth_chk = next(c for c in report.checks if c.check_id == "smoke.api.auth_enforcement")
    pag_chk = next(c for c in report.checks if c.check_id == "smoke.api.pagination_and_schema")
    assert auth_chk.status == QualificationStatus.FAIL
    assert pag_chk.status == QualificationStatus.FAIL


def test_database_and_redis_readiness_checks() -> None:
    """Direct DB probe, migration revision verification, and Redis readiness are enforced."""
    env_with_db = {**STAGING_ENV, "REGIMEX_STAGING_DIRECT_DB_PROBE": "1"}
    report_bad_rev = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=build_healthy_web_transport(),
        env=env_with_db,
        db_probe=lambda _u, _t: (True, "9999_unknown_revision", "OK"),
        redis_probe=lambda _u, _t: (False, "Connection refused"),
    )
    db_chk = next(c for c in report_bad_rev.checks if c.check_id == "smoke.deps.database_readiness")
    redis_chk = next(c for c in report_bad_rev.checks if c.check_id == "smoke.deps.redis_readiness")
    assert db_chk.status == QualificationStatus.FAIL
    assert "unknown" in db_chk.message
    assert redis_chk.status == QualificationStatus.FAIL

    env_no_redis = dict(STAGING_ENV)
    env_no_redis.pop("STAGING_REDIS_URL")
    report_no_redis = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=build_healthy_web_transport(),
        env=env_no_redis,
    )
    redis_opt = next(
        c for c in report_no_redis.checks if c.check_id == "smoke.deps.redis_readiness"
    )
    assert redis_opt.status == QualificationStatus.NOT_CONFIGURED


def test_request_timeout_and_retry_exhaustion() -> None:
    """Bounded retries execute on transient errors/503s and fail/block after exhaustion."""
    attempts = 0

    def flaky_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise httpx.ReadTimeout("Timed out reading staging socket", request=request)
        return httpx.Response(503, json={"status": "unavailable"})

    cfg = SmokeClientConfig(
        environment="staging",
        commit_sha=VALID_SHA,
        connect_timeout_seconds=1.0,
        read_timeout_seconds=1.0,
        max_retries=2,
        retry_backoff_seconds=0.0,
    )
    client = StagingHttpClient(
        "https://api.staging.regimex.example.com",
        config=cfg,
        env=STAGING_ENV,
        transport=httpx.MockTransport(flaky_handler),
    )
    resp = client.get("/api/v1/health/live")
    assert attempts == 3
    assert resp.attempts == 3
    assert resp.status_code == 503
    assert resp.ok is False

    # Pure timeout exhaustion returns status_code=None and error
    def always_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connect timeout", request=request)

    client_to = StagingHttpClient(
        "https://api.staging.regimex.example.com",
        config=cfg,
        env=STAGING_ENV,
        transport=httpx.MockTransport(always_timeout),
    )
    to_resp = client_to.get("/api/v1/health/live")
    assert to_resp.status_code is None
    assert to_resp.attempts == 3
    assert "ConnectTimeout" in (to_resp.error or "")


def test_secret_redaction_and_production_target_rejection() -> None:
    """Smoke client redacts secrets and rejects production URLs."""
    with pytest.raises(ValueError, match="Production target URL rejected"):
        StagingHttpClient(
            "https://api.regimex.io",
            config=SmokeClientConfig(environment="staging"),
            env=STAGING_ENV,
        )

    def leaky_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Failed auth Bearer secret-bearer-999 against postgresql://u:IsolatedSmokePassword2026!@h/db",
            request=request,
        )

    client = StagingHttpClient(
        "https://api.staging.regimex.example.com",
        config=SmokeClientConfig(environment="staging", max_retries=0),
        env=STAGING_ENV,
        transport=httpx.MockTransport(leaky_error),
    )
    resp = client.get("/api/v1/health/live")
    assert "IsolatedSmokePassword2026!" not in (resp.error or "")
    assert "secret-bearer-999" not in (resp.error or "")


def test_read_only_behavior_enforced() -> None:
    """StagingHttpClient refuses non-idempotent POST/PUT/DELETE methods by default."""
    client = StagingHttpClient(
        "https://api.staging.regimex.example.com",
        config=SmokeClientConfig(environment="staging"),
        env=STAGING_ENV,
        transport=build_healthy_api_transport(),
    )
    with pytest.raises(ValueError, match="prohibited in read-only smoke suite"):
        client.request("POST", "/api/v1/auth/register", json_payload={"email": "x@y.com"})


def test_live_test_opt_in_guard_enforcement() -> None:
    """Live test guard refuses execution unless opt-in and all safety gates hold."""
    # 1. Opt-in disabled
    res_off = StagingLiveTestGuard.evaluate(env=dict(STAGING_ENV), environment="staging")
    assert res_off.allowed is False
    assert res_off.status == QualificationStatus.NOT_RUN

    # 2. Production rejected even with opt-in
    opted_env = {**STAGING_ENV, "REGIMEX_STAGING_LIVE_TESTS": "1"}
    res_prod = StagingLiveTestGuard.evaluate(env=opted_env, environment="production")
    assert res_prod.allowed is False
    assert res_prod.status == QualificationStatus.FAIL

    # 3. Missing URL -> NOT_CONFIGURED
    no_url_env = {**opted_env}
    no_url_env.pop("STAGING_API_URL")
    res_no_url = StagingLiveTestGuard.evaluate(env=no_url_env, environment="staging")
    assert res_no_url.allowed is False
    assert res_no_url.status == QualificationStatus.NOT_CONFIGURED

    # 4. Missing credentials -> NOT_CONFIGURED
    no_cred_env = {**opted_env}
    no_cred_env.pop("STAGING_SMOKE_PASSWORD")
    res_no_cred = StagingLiveTestGuard.evaluate(env=no_cred_env, environment="staging")
    assert res_no_cred.allowed is False
    assert res_no_cred.status == QualificationStatus.NOT_CONFIGURED

    # 5. Failed V26 gate -> BLOCKED
    res_gate = StagingLiveTestGuard.evaluate(
        env=opted_env,
        environment="staging",
        gate_report=make_gate_report(is_ready=False),
    )
    assert res_gate.allowed is False
    assert res_gate.status == QualificationStatus.BLOCKED

    # 6. All satisfied -> allowed
    res_ok = StagingLiveTestGuard.evaluate(
        env=opted_env,
        environment="staging",
        gate_report=make_gate_report(is_ready=True),
    )
    assert res_ok.allowed is True
    assert res_ok.status == QualificationStatus.PASS


def test_missing_optional_ai_integration_does_not_fail_mandatory() -> None:
    """Missing optional AI API key reports NOT_CONFIGURED without failing mandatory pass."""
    env_opt = {**STAGING_ENV, "REGIMEX_AI_PROVIDER": "openai"}
    report = _run_suite_with_transports(
        api_transport=build_healthy_api_transport(),
        web_transport=build_healthy_web_transport(),
        env=env_opt,
    )
    ai_chk = next(c for c in report.checks if c.check_id == "smoke.service.ai_research_optional")
    assert ai_chk.mandatory is False
    assert ai_chk.status == QualificationStatus.NOT_CONFIGURED
    assert report.overall_status == QualificationStatus.PASS
    assert report.qualification_passed is True
    parsed = json.loads(report.to_json())
    assert parsed["live_qualification_authorized"] is False
