"""Unit tests for the RegimeX deployment orchestrator and provider adapters.

Verifies:
- Deployment configuration validation and secret redaction.
- Exact-SHA enforcement and validation.
- Fail-closed behavior when deployment provider is NOT_CONFIGURED.
- Migration boundary execution and forward-only failure handling.
- Backend and frontend deployment sequence and failure isolation.
- Post-deployment health verification with bounded retries and timeouts.
- Rollback handling without automatic database downgrades.
- Machine-readable metadata generation without leaking credentials.
- Prohibition of false-positive deployment success.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.deployment import (
    BaseProviderAdapter,
    DatabaseMigrationManager,
    DeploymentConfig,
    DeploymentOrchestrator,
    DeploymentStatus,
    PostDeploymentVerifier,
    RenderWebhookAdapter,
    redact_secrets,
    validate_commit_sha,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "5a4c7f5f9c91954f6ad569c4cd3008339aca003e"


# =============================================================================
# Helper Fixtures & Mocks
# =============================================================================


class MockSuccessfulAdapter(BaseProviderAdapter):
    """Test adapter that simulates successful provider actions."""

    name = "MOCK_SUCCESS"

    def validate_configuration(self, config: DeploymentConfig) -> tuple[bool, str]:
        return True, "Mock configuration valid"

    def deploy_backend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return True, "Mock backend deployed"

    def deploy_frontend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return True, "Mock frontend deployed"

    def rollback(self, config: DeploymentConfig, reason: str) -> tuple[bool, str]:
        return True, f"Mock rollback succeeded for reason: {reason}"


class MockFailingBackendAdapter(BaseProviderAdapter):
    """Test adapter that fails during backend deployment."""

    name = "MOCK_FAIL_BACKEND"

    def validate_configuration(self, config: DeploymentConfig) -> tuple[bool, str]:
        return True, "Valid"

    def deploy_backend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return False, "Backend container crashed on startup"

    def deploy_frontend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return True, "Frontend ok"

    def rollback(self, config: DeploymentConfig, reason: str) -> tuple[bool, str]:
        return True, "Rollback to previous release complete"


# =============================================================================
# Secret Redaction Tests
# =============================================================================


def test_redact_secrets_masks_urls_and_tokens() -> None:
    """Verify secrets and sensitive query parameters are masked."""
    url = "postgresql+asyncpg://admin:SuperSecret123@db.prod.internal:5432/regimex_prod"
    redacted = redact_secrets(url)
    assert "SuperSecret123" not in redacted
    assert "admin:***@" in redacted

    webhook = "https://api.render.com/deploy/srv-12345?key=SecretKey999&other=normal"
    redacted_hook = redact_secrets(webhook)
    assert "SecretKey999" not in redacted_hook
    assert "key=***" in redacted_hook

    bearer = "Authorization: Bearer my_jwt_token_123456"
    assert "my_jwt_token_123456" not in redact_secrets(bearer)
    assert "Bearer ***" in redact_secrets(bearer)


# =============================================================================
# Exact-SHA Enforcement Tests
# =============================================================================


def test_validate_commit_sha_validates_40_hex_chars() -> None:
    """Verify SHA validation requires full 40-character hex string."""
    assert validate_commit_sha(VALID_SHA) is True
    assert validate_commit_sha("5a4c7f5") is False  # Short SHA rejected
    assert validate_commit_sha("not-a-sha-at-all") is False
    assert validate_commit_sha("") is False
    assert validate_commit_sha(VALID_SHA + "extra") is False


def test_orchestrator_rejects_invalid_commit_sha() -> None:
    """Orchestrator immediately halts with FAILED status if SHA is malformed."""
    config = DeploymentConfig(commit_sha="invalid-sha", run_id="run-1", dry_run=True)
    orchestrator = DeploymentOrchestrator(config)
    summary = orchestrator.run_full_deployment()

    assert summary.overall_status == DeploymentStatus.FAILED
    assert summary.migration_status == DeploymentStatus.NOT_RUN
    assert summary.backend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.verification_status == DeploymentStatus.BLOCKED
    assert "Invalid commit SHA" in (summary.error_message or "")


# =============================================================================
# Missing Provider & Fail-Closed Tests
# =============================================================================


def test_missing_provider_fails_closed_with_not_configured() -> None:
    """When no provider secrets exist, deployment halts with NOT_CONFIGURED status.

    Guarantees no false-positive success.
    """
    config = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="run-1",
        render_deploy_hook_api=None,
        render_deploy_hook_web=None,
        dry_run=False,
    )
    orchestrator = DeploymentOrchestrator(config)
    assert orchestrator.adapter.name == "NOT_CONFIGURED"

    summary = orchestrator.run_full_deployment()
    assert summary.overall_status == DeploymentStatus.NOT_CONFIGURED
    assert summary.backend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.frontend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.migration_status == DeploymentStatus.NOT_RUN
    assert summary.verification_status == DeploymentStatus.BLOCKED
    assert "NOT_CONFIGURED" in (summary.error_message or "")
    assert len(summary.recovery_steps) > 0


# =============================================================================
# Migration Boundary Tests
# =============================================================================


def test_migration_manager_validates_files() -> None:
    """Verify migration manager checks for alembic.ini and versions directory."""
    manager = DatabaseMigrationManager(repo_root=REPO_ROOT)
    valid, msg = manager.validate_migration_files()
    assert valid is True
    assert "verified" in msg.lower()


def test_migration_failure_halts_deployment_without_downgrade() -> None:
    """If database migration fails, deployment halts and automatic downgrade is prevented."""
    config = DeploymentConfig(commit_sha=VALID_SHA, run_id="run-1", dry_run=False)

    mock_migrator = MagicMock(spec=DatabaseMigrationManager)
    mock_migrator.execute_migration.return_value = (
        False,
        "OperationalError: database connection refused",
    )

    orchestrator = DeploymentOrchestrator(
        config,
        adapter=MockSuccessfulAdapter(),
        migration_manager=mock_migrator,
    )
    summary = orchestrator.run_full_deployment()

    assert summary.overall_status == DeploymentStatus.FAILED
    assert summary.migration_status == DeploymentStatus.FAILED
    assert summary.backend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.frontend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.verification_status == DeploymentStatus.BLOCKED
    assert summary.rollback_status == DeploymentStatus.MANUAL_RECOVERY_REQUIRED
    assert any("downgrade" in step.lower() for step in summary.recovery_steps)


# =============================================================================
# Deployment Sequence & Rollback Tests
# =============================================================================


def test_backend_deployment_failure_triggers_rollback_and_halts_frontend() -> None:
    """Backend failure triggers rollback and blocks frontend deployment."""
    config = DeploymentConfig(commit_sha=VALID_SHA, run_id="run-1", dry_run=True)
    adapter = MockFailingBackendAdapter()
    orchestrator = DeploymentOrchestrator(config, adapter=adapter)

    # Mock migration to succeed
    with patch.object(
        orchestrator.migration_manager, "execute_migration", return_value=(True, "OK")
    ):
        summary = orchestrator.run_full_deployment()

    assert summary.overall_status == DeploymentStatus.FAILED
    assert summary.backend_deployment_status == DeploymentStatus.FAILED
    assert summary.frontend_deployment_status == DeploymentStatus.NOT_RUN
    assert summary.verification_status == DeploymentStatus.BLOCKED
    assert summary.rollback_status == DeploymentStatus.SUCCESS
    assert "Backend container crashed" in (summary.error_message or "")


# =============================================================================
# Post-Deployment Verification Tests
# =============================================================================


def test_post_deployment_verifier_retries_and_succeeds() -> None:
    """Verifier retries on transient errors and reports success when endpoints become ready."""
    config = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="run-1",
        api_url="http://test-api:8000",
        web_url="http://test-web:3000",
        max_retries=3,
        retry_delay_seconds=0.01,
        dry_run=False,
    )
    verifier = PostDeploymentVerifier(config)

    # Simulate: first live check returns 503, second returns 200; ready returns 200
    mock_responses = [
        (503, "Starting up"),
        (200, '{"status": "ok"}'),
        (200, '{"status": "ready"}'),
    ]

    with patch.object(verifier, "_http_get", side_effect=mock_responses):
        success, msg = verifier.verify_backend()

    assert success is True
    assert "attempt 2" in msg


def test_post_deployment_verifier_times_out_on_persistent_failure() -> None:
    """Verifier exhausts retries and reports failure if service never becomes ready."""
    config = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="run-1",
        max_retries=2,
        retry_delay_seconds=0.01,
        dry_run=False,
    )
    verifier = PostDeploymentVerifier(config)

    with patch.object(verifier, "_http_get", return_value=(500, "Internal Server Error")):
        success, msg = verifier.verify_backend()

    assert success is False
    assert "timed out" in msg


# =============================================================================
# Render Webhook Adapter Tests
# =============================================================================


def test_render_webhook_adapter_validation() -> None:
    """Render adapter validates presence and format of webhook URLs."""
    adapter = RenderWebhookAdapter()

    # Missing hooks
    cfg_empty = DeploymentConfig(commit_sha=VALID_SHA, run_id="1")
    valid, err = adapter.validate_configuration(cfg_empty)
    assert valid is False
    assert "RENDER_DEPLOY_HOOK_API" in err

    # Valid hooks
    cfg_valid = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="1",
        render_deploy_hook_api="https://api.render.com/deploy/srv-api?key=sec1",
        render_deploy_hook_web="https://api.render.com/deploy/srv-web?key=sec2",
    )
    valid, msg = adapter.validate_configuration(cfg_valid)
    assert valid is True
    assert "verified" in msg


def test_render_webhook_adapter_executes_in_dry_run() -> None:
    """Render adapter simulates webhooks cleanly in dry-run mode."""
    adapter = RenderWebhookAdapter()
    cfg = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="1",
        render_deploy_hook_api="https://api.render.com/deploy/srv-api?key=sec1",
        render_deploy_hook_web="https://api.render.com/deploy/srv-web?key=sec2",
        dry_run=True,
    )

    be_ok, be_msg = adapter.deploy_backend(cfg)
    fe_ok, fe_msg = adapter.deploy_frontend(cfg)

    assert be_ok is True
    assert "Simulated" in be_msg
    assert fe_ok is True
    assert "Simulated" in fe_msg


# =============================================================================
# Full Successful Deployment Orchestration (Dry-Run / Mocked)
# =============================================================================


def test_full_successful_deployment_orchestration() -> None:
    """Full orchestration runs migrations, deploys backend/frontend, and verifies health."""
    config = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="run-100",
        dry_run=True,
    )
    orchestrator = DeploymentOrchestrator(config, adapter=MockSuccessfulAdapter())
    summary = orchestrator.run_full_deployment()

    assert summary.overall_status == DeploymentStatus.SUCCESS
    assert summary.migration_status == DeploymentStatus.SUCCESS
    assert summary.backend_deployment_status == DeploymentStatus.SUCCESS
    assert summary.frontend_deployment_status == DeploymentStatus.SUCCESS
    assert summary.verification_status == DeploymentStatus.SUCCESS
    assert summary.rollback_status == DeploymentStatus.NOT_RUN
    assert summary.commit_sha == VALID_SHA
    assert summary.run_id == "run-100"

    # Verify JSON serialization and machine-readable schema
    summary_dict = json.loads(summary.to_json())
    assert summary_dict["overall_status"] == "SUCCESS"
    assert summary_dict["provider_status"] == "SUCCESS"
    assert summary_dict["release_tag"] == f"regimex-{VALID_SHA[:8]}"
    assert "deployment_timestamp" in summary_dict
    assert summary_dict["metadata"]["api_image"] == f"regimex-api:{VALID_SHA}"
    assert summary_dict["metadata"]["web_image"] == f"regimex-web:{VALID_SHA}"


def test_machine_readable_summary_unconfigured_contract() -> None:
    """Unconfigured deployment produces auditable summary with NOT_CONFIGURED status."""
    config = DeploymentConfig(
        commit_sha=VALID_SHA,
        run_id="run-200",
        release_tag="regimex-v25-test",
        dry_run=False,
    )
    orchestrator = DeploymentOrchestrator(config)
    summary = orchestrator.run_full_deployment()

    summary_dict = json.loads(summary.to_json())
    assert summary_dict["commit_sha"] == VALID_SHA
    assert summary_dict["release_tag"] == "regimex-v25-test"
    assert summary_dict["provider_status"] == "NOT_CONFIGURED"
    assert summary_dict["overall_status"] == "NOT_CONFIGURED"
    assert summary_dict["migration_status"] == "NOT_RUN"
    assert summary_dict["backend_deployment_status"] == "NOT_RUN"
    assert summary_dict["frontend_deployment_status"] == "NOT_RUN"
    assert summary_dict["verification_status"] == "BLOCKED"
    assert "deployment_timestamp" in summary_dict
    assert len(summary_dict["recovery_steps"]) > 0
