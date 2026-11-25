"""RegimeX — Production Deployment Orchestrator & Provider Adapters.

app.core.deployment
===================
Provides provider-independent deployment orchestration, migration management,
post-deployment health verification, and rollback recovery for RegimeX V25.

Invariants:
- Zero hardcoded credentials or plaintext secret logging.
- Exact-SHA verification: only deploy commits with verified CI success.
- Dedicated migration boundary: runs once as a pre-deployment step; never in API workers.
- Forward-only database lifecycle: automatic downgrades during rollback are prohibited.
- Fail-closed: missing or unconfigured providers halt deployment with NOT_CONFIGURED status.
- Post-deployment verification with bounded retries and timeouts.
- Machine-readable deployment metadata output (deployment-summary.json).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("regimex.deployment")


# =============================================================================
# Domain Models & Status Enums
# =============================================================================


class DeploymentStatus(StrEnum):
    """Execution status for deployment phases and overall outcome."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"
    MANUAL_RECOVERY_REQUIRED = "MANUAL_RECOVERY_REQUIRED"


@dataclass
class DeploymentConfig:
    """Runtime configuration for deployment execution."""

    commit_sha: str
    run_id: str
    environment: str = "production"
    provider: str = "NOT_CONFIGURED"
    release_tag: str = ""
    api_url: str = "http://localhost:8000"
    web_url: str = "http://localhost:3000"
    database_url: str | None = None
    render_deploy_hook_api: str | None = None
    render_deploy_hook_web: str | None = None
    dry_run: bool = False
    timeout_seconds: int = 15
    max_retries: int = 5
    retry_delay_seconds: float = 2.0


@dataclass
class DeploymentSummary:
    """Auditable machine-readable summary of a deployment run."""

    commit_sha: str
    run_id: str
    environment: str
    provider: str
    started_at: str
    completed_at: str
    overall_status: DeploymentStatus
    migration_status: DeploymentStatus
    backend_deployment_status: DeploymentStatus
    frontend_deployment_status: DeploymentStatus
    verification_status: DeploymentStatus
    rollback_status: DeploymentStatus
    provider_status: DeploymentStatus = DeploymentStatus.NOT_CONFIGURED
    release_tag: str = ""
    error_message: str | None = None
    recovery_steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to JSON-serializable dictionary."""
        data = asdict(self)
        for key in [
            "overall_status",
            "provider_status",
            "migration_status",
            "backend_deployment_status",
            "frontend_deployment_status",
            "verification_status",
            "rollback_status",
        ]:
            val = data.get(key)
            if isinstance(val, DeploymentStatus):
                data[key] = val.value
            elif val is not None and hasattr(val, "value"):
                data[key] = val.value
        if not data.get("release_tag"):
            data["release_tag"] = f"regimex-{self.commit_sha[:8]}" if self.commit_sha else "unknown"
        data["deployment_timestamp"] = self.completed_at
        return data

    def to_json(self, indent: int = 2) -> str:
        """Render summary as formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# =============================================================================
# Helper Utilities (Sanitization & Validation)
# =============================================================================


def redact_secrets(text: str) -> str:
    """Mask credentials, tokens, and authorization parameters from logs."""
    if not text:
        return ""
    sanitized = re.sub(r"(://[^:]+:)([^@]+)@", r"\1***@", text)
    sanitized = re.sub(r"([?&](?:token|key|secret|password|auth)=)[^&]+", r"\1***", sanitized)
    sanitized = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1***", sanitized)
    return sanitized


def validate_commit_sha(sha: str) -> bool:
    """Ensure SHA is a full 40-character hexadecimal Git commit hash."""
    if not isinstance(sha, str):
        return False
    return bool(re.fullmatch(r"^[0-9a-fA-F]{40}$", sha.strip()))


# =============================================================================
# Provider Adapter Interface & Implementations
# =============================================================================


