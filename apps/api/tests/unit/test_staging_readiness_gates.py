"""Unit tests for RegimeX staging readiness gate evaluator.

Verifies:
- All 6 core gate policies (Host/Runtime, Docker, Manifest, Secrets, Rollback, Governance).
- Evidence freshness validation and rejection of stale/expired reports.
- Commit SHA integrity matching between preflight and evidence reports.
- Detection and blocking of container engine failures.
- Enforcement of immutable container image digests (@sha256:...).
- Rejection of production secret leaks in smoke test credentials.
- Strict enforcement of Volume V26 governance boundaries:
  `live_qualification_authorized` and `production_deployment_authorized` MUST be False.
- Strict mode escalation of advisory warnings to failure.
- Machine-readable JSON report serialization.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.staging_gates import StagingReadinessGateEvaluator
from app.schemas.staging_readiness import (
    AuthStatus,
    CategorySummary,
    CheckStatus,
    DockerReadinessEvidence,
    GHCRAccessEvidence,
    GitHubAccessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
    StagingGateEvaluationReport,
    StagingPreflightReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "d8885b27a6c51205cab70271c857c1609e68d7b0"


def make_mock_preflight(
    overall_status: CheckStatus = CheckStatus.PASS,
    commit_sha: str = VALID_SHA,
) -> StagingPreflightReport:
    """Helper to create a valid StagingPreflightReport instance."""
    summary = CategorySummary(
        category="host",
        status=overall_status,
        total_checks=5,
        passed_checks=5 if overall_status == CheckStatus.PASS else 0,
        failed_checks=5 if overall_status == CheckStatus.FAIL else 0,
        blocked_checks=5 if overall_status == CheckStatus.BLOCKED else 0,
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
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=overall_status,
        is_ready=(overall_status == CheckStatus.PASS),
        strict_mode=False,
        host=summary,
        runtime=summary,
        security=summary,
        release=summary,
        failed_checks=["Host failure"] if overall_status == CheckStatus.FAIL else [],
        blocked_checks=["Docker blocked"] if overall_status == CheckStatus.BLOCKED else [],
        warnings=[],
        remediations=[],
    )


def make_mock_evidence(
    commit_sha: str = VALID_SHA,
    timestamp: str | None = None,
    docker_status: CheckStatus = CheckStatus.PASS,
    immutable_digests: bool = True,
    secret_leak: bool = False,
    runbooks_verified: bool = True,
    live_qual_auth: bool = False,
    prod_deploy_auth: bool = False,
) -> InfrastructureEvidenceReport:
    """Helper to create an InfrastructureEvidenceReport instance."""
    ts = timestamp or datetime.now(UTC).isoformat()
    return InfrastructureEvidenceReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=commit_sha,
        timestamp=ts,
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
            available_storage_gb=15.0,
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
            repository="luccy93/RegimeX",
            images={"api": f"ghcr.io/api@sha256:{'a' * 64}"},
            immutable_digests_verified=immutable_digests,
            provenance_verified=True,
        ),
        smoke_credentials=SmokeCredentialEvidence(
            status=CheckStatus.FAIL if secret_leak else CheckStatus.PASS,
            username_configured=True,
            password_configured=True,
            credentials_masked=True,
            production_secret_leak_detected=secret_leak,
        ),
        rollback=RollbackReadinessEvidence(
            status=CheckStatus.PASS if runbooks_verified else CheckStatus.FAIL,
            backup_configured=True,
            backup_directory_ready=True,
            recovery_runbook_verified=runbooks_verified,
            previous_release_identified=True,
            forward_only_migration_policy_verified=True,
        ),
        gpu=GPUCapabilityEvidence(
            status=CheckStatus.WARNING,
            mandatory=False,
            gpu_available=False,
            device_count=0,
        ),
        failed_checks=[],
        blocked_checks=[],
        warnings=["GPU optional advisory"],
        remediations=[],
    )


def test_gate_all_policies_pass() -> None:
    """When preflight and evidence are valid and matching, all gate policies PASS."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence()

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    assert report.overall_status == CheckStatus.PASS
    assert report.is_ready is True
    assert report.live_qualification_authorized is False
    assert report.production_deployment_authorized is False
    assert report.evidence_is_fresh is True
    assert len(report.gate_policies) == 7  # Integrity + 6 Core Policies
    assert all(p.status in (CheckStatus.PASS, CheckStatus.WARNING) for p in report.gate_policies)


