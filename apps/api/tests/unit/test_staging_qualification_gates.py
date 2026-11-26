"""End-to-end qualification gate & evidence audit tests (V27 Commit 03).

Covers the complete 20-scenario V27 test matrix:
1.  Fully mocked successful qualification -> NOT_QUALIFIED (never QUALIFIED).
2.  Missing staging configuration -> NOT_CONFIGURED.
3.  Failed V26 readiness gate -> BLOCKED.
4.  Backend liveness failure -> NOT_QUALIFIED.
5.  Backend readiness failure -> NOT_QUALIFIED.
6.  Frontend failure -> NOT_QUALIFIED.
7.  Database unavailable -> NOT_QUALIFIED.
8.  Redis unavailable (when configured) -> NOT_QUALIFIED.
9.  Invalid commit identity -> FAILED.
10. Environment identity mismatch -> FAILED.
11. Stale evidence -> BLOCKED.
12. Tampered evidence (contradictory results, duplicate IDs, bad schema) -> FAILED.
13. Mocked evidence presented as live -> FAILED.
14. Missing mandatory test evidence -> NOT_QUALIFIED.
15. Optional GPU unavailable -> does not block QUALIFIED/mandatory pass.
16. Optional AI integration unavailable -> does not fail mandatory qualification.
17. Multiple simultaneous failures -> all surfaced, optional never conceals mandatory.
18. Secret leakage prevention -> zero plaintext secrets in audit JSON or text.
19. Production URL rejection -> FAILED.
20. Governance flags remain false (and tampering them to True -> FAILED).
Plus valid LIVE_STAGING run -> QUALIFIED & CI workflow invariant checks.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from app.core.staging_qualification import StagingQualificationOrchestrator
from app.core.staging_qualification_gates import (
    QualificationEvidenceEvaluator,
    format_text_audit_report,
)
from app.core.staging_smoke import StagingSmokeSuite, build_smoke_stage_registry
from app.schemas.staging_readiness import (
    AuthStatus,
    CategorySummary,
    CheckStatus,
    DockerReadinessEvidence,
    ExecutionMode,
    GHCRAccessEvidence,
    GitHubAccessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
    QualificationDecision,
    QualificationEvidence,
    QualificationStatus,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
    StagingPreflightReport,
    StagingQualificationAuditReport,
    StagingQualificationReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "a6e7b4949daf44cc6159d93ef219d8d84d111a72"
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


def make_preflight(
    *,
    commit_sha: str = VALID_SHA,
    overall_status: CheckStatus = CheckStatus.PASS,
) -> StagingPreflightReport:
    summary = CategorySummary(
        category="host",
        status=overall_status,
        total_checks=1,
        passed_checks=1 if overall_status == CheckStatus.PASS else 0,
        failed_checks=1 if overall_status == CheckStatus.FAIL else 0,
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
        commit_sha=commit_sha,
        branch="main",
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=overall_status,
        is_ready=(overall_status == CheckStatus.PASS),
        host=summary,
        runtime=summary,
        security=summary,
        release=summary,
    )


def make_evidence(
    *,
    commit_sha: str = VALID_SHA,
    timestamp: str | None = None,
    gpu_available: bool = False,
) -> InfrastructureEvidenceReport:
    return InfrastructureEvidenceReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=commit_sha,
        timestamp=timestamp or datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        live_qualification_authorized=False,
        production_deployment_authorized=False,
        docker=DockerReadinessEvidence(
            status=CheckStatus.PASS,
            engine_accessible=True,
            compose_available=True,
            available_storage_gb=25.0,
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
            commit_sha=commit_sha,
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
            status=CheckStatus.PASS if gpu_available else CheckStatus.WARNING,
            mandatory=False,
            gpu_available=gpu_available,
            device_count=1 if gpu_available else 0,
        ),
    )


def healthy_api_transport(
    overrides: dict[str, httpx.Response] | None = None,
) -> httpx.MockTransport:
    overrides = overrides or {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in overrides:
            return overrides[path]
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
            if request.url.params.get("asset_class"):
                return httpx.Response(
                    422, json={"error": {"code": "VALIDATION_ERROR", "message": "Invalid"}}
                )
            return httpx.Response(200, json={"items": [], "total": 0, "limit": 2, "offset": 0})
        if path == "/api/v1/health/summary":
            return httpx.Response(200, json={"status": "healthy", "components": {"models": {}}})
        if path in ("/api/v1/health/models", "/api/v1/health/data", "/api/v1/health/pipeline"):
            return httpx.Response(200, json={"items": [], "total": 0})
        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


def healthy_web_transport(status_code: int = 200) -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            headers={"content-type": "text/html"},
            text="<html><body>RegimeX</body></html>" if status_code == 200 else "Error",
        )

    return httpx.MockTransport(handler)


def run_e2e_audit(
    *,
    env: dict[str, str] | None = None,
    environment: str = "staging",
    commit_sha: str = VALID_SHA,
    preflight: StagingPreflightReport | None = None,
    evidence: InfrastructureEvidenceReport | None = None,
    api_overrides: dict[str, httpx.Response] | None = None,
    web_status: int = 200,
    db_ok: bool = True,
    redis_ok: bool = True,
    execution_mode: ExecutionMode = ExecutionMode.MOCKED,
    include_smoke: bool = True,
    max_age_seconds: int = 3600,
) -> tuple[StagingQualificationReport, StagingQualificationAuditReport]:
    ev_report = evidence or make_evidence(commit_sha=commit_sha)
    pf_report = preflight or make_preflight(commit_sha=commit_sha)
    suite = StagingSmokeSuite(
        api_transport=healthy_api_transport(api_overrides),
        web_transport=healthy_web_transport(web_status),
        db_probe=lambda _u, _t: (
            (True, "0002_create_users_table", "OK")
            if db_ok
            else (False, None, "Database connection refused")
        ),
        redis_probe=lambda _u, _t: (redis_ok, "OK" if redis_ok else "Redis unreachable"),
        repo_root=REPO_ROOT,
    )
    registry = build_smoke_stage_registry(suite) if include_smoke else None
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment=environment,
        commit_sha=commit_sha,
        preflight_report=pf_report,
        evidence_report=ev_report,
        stage_registry=registry,
        execution_mode=execution_mode,
        max_age_seconds=max_age_seconds,
        env=env if env is not None else dict(STAGING_ENV),
    )
    qual_report = orch.run_qualification()
    evaluator = QualificationEvidenceEvaluator(
        max_age_seconds=max_age_seconds,
        env=env if env is not None else dict(STAGING_ENV),
    )
    audit = evaluator.evaluate(
        report=qual_report,
        execution_mode=execution_mode,
        infrastructure_evidence=ev_report,
    )
    return qual_report, audit


def test_01_fully_mocked_qualification_never_produces_qualified() -> None:
    """1. Mocked success proves correctness but MUST yield NOT_QUALIFIED, never QUALIFIED."""
    qual, audit = run_e2e_audit(execution_mode=ExecutionMode.MOCKED)
    assert qual.qualification_passed is True
    assert audit.execution_mode == ExecutionMode.MOCKED
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert "cannot establish live staging qualification" in audit.decision_reason


def test_live_staging_all_mandatory_pass_produces_qualified() -> None:
    """Valid LIVE_STAGING run with all mandatory checks passing yields QUALIFIED."""
    _, audit = run_e2e_audit(execution_mode=ExecutionMode.LIVE_STAGING)
    assert audit.decision == QualificationDecision.QUALIFIED
    assert audit.live_qualification_authorized is False
    assert audit.production_deployment_authorized is False
    assert audit.production_deployment_performed is False
    assert audit.container_images_published is False
    text_summary = format_text_audit_report(audit)
    assert "QUALIFIED" in text_summary


def test_02_missing_staging_configuration_returns_not_configured() -> None:
    """2. Missing staging target URLs results in NOT_CONFIGURED."""
    env = dict(STAGING_ENV)
    env.pop("STAGING_API_URL")
    _, audit = run_e2e_audit(env=env, execution_mode=ExecutionMode.LIVE_STAGING)
    assert audit.decision == QualificationDecision.NOT_CONFIGURED


def test_03_failed_v26_readiness_gate_returns_blocked() -> None:
    """3. Failed V26 readiness gate blocks qualification execution."""
    _, audit = run_e2e_audit(
        preflight=make_preflight(overall_status=CheckStatus.FAIL),
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.BLOCKED
    assert audit.v26_readiness_result == CheckStatus.FAIL


def test_04_backend_liveness_failure_returns_not_qualified() -> None:
    """4. Backend liveness failure yields NOT_QUALIFIED."""
    _, audit = run_e2e_audit(
        api_overrides={"/api/v1/health/live": httpx.Response(500, json={"status": "error"})},
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert audit.backend_smoke_result == QualificationStatus.FAIL


def test_05_backend_readiness_failure_returns_not_qualified() -> None:
    """5. Backend readiness failure yields NOT_QUALIFIED."""
    _, audit = run_e2e_audit(
        api_overrides={
            "/ready": httpx.Response(
                503, json={"status": "not_ready", "checks": {"database": "unavailable"}}
            )
        },
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.NOT_QUALIFIED


def test_06_frontend_failure_returns_not_qualified() -> None:
    """6. Frontend HTTP 500 failure yields NOT_QUALIFIED."""
    _, audit = run_e2e_audit(web_status=500, execution_mode=ExecutionMode.LIVE_STAGING)
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert audit.frontend_smoke_result == QualificationStatus.FAIL


def test_07_database_unavailable_returns_not_qualified() -> None:
    """7. Database unavailable during dependency probe yields NOT_QUALIFIED."""
    env_db = {**STAGING_ENV, "REGIMEX_STAGING_DIRECT_DB_PROBE": "1"}
    _, audit = run_e2e_audit(
        env=env_db,
        db_ok=False,
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert audit.database_result == QualificationStatus.FAIL


def test_08_redis_unavailable_returns_not_qualified() -> None:
    """8. Configured Redis failure yields NOT_QUALIFIED."""
    _, audit = run_e2e_audit(redis_ok=False, execution_mode=ExecutionMode.LIVE_STAGING)
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert audit.redis_result == QualificationStatus.FAIL


def test_09_invalid_commit_identity_returns_failed() -> None:
    """9. Invalid commit SHA returns FAILED."""
    _, audit = run_e2e_audit(
        commit_sha="invalid-sha",
        preflight=make_preflight(commit_sha=VALID_SHA),
        evidence=make_evidence(commit_sha=VALID_SHA),
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.FAILED
    assert audit.evidence_integrity_result == QualificationStatus.FAIL


def test_10_environment_identity_mismatch_returns_failed() -> None:
    """10. Environment mismatch returns FAILED."""
    qual, _ = run_e2e_audit(execution_mode=ExecutionMode.LIVE_STAGING)
    tampered_env = qual.environment.model_copy(update={"name": "qa"})
    tampered = qual.model_copy(update={"environment": tampered_env})
    audit = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
        report=tampered, execution_mode=ExecutionMode.LIVE_STAGING
    )
    assert audit.decision == QualificationDecision.FAILED
    assert audit.evidence_integrity_result == QualificationStatus.FAIL


def test_11_stale_evidence_returns_blocked() -> None:
    """11. Stale evidence blocks qualification."""
    stale_ts = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    _, audit = run_e2e_audit(
        evidence=make_evidence(timestamp=stale_ts),
        max_age_seconds=1800,
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.BLOCKED
    assert audit.evidence_freshness_result == QualificationStatus.BLOCKED


def test_12_tampered_evidence_rejected_as_failed() -> None:
    """12. Contradictory status, duplicate evidence IDs, and bad schema version yield FAILED."""
    qual, _ = run_e2e_audit(execution_mode=ExecutionMode.LIVE_STAGING)

    tampered_contradiction = qual.model_copy(
        update={
            "overall_status": QualificationStatus.PASS,
            "failed_checks": ["injected failure"],
        }
    )
    audit_c = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
        report=tampered_contradiction, execution_mode=ExecutionMode.LIVE_STAGING
    )
    assert audit_c.decision == QualificationDecision.FAILED

    dup_ev = [*qual.evidence, qual.evidence[0]]
    tampered_dup = qual.model_copy(update={"evidence": dup_ev, "schema_version": "9.9.9"})
    audit_d = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
        report=tampered_dup, execution_mode=ExecutionMode.LIVE_STAGING
    )
    assert audit_d.decision == QualificationDecision.FAILED


def test_13_mocked_evidence_presented_as_live_rejected() -> None:
    """13. Mocked evidence presented under LIVE_STAGING mode is rejected as FAILED."""
    mocked_qual, _ = run_e2e_audit(execution_mode=ExecutionMode.MOCKED)
    audit = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
        report=mocked_qual,
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.FAILED
    assert any("MOCKED under LIVE_STAGING" in fc for fc in audit.failed_checks)

    # Also test mocked source marker in QualificationEvidence
    fake_ev = QualificationEvidence(
        evidence_id="stage-fake",
        source="MockedTestTransport",
        timestamp=datetime.now(UTC).isoformat(),
        commit_sha=VALID_SHA,
        repository="luccy93/RegimeX",
        environment="staging",
        status=QualificationStatus.PASS,
        execution_mode=ExecutionMode.LIVE_STAGING,
        is_live=True,
        is_fresh=True,
    )
    tampered = mocked_qual.model_copy(update={"evidence": [fake_ev]})
    audit_src = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
        report=tampered, execution_mode=ExecutionMode.LIVE_STAGING
    )
    assert audit_src.decision == QualificationDecision.FAILED


def test_14_missing_mandatory_test_evidence_returns_not_qualified() -> None:
    """14. Omitting smoke stages leaves mandatory evidence incomplete -> NOT_QUALIFIED."""
    _, audit = run_e2e_audit(
        include_smoke=False,
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    smoke_pol = next(p for p in audit.mandatory_checks if p.policy_id == "QUAL-POL-SMOKE-COMPLETE")
    assert smoke_pol.status == QualificationStatus.NOT_RUN


def test_15_and_16_optional_gpu_and_ai_unavailable_do_not_block_qualified() -> None:
    """15 & 16. Missing optional GPU and AI integration keep LIVE_STAGING QUALIFIED."""
    env_no_ai = {
        **STAGING_ENV,
        "REGIMEX_AI_PROVIDER": "openai",
    }  # missing API key -> optional NOT_CONFIGURED
    _, audit = run_e2e_audit(
        env=env_no_ai,
        evidence=make_evidence(gpu_available=False),
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.QUALIFIED
    gpu_opt = next(p for p in audit.optional_checks if p.policy_id == "QUAL-OPT-GPU")
    ai_opt = next(p for p in audit.optional_checks if p.policy_id == "QUAL-OPT-AI")
    assert gpu_opt.mandatory is False
    assert ai_opt.mandatory is False
    assert ai_opt.status == QualificationStatus.NOT_CONFIGURED


def test_17_multiple_simultaneous_failures_not_concealed() -> None:
    """17. Multiple simultaneous failures are all reported without concealment."""
    _, audit = run_e2e_audit(
        api_overrides={
            "/api/v1/health/live": httpx.Response(500, json={"status": "err"}),
            "/ready": httpx.Response(
                503, json={"status": "not_ready", "checks": {"database": "unavailable"}}
            ),
        },
        web_status=502,
        redis_ok=False,
        execution_mode=ExecutionMode.LIVE_STAGING,
    )
    assert audit.decision == QualificationDecision.NOT_QUALIFIED
    assert len(audit.failed_checks) >= 3


def test_18_secret_leakage_prevention() -> None:
    """18. Credentials never appear in audit JSON or text reports."""
    _, audit = run_e2e_audit(execution_mode=ExecutionMode.LIVE_STAGING)
    json_str = audit.to_json(indent=2)
    text_str = format_text_audit_report(audit)
    for secret_val in (
        STAGING_ENV["STAGING_SMOKE_PASSWORD"],
        STAGING_ENV["REGIMEX_SECRET_KEY"],
        "StageSecret99!",
        "StageRedis99!",
    ):
        assert secret_val not in json_str
        assert secret_val not in text_str


def test_19_production_url_rejection() -> None:
    """19. Production target URL yields FAILED decision."""
    env_prod = {**STAGING_ENV, "STAGING_API_URL": "https://api.regimex.io"}
    _, audit = run_e2e_audit(env=env_prod, execution_mode=ExecutionMode.LIVE_STAGING)
    assert audit.decision == QualificationDecision.FAILED


def test_20_governance_flags_remain_false_and_tampering_rejected() -> None:
    """20. Governance flags always remain False; tampering any flag to True yields FAILED."""
    qual, audit = run_e2e_audit(execution_mode=ExecutionMode.LIVE_STAGING)
    parsed: dict[str, Any] = json.loads(audit.to_json())
    assert parsed["live_qualification_authorized"] is False
    assert parsed["production_deployment_authorized"] is False
    assert parsed["production_deployment_performed"] is False
    assert parsed["container_images_published"] is False
    assert isinstance(audit, StagingQualificationAuditReport)

    for flag in (
        "live_qualification_authorized",
        "production_deployment_authorized",
        "production_deployment_performed",
        "container_images_published",
    ):
        tampered = qual.model_copy(update={flag: True})
        bad_audit = QualificationEvidenceEvaluator(env=STAGING_ENV).evaluate(
            report=tampered, execution_mode=ExecutionMode.LIVE_STAGING
        )
        assert bad_audit.decision == QualificationDecision.FAILED
        assert bad_audit.production_deployment_authorized is False
        assert bad_audit.live_qualification_authorized is False


def test_ci_workflow_includes_v27_qualification_gates() -> None:
    """CI workflow runs V27 mocked qualification tests without live staging or deployment."""
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    content = ci_path.read_text(encoding="utf-8")
    assert "test_staging_qualification_gates.py" in content
    assert "REGIMEX_STAGING_LIVE_TESTS" in content
    assert "StagingQualificationAuditReport" in content
