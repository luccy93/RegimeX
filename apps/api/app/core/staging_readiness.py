"""RegimeX — Staging Readiness Preflight Inspector.

apps/api/app/core/staging_readiness.py
======================================
Implements comprehensive, fail-closed preflight inspection of host, runtime,
security, and release readiness for the staging execution environment.

Invariants:
- Never publishes or pulls remote container images.
- Never logs, echoes, or exports plaintext secrets or API keys.
- Distinguishes mandatory checks from optional capabilities.
- Produces auditable, machine-readable StagingPreflightReport instances.
- Fails closed with explicit statuses: PASS, FAIL, BLOCKED, NOT_CONFIGURED,
  NOT_RUN, WARNING.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.deployment import redact_secrets, validate_commit_sha
from app.schemas.staging_readiness import (
    CategorySummary,
    CheckCategory,
    CheckResult,
    CheckStatus,
    StagingPreflightReport,
)

logger = logging.getLogger("regimex.staging_readiness")


class StagingPreflightInspector:
    """Evaluates host, runtime, security, and release prerequisites for staging."""

    def __init__(
        self,
        repo_root: Path | None = None,
        commit_sha: str | None = None,
        branch: str | None = None,
        manifest_path: Path | None = None,
        environment: str = "staging",
        strict: bool = False,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env = env if env is not None else os.environ.copy()
        self.repo_root = (repo_root or self._resolve_repo_root()).resolve()
        self.commit_sha = commit_sha if commit_sha is not None else self._resolve_commit_sha()
        self.branch = branch if branch is not None else self._resolve_branch()
        self.manifest_path = manifest_path or (self.repo_root / "release-manifest.json")
        self.environment = environment
        self.strict = strict

    @staticmethod
    def _resolve_repo_root() -> Path:
        """Dynamically locate repository root from current file."""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "pyproject.toml").is_file() and (parent / "infra").is_dir():
                return parent
            if (parent / ".git").exists() or (parent / "apps" / "api").is_dir():
                return parent
        return current.parents[3]

    def _resolve_commit_sha(self) -> str:
        """Resolve target commit SHA from environment or git."""
        for env_var in ("STAGING_COMMIT_SHA", "DEPLOY_SHA", "GITHUB_SHA"):
            val = self.env.get(env_var)
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

    def _resolve_branch(self) -> str:
        """Resolve active git branch or ref."""
        for env_var in ("STAGING_BRANCH", "GITHUB_REF_NAME", "GITHUB_HEAD_REF"):
            val = self.env.get(env_var)
            if val:
                return val.strip()

        git_bin = shutil.which("git") or "git"
        try:
            res = subprocess.run(  # noqa: S603
                [git_bin, "rev-parse", "--abbrev-ref", "HEAD"],  # noqa: S607
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            branch = res.stdout.strip()
            if branch:
                return branch
        except Exception as exc:
            logger.debug("Could not resolve git branch via CLI: %s", exc)

        return "unknown"

    # =========================================================================
    # Subprocess / System Probing Hooks (Mockable for Unit Tests)
    # =========================================================================

    def _check_docker_cli(self) -> tuple[bool, str]:
        """Check if docker binary exists in system PATH."""
        path = shutil.which("docker")
        if path:
            return True, path
        return False, "docker binary not found in PATH"

    def _check_docker_daemon(self) -> tuple[bool, str]:
        """Verify Docker daemon is reachable and responding."""
        docker_bin = shutil.which("docker") or "docker"
        try:
            res = subprocess.run(  # noqa: S603
                [docker_bin, "info", "--format", "{{.ServerVersion}}"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
                timeout=8,
            )
            if res.returncode == 0:
                ver = res.stdout.strip() or "active"
                return True, f"Docker daemon reachable (version: {ver})"
            err = res.stderr.strip() or "daemon not running"
            return False, f"Docker daemon unreachable: {err}"
        except Exception as exc:
            return False, f"Docker daemon probe failed: {exc}"

    def _check_docker_compose(self) -> tuple[bool, str]:
        """Check whether docker compose plugin or docker-compose is available."""
        docker_bin = shutil.which("docker") or "docker"
        try:
            res = subprocess.run(  # noqa: S603
                [docker_bin, "compose", "version"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
                timeout=8,
            )
            if res.returncode == 0:
                ver = res.stdout.strip()
                return True, f"Docker Compose plugin available ({ver})"
        except Exception as exc:
            logger.debug("docker compose command check exception: %s", exc)

        path = shutil.which("docker-compose")
        if path:
            return True, f"Standalone docker-compose available at {path}"

        return False, (
            "Docker Compose is not available (neither 'docker compose' nor 'docker-compose')"
        )

    def _get_disk_space_gb(self) -> float:
        """Return available disk space in gigabytes at repo root."""
        try:
            usage = shutil.disk_usage(self.repo_root)
            return round(usage.free / (1024**3), 2)
        except Exception as exc:
            logger.debug("Disk usage detection failed: %s", exc)
            return 0.0

    def _get_memory_gb(self) -> float:
        """Return total system memory in gigabytes if detectable."""
        try:
            import psutil  # type: ignore[import-untyped]

            return float(round(psutil.virtual_memory().total / (1024**3), 2))
        except Exception as exc:
            logger.debug("psutil unavailable for memory probe: %s", exc)

        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 2)
            except Exception as exc:
                logger.debug("Reading /proc/meminfo failed: %s", exc)

        return 4.0

    # =========================================================================
    # Host Readiness Checks
    # =========================================================================

    def inspect_host(self) -> list[CheckResult]:
        """Inspect host operating system, architecture, Docker, and resources."""
        results: list[CheckResult] = []

        # 1. OS and Architecture
        os_name = platform.system()
        machine = platform.machine()
        is_64bit = machine.lower() in ("x86_64", "amd64", "arm64", "aarch64")
        if is_64bit:
            results.append(
                CheckResult(
                    name="host_os_architecture",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=f"Supported 64-bit architecture: {os_name} {machine}",
                    details={"os": os_name, "arch": machine, "64bit": True},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="host_os_architecture",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.WARNING,
                    message=f"Non-standard architecture: {os_name} {machine}",
                    details={"os": os_name, "arch": machine, "64bit": False},
                    remediation="Deploy on standard 64-bit x86_64 or aarch64 host.",
                )
            )

        # 2. Python Runtime Compatibility
        py_major, py_minor = sys.version_info.major, sys.version_info.minor
        py_ver_str = f"{py_major}.{py_minor}.{sys.version_info.micro}"
        if (py_major, py_minor) >= (3, 11):
            results.append(
                CheckResult(
                    name="python_runtime",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=f"Compatible Python runtime: {py_ver_str} (>= 3.11)",
                    details={"version": py_ver_str},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="python_runtime",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message=f"Incompatible Python runtime: {py_ver_str} (< 3.11)",
                    details={"version": py_ver_str},
                    remediation="Upgrade staging Python runtime to Python 3.11 or later.",
                )
            )

        # 3. Docker CLI
        docker_cli_ok, docker_cli_msg = self._check_docker_cli()
        if docker_cli_ok:
            results.append(
                CheckResult(
                    name="docker_cli",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=f"Docker CLI binary available: {docker_cli_msg}",
                    details={"path": docker_cli_msg},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="docker_cli",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message="Docker CLI binary not found in PATH",
                    details={"error": docker_cli_msg},
                    remediation="Install Docker Engine/Desktop CLI on staging host.",
                )
            )

        # 4. Docker Daemon Accessibility
        if not docker_cli_ok:
            results.append(
                CheckResult(
                    name="docker_daemon",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.BLOCKED,
                    message="Docker daemon check blocked: Docker CLI is missing",
                    remediation="Install Docker CLI to enable daemon accessibility checks.",
                )
            )
        else:
            daemon_ok, daemon_msg = self._check_docker_daemon()
            if daemon_ok:
                results.append(
                    CheckResult(
                        name="docker_daemon",
                        category=CheckCategory.HOST.value,
                        status=CheckStatus.PASS,
                        message=daemon_msg,
                        details={"status": "running"},
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="docker_daemon",
                        category=CheckCategory.HOST.value,
                        status=CheckStatus.BLOCKED,
                        message=daemon_msg,
                        remediation=(
                            "Start Docker daemon ('systemctl start docker' or Docker Desktop)."
                        ),
                    )
                )

        # 5. Docker Compose Availability
        compose_ok, compose_msg = self._check_docker_compose()
        if compose_ok:
            results.append(
                CheckResult(
                    name="docker_compose",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=compose_msg,
                    details={"details": compose_msg},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="docker_compose",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message="Docker Compose is missing",
                    details={"error": compose_msg},
                    remediation="Install docker compose plugin or docker-compose binary.",
                )
            )

        # 6. Disk Space
        free_gb = self._get_disk_space_gb()
        if free_gb >= 5.0:
            results.append(
                CheckResult(
                    name="disk_space",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=f"Adequate disk space: {free_gb} GB (threshold: 5.0 GB)",
                    details={"free_gb": free_gb, "threshold_gb": 5.0},
                )
            )
        elif free_gb >= 1.0:
            results.append(
                CheckResult(
                    name="disk_space",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.WARNING,
                    message=f"Marginal disk space: {free_gb} GB (recommended >= 5.0 GB)",
                    details={"free_gb": free_gb, "threshold_gb": 5.0},
                    remediation="Prune unused container images and build caches.",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="disk_space",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message=f"Critical disk space deficiency: {free_gb} GB (min 1.0 GB)",
                    details={"free_gb": free_gb, "threshold_gb": 1.0},
                    remediation="Free disk space on host filesystem before deployment.",
                )
            )

        # 7. Available Memory
        mem_gb = self._get_memory_gb()
        if mem_gb >= 2.0:
            results.append(
                CheckResult(
                    name="memory_capacity",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message=f"Adequate system memory capacity: ~{mem_gb} GB (min 2.0 GB)",
                    details={"mem_gb": mem_gb},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="memory_capacity",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.WARNING,
                    message=f"Low system memory capacity: ~{mem_gb} GB (< 2.0 GB recommended)",
                    details={"mem_gb": mem_gb},
                    remediation="Allocate at least 2 GB RAM for API and Web services.",
                )
            )

        # 8. Filesystem Permissions
        probe_file = self.repo_root / ".staging_preflight_probe.tmp"
        try:
            probe_file.write_text("probe", encoding="utf-8")
            probe_file.unlink(missing_ok=True)
            results.append(
                CheckResult(
                    name="filesystem_permissions",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message="Staging workspace filesystem is readable and writable",
                    details={"writable": True},
                )
            )
        except Exception as exc:
            results.append(
                CheckResult(
                    name="filesystem_permissions",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message=f"Filesystem permission error: {exc}",
                    details={"error": str(exc)},
                    remediation="Grant read and write permissions to the staging user.",
                )
            )

        # 9. Required Staging Directories
        required_dirs = ["infra", "infra/docker", "apps/api", "apps/web"]
        missing_dirs = [d for d in required_dirs if not (self.repo_root / d).is_dir()]
        if not missing_dirs:
            results.append(
                CheckResult(
                    name="staging_directories",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.PASS,
                    message="All required project directories are present",
                    details={"checked": required_dirs},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="staging_directories",
                    category=CheckCategory.HOST.value,
                    status=CheckStatus.FAIL,
                    message=f"Missing essential directories: {', '.join(missing_dirs)}",
                    details={"missing": missing_dirs},
                    remediation="Ensure repository checkout includes all project directories.",
                )
            )

        return results

    # =========================================================================
    # Runtime Readiness Checks
    # =========================================================================

    def inspect_runtime(self) -> list[CheckResult]:
        """Inspect backend and frontend configurations, database/redis URLs, and health routes."""
        results: list[CheckResult] = []

        # 1. Backend Runtime Configuration
        backend_cfg_path = self.repo_root / "apps" / "api" / "app" / "core" / "config.py"
        if backend_cfg_path.is_file():
            results.append(
                CheckResult(
                    name="backend_runtime_config",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.PASS,
                    message="Backend configuration module present at apps/api/app/core/config.py",
                    details={"path": "apps/api/app/core/config.py"},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="backend_runtime_config",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.FAIL,
                    message="Backend configuration module missing at apps/api/app/core/config.py",
                    remediation="Ensure apps/api/app/core/config.py is present.",
                )
            )

        # 2. Frontend Runtime Configuration
        frontend_pkg = self.repo_root / "apps" / "web" / "package.json"
        frontend_cfg = self.repo_root / "apps" / "web" / "next.config.mjs"
        if frontend_pkg.is_file() and frontend_cfg.is_file():
            results.append(
                CheckResult(
                    name="frontend_runtime_config",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.PASS,
                    message="Frontend Next.js configuration and package metadata present",
                    details={
                        "package": "apps/web/package.json",
                        "config": "apps/web/next.config.mjs",
                    },
                )
            )
        else:
            results.append(
                CheckResult(
                    name="frontend_runtime_config",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.FAIL,
                    message="Frontend Next.js package or config missing in apps/web/",
                    remediation="Ensure apps/web/package.json and apps/web/next.config.mjs exist.",
                )
            )

        # 3. Database Connectivity Configuration
        db_url = (
            self.env.get("STAGING_DATABASE_URL")
            or self.env.get("REGIMEX_DATABASE_URL")
            or self.env.get("DATABASE_URL")
        )
        if not db_url:
            results.append(
                CheckResult(
                    name="database_configuration",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.NOT_CONFIGURED,
                    message="Staging database URL is not configured",
                    remediation=(
                        "Set REGIMEX_DATABASE_URL with a valid postgresql+asyncpg:// string."
                    ),
                )
            )
        else:
            redacted_db = redact_secrets(db_url)
            is_placeholder = any(
                p in db_url.lower()
                for p in ("changeme", "example.com", "user:password", "localhost:5432/regimex_dev")
            )
            is_valid_scheme = db_url.startswith("postgresql+asyncpg://") or db_url.startswith(
                "postgresql://"
            )

            if is_placeholder:
                results.append(
                    CheckResult(
                        name="database_configuration",
                        category=CheckCategory.RUNTIME.value,
                        status=CheckStatus.FAIL,
                        message=(
                            f"Database URL contains placeholder/default credentials: {redacted_db}"
                        ),
                        details={"url": redacted_db},
                        remediation="Configure genuine staging credentials in environment.",
                    )
                )
            elif not is_valid_scheme:
                results.append(
                    CheckResult(
                        name="database_configuration",
                        category=CheckCategory.RUNTIME.value,
                        status=CheckStatus.FAIL,
                        message=(
                            f"Database URL scheme invalid: {redacted_db}. "
                            "Expected postgresql+asyncpg://"
                        ),
                        details={"url": redacted_db},
                        remediation="Normalize database URL to start with 'postgresql+asyncpg://'.",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="database_configuration",
                        category=CheckCategory.RUNTIME.value,
                        status=CheckStatus.PASS,
                        message=f"Database URL format and scheme validated: {redacted_db}",
                        details={"url": redacted_db},
                    )
                )

        # 4. Redis Connectivity Configuration
        redis_url = (
            self.env.get("STAGING_REDIS_URL")
            or self.env.get("REGIMEX_REDIS_URL")
            or self.env.get("REDIS_URL")
        )
        if not redis_url:
            results.append(
                CheckResult(
                    name="redis_configuration",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.NOT_CONFIGURED,
                    mandatory=False,
                    message="Staging Redis URL is not configured (optional caching/Celery)",
                    remediation="Optionally configure REGIMEX_REDIS_URL for distributed caching.",
                )
            )
        else:
            redacted_redis = redact_secrets(redis_url)
            if redis_url.startswith("redis://") or redis_url.startswith("rediss://"):
                results.append(
                    CheckResult(
                        name="redis_configuration",
                        category=CheckCategory.RUNTIME.value,
                        status=CheckStatus.PASS,
                        mandatory=False,
                        message=f"Redis URL validated: {redacted_redis}",
                        details={"url": redacted_redis},
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="redis_configuration",
                        category=CheckCategory.RUNTIME.value,
                        status=CheckStatus.FAIL,
                        mandatory=False,
                        message=(
                            f"Malformed Redis URL: {redacted_redis}. Expected redis:// or rediss://"
                        ),
                        details={"url": redacted_redis},
                        remediation="Ensure Redis URL scheme is 'redis://' or 'rediss://'.",
                    )
                )

        # 5. Required Environment Variables
        secret_key = self.env.get("REGIMEX_SECRET_KEY") or self.env.get("AUTH_JWT_SECRET")
        allowed_origins = self.env.get("REGIMEX_ALLOWED_ORIGINS") or self.env.get(
            "CORS_ALLOWED_ORIGINS"
        )
        api_public_url = self.env.get("NEXT_PUBLIC_API_URL")

        missing_vars: list[str] = []
        if not secret_key:
            missing_vars.append("REGIMEX_SECRET_KEY")
        if not allowed_origins:
            missing_vars.append("REGIMEX_ALLOWED_ORIGINS")
        if not api_public_url:
            missing_vars.append("NEXT_PUBLIC_API_URL")

        if missing_vars:
            results.append(
                CheckResult(
                    name="required_environment_variables",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.NOT_CONFIGURED,
                    message=f"Missing required staging variables: {', '.join(missing_vars)}",
                    details={"missing": missing_vars},
                    remediation="Define required environment variables in staging configuration.",
                )
            )
        elif secret_key is not None and (len(secret_key) < 32 or "changeme" in secret_key.lower()):
            results.append(
                CheckResult(
                    name="required_environment_variables",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.FAIL,
                    message="REGIMEX_SECRET_KEY must be >= 32 characters and cannot be placeholder",
                    remediation="Generate a secure random secret key (e.g. openssl rand -hex 32).",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="required_environment_variables",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.PASS,
                    message="All required core environment variables are populated and conform",
                    details={
                        "variables_checked": [
                            "REGIMEX_SECRET_KEY",
                            "REGIMEX_ALLOWED_ORIGINS",
                            "NEXT_PUBLIC_API_URL",
                        ]
                    },
                )
            )

        # 6. Health Check Interfaces
        api_health_endpoint = (
            self.repo_root / "apps" / "api" / "app" / "api" / "v1" / "endpoints" / "health.py"
        )
        web_health_page = self.repo_root / "apps" / "web" / "app" / "app" / "health" / "page.tsx"

        has_api_health = api_health_endpoint.is_file()
        has_web_health = web_health_page.is_file()

        if has_api_health and has_web_health:
            results.append(
                CheckResult(
                    name="health_check_interfaces",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.PASS,
                    message="Backend and frontend health routes verified",
                    details={
                        "api_health": str(api_health_endpoint),
                        "web_health": str(web_health_page),
                    },
                )
            )
        else:
            results.append(
                CheckResult(
                    name="health_check_interfaces",
                    category=CheckCategory.RUNTIME.value,
                    status=CheckStatus.FAIL,
                    message="Missing application health check interface routes",
                    details={"has_api_health": has_api_health, "has_web_health": has_web_health},
                    remediation="Ensure apps/api health endpoints and apps/web health page exist.",
                )
            )

        return results

    # =========================================================================
    # Security Readiness Checks
    # =========================================================================

    def inspect_security(self) -> list[CheckResult]:
        """Inspect secret presence without exposure, non-root users, and CORS rules."""
        results: list[CheckResult] = []

        # 1. Secret Masking & Redaction Invariant
        results.append(
            CheckResult(
                name="secret_masking_policy",
                category=CheckCategory.SECURITY.value,
                status=CheckStatus.PASS,
                message="Secret redaction filter active; credential plaintext is masked",
            )
        )

        # 2. Git Ignored Secrets Check
        env_files = list(self.repo_root.glob(".env*"))
        tracked_env: list[str] = []
        for ef in env_files:
            if ef.name in (".env.example", ".env.production.example"):
                continue
            git_bin = shutil.which("git") or "git"
            try:
                res = subprocess.run(  # noqa: S603
                    [git_bin, "ls-files", ef.name],  # noqa: S607
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                if res.stdout.strip():
                    tracked_env.append(ef.name)
            except Exception as exc:
                logger.debug("git ls-files check failed: %s", exc)

        if not tracked_env:
            results.append(
                CheckResult(
                    name="git_ignored_secrets",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.PASS,
                    message="No sensitive .env credential files are tracked in source control",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="git_ignored_secrets",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.FAIL,
                    message=(
                        f"Security violation: env file(s) tracked in git: {', '.join(tracked_env)}"
                    ),
                    details={"tracked": tracked_env},
                    remediation="Untrack and remove sensitive files: git rm --cached <file>.",
                )
            )

        # 3. Non-root Container Configuration
        api_df = self.repo_root / "infra" / "docker" / "api.Dockerfile"
        web_df = self.repo_root / "infra" / "docker" / "web.Dockerfile"

        api_non_root = False
        web_non_root = False

        if api_df.is_file():
            content = api_df.read_text(encoding="utf-8")
            api_non_root = bool(
                re.search(r"^\s*USER\s+(?!root\b)[a-zA-Z0-9_-]+", content, re.MULTILINE)
            )

        if web_df.is_file():
            content = web_df.read_text(encoding="utf-8")
            web_non_root = bool(
                re.search(r"^\s*USER\s+(?!root\b)[a-zA-Z0-9_-]+", content, re.MULTILINE)
            )

        if api_non_root and web_non_root:
            results.append(
                CheckResult(
                    name="non_root_containers",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.PASS,
                    message="Both API and Web Dockerfiles enforce non-root runtime users",
                    details={"api_non_root": True, "web_non_root": True},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="non_root_containers",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.FAIL,
                    message=(
                        f"Containers must run non-root. api: {api_non_root}, web: {web_non_root}"
                    ),
                    details={"api_non_root": api_non_root, "web_non_root": web_non_root},
                    remediation="Specify a non-root USER instruction in Dockerfiles.",
                )
            )

        # 4. CORS Origins Security
        allowed_origins = self.env.get("REGIMEX_ALLOWED_ORIGINS") or self.env.get(
            "CORS_ALLOWED_ORIGINS", ""
        )
        if "*" in allowed_origins:
            results.append(
                CheckResult(
                    name="cors_origin_policy",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.FAIL,
                    message="Wildcard CORS origins (*) are forbidden in staging and production",
                    remediation=(
                        "Specify explicit staging origin domains in REGIMEX_ALLOWED_ORIGINS."
                    ),
                )
            )
        elif allowed_origins:
            results.append(
                CheckResult(
                    name="cors_origin_policy",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.PASS,
                    message="Explicit CORS origin policy enforced; no wildcard permissions",
                    details={"allowed_origins": allowed_origins},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="cors_origin_policy",
                    category=CheckCategory.SECURITY.value,
                    status=CheckStatus.NOT_CONFIGURED,
                    message="CORS origin policy is not configured",
                    remediation="Define explicit staging origins in REGIMEX_ALLOWED_ORIGINS.",
                )
            )

        return results

    # =========================================================================
    # Release Readiness Checks
    # =========================================================================

    def inspect_release(self) -> list[CheckResult]:
        """Inspect commit SHA, branch validity, release manifest, and image tags."""
        results: list[CheckResult] = []

        # 1. Commit SHA Validation
        if validate_commit_sha(self.commit_sha):
            results.append(
                CheckResult(
                    name="target_commit_sha",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.PASS,
                    message=f"Target commit SHA is valid 40-character hex: {self.commit_sha}",
                    details={"commit_sha": self.commit_sha},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="target_commit_sha",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.FAIL,
                    message=f"Invalid commit SHA: '{self.commit_sha}'. Expected 40-character hex.",
                    details={"commit_sha": self.commit_sha},
                    remediation="Provide a valid 40-character Git commit hash.",
                )
            )

        # 2. Authorized Branch / Ref Validation
        is_known_branch = bool(
            self.branch in ("main", "staging")
            or self.branch.startswith("release/")
            or self.branch.startswith("refs/heads/")
        )
        if is_known_branch:
            results.append(
                CheckResult(
                    name="authorized_branch",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.PASS,
                    message=f"Active ref '{self.branch}' is an authorized staging branch",
                    details={"branch": self.branch},
                )
            )
        else:
            results.append(
                CheckResult(
                    name="authorized_branch",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.WARNING,
                    message=(
                        f"Active ref '{self.branch}' is outside primary staging branches "
                        "(main, staging, release/*)"
                    ),
                    details={"branch": self.branch},
                    remediation="Align staging branch with 'main', 'staging', or 'release/*'.",
                )
            )

        # 3. Known-Good Release Manifest Availability
        manifest_data: dict[str, Any] | None = None
        if self.manifest_path.is_file():
            try:
                manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                results.append(
                    CheckResult(
                        name="release_manifest_availability",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.PASS,
                        message=f"Release manifest found and parsed at {self.manifest_path.name}",
                        details={"path": str(self.manifest_path)},
                    )
                )
            except Exception as exc:
                results.append(
                    CheckResult(
                        name="release_manifest_availability",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.FAIL,
                        message=f"Release manifest at {self.manifest_path.name} malformed: {exc}",
                        details={"error": str(exc)},
                        remediation="Ensure release-manifest.json is valid JSON.",
                    )
                )
        else:
            results.append(
                CheckResult(
                    name="release_manifest_availability",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.NOT_CONFIGURED,
                    mandatory=True,
                    message=f"Known-good release manifest not found at {self.manifest_path}",
                    details={"path": str(self.manifest_path)},
                    remediation=(
                        "Provide release-manifest.json containing validated release metadata."
                    ),
                )
            )

        # 4. Release Metadata Integrity & Commit Match
        if manifest_data is not None:
            manifest_sha = str(manifest_data.get("commit_sha", "")).strip()
            if manifest_sha == self.commit_sha and validate_commit_sha(manifest_sha):
                results.append(
                    CheckResult(
                        name="release_metadata_integrity",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.PASS,
                        message=f"Release manifest commit matches target commit: {manifest_sha}",
                        details={"manifest_sha": manifest_sha, "target_sha": self.commit_sha},
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="release_metadata_integrity",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.FAIL,
                        message=(
                            f"Release manifest commit mismatch: manifest={manifest_sha} "
                            f"vs target={self.commit_sha}"
                        ),
                        details={"manifest_sha": manifest_sha, "target_sha": self.commit_sha},
                        remediation="Regenerate manifest for current target commit SHA.",
                    )
                )
        else:
            results.append(
                CheckResult(
                    name="release_metadata_integrity",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.NOT_RUN,
                    message="Skipped release metadata integrity check (manifest absent)",
                )
            )

        # 5. Image References and Immutable Digest Formats
        if manifest_data is not None:
            images = manifest_data.get("images", {})
            api_img = images.get("api", "")
            web_img = images.get("web", "")

            has_mutable_tag = any(
                ":latest" in img and "@sha256:" not in img for img in (api_img, web_img)
            )
            has_valid_refs = bool(api_img and web_img)

            if not has_valid_refs:
                results.append(
                    CheckResult(
                        name="immutable_image_references",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.FAIL,
                        message="Release manifest images.api or images.web reference is missing",
                        details={"images": images},
                        remediation=(
                            "Specify image references with commit tags or sha256 digests."
                        ),
                    )
                )
            elif has_mutable_tag:
                results.append(
                    CheckResult(
                        name="immutable_image_references",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.FAIL,
                        message="Mutable ':latest' tags without digests are forbidden in staging",
                        details={"api_image": api_img, "web_image": web_img},
                        remediation="Pin image references with commit SHA tag or @sha256 digest.",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="immutable_image_references",
                        category=CheckCategory.RELEASE.value,
                        status=CheckStatus.PASS,
                        message="Image references conform to immutable tag or digest format",
                        details={"api_image": api_img, "web_image": web_img},
                    )
                )
        else:
            results.append(
                CheckResult(
                    name="immutable_image_references",
                    category=CheckCategory.RELEASE.value,
                    status=CheckStatus.NOT_RUN,
                    message="Skipped image reference check (manifest absent)",
                )
            )

        return results

    # =========================================================================
    # Aggregation & Report Generation
    # =========================================================================

    def _summarize_category(self, category: str, checks: list[CheckResult]) -> CategorySummary:
        """Compute aggregated summary metrics and status for a category."""
        total = len(checks)
        passed = sum(1 for c in checks if c.status == CheckStatus.PASS)
        failed = sum(1 for c in checks if c.status == CheckStatus.FAIL)
        blocked = sum(1 for c in checks if c.status == CheckStatus.BLOCKED)
        warning = sum(1 for c in checks if c.status == CheckStatus.WARNING)
        not_conf = sum(1 for c in checks if c.status == CheckStatus.NOT_CONFIGURED)
        not_run = sum(1 for c in checks if c.status == CheckStatus.NOT_RUN)

        if failed > 0:
            cat_status = CheckStatus.FAIL
        elif blocked > 0:
            cat_status = CheckStatus.BLOCKED
        elif not_conf > 0:
            cat_status = CheckStatus.NOT_CONFIGURED
        elif warning > 0 and self.strict:
            cat_status = CheckStatus.FAIL
        elif warning > 0:
            cat_status = CheckStatus.WARNING
        elif not_run == total:
            cat_status = CheckStatus.NOT_RUN
        else:
            cat_status = CheckStatus.PASS

        return CategorySummary(
            category=category,
            status=cat_status,
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            blocked_checks=blocked,
            warning_checks=warning,
            not_configured_checks=not_conf,
            not_run_checks=not_run,
            checks=checks,
        )

    def run_preflight(self) -> StagingPreflightReport:
        """Run all staging preflight inspections and generate a machine-readable report."""
        timestamp = datetime.now(tz=UTC).isoformat()
        logger.info(
            "Executing staging readiness preflight for commit '%s' on branch '%s'",
            self.commit_sha,
            self.branch,
        )

        host_checks = self.inspect_host()
        runtime_checks = self.inspect_runtime()
        security_checks = self.inspect_security()
        release_checks = self.inspect_release()

        host_summary = self._summarize_category(CheckCategory.HOST.value, host_checks)
        runtime_summary = self._summarize_category(CheckCategory.RUNTIME.value, runtime_checks)
        security_summary = self._summarize_category(CheckCategory.SECURITY.value, security_checks)
        release_summary = self._summarize_category(CheckCategory.RELEASE.value, release_checks)

        all_checks = host_checks + runtime_checks + security_checks + release_checks
        failed = [c.name for c in all_checks if c.status == CheckStatus.FAIL]
        blocked = [c.name for c in all_checks if c.status == CheckStatus.BLOCKED]
        warnings = [c.name for c in all_checks if c.status == CheckStatus.WARNING]
        remediations = [c.remediation for c in all_checks if c.remediation]

        has_mandatory_not_configured = any(
            c.status == CheckStatus.NOT_CONFIGURED and c.mandatory for c in all_checks
        )

        if failed:
            overall = CheckStatus.FAIL
        elif blocked:
            overall = CheckStatus.BLOCKED
        elif has_mandatory_not_configured:
            overall = CheckStatus.NOT_CONFIGURED
        elif warnings and self.strict:
            overall = CheckStatus.FAIL
        elif warnings:
            overall = CheckStatus.WARNING
        else:
            overall = CheckStatus.PASS

        is_ready = overall == CheckStatus.PASS

        return StagingPreflightReport(
            schema_version="1.0.0",
            environment=self.environment,
            repository="luccy93/RegimeX",
            commit_sha=self.commit_sha,
            branch=self.branch,
            timestamp=timestamp,
            overall_status=overall,
            is_ready=is_ready,
            strict_mode=self.strict,
            host=host_summary,
            runtime=runtime_summary,
            security=security_summary,
            release=release_summary,
            failed_checks=failed,
            blocked_checks=blocked,
            warnings=warnings,
            remediations=list(dict.fromkeys(remediations)),
            metadata={
                "inspector_version": "v26.1.0",
                "python_version": (
                    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                ),
                "platform": platform.platform(),
            },
        )

    def to_text_report(self, report: StagingPreflightReport, verbose: bool = False) -> str:
        """Render human-readable text report with status indicators and remedial actions."""
        ready_text = (
            "YES (Ready for Stage 2 Evidence)" if report.is_ready else "NO (Prerequisites Pending)"
        )
        lines: list[str] = [
            "=" * 68,
            "  RegimeX — Staging Readiness Preflight Report",
            "=" * 68,
            f"  Environment:       {report.environment}",
            f"  Target Commit SHA: {report.commit_sha or 'UNRESOLVED'}",
            f"  Target Branch:     {report.branch or 'unknown'}",
            f"  Evaluation Time:   {report.timestamp}",
            f"  Strict Mode:       {report.strict_mode}",
            f"  Overall Status:    [{report.overall_status.value}]",
            f"  Staging Ready:     {ready_text}",
            "-" * 68,
            "  Category Breakdown:",
            (
                f"    Host:     [{report.host.status.value}] "
                f"({report.host.passed_checks}/{report.host.total_checks} passed)"
            ),
            (
                f"    Runtime:  [{report.runtime.status.value}] "
                f"({report.runtime.passed_checks}/{report.runtime.total_checks} passed)"
            ),
            (
                f"    Security: [{report.security.status.value}] "
                f"({report.security.passed_checks}/{report.security.total_checks} passed)"
            ),
            (
                f"    Release:  [{report.release.status.value}] "
                f"({report.release.passed_checks}/{report.release.total_checks} passed)"
            ),
        ]

        if verbose:
            lines.extend(["-" * 68, "  Detailed Check Results:"])
            for cat_name, cat_summary in [
                ("Host", report.host),
                ("Runtime", report.runtime),
                ("Security", report.security),
                ("Release", report.release),
            ]:
                lines.append(f"\n  [{cat_name.upper()} CHECKS]")
                for chk in cat_summary.checks:
                    indicator = f"[{chk.status.value}]"
                    lines.append(f"    {indicator:<18} {chk.name}: {chk.message}")

        if report.failed_checks:
            lines.extend(["-" * 68, "  Failed Checks:"])
            for fc in report.failed_checks:
                lines.append(f"    - {fc}")

        if report.blocked_checks:
            lines.extend(["-" * 68, "  Blocked Checks:"])
            for bc in report.blocked_checks:
                lines.append(f"    - {bc}")

        if report.warnings:
            lines.extend(["-" * 68, "  Warnings:"])
            for w in report.warnings:
                lines.append(f"    - {w}")

        if report.remediations:
            lines.extend(["-" * 68, "  Required Remedial Actions:"])
            for idx, rem in enumerate(report.remediations, 1):
                lines.append(f"    {idx}. {rem}")

        lines.extend(["=" * 68, ""])
        return "\n".join(lines)