class BaseProviderAdapter:
    """Abstract interface for hosting provider deployment adapters."""

    name: str = "BASE"

    def validate_configuration(self, config: DeploymentConfig) -> tuple[bool, str]:
        """Validate whether provider credentials and endpoints are configured."""
        raise NotImplementedError

    def deploy_backend(self, config: DeploymentConfig) -> tuple[bool, str]:
        """Trigger backend service deployment."""
        raise NotImplementedError

    def deploy_frontend(self, config: DeploymentConfig) -> tuple[bool, str]:
        """Trigger frontend service deployment."""
        raise NotImplementedError

    def rollback(self, config: DeploymentConfig, reason: str) -> tuple[bool, str]:
        """Perform rollback to previous known-good deployment if supported."""
        raise NotImplementedError


class UnconfiguredProviderAdapter(BaseProviderAdapter):
    """Adapter used when no external provider credentials or hooks are configured.

    Enforces fail-closed behavior: never reports false-positive deployment success.
    """

    name: str = "NOT_CONFIGURED"

    def validate_configuration(self, config: DeploymentConfig) -> tuple[bool, str]:
        return (
            False,
            "Deployment provider is NOT_CONFIGURED. No provider credentials (such as "
            "RENDER_DEPLOY_HOOK_API, RENDER_DEPLOY_HOOK_WEB, or registry secrets) were "
            "supplied in GitHub Environment secrets.",
        )

    def deploy_backend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return (
            False,
            "Backend deployment aborted: provider is NOT_CONFIGURED.",
        )

    def deploy_frontend(self, config: DeploymentConfig) -> tuple[bool, str]:
        return (
            False,
            "Frontend deployment aborted: provider is NOT_CONFIGURED.",
        )

    def rollback(self, config: DeploymentConfig, reason: str) -> tuple[bool, str]:
        return (
            False,
            f"Rollback unavailable for unconfigured provider (reason: {reason}). "
            "Manual intervention required.",
        )


class RenderWebhookAdapter(BaseProviderAdapter):
    """Adapter for Render managed PaaS using deployment webhooks."""

    name: str = "RENDER"

    def validate_configuration(self, config: DeploymentConfig) -> tuple[bool, str]:
        if not config.render_deploy_hook_api:
            return False, "Missing required secret: RENDER_DEPLOY_HOOK_API"
        if not config.render_deploy_hook_web:
            return False, "Missing required secret: RENDER_DEPLOY_HOOK_WEB"

        for url in (config.render_deploy_hook_api, config.render_deploy_hook_web):
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, f"Malformed deploy hook URL: {redact_secrets(url)}"
        return True, "Render deploy webhooks verified."

    def _trigger_webhook(
        self, url: str, service_name: str, config: DeploymentConfig
    ) -> tuple[bool, str]:
        if config.dry_run:
            logger.info(
                "Dry-run: simulated POST webhook for %s -> %s", service_name, redact_secrets(url)
            )
            return True, f"Simulated {service_name} deploy webhook success"

        try:
            req = urllib.request.Request(  # noqa: S310
                url,
                data=b"",
                method="POST",
                headers={
                    "User-Agent": "RegimeX-Deploy/1.0",
                    "X-RegimeX-Commit": config.commit_sha,
                },
            )
            with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:  # noqa: S310
                status_code = resp.getcode()
                if 200 <= status_code < 300:
                    return True, f"{service_name} deploy webhook triggered (HTTP {status_code})"
                return False, f"{service_name} deploy webhook failed with HTTP {status_code}"
        except urllib.error.HTTPError as e:
            return False, f"{service_name} deploy webhook HTTP error: {e.code}"
        except Exception as e:
            return False, f"{service_name} deploy webhook network error: {redact_secrets(str(e))}"

    def deploy_backend(self, config: DeploymentConfig) -> tuple[bool, str]:
        assert config.render_deploy_hook_api is not None
        return self._trigger_webhook(config.render_deploy_hook_api, "Backend (API)", config)

    def deploy_frontend(self, config: DeploymentConfig) -> tuple[bool, str]:
        assert config.render_deploy_hook_web is not None
        return self._trigger_webhook(config.render_deploy_hook_web, "Frontend (Web)", config)

    def rollback(self, config: DeploymentConfig, reason: str) -> tuple[bool, str]:
        return (
            False,
            f"Render deploy hooks do not support automatic commit revert (reason: {reason}). "
            "Trigger manual deploy of previous known-good commit in Render Dashboard.",
        )