def test_gate_stale_evidence_report_fails_freshness() -> None:
    """Evidence older than max_age_seconds fails the freshness gate."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT, max_age_seconds=1800)
    stale_time = (datetime.now(UTC) - timedelta(seconds=3600)).isoformat()
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(timestamp=stale_time)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    integrity_policy = next(
        p for p in report.gate_policies if p.policy_id == "GATE-EVIDENCE-INTEGRITY"
    )
    assert integrity_policy.status in (CheckStatus.BLOCKED, CheckStatus.FAIL)
    assert report.evidence_is_fresh is False
    assert "Evidence is stale" in integrity_policy.message
    assert report.is_ready is False


def test_gate_commit_sha_mismatch_fails_integrity() -> None:
    """When preflight SHA and evidence SHA differ, GATE-EVIDENCE-INTEGRITY fails with FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight(commit_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    evidence = make_mock_evidence(commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    integrity_policy = next(
        p for p in report.gate_policies if p.policy_id == "GATE-EVIDENCE-INTEGRITY"
    )
    assert integrity_policy.status == CheckStatus.FAIL
    assert "Commit SHA mismatch" in integrity_policy.message
    assert report.overall_status == CheckStatus.FAIL
    assert report.is_ready is False


def test_gate_preflight_fail_fails_host_runtime_policy() -> None:
    """When preflight reports FAIL, GATE-HOST-RUNTIME reports FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight(overall_status=CheckStatus.FAIL)
    evidence = make_mock_evidence()

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    policy = next(p for p in report.gate_policies if p.policy_id == "GATE-HOST-RUNTIME")
    assert policy.status == CheckStatus.FAIL
    assert report.overall_status == CheckStatus.FAIL


def test_gate_docker_blocked_blocks_container_policy() -> None:
    """When Docker engine is inaccessible, GATE-DOCKER-CONTAINER reports BLOCKED."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(docker_status=CheckStatus.BLOCKED)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    policy = next(p for p in report.gate_policies if p.policy_id == "GATE-DOCKER-CONTAINER")
    assert policy.status == CheckStatus.BLOCKED
    assert report.overall_status == CheckStatus.BLOCKED


def test_gate_release_manifest_mutable_tag_fails_digest_policy() -> None:
    """When immutable digests are not verified, GATE-IMMUTABLE-DIGESTS reports FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(immutable_digests=False)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    policy = next(p for p in report.gate_policies if p.policy_id == "GATE-IMMUTABLE-DIGESTS")
    assert policy.status == CheckStatus.FAIL
    assert report.overall_status == CheckStatus.FAIL


def test_gate_production_secret_leak_fails_secret_policy() -> None:
    """When smoke test credentials collide with production secrets, fails with FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(secret_leak=True)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    policy = next(p for p in report.gate_policies if p.policy_id == "GATE-SECRET-ISOLATION")
    assert policy.status == CheckStatus.FAIL
    assert "CRITICAL" in policy.message
    assert report.overall_status == CheckStatus.FAIL


def test_gate_unauthorized_qualification_flag_fails_v26_governance() -> None:
    """Attempting to set live_qualification_authorized=True in V26 fails governance gate."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(live_qual_auth=True)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    gov_policy = next(p for p in report.gate_policies if p.policy_id == "GATE-V26-GOVERNANCE")
    assert gov_policy.status == CheckStatus.FAIL
    assert "CRITICAL GOVERNANCE VIOLATION" in gov_policy.message
    assert report.overall_status == CheckStatus.FAIL
    # Output must strictly remain False regardless of violation attempt
    assert report.live_qualification_authorized is False


def test_gate_missing_runbooks_fails_rollback_policy() -> None:
    """When recovery runbooks are missing, GATE-ROLLBACK-LIFECYCLE reports FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence(runbooks_verified=False)

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    policy = next(p for p in report.gate_policies if p.policy_id == "GATE-ROLLBACK-LIFECYCLE")
    assert policy.status == CheckStatus.FAIL
    assert report.overall_status == CheckStatus.FAIL


def test_gate_strict_mode_escalates_warnings() -> None:
    """In strict mode, advisory warnings cause the overall gate to FAIL."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT, strict=True)
    preflight = make_mock_preflight(overall_status=CheckStatus.WARNING)
    evidence = make_mock_evidence()

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

    assert report.overall_status == CheckStatus.FAIL
    assert report.strict_mode is True
    assert report.is_ready is False


def test_gate_report_serialization() -> None:
    """Gate report serializes to valid JSON adhering to schema."""
    evaluator = StagingReadinessGateEvaluator(repo_root=REPO_ROOT)
    preflight = make_mock_preflight()
    evidence = make_mock_evidence()

    report = evaluator.evaluate_gates(preflight=preflight, evidence=evidence)
    json_str = report.to_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["environment"] == "staging"
    assert parsed["live_qualification_authorized"] is False
    assert parsed["production_deployment_authorized"] is False
    assert len(parsed["gate_policies"]) == 7
    assert isinstance(report, StagingGateEvaluationReport)
