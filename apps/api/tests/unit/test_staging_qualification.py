"""Unit tests for RegimeX controlled staging qualification orchestration (V27 Commit 01).

Verifies:
- Valid qualification request and 13-step orchestration sequence.
- Rejection of invalid/malformed 40-char commit SHAs.
- Rejection of invalid environment names and production environment targets.
- Rejection of production target URLs and colliding production credentials.
- Missing staging target configuration resulting in NOT_CONFIGURED.
- Missing or malformed V26 preflight/evidence reports.
- Failed or blocked V26 readiness gates halting qualification before stages run.
- Stale V26 evidence rejection.
- Repository identity mismatch rejection.
- Dry-run isolation (zero network calls, live stages skipped with NOT_RUN).
- Unique qualification run identity and immutable release identity.
- Structured StagingQualificationReport generation and lifecycle distinction.
- Comprehensive secret redaction in reports, errors, and details.
- Controlled stage registry enforcement (rejecting unregistered/unapproved stages).
- CLI argument handling and exit codes.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from app.core.staging_qualification import (
    QualificationContext,
    QualificationStageRegistry,
    StagingQualificationOrchestrator,
    build_default_stage_registry,
    sanitize_mapping,
    sanitize_text,
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
    QualificationCheckResult,
    QualificationStage,
    QualificationStageResult,
    QualificationStatus,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
    StagingPreflightReport,
    StagingQualificationReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CLI_PATH = REPO_ROOT / "scripts" / "staging_qualification.py"


def _load_cli_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("staging_qualification_cli", CLI_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qual_cli = _load_cli_module()

VALID_SHA = "7cd7701a6c51205cab70271c857c1609e68d7b01"
BASE_STAGING_ENV = {
    "STAGING_API_URL": "https://api.staging.regimex.example.com",
    "STAGING_WEB_URL": "https://staging.regimex.example.com",
    "STAGING_DATABASE_URL": "postgresql+asyncpg://stage_user:StageSecret99!@db.staging.internal:5432/regimex_stage",
    "STAGING_REDIS_URL": "redis://:RedisStageSecret!@redis.staging.internal:6379/0",
    "STAGING_SMOKE_USER": "staging_smoke",
    "STAGING_SMOKE_PASSWORD": "IsolatedSmokePassword2026!",
    "REGIMEX_SECRET_KEY": "staging-jwt-secret-key-at-least-32-characters-long",
}


def make_preflight(
    *,
    commit_sha: str = VALID_SHA,
    repository: str = "luccy93/RegimeX",
    overall_status: CheckStatus = CheckStatus.PASS,
    environment: str = "staging",
) -> StagingPreflightReport:
    """Create a synthetic V26 preflight report."""
    summary = CategorySummary(
        category="host",
        status=overall_status,
        total_checks=4,
        passed_checks=4 if overall_status == CheckStatus.PASS else 0,
        failed_checks=1 if overall_status == CheckStatus.FAIL else 0,
        blocked_checks=1 if overall_status == CheckStatus.BLOCKED else 0,
        warning_checks=0,
        not_configured_checks=1 if overall_status == CheckStatus.NOT_CONFIGURED else 0,
        not_run_checks=0,
        checks=[],
    )
    return StagingPreflightReport(
        schema_version="1.0.0",
        environment=environment,
        repository=repository,
        commit_sha=commit_sha,
        branch="main",
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=overall_status,
        is_ready=(overall_status == CheckStatus.PASS),
        strict_mode=False,
        host=summary,
        runtime=summary,
        security=summary,
        release=summary,
        failed_checks=["host_fail"] if overall_status == CheckStatus.FAIL else [],
        blocked_checks=["docker_blocked"] if overall_status == CheckStatus.BLOCKED else [],
    )


def make_evidence(
    *,
    commit_sha: str = VALID_SHA,
    repository: str = "luccy93/RegimeX",
    timestamp: str | None = None,
    docker_status: CheckStatus = CheckStatus.PASS,
    immutable_digests: bool = True,
    live_qual_auth: bool = False,
    prod_deploy_auth: bool = False,
) -> InfrastructureEvidenceReport:
    """Create a synthetic V26 infrastructure evidence report."""
    return InfrastructureEvidenceReport(
        schema_version="1.0.0",
        environment="staging",
        repository=repository,
        commit_sha=commit_sha,
        timestamp=timestamp or datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        strict_mode=False,
        live_qualification_authorized=live_qual_auth,
        production_deployment_authorized=prod_deploy_auth,
        docker=DockerReadinessEvidence(
            status=docker_status,
            engine_accessible=(docker_status == CheckStatus.PASS),
            engine_version="25.0.3",
            compose_available=True,
            compose_version="v2.24.5",
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
            status=CheckStatus.PASS if immutable_digests else CheckStatus.FAIL,
            commit_sha=commit_sha,
            repository=repository,
            images={"api": f"ghcr.io/luccy93/regimex-api@sha256:{'a' * 64}"},
            immutable_digests_verified=immutable_digests,
            provenance_verified=True,
        ),
        smoke_credentials=SmokeCredentialEvidence(
            status=CheckStatus.PASS,
            username_configured=True,
            password_configured=True,
            credentials_masked=True,
            production_secret_leak_detected=False,
        ),
        rollback=RollbackReadinessEvidence(
            status=CheckStatus.PASS,
            backup_configured=True,
            backup_directory_ready=True,
            recovery_runbook_verified=True,
            previous_release_identified=True,
            forward_only_migration_policy_verified=True,
        ),
        gpu=GPUCapabilityEvidence(
            status=CheckStatus.WARNING,
            mandatory=False,
            gpu_available=False,
            device_count=0,
        ),
    )


def test_valid_qualification_request_passes() -> None:
    """Valid staging qualification request passes all baseline approved stages."""
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=dict(BASE_STAGING_ENV),
    )

    report = orch.run_qualification()

    assert isinstance(report, StagingQualificationReport)
    assert report.overall_status == QualificationStatus.PASS
    assert report.qualification_requested is True
    assert report.qualification_started is True
    assert report.qualification_completed is True
    assert report.qualification_passed is True
    assert report.qualification_blocked is False
    assert report.qualification_failed is False
    assert report.v26_gate_passed is True
    assert report.environment.name == "staging"
    assert report.environment.isolated_from_production is True
    assert report.live_qualification_authorized is False
    assert report.production_deployment_authorized is False
    assert report.production_deployment_performed is False
    assert report.container_images_published is False
    assert len(report.stages) == 3


def test_invalid_commit_sha_rejected() -> None:
    """Malformed or short commit SHAs fail before qualification stages start."""
    for bad_sha in ("", "abc123", "z" * 40, "7cd7701"):
        orch = StagingQualificationOrchestrator(
            repo_root=REPO_ROOT,
            environment="staging",
            commit_sha=bad_sha,
            preflight_report=make_preflight(),
            evidence_report=make_evidence(),
            env=dict(BASE_STAGING_ENV),
        )
        report = orch.run_qualification()

        assert report.overall_status == QualificationStatus.FAIL
        assert report.qualification_requested is True
        assert report.qualification_started is False
        assert report.qualification_completed is True
        assert report.qualification_failed is True
        assert report.qualification_passed is False
        assert "Invalid commit SHA" in (report.error_message or "")


def test_invalid_environment_rejected() -> None:
    """Non-staging environments like 'development' or 'qa' are rejected."""
    for bad_env in ("development", "dev", "qa", "test", ""):
        orch = StagingQualificationOrchestrator(
            repo_root=REPO_ROOT,
            environment=bad_env,
            commit_sha=VALID_SHA,
            preflight_report=make_preflight(),
            evidence_report=make_evidence(),
            env=dict(BASE_STAGING_ENV),
        )
        report = orch.run_qualification()

        assert report.overall_status == QualificationStatus.FAIL
        assert report.qualification_started is False
        assert report.qualification_failed is True
        assert "Invalid environment" in (report.error_message or "")


def test_production_environment_rejected() -> None:
    """Production environment names are strictly rejected."""
    for prod_env in ("production", "prod", "PROD", "live", "production-us"):
        orch = StagingQualificationOrchestrator(
            repo_root=REPO_ROOT,
            environment=prod_env,
            commit_sha=VALID_SHA,
            preflight_report=make_preflight(),
            evidence_report=make_evidence(),
            env=dict(BASE_STAGING_ENV),
        )
        report = orch.run_qualification()

        assert report.overall_status == QualificationStatus.FAIL
        assert report.qualification_started is False
        assert report.qualification_failed is True
        assert report.environment.isolated_from_production is False
        assert "Production environment" in (report.error_message or "")


def test_production_url_and_credential_collision_rejected() -> None:
    """Production URLs and colliding production credentials are rejected."""
    env_prod_url = dict(BASE_STAGING_ENV)
    env_prod_url["STAGING_API_URL"] = "https://api.regimex.io"

    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=env_prod_url,
    )
    report = orch.run_qualification()
    assert report.overall_status == QualificationStatus.FAIL
    assert report.environment.isolated_from_production is False
    assert "Production target rejected" in (report.error_message or "")

    env_cred_collision = dict(BASE_STAGING_ENV)
    env_cred_collision["PRODUCTION_SECRET_KEY"] = BASE_STAGING_ENV["STAGING_SMOKE_PASSWORD"]
    orch_cred = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=env_cred_collision,
    )
    report_cred = orch_cred.run_qualification()
    assert report_cred.overall_status == QualificationStatus.FAIL
    assert "collides with production credential" in (report_cred.error_message or "")


def test_missing_staging_target_reports_not_configured() -> None:
    """Missing STAGING_API_URL / STAGING_WEB_URL never falls back to prod."""
    env_missing = {
        "STAGING_SMOKE_USER": "staging_smoke",
        "STAGING_SMOKE_PASSWORD": "IsolatedSmokePassword2026!",
        "PRODUCTION_API_URL": "https://api.prod.regimex.example.com",
        "PRODUCTION_WEB_URL": "https://prod.regimex.example.com",
    }
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=env_missing,
    )
    report = orch.run_qualification()

    assert report.overall_status == QualificationStatus.NOT_CONFIGURED
    assert report.qualification_blocked is True
    assert report.qualification_passed is False
    assert report.environment.api_url is None
    assert "Missing staging target configuration" in (report.error_message or "")


def test_missing_v26_evidence_reports_blocked(tmp_path: Path) -> None:
    """Explicitly specified but missing V26 preflight or evidence file returns BLOCKED."""
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report_path=tmp_path / "missing-preflight.json",
        evidence_report=make_evidence(),
        env=dict(BASE_STAGING_ENV),
    )
    report = orch.run_qualification()
    assert report.overall_status == QualificationStatus.BLOCKED
    assert report.qualification_blocked is True
    assert report.qualification_passed is False

    orch_ev = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report_path=tmp_path / "missing-evidence.json",
        env=dict(BASE_STAGING_ENV),
    )
    report_ev = orch_ev.run_qualification()
    assert report_ev.overall_status == QualificationStatus.BLOCKED
    assert report_ev.qualification_blocked is True


def test_failed_v26_readiness_gate_halts_qualification() -> None:
    """When V26 readiness gates fail or are blocked, qualification stages must not execute."""
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(overall_status=CheckStatus.FAIL),
        evidence_report=make_evidence(docker_status=CheckStatus.BLOCKED),
        env=dict(BASE_STAGING_ENV),
    )
    report = orch.run_qualification()

    assert report.overall_status == QualificationStatus.FAIL
    assert report.v26_gate_passed is False
    assert report.qualification_passed is False
    assert report.qualification_failed is True
    assert report.stages == []
    assert "V26 readiness gates did not pass" in (report.error_message or "")


def test_stale_v26_evidence_blocks_qualification() -> None:
    """Stale V26 evidence fails freshness gate and prevents qualification execution."""
    stale_ts = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(timestamp=stale_ts),
        max_age_seconds=1800,
        env=dict(BASE_STAGING_ENV),
    )
    report = orch.run_qualification()

    assert report.overall_status == QualificationStatus.BLOCKED
    assert report.v26_gate_passed is False
    assert report.qualification_blocked is True
    assert report.stages == []


def test_repository_mismatch_rejected() -> None:
    """Mismatched repository identity in request or V26 reports fails closed."""
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        repository="attacker/RegimeX-fork",
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=dict(BASE_STAGING_ENV),
    )
    report = orch.run_qualification()
    assert report.overall_status == QualificationStatus.FAIL
    assert report.qualification_started is False
    assert "Repository identity mismatch" in (report.error_message or "")

    orch_ev = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(repository="other/RegimeX"),
        env=dict(BASE_STAGING_ENV),
    )
    report_ev = orch_ev.run_qualification()
    assert report_ev.overall_status == QualificationStatus.FAIL
    assert "V26 evidence repository mismatch" in (report_ev.error_message or "")


def test_dry_run_isolation_makes_no_network_calls() -> None:
    """Dry-run skips live staging stages without invoking live handlers or network calls."""
    live_called = False

    def _live_handler(ctx: QualificationContext) -> QualificationStageResult:
        nonlocal live_called
        live_called = True
        return QualificationStageResult(
            stage_id="live_smoke",
            name="Live Smoke",
            status=QualificationStatus.PASS,
        )

    registry = build_default_stage_registry()
    registry.register(
        QualificationStage(
            stage_id="live_smoke",
            name="Live Smoke Stage",
            prerequisites=["qualification_policy"],
            requires_live_staging=True,
            timeout_seconds=15.0,
            mandatory=True,
            approved=True,
        ),
        _live_handler,
    )

    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        dry_run=True,
        stage_registry=registry,
        env=dict(BASE_STAGING_ENV),
    )

    with patch("urllib.request.urlopen", side_effect=AssertionError("Network call forbidden")):
        report = orch.run_qualification()

    assert live_called is False
    assert report.run_metadata.dry_run is True
    assert report.qualification_completed is True
    assert report.qualification_passed is False
    assert report.overall_status == QualificationStatus.NOT_RUN
    live_stage = next(s for s in report.stages if s.stage_id == "live_smoke")
    assert live_stage.status == QualificationStatus.NOT_RUN
    assert "Dry-run" in live_stage.message


def test_unique_qualification_run_identity_and_structured_report() -> None:
    """Each run generates a unique run_id, immutable release identity, and valid JSON schema."""
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        env=dict(BASE_STAGING_ENV),
    )
    r1 = orch.run_qualification()
    r2 = orch.run_qualification()

    assert r1.run_id != r2.run_id
    assert r1.run_id.startswith("qual-")
    assert r1.release_tag == f"regimex-{VALID_SHA[:8]}"
    assert r1.commit_sha == VALID_SHA

    parsed = json.loads(r1.to_json(indent=2))
    assert parsed["run_id"] == r1.run_id
    assert parsed["live_qualification_authorized"] is False
    assert parsed["production_deployment_authorized"] is False
    assert parsed["production_deployment_performed"] is False
    assert parsed["container_images_published"] is False


def test_secret_redaction_in_reports_and_errors() -> None:
    """Secrets, tokens, passwords, and DB DSNs are strictly redacted from outputs."""
    secret_env = {
        **BASE_STAGING_ENV,
        "GITHUB_TOKEN": "ghp_superSecretTokenValue1234567890",
        "STAGING_SMOKE_PASSWORD": "UltraSecretSmokePassword987!",
    }
    raw_msg = (
        "Failed connecting postgresql+asyncpg://user:UltraSecretSmokePassword987!@db/app "
        "with Authorization: Bearer my-jwt-token-xyz and ghp_superSecretTokenValue1234567890"
    )
    redacted = sanitize_text(raw_msg, env=secret_env)
    assert "UltraSecretSmokePassword987!" not in redacted
    assert "ghp_superSecretTokenValue1234567890" not in redacted
    assert "my-jwt-token-xyz" not in redacted

    clean_map = sanitize_mapping(
        {"password": "abc", "nested": {"api_key": "sk-1234567890abcdef"}, "msg": raw_msg},
        env=secret_env,
    )
    assert clean_map["password"] == "***"
    assert clean_map["nested"]["api_key"] == "***"
    assert "UltraSecretSmokePassword987!" not in clean_map["msg"]

    def _leaky_stage(ctx: QualificationContext) -> QualificationStageResult:
        return QualificationStageResult(
            stage_id="leaky",
            name="Leaky",
            status=QualificationStatus.FAIL,
            requires_live_staging=False,
            checks=[
                QualificationCheckResult(
                    check_id="leaky.chk",
                    stage_id="leaky",
                    name="Leaky Check",
                    status=QualificationStatus.FAIL,
                    message=raw_msg,
                    error=raw_msg,
                    details={"token": "secret-val", "note": raw_msg},
                )
            ],
            message=raw_msg,
            error=raw_msg,
        )

    registry = build_default_stage_registry()
    registry.register(
        QualificationStage(
            stage_id="leaky",
            name="Leaky Stage",
            requires_live_staging=False,
            timeout_seconds=5.0,
        ),
        _leaky_stage,
    )
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        stage_registry=registry,
        env=secret_env,
    )
    report_json = orch.run_qualification().to_json()
    assert "UltraSecretSmokePassword987!" not in report_json
    assert "ghp_superSecretTokenValue1234567890" not in report_json
    assert "my-jwt-token-xyz" not in report_json


def test_unapproved_or_unregistered_stage_rejected() -> None:
    """Stage registry refuses unregistered or unapproved stages."""
    registry = QualificationStageRegistry()
    registry.register(
        QualificationStage(
            stage_id="unapproved_stage",
            name="Unapproved",
            requires_live_staging=False,
            approved=False,
        ),
        lambda _ctx: QualificationStageResult(
            stage_id="unapproved_stage",
            name="Unapproved",
            status=QualificationStatus.PASS,
        ),
    )
    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        commit_sha=VALID_SHA,
        preflight_report=make_preflight(),
        evidence_report=make_evidence(),
        stage_registry=registry,
        approved_stage_ids=["unapproved_stage"],
        env=dict(BASE_STAGING_ENV),
    )
    report = orch.run_qualification()
    assert report.overall_status == QualificationStatus.FAIL
    assert "Unapproved qualification stage rejected" in (report.error_message or "")


def test_cli_dry_run_and_exit_codes(tmp_path: Path) -> None:
    """CLI writes JSON report, respects dry-run, and returns deterministic exit codes."""
    pf_path = tmp_path / "preflight.json"
    ev_path = tmp_path / "evidence.json"
    out_path = tmp_path / "qual-report.json"

    pf_path.write_text(make_preflight().to_json(), encoding="utf-8")
    ev_path.write_text(make_evidence().to_json(), encoding="utf-8")

    code = qual_cli.main(
        [
            "--environment",
            "staging",
            "--commit-sha",
            VALID_SHA,
            "--preflight-report",
            str(pf_path),
            "--evidence-report",
            str(ev_path),
            "--staging-api-url",
            "https://api.staging.regimex.example.com",
            "--staging-web-url",
            "https://staging.regimex.example.com",
            "--format",
            "json",
            "--output",
            str(out_path),
            "--dry-run",
        ]
    )
    assert code == qual_cli.EXIT_SUCCESS
    assert out_path.is_file()
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    assert parsed["overall_status"] == "PASS"
    assert parsed["run_metadata"]["dry_run"] is True

    bad_env_code = qual_cli.main(
        [
            "--environment",
            "production",
            "--commit-sha",
            VALID_SHA,
            "--format",
            "text",
        ]
    )
    assert bad_env_code == qual_cli.EXIT_INVALID_ARGS
