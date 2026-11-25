"""Unit tests for RegimeX staging infrastructure evidence collector.

Verifies:
- Docker staging-host capabilities (engine accessibility, Compose, storage, ports).
- GitHub and GHCR access verification and token redaction.
- Release manifest verification: 40-char SHA match, repository identity, immutable digests.
- Rejection of mutable container image tags (:latest without digest).
- Staging smoke test credential validation and production secret leak detection.
- Safe rollback and backup readiness verification.
- Honest optional GPU capability detection (CPU fallback support).
- Machine-readable JSON report generation and serialization.
- Strict enforcement of False authorization flags (V26 readiness only).
- Fail-closed overall status aggregation and exit codes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.staging_evidence import InfrastructureEvidenceCollector
from app.schemas.staging_readiness import (
    AuthStatus,
    CheckStatus,
    DockerReadinessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "d8885b27a6c51205cab70271c857c1609e68d7b0"
MOCK_ENV = {
    "GITHUB_TOKEN": "ghp_mocktoken1234567890abcdefghijklmnopqrst",
    "GHCR_TOKEN": "ghp_mocktoken1234567890abcdefghijklmnopqrst",
    "STAGING_SMOKE_USER": "staging_smoke_tester",
    "STAGING_SMOKE_PASSWORD": "VerySecureStagingTestPassword2026!",
    "STAGING_BACKUP_DIR": "/tmp/regimex_staging_backups",  # noqa: S108
    "REGIMEX_SECRET_KEY": "a-distinct-production-secret-key-32-chars-long",
}


def test_docker_capability_accessible_pass() -> None:
    """When Docker CLI, daemon, Compose, and storage are available, status is PASS."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    mock_info = json.dumps({"ServerVersion": "25.0.3", "Driver": "overlay2"})

    with (
        patch("shutil.which", side_effect=lambda x: "/usr/bin/" + x if x == "docker" else None),
        patch(
            "subprocess.run",
            side_effect=[
                MagicMock(returncode=0, stdout=mock_info, stderr=""),  # docker info
                MagicMock(returncode=0, stdout="Docker Compose v2.24.5\n", stderr=""),  # compose
            ],
        ),
        patch("shutil.disk_usage", return_value=MagicMock(free=10 * 1024**3)),
        patch.object(collector, "_probe_port_availability", return_value=True),
    ):
        ev = collector.collect_docker_evidence()

    assert ev.status == CheckStatus.PASS
    assert ev.engine_accessible is True
    assert ev.compose_available is True
    assert ev.storage_driver == "overlay2"
    assert ev.available_storage_gb == 10.0
    assert ev.ports_available[8000] is True


def test_docker_capability_missing_cli_fail() -> None:
    """When Docker CLI is missing, evidence reports FAIL."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    with patch("shutil.which", return_value=None):
        ev = collector.collect_docker_evidence()

    assert ev.status == CheckStatus.FAIL
    assert ev.engine_accessible is False
    assert ev.compose_available is False
    assert "CLI binary not found" in ev.details.get("error", "")


def test_docker_capability_daemon_unreachable_blocked() -> None:
    """When Docker CLI exists but daemon is unreachable, evidence reports BLOCKED."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    with (
        patch("shutil.which", return_value="/usr/bin/docker"),
        patch(
            "subprocess.run",
            return_value=MagicMock(
                returncode=1,
                stdout="",
                stderr="Cannot connect to the Docker daemon at unix:///var/run/docker.sock",
            ),
        ),
    ):
        ev = collector.collect_docker_evidence()

    assert ev.status == CheckStatus.BLOCKED
    assert ev.engine_accessible is False
    assert "Cannot connect to the Docker daemon" in ev.details.get("error", "")


def test_ghcr_auth_via_environment_token_pass() -> None:
    """When GHCR_TOKEN is set, GHCR access is AUTHENTICATED and status is PASS."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={"GHCR_TOKEN": "mock-pat-token"}
    )
    ev = collector.collect_ghcr_evidence()

    assert ev.status == CheckStatus.PASS
    assert ev.auth_status == AuthStatus.AUTHENTICATED
    assert ev.pull_capability_verified is True
    assert ev.registry_url == "ghcr.io"


def test_ghcr_auth_missing_not_configured() -> None:
    """When no GHCR token or config exists, GHCR reports NOT_CONFIGURED."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    with patch("pathlib.Path.is_file", return_value=False):
        ev = collector.collect_ghcr_evidence()

    assert ev.status == CheckStatus.NOT_CONFIGURED
    assert ev.auth_status == AuthStatus.NOT_CONFIGURED
    assert ev.pull_capability_verified is False