# =============================================================================
# Database Migration Boundary Manager
# =============================================================================


class DatabaseMigrationManager:
    """Manages Alembic database migration execution and contract validation."""

    def __init__(self, repo_root: Path | None = None) -> None:
        if repo_root is not None:
            self.repo_root = repo_root
        else:
            # Walk up to find directory containing apps/api/alembic.ini
            current = Path(__file__).resolve()
            found_root = current.parent.parent.parent.parent
            for parent in current.parents:
                if (parent / "apps" / "api" / "alembic.ini").is_file():
                    found_root = parent
                    break
                if (parent / "alembic.ini").is_file():
                    found_root = parent
                    break
            self.repo_root = found_root

        if (self.repo_root / "apps" / "api" / "alembic.ini").is_file():
            self.api_dir = self.repo_root / "apps" / "api"
        elif (self.repo_root / "alembic.ini").is_file():
            self.api_dir = self.repo_root
        else:
            self.api_dir = self.repo_root / "apps" / "api"

        self.alembic_ini = self.api_dir / "alembic.ini"
        self.versions_dir = self.api_dir / "alembic" / "versions"

    def validate_migration_files(self) -> tuple[bool, str]:
        """Verify that alembic.ini and versions directory exist and are accessible."""
        if not self.alembic_ini.is_file():
            return False, f"Missing alembic configuration at {self.alembic_ini}"
        if not self.versions_dir.is_dir():
            return False, f"Missing alembic versions directory at {self.versions_dir}"
        return True, "Alembic configuration and migration versions verified."

    def execute_migration(self, config: DeploymentConfig) -> tuple[bool, str]:
        """Execute alembic upgrade head as a dedicated pre-deployment task.

        Invariants:
        - Never executed inside individual API uvicorn runtime workers.
        - Forward-only: automatic downgrades during rollback are prohibited.
        """
        valid, msg = self.validate_migration_files()
        if not valid:
            return False, msg

        if config.dry_run:
            logger.info("Dry-run: simulated database migration 'alembic upgrade head'")
            return True, "Simulated database migration succeeded (dry-run)"

        if not config.database_url:
            return (
                False,
                "Cannot execute migration: DATABASE_URL / REGIMEX_DATABASE_URL is not set.",
            )

        logger.info("Executing migration: alembic upgrade head")
        try:
            import subprocess

            env = os.environ.copy()
            env["DATABASE_URL"] = config.database_url
            env["REGIMEX_DATABASE_URL"] = config.database_url

            proc = subprocess.run(
                ["alembic", "upgrade", "head"],  # noqa: S607
                cwd=str(self.api_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds * 2,
            )
            if proc.returncode == 0:
                logger.info("Alembic upgrade head completed successfully.")
                return True, "Database migration applied successfully (alembic upgrade head)."
            err_output = redact_secrets(proc.stderr or proc.stdout)
            return False, f"Alembic migration failed with code {proc.returncode}: {err_output}"
        except Exception as e:
            return False, f"Failed to execute alembic migration: {redact_secrets(str(e))}"


# =============================================================================
# Post-Deployment Health Verifier
# =============================================================================


class PostDeploymentVerifier:
    """Verifies live health and operational readiness of deployed services."""

    def __init__(self, config: DeploymentConfig) -> None:
        self.config = config

    def _http_get(self, url: str) -> tuple[int, str]:
        """Perform HTTP GET request with timeouts."""
        req = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": "RegimeX-HealthProbe/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:  # noqa: S310
                body = resp.read().decode("utf-8", errors="replace")
                return resp.getcode(), body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return e.code, body
        except Exception as e:
            return 0, redact_secrets(str(e))

    def verify_backend(self) -> tuple[bool, str]:
        """Verify API liveness and readiness endpoints with bounded retries."""
        if self.config.dry_run:
            logger.info("Dry-run: simulated backend health probe to %s", self.config.api_url)
            return True, "Backend health verification simulated: PASSED"

        base_url = self.config.api_url.rstrip("/")
        live_url = f"{base_url}/api/v1/health/live"
        ready_url = f"{base_url}/api/v1/health/ready"

        logger.info(
            "Verifying backend health at %s (max %d retries)", live_url, self.config.max_retries
        )

        for attempt in range(1, self.config.max_retries + 1):
            code_live, _ = self._http_get(live_url)
            if code_live == 200:
                code_ready, body_ready = self._http_get(ready_url)
                if code_ready == 200:
                    logger.info("Backend liveness and readiness verified on attempt %d.", attempt)
                    return True, f"Backend live and ready (attempt {attempt})"
                logger.warning(
                    "Backend live (200) but readiness returned %d (attempt %d/%d): %s",
                    code_ready,
                    attempt,
                    self.config.max_retries,
                    body_ready[:100],
                )
            else:
                logger.warning(
                    "Backend liveness returned %d (attempt %d/%d)",
                    code_live,
                    attempt,
                    self.config.max_retries,
                )

            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_delay_seconds)

        return (
            False,
            f"Backend health verification timed out after {self.config.max_retries} attempts.",
        )

    def verify_frontend(self) -> tuple[bool, str]:
        """Verify frontend homepage or health page with bounded retries."""
        if self.config.dry_run:
            logger.info("Dry-run: simulated frontend health probe to %s", self.config.web_url)
            return True, "Frontend health verification simulated: PASSED"

        web_url = self.config.web_url.rstrip("/") + "/"
        logger.info("Verifying frontend at %s (max %d retries)", web_url, self.config.max_retries)

        for attempt in range(1, self.config.max_retries + 1):
            code, _ = self._http_get(web_url)
            if 200 <= code < 500:
                logger.info("Frontend responded with HTTP %d on attempt %d.", code, attempt)
                return True, f"Frontend reachable with HTTP {code} (attempt {attempt})"

            logger.warning(
                "Frontend returned HTTP %d on attempt %d/%d",
                code,
                attempt,
                self.config.max_retries,
            )
            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_delay_seconds)

        return (
            False,
            f"Frontend health verification timed out after {self.config.max_retries} attempts.",
        )


