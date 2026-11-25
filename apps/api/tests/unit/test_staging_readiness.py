"""Unit tests for RegimeX staging readiness preflight inspector.

Verifies:
- Host readiness: OS, Python version, Docker, Compose, disk, memory, permissions.
- Runtime readiness: backend/frontend configs, DB/Redis URLs, env vars, health routes.
- Security readiness: secret masking, non-root containers, git ignored secrets, CORS.
- Release readiness: commit SHA validation, branch check, manifest, immutable digests.
- Fail-closed behavior: explicit statuses (PASS, FAIL, BLOCKED, NOT_CONFIGURED, WARNING).
- Strict mode behavior and non-zero exit codes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.core.staging_readiness import StagingPreflightInspector
from app.schemas.staging_readiness import CheckCategory, CheckStatus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "d8885b27a6c51205cab70271c857c1609e68d7b0"
MOCK_ENV = {
    "REGIMEX_SECRET_KEY": "a-very-secure-random-staging-secret-key-that-is-over-32-chars-long",
    "REGIMEX_DATABASE_URL": (
        "postgresql+asyncpg://regimex_stage:StagePass123!@db.staging.internal:5432/regimex_staging"
    ),
    "REGIMEX_REDIS_URL": "redis://redis.staging.internal:6379/0",
    "REGIMEX_ALLOWED_ORIGINS": "https://staging.regimex.example.com",
    "NEXT_PUBLIC_API_URL": "https://api.staging.regimex.example.com",
}


def test_docker_cli_unavailable_reports_fail() -> None:
    """When Docker CLI is missing, docker_cli reports FAIL and docker_daemon is BLOCKED."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    with patch.object(inspector, "_check_docker_cli", return_value=(False, "not found")):
        checks = inspector.inspect_host()

    docker_cli_chk = next(c for c in checks if c.name == "docker_cli")
    assert docker_cli_chk.status == CheckStatus.FAIL

    daemon_chk = next(c for c in checks if c.name == "docker_daemon")
    assert daemon_chk.status == CheckStatus.BLOCKED


def test_docker_daemon_unavailable_reports_blocked() -> None:
    """When Docker CLI is present but daemon is unreachable, docker_daemon reports BLOCKED."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    with (
        patch.object(inspector, "_check_docker_cli", return_value=(True, "/usr/bin/docker")),
        patch.object(
            inspector,
            "_check_docker_daemon",
            return_value=(False, "Docker daemon probe failed: connection refused"),
        ),
    ):
        checks = inspector.inspect_host()

    daemon_chk = next(c for c in checks if c.name == "docker_daemon")
    assert daemon_chk.status == CheckStatus.BLOCKED
    assert (
        "unreachable" in daemon_chk.message.lower()
        or "connection refused" in daemon_chk.message.lower()
    )


def test_missing_required_environment_variables_reports_not_configured() -> None:
    """Missing core environment variables reports NOT_CONFIGURED."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    checks = inspector.inspect_runtime()

    env_chk = next(c for c in checks if c.name == "required_environment_variables")
    assert env_chk.status == CheckStatus.NOT_CONFIGURED
    assert "missing required" in env_chk.message.lower()


def test_invalid_commit_sha_reports_fail() -> None:
    """Malformed commit SHAs (short, non-hex, empty) report FAIL."""
    for invalid_sha in ("shortsha", "not-a-hex-string-xyz", "", "d8885b2"):
        inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=invalid_sha)
        checks = inspector.inspect_release()
        sha_chk = next(c for c in checks if c.name == "target_commit_sha")
        assert sha_chk.status == CheckStatus.FAIL


def test_release_metadata_integrity_detects_mismatch(tmp_path: Path) -> None:
    """Release manifest commit SHA mismatch reports FAIL."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "commit_sha": "0000000000000000000000000000000000000000",
                "images": {
                    "api": "ghcr.io/luccy93/regimex-api:0000000000000000000000000000000000000000",
                    "web": "ghcr.io/luccy93/regimex-web:0000000000000000000000000000000000000000",
                },
            }
        ),
        encoding="utf-8",
    )

    inspector = StagingPreflightInspector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        manifest_path=manifest_file,
    )
    checks = inspector.inspect_release()
    meta_chk = next(c for c in checks if c.name == "release_metadata_integrity")
    assert meta_chk.status == CheckStatus.FAIL
    assert "mismatch" in meta_chk.message.lower()


def test_missing_database_configuration_reports_not_configured() -> None:
    """Unset database URL reports NOT_CONFIGURED."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    checks = inspector.inspect_runtime()

    db_chk = next(c for c in checks if c.name == "database_configuration")
    assert db_chk.status == CheckStatus.NOT_CONFIGURED


def test_placeholder_database_credentials_report_fail() -> None:
    """Database URL containing placeholder 'changeme' credentials reports FAIL."""
    env = {"REGIMEX_DATABASE_URL": "postgresql+asyncpg://admin:changeme@localhost:5432/regimex"}
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env=env)
    checks = inspector.inspect_runtime()

    db_chk = next(c for c in checks if c.name == "database_configuration")
    assert db_chk.status == CheckStatus.FAIL
    assert "placeholder" in db_chk.message.lower()