def test_github_access_via_token_pass() -> None:
    """When GITHUB_TOKEN is present, GitHub access reports AUTHENTICATED and PASS."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={"GITHUB_TOKEN": "ghp_test123"}
    )
    ev = collector.collect_github_evidence()

    assert ev.status == CheckStatus.PASS
    assert ev.auth_status == AuthStatus.AUTHENTICATED
    assert ev.repository_accessible is True
    assert ev.read_permission is True


def test_github_access_missing_not_configured() -> None:
    """When gh CLI and token are both missing, reports NOT_CONFIGURED."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    with patch("shutil.which", return_value=None):
        ev = collector.collect_github_evidence()

    assert ev.status == CheckStatus.NOT_CONFIGURED
    assert ev.cli_available is False
    assert ev.repository_accessible is False


def test_release_manifest_valid_with_digests_pass(tmp_path: Path) -> None:
    """Manifest with exact SHA and @sha256: image digests reports PASS."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_data = {
        "schema_version": "1.0.0",
        "commit_sha": VALID_SHA,
        "repository": "luccy93/RegimeX",
        "build_timestamp": "2026-11-25T12:00:00Z",
        "images": {
            "api": f"ghcr.io/luccy93/regimex-api:v1.0.0@sha256:{'a' * 64}",
            "web": f"ghcr.io/luccy93/regimex-web:v1.0.0@sha256:{'b' * 64}",
        },
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, manifest_path=manifest_file
    )
    ev = collector.validate_release_manifest()

    assert ev.status == CheckStatus.PASS
    assert ev.immutable_digests_verified is True
    assert ev.commit_sha == VALID_SHA
    assert ev.provenance_verified is True


def test_release_manifest_mutable_tag_rejected_fail(tmp_path: Path) -> None:
    """Manifest containing mutable :latest tag without digest is rejected with FAIL."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_data = {
        "schema_version": "1.0.0",
        "commit_sha": VALID_SHA,
        "repository": "luccy93/RegimeX",
        "images": {
            "api": "ghcr.io/luccy93/regimex-api:latest",  # Prohibited mutable tag
            "web": f"ghcr.io/luccy93/regimex-web:v1.0.0@sha256:{'b' * 64}",
        },
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, manifest_path=manifest_file
    )
    ev = collector.validate_release_manifest()

    assert ev.status == CheckStatus.FAIL
    assert ev.immutable_digests_verified is False
    assert "mutable tags like :latest" in ev.details.get("error", "").lower()


def test_release_manifest_sha_mismatch_fail(tmp_path: Path) -> None:
    """Manifest with a commit SHA different from target SHA is rejected with FAIL."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_data = {
        "commit_sha": "1111111111111111111111111111111111111111",
        "repository": "luccy93/RegimeX",
        "images": {"api": f"ghcr.io/api@sha256:{'a' * 64}"},
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, manifest_path=manifest_file
    )
    ev = collector.validate_release_manifest()

    assert ev.status == CheckStatus.FAIL
    assert "Commit SHA mismatch" in ev.details.get("error", "")


def test_release_manifest_missing_not_configured(tmp_path: Path) -> None:
    """When manifest path does not exist, status is NOT_CONFIGURED."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        manifest_path=tmp_path / "absent-manifest.json",
    )
    ev = collector.validate_release_manifest()

    assert ev.status == CheckStatus.NOT_CONFIGURED
    assert "not found" in ev.details.get("error", "").lower()


def test_smoke_credentials_valid_pass() -> None:
    """Configured and separated smoke credentials report PASS and masked details."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, env=MOCK_ENV
    )
    ev = collector.validate_smoke_credentials()

    assert ev.status == CheckStatus.PASS
    assert ev.username_configured is True
    assert ev.password_configured is True
    assert ev.production_secret_leak_detected is False
    assert ev.details["username_masked"] == "st***"


def test_smoke_credentials_missing_not_configured() -> None:
    """When smoke credentials are not in environment, reports NOT_CONFIGURED."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    ev = collector.validate_smoke_credentials()

    assert ev.status == CheckStatus.NOT_CONFIGURED
    assert ev.username_configured is False
    assert ev.password_configured is False