# =============================================================================
# Deployment Orchestrator
# =============================================================================


class DeploymentOrchestrator:
    """Coordinates migration, deployment dispatch, verification, and recovery."""

    def __init__(
        self,
        config: DeploymentConfig,
        adapter: BaseProviderAdapter | None = None,
        migration_manager: DatabaseMigrationManager | None = None,
    ) -> None:
        self.config = config
        self.migration_manager = migration_manager or DatabaseMigrationManager()
        self.adapter = adapter or self._resolve_adapter()
        self.verifier = PostDeploymentVerifier(config)

    def _resolve_adapter(self) -> BaseProviderAdapter:
        """Resolve adapter from configuration."""
        if self.config.render_deploy_hook_api and self.config.render_deploy_hook_web:
            return RenderWebhookAdapter()
        return UnconfiguredProviderAdapter()

    def run_full_deployment(self) -> DeploymentSummary:
        """Execute full automated deployment pipeline with failure isolation."""
        started_at = datetime.now(tz=UTC).isoformat()
        rel_tag = self.config.release_tag or (
            f"regimex-{self.config.commit_sha[:8]}" if self.config.commit_sha else "unknown"
        )
        logger.info("==================================================")
        logger.info("  RegimeX Production Deployment Orchestration")
        logger.info("==================================================")
        logger.info("  Commit SHA:    %s", self.config.commit_sha)
        logger.info("  Release Tag:   %s", rel_tag)
        logger.info("  Run ID:        %s", self.config.run_id)
        logger.info("  Environment:   %s", self.config.environment)
        logger.info("  Provider:      %s", self.adapter.name)
        logger.info("  Dry-run:       %s", self.config.dry_run)
        logger.info("==================================================")

        # 1. Exact-SHA Validation
        if not validate_commit_sha(self.config.commit_sha):
            msg = (
                f"Invalid commit SHA: '{self.config.commit_sha}'. "
                "Expected 40-character hexadecimal hash."
            )
            logger.error(msg)
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=DeploymentStatus.NOT_CONFIGURED,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.FAILED,
                migration_status=DeploymentStatus.NOT_RUN,
                backend_deployment_status=DeploymentStatus.NOT_RUN,
                frontend_deployment_status=DeploymentStatus.NOT_RUN,
                verification_status=DeploymentStatus.BLOCKED,
                rollback_status=DeploymentStatus.NOT_RUN,
                error_message=msg,
                recovery_steps=["Provide a valid 40-character Git commit hash to deploy."],
            )

        # 2. Provider Configuration Validation
        valid_provider, provider_msg = self.adapter.validate_configuration(self.config)
        if not valid_provider:
            logger.warning("Provider validation failed: %s", provider_msg)
            is_unconfigured = isinstance(self.adapter, UnconfiguredProviderAdapter)
            prov_status = (
                DeploymentStatus.NOT_CONFIGURED if is_unconfigured else DeploymentStatus.FAILED
            )
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=prov_status,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.NOT_CONFIGURED,
                migration_status=DeploymentStatus.NOT_RUN,
                backend_deployment_status=DeploymentStatus.NOT_RUN,
                frontend_deployment_status=DeploymentStatus.NOT_RUN,
                verification_status=DeploymentStatus.BLOCKED,
                rollback_status=DeploymentStatus.NOT_RUN,
                error_message=provider_msg,
                recovery_steps=[
                    "Configure production deployment secrets in GitHub Repository Settings -> "
                    "Environments -> production.",
                    "For Render managed hosting: configure RENDER_DEPLOY_HOOK_API and "
                    "RENDER_DEPLOY_HOOK_WEB.",
                    "For containerized self-hosting: deploy verified image tags "
                    "(regimex-api:<SHA>, regimex-web:<SHA>) via Docker Compose.",
                ],
            )

        # 3. Database Migration Execution (Dedicated Pre-Deployment Boundary)
        mig_ok, mig_msg = self.migration_manager.execute_migration(self.config)
        if not mig_ok:
            logger.error("Migration failed: %s", mig_msg)
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=DeploymentStatus.SUCCESS,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.FAILED,
                migration_status=DeploymentStatus.FAILED,
                backend_deployment_status=DeploymentStatus.NOT_RUN,
                frontend_deployment_status=DeploymentStatus.NOT_RUN,
                verification_status=DeploymentStatus.BLOCKED,
                rollback_status=DeploymentStatus.MANUAL_RECOVERY_REQUIRED,
                error_message=f"Database migration failure: {mig_msg}",
                recovery_steps=[
                    "Inspect database connection and credentials in GitHub Environment secrets.",
                    "Run 'alembic current' to inspect migration head.",
                    "NEVER perform automatic schema downgrades without DBA review.",
                    "Deploy forward hotfix migration if schema mismatch occurred.",
                ],
            )

        # 4. Backend Deployment Stage
        be_ok, be_msg = self.adapter.deploy_backend(self.config)
        if not be_ok:
            logger.error("Backend deployment failed: %s", be_msg)
            rb_ok, rb_msg = self.adapter.rollback(self.config, reason=be_msg)
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=DeploymentStatus.SUCCESS,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.FAILED,
                migration_status=DeploymentStatus.SUCCESS,
                backend_deployment_status=DeploymentStatus.FAILED,
                frontend_deployment_status=DeploymentStatus.NOT_RUN,
                verification_status=DeploymentStatus.BLOCKED,
                rollback_status=DeploymentStatus.SUCCESS if rb_ok else DeploymentStatus.FAILED,
                error_message=f"Backend deployment failure: {be_msg}. Rollback: {rb_msg}",
                recovery_steps=[
                    "Check provider console and container logs for startup failures.",
                    "Verify memory allocation and PORT binding.",
                    "Trigger manual rollback to previous known-good deployment if automated "
                    "rollback failed.",
                ],
            )

        # 5. Frontend Deployment Stage
        fe_ok, fe_msg = self.adapter.deploy_frontend(self.config)
        if not fe_ok:
            logger.error("Frontend deployment failed: %s", fe_msg)
            rb_ok, rb_msg = self.adapter.rollback(self.config, reason=fe_msg)
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=DeploymentStatus.SUCCESS,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.FAILED,
                migration_status=DeploymentStatus.SUCCESS,
                backend_deployment_status=DeploymentStatus.SUCCESS,
                frontend_deployment_status=DeploymentStatus.FAILED,
                verification_status=DeploymentStatus.BLOCKED,
                rollback_status=DeploymentStatus.SUCCESS if rb_ok else DeploymentStatus.FAILED,
                error_message=f"Frontend deployment failure: {fe_msg}. Rollback: {rb_msg}",
                recovery_steps=[
                    "Check frontend build logs and NEXT_PUBLIC_API_URL configuration.",
                    "Verify reverse proxy and web container routing.",
                ],
            )

        # 6. Post-Deployment Verification
        be_health_ok, be_health_msg = self.verifier.verify_backend()
        fe_health_ok, fe_health_msg = self.verifier.verify_frontend()

        if not (be_health_ok and fe_health_ok):
            fail_reason = (
                f"Verification failed. Backend: {be_health_msg} | Frontend: {fe_health_msg}"
            )
            logger.error(fail_reason)
            rb_ok, rb_msg = self.adapter.rollback(self.config, reason=fail_reason)
            return DeploymentSummary(
                commit_sha=self.config.commit_sha,
                run_id=self.config.run_id,
                environment=self.config.environment,
                provider=self.adapter.name,
                provider_status=DeploymentStatus.SUCCESS,
                release_tag=rel_tag,
                started_at=started_at,
                completed_at=datetime.now(tz=UTC).isoformat(),
                overall_status=DeploymentStatus.FAILED,
                migration_status=DeploymentStatus.SUCCESS,
                backend_deployment_status=DeploymentStatus.SUCCESS,
                frontend_deployment_status=DeploymentStatus.SUCCESS,
                verification_status=DeploymentStatus.FAILED,
                rollback_status=DeploymentStatus.SUCCESS if rb_ok else DeploymentStatus.FAILED,
                error_message=f"{fail_reason}. Rollback: {rb_msg}",
                recovery_steps=[
                    "Check /api/v1/health/ready for component check failures.",
                    "Verify database reachability and redis connectivity.",
                    "Review application logs for unhandled startup exceptions.",
                ],
            )

        # 7. Deployment Succeeded
        logger.info("Deployment, migrations, and health verification completed successfully!")
        return DeploymentSummary(
            commit_sha=self.config.commit_sha,
            run_id=self.config.run_id,
            environment=self.config.environment,
            provider=self.adapter.name,
            provider_status=DeploymentStatus.SUCCESS,
            release_tag=rel_tag,
            started_at=started_at,
            completed_at=datetime.now(tz=UTC).isoformat(),
            overall_status=DeploymentStatus.SUCCESS,
            migration_status=DeploymentStatus.SUCCESS,
            backend_deployment_status=DeploymentStatus.SUCCESS,
            frontend_deployment_status=DeploymentStatus.SUCCESS,
            verification_status=DeploymentStatus.SUCCESS,
            rollback_status=DeploymentStatus.NOT_RUN,
            metadata={
                "api_image": f"regimex-api:{self.config.commit_sha}",
                "web_image": f"regimex-web:{self.config.commit_sha}",
            },
        )


