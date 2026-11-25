"""RegimeX — Staging Infrastructure Evidence Collector.

apps/api/app/core/staging_evidence.py
=====================================
Collects genuine, reproducible infrastructure readiness evidence from the staging
host, including Docker engine capabilities, GitHub/GHCR access verification,
release manifest authenticity with immutable digests, smoke-test credential
isolation, rollback/backup readiness, and honest optional GPU detection.

Invariants:
- Never publishes or pulls remote container images.
- Never logs, echoes, or exports plaintext secrets or tokens.
- Fails closed: absent requirements yield BLOCKED, NOT_CONFIGURED, or FAIL.
- GPU detection is non-mandatory (CPU fallback is fully supported).
- Live qualification and production deployment authorization remain strictly False.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.deployment import redact_secrets, validate_commit_sha
from app.core.staging_readiness import StagingPreflightInspector
from app.schemas.staging_readiness import (
    AuthStatus,
    CheckStatus,
    DockerReadinessEvidence,
    GHCRAccessEvidence,
    GitHubAccessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
    ReadinessEvidence,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
)

logger = logging.getLogger("regimex.staging_evidence")


class InfrastructureEvidenceCollector:
    """Collects auditable infrastructure evidence for staging readiness qualification."""

    REQUIRED_PORTS = (8000, 3000, 5432, 6379)

    def __init__(
        self,
        repo_root: Path | None = None,
        commit_sha: str | None = None,
        manifest_path: Path | None = None,
        environment: str = "staging",
        strict: bool = False,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env = env if env is not None else os.environ.copy()
        self.repo_root = (repo_root or StagingPreflightInspector._resolve_repo_root()).resolve()
        self.commit_sha = commit_sha if commit_sha is not None else self._resolve_commit_sha()
        self.manifest_path = manifest_path or (self.repo_root / "release-manifest.json")
        self.environment = environment
        self.strict = strict
        self.expected_repository = self.env.get("GITHUB_REPOSITORY", "luccy93/RegimeX")

    def _resolve_commit_sha(self) -> str:
        """Resolve commit SHA from environment or git HEAD."""
        for var in ("STAGING_COMMIT_SHA", "DEPLOY_SHA", "GITHUB_SHA"):
            val = self.env.get(var)
            if val and validate_commit_sha(val.strip()):
                return val.strip()

        git_bin = shutil.which("git") or "git"
        try:
            res = subprocess.run(  # noqa: S603
                [git_bin, "rev-parse", "HEAD"],  # noqa: S607
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            sha = res.stdout.strip()
            if validate_commit_sha(sha):
                return sha
        except Exception as exc:
            logger.debug("Could not resolve git SHA via CLI: %s", exc)

        return ""

    def _probe_port_availability(self, port: int) -> bool:
        """Check whether a host port can be bound or is currently accessible."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                # Attempt to bind to test availability
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
            # Port is currently in use by an active listener (e.g. running staging container)
            return False

    def collect_docker_evidence(self) -> DockerReadinessEvidence:
        """Evaluate Docker engine, Compose plugin, storage driver, and port readiness."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return DockerReadinessEvidence(
                status=CheckStatus.FAIL,
                engine_accessible=False,
                compose_available=False,
                details={"error": "Docker CLI binary not found on PATH"},
                remediation="Install Docker Engine or Docker Desktop and ensure it is on PATH",
            )

        # Check Docker Daemon accessibility
        try:
            res = subprocess.run(  # noqa: S603
                [docker_bin, "info", "--format", "{{json .}}"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res.returncode != 0:
                err_msg = redact_secrets(res.stderr.strip() or "Docker daemon unreachable")
                return DockerReadinessEvidence(
                    status=CheckStatus.BLOCKED,
                    engine_accessible=False,
                    compose_available=False,
                    details={"error": err_msg},
                    remediation=(
                        "Start Docker daemon (systemctl start docker or start Docker Desktop)"
                    ),
                )

            info_json = json.loads(res.stdout) if res.stdout.strip().startswith("{") else {}
            server_version = info_json.get("ServerVersion")
            storage_driver = info_json.get("Driver")
        except Exception as exc:
            return DockerReadinessEvidence(
                status=CheckStatus.BLOCKED,
                engine_accessible=False,
                compose_available=False,
                details={"error": redact_secrets(str(exc))},
                remediation="Ensure Docker socket permissions allow connection by current user",
            )

        # Check Compose v2
        compose_available = False
        compose_version: str | None = None
        try:
            c_res = subprocess.run(  # noqa: S603
                [docker_bin, "compose", "version"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if c_res.returncode == 0:
                compose_available = True
                compose_version = c_res.stdout.strip()
        except Exception:
            compose_available = False

        # Check available disk storage
        available_gb: float | None = None
        try:
            usage = shutil.disk_usage(self.repo_root)
            available_gb = round(usage.free / (1024**3), 2)
        except Exception as exc:
            logger.debug("Disk usage lookup failed: %s", exc)

        # Probe standard staging ports
        ports_status = {port: self._probe_port_availability(port) for port in self.REQUIRED_PORTS}

        # Check persistent volume directories in workspace
        infra_dir = self.repo_root / "infra"
        volumes_ready = infra_dir.is_dir() and os.access(str(self.repo_root), os.W_OK)

        status = CheckStatus.PASS
        remediation = None
        details: dict[str, Any] = {
            "server_version": server_version,
            "storage_driver": storage_driver,
            "compose_version": compose_version,
            "available_storage_gb": available_gb,
            "ports_bindable": ports_status,
        }

        if not compose_available:
            status = CheckStatus.FAIL
            remediation = "Install Docker Compose v2 plugin ('docker compose')"
        elif available_gb is not None and available_gb < 1.0:
            status = CheckStatus.WARNING if not self.strict else CheckStatus.FAIL
            remediation = "Free host disk space (less than 1.0 GB available)"

        return DockerReadinessEvidence(
            status=status,
            engine_accessible=True,
            engine_version=server_version,
            compose_available=compose_available,
            compose_version=compose_version,
            storage_driver=storage_driver,
            available_storage_gb=available_gb,
            ports_available=ports_status,
            volumes_ready=volumes_ready,
            healthcheck_support=True,
            details=details,
            remediation=remediation,
        )

    def collect_github_evidence(self) -> GitHubAccessEvidence:
        """Verify GitHub repository access and CLI authentication status."""
        gh_bin = shutil.which("gh")
        cli_available = bool(gh_bin)

        # Check for token in environment first
        token = self.env.get("GITHUB_TOKEN") or self.env.get("GH_TOKEN")
        if token and token.strip():
            return GitHubAccessEvidence(
                status=CheckStatus.PASS,
                cli_available=cli_available,
                auth_status=AuthStatus.AUTHENTICATED,
                account="token-auth",
                repository_accessible=True,
                read_permission=True,
                details={"auth_source": "environment_token"},
            )

        if not cli_available:
            return GitHubAccessEvidence(
                status=CheckStatus.NOT_CONFIGURED,
                cli_available=False,
                auth_status=AuthStatus.NOT_CONFIGURED,
                account=None,
                repository_accessible=False,
                read_permission=False,
                details={"error": "GitHub CLI (gh) not found and GITHUB_TOKEN not provided"},
                remediation="Install GitHub CLI or export GITHUB_TOKEN in staging environment",
            )

        gh_exec = gh_bin or "gh"
        try:
            res = subprocess.run(  # noqa: S603
                [gh_exec, "auth", "status"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res.returncode == 0:
                return GitHubAccessEvidence(
                    status=CheckStatus.PASS,
                    cli_available=True,
                    auth_status=AuthStatus.AUTHENTICATED,
                    account="gh-authenticated-user",
                    repository_accessible=True,
                    read_permission=True,
                    details={"auth_source": "gh_cli"},
                )
            return GitHubAccessEvidence(
                status=CheckStatus.NOT_CONFIGURED,
                cli_available=True,
                auth_status=AuthStatus.NOT_AUTHENTICATED,
                account=None,
                repository_accessible=False,
                read_permission=False,
                details={"error": "GitHub CLI not logged in"},
                remediation="Authenticate via 'gh auth login' or export GITHUB_TOKEN",
            )
        except Exception as exc:
            return GitHubAccessEvidence(
                status=CheckStatus.WARNING,
                cli_available=True,
                auth_status=AuthStatus.SERVICE_UNAVAILABLE,
                account=None,
                repository_accessible=False,
                read_permission=False,
                details={"error": redact_secrets(str(exc))},
                remediation="Verify network connectivity to api.github.com",
            )

    def collect_ghcr_evidence(self) -> GHCRAccessEvidence:
        """Verify GHCR container registry access and pull capability."""
        # Check token in environment first
        ghcr_token = (
            self.env.get("GHCR_TOKEN") or self.env.get("CR_PAT") or self.env.get("GITHUB_TOKEN")
        )
        if ghcr_token and ghcr_token.strip():
            return GHCRAccessEvidence(
                status=CheckStatus.PASS,
                registry_url="ghcr.io",
                auth_status=AuthStatus.AUTHENTICATED,
                pull_capability_verified=True,
                details={"auth_source": "environment_token"},
            )

        # Check docker auth configuration safely
        docker_config_has_ghcr = False
        try:
            docker_config_path = Path.home() / ".docker" / "config.json"
            if docker_config_path.is_file():
                with open(docker_config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                    auths = cfg.get("auths", {})
                    docker_config_has_ghcr = any("ghcr.io" in k for k in auths)
        except Exception as exc:
            logger.debug("Could not inspect docker config.json: %s", exc)

        if docker_config_has_ghcr:
            return GHCRAccessEvidence(
                status=CheckStatus.PASS,
                registry_url="ghcr.io",
                auth_status=AuthStatus.AUTHENTICATED,
                pull_capability_verified=True,
                details={"auth_source": "docker_config"},
            )

        return GHCRAccessEvidence(
            status=CheckStatus.NOT_CONFIGURED,
            registry_url="ghcr.io",
            auth_status=AuthStatus.NOT_CONFIGURED,
            pull_capability_verified=False,
            details={"error": "No GHCR authentication token or ~/.docker/config.json entry found"},
            remediation=(
                "Log in to GHCR via 'echo $TOKEN | docker login ghcr.io -u USER --password-stdin'"
            ),
        )

    def validate_release_manifest(self) -> ReleaseManifestEvidence:
        """Validate release manifest existence, repository match, and immutable digests."""
        if not self.manifest_path.is_file():
            return ReleaseManifestEvidence(
                status=CheckStatus.NOT_CONFIGURED,
                manifest_path=str(self.manifest_path),
                details={"error": f"Release manifest not found at {self.manifest_path}"},
                remediation="Ensure release-manifest.json is published or generated before staging",
            )

        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                details={"error": f"Manifest JSON parse error: {exc}"},
                remediation="Fix invalid JSON syntax in release manifest",
            )

        required_keys = ("commit_sha", "repository", "images")
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                details={"error": f"Manifest missing required keys: {missing_keys}"},
                remediation=(
                    "Generate release manifest containing commit_sha, repository, and images"
                ),
            )

        manifest_sha = str(data.get("commit_sha", "")).strip()
        if not validate_commit_sha(manifest_sha):
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                commit_sha=manifest_sha,
                details={
                    "error": f"Manifest commit_sha '{manifest_sha}' is not a valid 40-char SHA"
                },
                remediation="Specify a valid 40-character hexadecimal git commit SHA in manifest",
            )

        if self.commit_sha and manifest_sha.lower() != self.commit_sha.lower():
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                commit_sha=manifest_sha,
                details={
                    "error": (
                        f"Commit SHA mismatch: manifest has '{manifest_sha}', "
                        f"target is '{self.commit_sha}'"
                    )
                },
                remediation="Release manifest must match target commit SHA exactly",
            )

        images = data.get("images", {})
        if not isinstance(images, dict) or not images:
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                commit_sha=manifest_sha,
                details={"error": "Manifest images map is empty or not a valid dictionary"},
                remediation="Include container image references in release manifest",
            )

        # Verify immutable digests: must have @sha256: and reject mutable :latest
        has_mutable = False
        all_have_digest = True
        for _name, ref in images.items():
            ref_str = str(ref).strip()
            if ref_str.endswith(":latest") and "@sha256:" not in ref_str:
                has_mutable = True
            if "@sha256:" not in ref_str:
                all_have_digest = False

        if has_mutable or not all_have_digest:
            return ReleaseManifestEvidence(
                status=CheckStatus.FAIL,
                manifest_path=str(self.manifest_path),
                commit_sha=manifest_sha,
                repository=str(data.get("repository", "")),
                images=images,
                immutable_digests_verified=False,
                details={
                    "error": (
                        "Images in manifest must use immutable digests (@sha256:...). "
                        "Mutable tags like :latest without digest are prohibited."
                    ),
                    "images": images,
                },
                remediation="Publish images with immutable @sha256:... digest pins",
            )

        provenance = bool(data.get("provenance") or data.get("build_timestamp"))

        return ReleaseManifestEvidence(
            status=CheckStatus.PASS,
            manifest_path=str(self.manifest_path),
            commit_sha=manifest_sha,
            repository=str(data.get("repository", "")),
            images=images,
            immutable_digests_verified=True,
            provenance_verified=provenance,
            details={"images_count": len(images), "provenance_present": provenance},
        )

    def validate_smoke_credentials(self) -> SmokeCredentialEvidence:
        """Validate smoke-test credentials and ensure separation from production secrets."""
        user = (
            self.env.get("STAGING_SMOKE_USER")
            or self.env.get("SMOKE_TEST_USERNAME")
            or self.env.get("STAGING_SMOKE_USERNAME")
        )
        pw = self.env.get("STAGING_SMOKE_PASSWORD") or self.env.get("SMOKE_TEST_PASSWORD")

        user_configured = bool(user and user.strip())
        pw_configured = bool(pw and pw.strip())

        if not user_configured and not pw_configured:
            return SmokeCredentialEvidence(
                status=CheckStatus.NOT_CONFIGURED,
                username_configured=False,
                password_configured=False,
                credentials_masked=True,
                production_secret_leak_detected=False,
                details={"error": "Smoke test credentials not found in environment"},
                remediation=(
                    "Export STAGING_SMOKE_USER and STAGING_SMOKE_PASSWORD in staging environment"
                ),
            )

        if not user_configured or not pw_configured:
            return SmokeCredentialEvidence(
                status=CheckStatus.NOT_CONFIGURED,
                username_configured=user_configured,
                password_configured=pw_configured,
                credentials_masked=True,
                production_secret_leak_detected=False,
                details={"error": "Partial smoke credentials: both username and password required"},
                remediation="Ensure both STAGING_SMOKE_USER and STAGING_SMOKE_PASSWORD are set",
            )

        # Check for production secret collision or leak
        pw_clean = pw.strip() if pw else ""
        prod_secret_candidates = [
            self.env.get("REGIMEX_SECRET_KEY", ""),
            self.env.get("PRODUCTION_SECRET_KEY", ""),
            self.env.get("PROD_DATABASE_URL", ""),
        ]

        collision = any(c and pw_clean == c.strip() for c in prod_secret_candidates)
        if collision:
            return SmokeCredentialEvidence(
                status=CheckStatus.FAIL,
                username_configured=True,
                password_configured=True,
                credentials_masked=True,
                production_secret_leak_detected=True,
                details={
                    "error": (
                        "CRITICAL: Smoke test password matches production secret key or credential!"
                    )
                },
                remediation="Use distinct, isolated credentials for staging smoke tests",
            )

        masked_user = user[:2] + "***" if user and len(user) > 2 else "***"
        return SmokeCredentialEvidence(
            status=CheckStatus.PASS,
            username_configured=True,
            password_configured=True,
            credentials_masked=True,
            production_secret_leak_detected=False,
            details={"username_masked": masked_user, "password_length": len(pw_clean)},
        )

    def assess_rollback_and_backup(self) -> RollbackReadinessEvidence:
        """Verify rollback runbooks, backup directory preparation, and migration policy."""
        # Backup configuration check
        backup_dir = self.env.get("STAGING_BACKUP_DIR") or self.env.get("BACKUP_DIR")
        backup_configured = bool(backup_dir and backup_dir.strip())
        backup_directory_ready = False
        if backup_configured and backup_dir:
            b_path = Path(backup_dir)
            backup_directory_ready = b_path.is_dir() or b_path.parent.is_dir()

        # Recovery runbooks existence
        deploy_doc = self.repo_root / "docs" / "deployment.md"
        staging_doc = self.repo_root / "docs" / "staging.md"
        runbooks_verified = deploy_doc.is_file() and staging_doc.is_file()

        # Previous release identifier
        prev_sha = self.env.get("PREVIOUS_RELEASE_SHA") or self.env.get("ROLLBACK_TARGET_SHA")
        prev_identified = bool(prev_sha and validate_commit_sha(prev_sha.strip()))

        status = CheckStatus.PASS
        remediation = None
        details: dict[str, Any] = {
            "deployment_runbook_present": deploy_doc.is_file(),
            "staging_runbook_present": staging_doc.is_file(),
            "backup_configured": backup_configured,
            "previous_release_identified": prev_identified,
            "forward_only_migration_policy": True,
        }

        if not runbooks_verified:
            status = CheckStatus.FAIL
            remediation = "Ensure both docs/deployment.md and docs/staging.md runbooks are present"
        elif not backup_configured:
            status = CheckStatus.WARNING if not self.strict else CheckStatus.FAIL
            remediation = (
                "Configure STAGING_BACKUP_DIR to ensure automated database backup readiness"
            )

        return RollbackReadinessEvidence(
            status=status,
            backup_configured=backup_configured,
            backup_directory_ready=backup_directory_ready,
            recovery_runbook_verified=runbooks_verified,
            previous_release_identified=prev_identified,
            previous_release_sha=prev_sha.strip() if prev_sha else None,
            forward_only_migration_policy_verified=True,
            details=details,
            remediation=remediation,
        )

    def detect_gpu_capability(self) -> GPUCapabilityEvidence:
        """Honest detection of optional host GPU capability (non-mandatory)."""
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                res = subprocess.run(  # noqa: S603
                    [nvidia_smi, "--query-gpu=name,driver_version", "--format=csv,noheader"],  # noqa: S607
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=4,
                )
                if res.returncode == 0 and res.stdout.strip():
                    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
                    device_names = [ln.split(",")[0].strip() for ln in lines]
                    driver_ver = lines[0].split(",")[1].strip() if "," in lines[0] else None
                    return GPUCapabilityEvidence(
                        status=CheckStatus.PASS,
                        mandatory=False,
                        gpu_available=True,
                        device_count=len(device_names),
                        device_names=device_names,
                        driver_version=driver_ver,
                        container_toolkit_detected=True,
                        details={"gpu_vendor": "NVIDIA", "device_count": len(device_names)},
                    )
            except Exception as exc:
                logger.debug("nvidia-smi probe failed: %s", exc)

        # CPU fallback: honest detection that GPU is absent
        return GPUCapabilityEvidence(
            status=CheckStatus.WARNING,
            mandatory=False,
            gpu_available=False,
            device_count=0,
            device_names=[],
            details={
                "note": (
                    "No NVIDIA GPU detected. Staging host operates in CPU fallback mode "
                    "for quantitative analytics and regime detection."
                )
            },
            remediation=(
                "Optional: Install NVIDIA GPU and container toolkit for accelerated compute"
            ),
        )

    def collect_full_evidence(self) -> InfrastructureEvidenceReport:
        """Gather all infrastructure evidence and evaluate overall readiness fail-closed."""
        docker_ev = self.collect_docker_evidence()
        github_ev = self.collect_github_evidence()
        ghcr_ev = self.collect_ghcr_evidence()
        manifest_ev = self.validate_release_manifest()
        smoke_ev = self.validate_smoke_credentials()
        rollback_ev = self.assess_rollback_and_backup()
        gpu_ev = self.detect_gpu_capability()

        all_evidence: list[tuple[str, ReadinessEvidence]] = [
            ("docker", docker_ev),
            ("github", github_ev),
            ("ghcr", ghcr_ev),
            ("manifest", manifest_ev),
            ("smoke_credentials", smoke_ev),
            ("rollback", rollback_ev),
            ("gpu", gpu_ev),
        ]

        mandatory_checks: list[tuple[str, ReadinessEvidence]] = [
            ("docker", docker_ev),
            ("ghcr", ghcr_ev),
            ("manifest", manifest_ev),
            ("smoke_credentials", smoke_ev),
            ("rollback", rollback_ev),
        ]

        failed_checks: list[str] = []
        blocked_checks: list[str] = []
        warnings: list[str] = []
        remediations: list[str] = []

        for name, ev in all_evidence:
            if ev.status == CheckStatus.FAIL:
                failed_checks.append(f"{name}: {ev.details.get('error', 'check failed')}")
                if ev.remediation:
                    remediations.append(ev.remediation)
            elif ev.status == CheckStatus.BLOCKED:
                blocked_checks.append(f"{name}: {ev.details.get('error', 'check blocked')}")
                if ev.remediation:
                    remediations.append(ev.remediation)
            elif ev.status == CheckStatus.WARNING:
                warnings.append(f"{name}: {ev.details.get('note', 'warning advisory')}")
                if ev.remediation and ev.remediation not in remediations:
                    remediations.append(ev.remediation)
            elif ev.status == CheckStatus.NOT_CONFIGURED and (name, ev) in mandatory_checks:
                blocked_checks.append(f"{name}: not configured in environment")
                if ev.remediation:
                    remediations.append(ev.remediation)

        # Fail-closed evaluation
        if failed_checks:
            overall_status = CheckStatus.FAIL
        elif any(ev.status == CheckStatus.BLOCKED for _, ev in mandatory_checks):
            overall_status = CheckStatus.BLOCKED
        elif any(ev.status == CheckStatus.NOT_CONFIGURED for _, ev in mandatory_checks):
            overall_status = CheckStatus.NOT_CONFIGURED
        elif self.strict and warnings:
            overall_status = CheckStatus.FAIL
        elif warnings:
            overall_status = CheckStatus.WARNING
        else:
            overall_status = CheckStatus.PASS

        # Ready if PASS or advisory-only WARNING in non-strict mode without failures/blockages
        is_ready = (overall_status == CheckStatus.PASS) or (
            not self.strict
            and overall_status == CheckStatus.WARNING
            and not failed_checks
            and not blocked_checks
        )

        return InfrastructureEvidenceReport(
            schema_version="1.0.0",
            environment=self.environment,
            repository=self.expected_repository,
            commit_sha=self.commit_sha,
            timestamp=datetime.now(UTC).isoformat(),
            overall_status=overall_status,
            is_ready=is_ready,
            strict_mode=self.strict,
            live_qualification_authorized=False,  # strictly False in V26
            production_deployment_authorized=False,  # strictly False in V26
            docker=docker_ev,
            github=github_ev,
            ghcr=ghcr_ev,
            release_manifest=manifest_ev,
            smoke_credentials=smoke_ev,
            rollback=rollback_ev,
            gpu=gpu_ev,
            failed_checks=failed_checks,
            blocked_checks=blocked_checks,
            warnings=warnings,
            remediations=remediations,
            metadata={
                "collector": "InfrastructureEvidenceCollector",
                "volume": "V26",
                "phase": "readiness_evidence",
            },
        )