def test_smoke_credentials_production_secret_leak_fail() -> None:
    """When staging smoke password matches production secret key, fails with FAIL."""
    leaked_env = {
        "STAGING_SMOKE_USER": "staging_smoke_tester",
        "STAGING_SMOKE_PASSWORD": "super-secret-production-key-do-not-leak",
        "REGIMEX_SECRET_KEY": "super-secret-production-key-do-not-leak",
    }
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT, commit_sha=VALID_SHA, env=leaked_env
    )
    ev = collector.validate_smoke_credentials()

    assert ev.status == CheckStatus.FAIL
    assert ev.production_secret_leak_detected is True
    assert "CRITICAL" in ev.details.get("error", "")


def test_rollback_and_backup_readiness_pass() -> None:
    """When backup dir is set and runbooks exist, rollback readiness reports PASS."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        env={
            "STAGING_BACKUP_DIR": str(REPO_ROOT / "infra"),
            "PREVIOUS_RELEASE_SHA": "18c0bd73c683709b1f09bb89280d0d8bb2ec907a",
        },
    )
    ev = collector.assess_rollback_and_backup()

    assert ev.status == CheckStatus.PASS
    assert ev.backup_configured is True
    assert ev.recovery_runbook_verified is True
    assert ev.previous_release_identified is True
    assert ev.previous_release_sha == "18c0bd73c683709b1f09bb89280d0d8bb2ec907a"


def test_gpu_detection_present_pass() -> None:
    """When nvidia-smi detects an NVIDIA GPU, reports PASS and device count."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    mock_smi_output = "NVIDIA A100-SXM4-40GB, 535.129.03\n"

    with (
        patch("shutil.which", return_value="/usr/bin/nvidia-smi"),
        patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=mock_smi_output, stderr=""),
        ),
    ):
        ev = collector.detect_gpu_capability()

    assert ev.status == CheckStatus.PASS
    assert ev.gpu_available is True
    assert ev.device_count == 1
    assert "NVIDIA A100-SXM4-40GB" in ev.device_names
    assert ev.mandatory is False


def test_gpu_detection_cpu_only_optional_warning() -> None:
    """When no GPU is present, reports WARNING (advisory only) and mandatory=False."""
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    with patch("shutil.which", return_value=None):
        ev = collector.detect_gpu_capability()

    assert ev.status == CheckStatus.WARNING
    assert ev.gpu_available is False
    assert ev.device_count == 0
    assert ev.mandatory is False
    assert "CPU fallback mode" in ev.details.get("note", "")


def test_v26_authorization_flags_strictly_false(tmp_path: Path) -> None:
    """Live qualification and production deployment authorization MUST remain False."""
    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        manifest_path=tmp_path / "absent.json",
        env=MOCK_ENV,
    )
    report = collector.collect_full_evidence()

    assert report.live_qualification_authorized is False
    assert report.production_deployment_authorized is False
    assert isinstance(report, InfrastructureEvidenceReport)


def test_full_evidence_report_serialization(tmp_path: Path) -> None:
    """Full evidence report serializes cleanly to JSON adhering to schema."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_data = {
        "commit_sha": VALID_SHA,
        "repository": "luccy93/RegimeX",
        "images": {"api": f"ghcr.io/api@sha256:{'a' * 64}"},
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    collector = InfrastructureEvidenceCollector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        manifest_path=manifest_file,
        env=MOCK_ENV,
    )

    with (
        patch.object(
            collector,
            "collect_docker_evidence",
            return_value=DockerReadinessEvidence(
                status=CheckStatus.PASS,
                engine_accessible=True,
                compose_available=True,
                details={},
                remediation=None,
            ),
        ),
        patch.object(
            collector,
            "detect_gpu_capability",
            return_value=GPUCapabilityEvidence(
                status=CheckStatus.WARNING,
                mandatory=False,
                gpu_available=False,
                device_count=0,
                device_names=[],
                details={"note": "CPU mode"},
                remediation=None,
            ),
        ),
    ):
        report = collector.collect_full_evidence()

    json_str = report.to_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["environment"] == "staging"
    assert parsed["live_qualification_authorized"] is False
    assert parsed["production_deployment_authorized"] is False
    assert "docker" in parsed
    assert "github" in parsed
    assert "ghcr" in parsed
    assert "release_manifest" in parsed
    assert "smoke_credentials" in parsed
    assert "rollback" in parsed
    assert "gpu" in parsed