def test_missing_redis_configuration_reports_not_configured() -> None:
    """Unset Redis URL reports NOT_CONFIGURED (optional)."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env={})
    checks = inspector.inspect_runtime()

    redis_chk = next(c for c in checks if c.name == "redis_configuration")
    assert redis_chk.status == CheckStatus.NOT_CONFIGURED
    assert redis_chk.mandatory is False


def test_malformed_redis_configuration_reports_fail() -> None:
    """Invalid scheme for Redis URL reports FAIL."""
    env = {"REGIMEX_REDIS_URL": "http://invalid-redis-host:6379"}
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env=env)
    checks = inspector.inspect_runtime()

    redis_chk = next(c for c in checks if c.name == "redis_configuration")
    assert redis_chk.status == CheckStatus.FAIL


def test_filesystem_permission_failure_reports_fail(tmp_path: Path) -> None:
    """Filesystem permission errors report FAIL with remediation."""
    inspector = StagingPreflightInspector(repo_root=tmp_path, commit_sha=VALID_SHA)
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
        checks = inspector.inspect_host()

    fs_chk = next(c for c in checks if c.name == "filesystem_permissions")
    assert fs_chk.status == CheckStatus.FAIL
    assert "permission" in fs_chk.message.lower()


def test_secret_redaction_in_preflight_report() -> None:
    """Report JSON and text representation strictly mask passwords and keys."""
    env = dict(MOCK_ENV)
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA, env=env)
    report = inspector.run_preflight()

    report_json = report.to_json()
    assert "StagePass123!" not in report_json
    assert "a-very-secure-random" not in report_json

    text_report = inspector.to_text_report(report, verbose=True)
    assert "StagePass123!" not in text_report
    assert "a-very-secure-random" not in text_report


def test_strict_mode_converts_warnings_to_failure(tmp_path: Path) -> None:
    """Under strict mode, an inspector encountering a WARNING evaluates to FAIL overall."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "commit_sha": VALID_SHA,
                "images": {
                    "api": f"ghcr.io/luccy93/regimex-api:{VALID_SHA}",
                    "web": f"ghcr.io/luccy93/regimex-web:{VALID_SHA}",
                },
            }
        ),
        encoding="utf-8",
    )

    inspector = StagingPreflightInspector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        branch="feature/experiment-branch",  # triggers WARNING on branch
        manifest_path=manifest_file,
        strict=True,
        env=MOCK_ENV,
    )
    with (
        patch.object(inspector, "_check_docker_cli", return_value=(True, "/bin/docker")),
        patch.object(inspector, "_check_docker_daemon", return_value=(True, "active")),
        patch.object(inspector, "_check_docker_compose", return_value=(True, "compose")),
        patch.object(inspector, "_get_disk_space_gb", return_value=10.0),
        patch.object(inspector, "_get_memory_gb", return_value=4.0),
    ):
        report = inspector.run_preflight()

    assert report.strict_mode is True
    assert report.overall_status == CheckStatus.FAIL
    assert report.is_ready is False


def test_successful_mocked_staging_preflight(tmp_path: Path) -> None:
    """When all host, runtime, security, and release checks pass, report status is PASS."""
    manifest_file = tmp_path / "release-manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "commit_sha": VALID_SHA,
                "images": {
                    "api": f"ghcr.io/luccy93/regimex-api:{VALID_SHA}",
                    "web": f"ghcr.io/luccy93/regimex-web:{VALID_SHA}",
                },
            }
        ),
        encoding="utf-8",
    )

    inspector = StagingPreflightInspector(
        repo_root=REPO_ROOT,
        commit_sha=VALID_SHA,
        branch="main",
        manifest_path=manifest_file,
        strict=False,
        env=MOCK_ENV,
    )

    with (
        patch.object(inspector, "_check_docker_cli", return_value=(True, "/usr/bin/docker")),
        patch.object(inspector, "_check_docker_daemon", return_value=(True, "Docker 24.0.7")),
        patch.object(
            inspector, "_check_docker_compose", return_value=(True, "Docker Compose v2.23.1")
        ),
        patch.object(inspector, "_get_disk_space_gb", return_value=25.0),
        patch.object(inspector, "_get_memory_gb", return_value=8.0),
    ):
        report = inspector.run_preflight()

    assert report.overall_status == CheckStatus.PASS
    assert report.is_ready is True
    assert report.host.status == CheckStatus.PASS
    assert report.runtime.status == CheckStatus.PASS
    assert report.security.status == CheckStatus.PASS
    assert report.release.status == CheckStatus.PASS
    assert len(report.failed_checks) == 0
    assert len(report.blocked_checks) == 0

    parsed = json.loads(report.to_json())
    assert parsed["is_ready"] is True
    assert parsed["overall_status"] == "PASS"
    assert parsed["commit_sha"] == VALID_SHA


def test_category_summary_metrics() -> None:
    """Category summaries compute correct counts and statuses."""
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, commit_sha=VALID_SHA)
    checks = inspector.inspect_host()
    summary = inspector._summarize_category(CheckCategory.HOST.value, checks)

    assert summary.total_checks == len(checks)
    assert (
        summary.passed_checks
        + summary.failed_checks
        + summary.blocked_checks
        + summary.warning_checks
        + summary.not_configured_checks
        + summary.not_run_checks
        == summary.total_checks
    )