# =============================================================================
# CLI Interface
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="RegimeX automated production deployment and verification orchestration."
    )
    parser.add_argument(
        "--commit-sha",
        default=os.environ.get("DEPLOY_SHA") or os.environ.get("GITHUB_SHA") or "",
        help="Git commit SHA to deploy (must be 40-character hex)",
    )
    parser.add_argument(
        "--run-id",
        default=os.environ.get("DEPLOY_RUN_ID") or os.environ.get("GITHUB_RUN_ID") or "local-run",
        help="CI/CD run identifier",
    )
    parser.add_argument(
        "--environment",
        default=os.environ.get("DEPLOY_ENVIRONMENT") or "production",
        help="Target environment (default: production)",
    )
    parser.add_argument(
        "--release-tag",
        default=os.environ.get("DEPLOY_RELEASE_TAG") or "",
        help="Release identifier or image tag",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("DEPLOY_API_URL") or "http://localhost:8000",
        help="Backend base URL for post-deployment health verification",
    )
    parser.add_argument(
        "--web-url",
        default=os.environ.get("DEPLOY_WEB_URL") or "http://localhost:3000",
        help="Frontend base URL for post-deployment verification",
    )
    parser.add_argument(
        "--output-summary",
        default="deployment-summary.json",
        help="Path to save the JSON deployment summary report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DEPLOY_DRY_RUN", "").lower() in ("1", "true", "yes"),
        help="Run deployment pipeline in simulated dry-run mode without external mutations",
    )
    parser.add_argument(
        "--allow-unconfigured",
        action="store_true",
        default=os.environ.get("DEPLOY_ALLOW_UNCONFIGURED", "").lower() in ("1", "true", "yes"),
        help="Exit with code 0 when deployment provider is unconfigured",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config = DeploymentConfig(
        commit_sha=args.commit_sha,
        run_id=args.run_id,
        environment=args.environment,
        release_tag=args.release_tag,
        api_url=args.api_url,
        web_url=args.web_url,
        database_url=os.environ.get("REGIMEX_DATABASE_URL") or os.environ.get("DATABASE_URL"),
        render_deploy_hook_api=os.environ.get("RENDER_DEPLOY_HOOK_API"),
        render_deploy_hook_web=os.environ.get("RENDER_DEPLOY_HOOK_WEB"),
        dry_run=args.dry_run,
    )

    orchestrator = DeploymentOrchestrator(config)
    summary = orchestrator.run_full_deployment()

    summary_path = Path(args.output_summary)
    summary_path.write_text(summary.to_json(), encoding="utf-8")
    logger.info("Deployment summary written to %s", summary_path.resolve())

    print("\n" + "=" * 50)
    print("  Deployment Execution Summary")
    print("=" * 50)
    print(f"  Overall Status:   {summary.overall_status.value}")
    print(f"  Commit SHA:       {summary.commit_sha}")
    print(f"  Provider:         {summary.provider}")
    print(f"  Migration:        {summary.migration_status.value}")
    print(f"  Backend Deploy:   {summary.backend_deployment_status.value}")
    print(f"  Frontend Deploy:  {summary.frontend_deployment_status.value}")
    print(f"  Verification:     {summary.verification_status.value}")
    print(f"  Rollback:         {summary.rollback_status.value}")
    if summary.error_message:
        print(f"  Message:          {summary.error_message}")
    if summary.recovery_steps:
        print("  Recovery Steps:")
        for step in summary.recovery_steps:
            print(f"    - {step}")
    print("=" * 50 + "\n")

    if summary.overall_status == DeploymentStatus.SUCCESS:
        return 0
    if args.allow_unconfigured and summary.overall_status == DeploymentStatus.NOT_CONFIGURED:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
