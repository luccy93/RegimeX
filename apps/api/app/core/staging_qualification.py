"""RegimeX — Controlled Staging Qualification Orchestrator.

apps/api/app/core/staging_qualification.py
==========================================
Provides controlled, auditable staging qualification orchestration on top of
Volume V26 readiness preflight, infrastructure evidence, and unified readiness gates.

Invariants:
- Never falls back to production environment names, URLs, or credentials.
- Refuses to proceed if V26 readiness gates have not passed.
- Executes only explicitly registered, approved qualification stages with bounded timeouts.
- Never executes arbitrary shell commands supplied by users or reports.
- Dry-run mode performs zero network requests and zero infrastructure mutations.
- Redacts all secrets, tokens, passwords, and connection strings from logs and reports.
- Governance flags (live_qualification_authorized, production_deployment_authorized,
  production_deployment_performed, container_images_published) remain strictly False.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import re
import time
import urllib.parse
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.deployment import redact_secrets, validate_commit_sha
from app.core.staging_evidence import InfrastructureEvidenceCollector
from app.core.staging_gates import StagingReadinessGateEvaluator
from app.core.staging_readiness import StagingPreflightInspector
from app.schemas.staging_readiness import (
    CheckStatus,
    ExecutionMode,
    InfrastructureEvidenceReport,
    QualificationCheckResult,
    QualificationEnvironment,
    QualificationEvidence,
    QualificationRunMetadata,
    QualificationStage,
    QualificationStageResult,
    QualificationStatus,
    StagingGateEvaluationReport,
    StagingPreflightReport,
    StagingQualificationReport,
)

logger = logging.getLogger("regimex.staging_qualification")

EXPECTED_REPOSITORY = "luccy93/RegimeX"
ALLOWED_STAGING_ENVIRONMENTS = frozenset({"staging"})
REJECTED_PRODUCTION_ENVIRONMENTS = frozenset(
    {
        "production",
        "prod",
        "prd",
        "live",
        "production-live",
        "prod-us",
        "prod-eu",
    }
)
PRODUCTION_HOST_MARKERS = (
    "prod.",
    ".prod.",
    "production.",
    ".production.",
    "api.regimex.io",
    "app.regimex.io",
)
SENSITIVE_ENV_KEYS = (
    "REGIMEX_SECRET_KEY",
    "AUTH_JWT_SECRET",
    "SECRET_KEY",
    "PRODUCTION_SECRET_KEY",
    "PRODUCTION_API_TOKEN",
    "REGIMEX_DATABASE_URL",
    "STAGING_DATABASE_URL",
    "DATABASE_URL",
    "PROD_DATABASE_URL",
    "REGIMEX_REDIS_URL",
    "STAGING_REDIS_URL",
    "REDIS_URL",
    "PROD_REDIS_URL",
    "STAGING_SMOKE_PASSWORD",
    "SMOKE_TEST_PASSWORD",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GHCR_TOKEN",
    "CR_PAT",
    "AI_API_KEY",
    "REGIMEX_AI_API_KEY",
    "RENDER_DEPLOY_HOOK_API",
    "RENDER_DEPLOY_HOOK_WEB",
)
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization",
        "auth",
        "credential",
        "credentials",
        "database_url",
        "dsn",
        "connection_string",
    }
)


# =============================================================================
# Secret Redaction & Isolation Helpers
# =============================================================================


def sanitize_text(text: str, env: dict[str, str] | None = None) -> str:
    """Redact credentials, tokens, connection strings, and known secret env values."""
    if not text:
        return ""
    sanitized = redact_secrets(text)
    sanitized = re.sub(
        r"(?i)(Authorization\s*:\s*(?:Bearer|Basic|Token)\s+)[^\s,;\"']+",
        r"\1***",
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)(Basic\s+)[a-zA-Z0-9+/=_\-]+",
        r"\1***",
        sanitized,
    )
    sanitized = re.sub(
        r"(?i)\b(password|passwd|secret|token|api_key|apikey|auth)\s*[:=]\s*[^\s,;\"']+",
        r"\1=***",
        sanitized,
    )
    sanitized = re.sub(
        r"\b(gh[pousr]_[a-zA-Z0-9]{10,}|github_pat_[a-zA-Z0-9_]{10,})\b",
        "***",
        sanitized,
    )
    sanitized = re.sub(r"\b(sk-[a-zA-Z0-9_\-]{10,})\b", "***", sanitized)

    if env:
        for key in SENSITIVE_ENV_KEYS:
            val = env.get(key)
            if val and len(val.strip()) >= 4:
                clean_val = val.strip()
                if clean_val in sanitized:
                    sanitized = sanitized.replace(clean_val, "***")
    return sanitized


def sanitize_mapping(data: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    """Recursively sanitize a dictionary to guarantee zero secret leakage."""
    sanitized: dict[str, Any] = {}
    for k, v in data.items():
        key_lower = str(k).lower()
        if key_lower in SENSITIVE_FIELD_NAMES or any(
            s in key_lower for s in ("password", "secret", "token", "api_key", "authorization")
        ):
            sanitized[k] = "***" if v is not None else None
        elif isinstance(v, str):
            sanitized[k] = sanitize_text(v, env=env)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_mapping(v, env=env)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_mapping(item, env=env)
                if isinstance(item, dict)
                else (sanitize_text(item, env=env) if isinstance(item, str) else item)
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def _is_production_environment(env_name: str) -> bool:
    """Return True if the environment name refers to production or live."""
    normalized = env_name.strip().lower()
    if normalized in REJECTED_PRODUCTION_ENVIRONMENTS:
        return True
    if "production" in normalized or normalized.startswith("prod"):
        return True
    return False


def _is_production_url(url: str, env: dict[str, str]) -> tuple[bool, str | None]:
    """Detect whether a target URL points to or collides with a production endpoint."""
    parsed = urllib.parse.urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    normalized_url = url.strip().rstrip("/").lower()

    prod_candidates = (
        env.get("PRODUCTION_API_URL", ""),
        env.get("PRODUCTION_WEB_URL", ""),
        env.get("PROD_API_URL", ""),
        env.get("PROD_WEB_URL", ""),
    )
    for cand in prod_candidates:
        clean_cand = cand.strip().rstrip("/").lower()
        if clean_cand and normalized_url == clean_cand:
            return True, "Target URL matches configured production URL"

    for marker in PRODUCTION_HOST_MARKERS:
        if marker in host:
            return True, f"Target hostname '{host}' contains production marker '{marker}'"

    if host in ("prod", "production") or host.startswith("prod-") or host.endswith(".prod"):
        return True, f"Target hostname '{host}' identifies a production host"

    return False, None


def _validate_target_url(
    url: str | None, label: str, env: dict[str, str]
) -> tuple[bool, str | None]:
    """Validate URL format and ensure it does not target production."""
    if not url or not url.strip():
        return False, f"Missing {label}"

    clean_url = url.strip()
    parsed = urllib.parse.urlparse(clean_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False, f"Malformed {label}: {sanitize_text(clean_url, env)}"

    if parsed.username or parsed.password:
        return False, f"{label} must not embed credentials in URL"

    is_prod, prod_reason = _is_production_url(clean_url, env)
    if is_prod:
        return False, f"Production target rejected for {label}: {prod_reason}"

    return True, None


# =============================================================================
# Stage Registry & Execution Context
# =============================================================================


@dataclass(frozen=True)
class QualificationContext:
    """Immutable execution context passed to approved qualification stage handlers."""

    run_id: str
    environment: str
    repository: str
    commit_sha: str
    release_tag: str
    dry_run: bool
    strict: bool
    env: dict[str, str]
    preflight_report: StagingPreflightReport
    evidence_report: InfrastructureEvidenceReport
    gate_report: StagingGateEvaluationReport
    staging_api_url: str | None
    staging_web_url: str | None
    execution_mode: ExecutionMode = ExecutionMode.MOCKED


StageHandler = Callable[[QualificationContext], QualificationStageResult]


@dataclass(frozen=True)
class RegisteredQualificationStage:
    """Registry entry combining stage metadata with its Python handler."""

    definition: QualificationStage
    handler: StageHandler


class QualificationStageRegistry:
    """Controlled registry of explicitly approved staging qualification stages."""

    def __init__(self) -> None:
        self._stages: dict[str, RegisteredQualificationStage] = {}

    def register(
        self,
        definition: QualificationStage,
        handler: StageHandler,
        *,
        replace: bool = False,
    ) -> None:
        """Register a qualification stage with bounded timeout validation."""
        if not definition.stage_id or not re.fullmatch(r"[a-z0-9_.-]+", definition.stage_id):
            raise ValueError(f"Invalid stage_id '{definition.stage_id}': must match [a-z0-9_.-]+")
        if definition.timeout_seconds <= 0 or definition.timeout_seconds > 300:
            raise ValueError("Stage timeout_seconds must be within (0, 300]")
        if definition.stage_id in self._stages and not replace:
            raise ValueError(f"Duplicate qualification stage_id '{definition.stage_id}'")
        self._stages[definition.stage_id] = RegisteredQualificationStage(
            definition=definition,
            handler=handler,
        )

    def get(self, stage_id: str) -> RegisteredQualificationStage | None:
        """Retrieve a registered stage by unique identifier."""
        return self._stages.get(stage_id)

    def list_stages(self) -> list[QualificationStage]:
        """List all registered stage definitions in registration order."""
        return [entry.definition for entry in self._stages.values()]

    def list_approved_stages(self) -> list[QualificationStage]:
        """List only explicitly approved stage definitions."""
        return [entry.definition for entry in self._stages.values() if entry.definition.approved]

    def validate_selection(
        self, stage_ids: Sequence[str] | None = None
    ) -> tuple[bool, list[RegisteredQualificationStage], str | None]:
        """Validate that requested stages exist in the registry and are explicitly approved."""
        if stage_ids is None:
            selected = [entry for entry in self._stages.values() if entry.definition.approved]
            return True, selected, None

        selected = []
        for sid in stage_ids:
            entry = self._stages.get(sid)
            if entry is None:
                return False, [], f"Unregistered qualification stage requested: '{sid}'"
            if not entry.definition.approved:
                return False, [], f"Unapproved qualification stage rejected: '{sid}'"
            selected.append(entry)
        return True, selected, None


# =============================================================================
# Default Approved Governance & Verification Stages
# =============================================================================


def _run_environment_isolation_stage(ctx: QualificationContext) -> QualificationStageResult:
    """Verify staging environment isolation from production URLs and credentials."""
    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()

    checks: list[QualificationCheckResult] = []

    api_ok, api_err = _validate_target_url(ctx.staging_api_url, "STAGING_API_URL", ctx.env)
    checks.append(
        QualificationCheckResult(
            check_id="env.isolation.api_url",
            stage_id="environment_isolation",
            name="Staging API URL Isolation",
            status=QualificationStatus.PASS if api_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                f"Staging API target verified: {sanitize_text(ctx.staging_api_url or '', ctx.env)}"
                if api_ok
                else (api_err or "Invalid STAGING_API_URL")
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
            error=None if api_ok else api_err,
        )
    )

    web_ok, web_err = _validate_target_url(ctx.staging_web_url, "STAGING_WEB_URL", ctx.env)
    checks.append(
        QualificationCheckResult(
            check_id="env.isolation.web_url",
            stage_id="environment_isolation",
            name="Staging Web URL Isolation",
            status=QualificationStatus.PASS if web_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                f"Staging Web target verified: {sanitize_text(ctx.staging_web_url or '', ctx.env)}"
                if web_ok
                else (web_err or "Invalid STAGING_WEB_URL")
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
            error=None if web_ok else web_err,
        )
    )

    overall_ok = api_ok and web_ok
    duration = round(time.monotonic() - t0, 4)
    return QualificationStageResult(
        stage_id="environment_isolation",
        name="Environment Isolation Verification",
        status=QualificationStatus.PASS if overall_ok else QualificationStatus.FAIL,
        mandatory=True,
        requires_live_staging=False,
        started_at=started,
        completed_at=datetime.now(UTC).isoformat(),
        duration_seconds=duration,
        checks=checks,
        message=(
            "Staging target URLs and secrets isolated from production"
            if overall_ok
            else "Staging environment isolation check failed"
        ),
        error=None if overall_ok else "Target configuration violated staging isolation rules",
    )


def _run_release_identity_stage(ctx: QualificationContext) -> QualificationStageResult:
    """Verify immutable commit SHA, repository identity, and release manifest alignment."""
    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()

    sha_ok = (
        validate_commit_sha(ctx.commit_sha)
        and ctx.preflight_report.commit_sha.lower() == ctx.commit_sha.lower()
        and ctx.evidence_report.commit_sha.lower() == ctx.commit_sha.lower()
    )
    repo_ok = (
        ctx.repository == EXPECTED_REPOSITORY
        and ctx.preflight_report.repository == EXPECTED_REPOSITORY
        and ctx.evidence_report.repository == EXPECTED_REPOSITORY
    )
    manifest_ev = ctx.evidence_report.release_manifest
    manifest_ok = (
        manifest_ev.status == CheckStatus.PASS
        and manifest_ev.immutable_digests_verified
        and (manifest_ev.commit_sha or "").lower() == ctx.commit_sha.lower()
    )

    checks = [
        QualificationCheckResult(
            check_id="release.identity.commit_sha",
            stage_id="release_identity",
            name="Commit SHA Consistency",
            status=QualificationStatus.PASS if sha_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                f"Immutable 40-char commit SHA verified across all reports: {ctx.commit_sha}"
                if sha_ok
                else "Commit SHA mismatch across qualification inputs"
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
            details={"commit_sha": ctx.commit_sha, "release_tag": ctx.release_tag},
        ),
        QualificationCheckResult(
            check_id="release.identity.repository",
            stage_id="release_identity",
            name="Repository Identity",
            status=QualificationStatus.PASS if repo_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                f"Repository identity verified: {ctx.repository}"
                if repo_ok
                else f"Repository mismatch (expected {EXPECTED_REPOSITORY})"
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
        ),
        QualificationCheckResult(
            check_id="release.identity.manifest_digests",
            stage_id="release_identity",
            name="Release Manifest Immutable Digests",
            status=QualificationStatus.PASS if manifest_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                "Release manifest immutable @sha256 digests verified"
                if manifest_ok
                else "Release manifest immutable digests not verified"
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
        ),
    ]

    all_ok = sha_ok and repo_ok and manifest_ok
    return QualificationStageResult(
        stage_id="release_identity",
        name="Immutable Release Identity Verification",
        status=QualificationStatus.PASS if all_ok else QualificationStatus.FAIL,
        mandatory=True,
        requires_live_staging=False,
        started_at=started,
        completed_at=datetime.now(UTC).isoformat(),
        duration_seconds=round(time.monotonic() - t0, 4),
        checks=checks,
        message=(
            f"Release identity verified ({ctx.release_tag})"
            if all_ok
            else "Release identity verification failed"
        ),
        error=None if all_ok else "Release identity or manifest digest verification failed",
    )


def _run_qualification_policy_stage(ctx: QualificationContext) -> QualificationStageResult:
    """Verify V26 gate approval and V27 governance non-authorization invariants."""
    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()

    gate_ok = ctx.gate_report.is_ready
    gov_ok = (
        not ctx.evidence_report.live_qualification_authorized
        and not ctx.evidence_report.production_deployment_authorized
        and not ctx.gate_report.live_qualification_authorized
        and not ctx.gate_report.production_deployment_authorized
    )

    checks = [
        QualificationCheckResult(
            check_id="policy.v26_readiness_gate",
            stage_id="qualification_policy",
            name="V26 Unified Readiness Gate",
            status=QualificationStatus.PASS if gate_ok else QualificationStatus.BLOCKED,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                f"V26 readiness gate passed ({ctx.gate_report.overall_status.value})"
                if gate_ok
                else f"V26 readiness gate not ready ({ctx.gate_report.overall_status.value})"
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
        ),
        QualificationCheckResult(
            check_id="policy.governance_boundaries",
            stage_id="qualification_policy",
            name="Governance Authorization Boundaries",
            status=QualificationStatus.PASS if gov_ok else QualificationStatus.FAIL,
            mandatory=True,
            execution_mode=ctx.execution_mode,
            message=(
                "Governance invariants enforced: production deployment and image push disabled"
                if gov_ok
                else "Governance boundary violation detected in V26 inputs"
            ),
            started_at=started,
            completed_at=datetime.now(UTC).isoformat(),
        ),
    ]

    all_ok = gate_ok and gov_ok
    status = (
        QualificationStatus.PASS
        if all_ok
        else (QualificationStatus.FAIL if not gov_ok else QualificationStatus.BLOCKED)
    )
    return QualificationStageResult(
        stage_id="qualification_policy",
        name="Governance & Qualification Policy Verification",
        status=status,
        mandatory=True,
        requires_live_staging=False,
        started_at=started,
        completed_at=datetime.now(UTC).isoformat(),
        duration_seconds=round(time.monotonic() - t0, 4),
        checks=checks,
        message=(
            "Qualification policy and governance invariants verified"
            if all_ok
            else "Qualification policy check failed or blocked"
        ),
        error=None if all_ok else "Qualification policy preconditions not met",
    )


def build_default_stage_registry() -> QualificationStageRegistry:
    """Create the default approved qualification stage registry."""
    registry = QualificationStageRegistry()
    registry.register(
        QualificationStage(
            stage_id="environment_isolation",
            name="Environment Isolation Verification",
            description="Validates staging target isolation and secret separation.",
            prerequisites=[],
            requires_live_staging=False,
            timeout_seconds=10.0,
            mandatory=True,
            approved=True,
        ),
        _run_environment_isolation_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="release_identity",
            name="Immutable Release Identity Verification",
            description="Validates 40-char commit SHA, repository identity, and manifest digests.",
            prerequisites=["environment_isolation"],
            requires_live_staging=False,
            timeout_seconds=10.0,
            mandatory=True,
            approved=True,
        ),
        _run_release_identity_stage,
    )
    registry.register(
        QualificationStage(
            stage_id="qualification_policy",
            name="Governance & Qualification Policy Verification",
            description="Validates V26 gate status and non-authorization governance invariants.",
            prerequisites=["environment_isolation", "release_identity"],
            requires_live_staging=False,
            timeout_seconds=10.0,
            mandatory=True,
            approved=True,
        ),
        _run_qualification_policy_stage,
    )
    return registry


# =============================================================================
# Controlled Staging Qualification Orchestrator
# =============================================================================


class StagingQualificationOrchestrator:
    """Executes the controlled 13-step staging qualification orchestration sequence."""

    def __init__(
        self,
        repo_root: Path | None = None,
        environment: str = "staging",
        commit_sha: str | None = None,
        repository: str | None = None,
        preflight_report: StagingPreflightReport | None = None,
        evidence_report: InfrastructureEvidenceReport | None = None,
        preflight_report_path: Path | None = None,
        evidence_report_path: Path | None = None,
        staging_api_url: str | None = None,
        staging_web_url: str | None = None,
        max_age_seconds: int = StagingReadinessGateEvaluator.DEFAULT_MAX_AGE_SECONDS,
        dry_run: bool = False,
        strict: bool = False,
        stage_registry: QualificationStageRegistry | None = None,
        approved_stage_ids: Sequence[str] | None = None,
        execution_mode: ExecutionMode = ExecutionMode.MOCKED,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env = env if env is not None else os.environ.copy()
        self.repo_root = (repo_root or StagingPreflightInspector._resolve_repo_root()).resolve()
        self.environment = environment
        self.commit_sha = commit_sha
        self.repository = repository
        self.preflight_report = preflight_report
        self.evidence_report = evidence_report
        self.preflight_report_path = preflight_report_path
        self.evidence_report_path = evidence_report_path
        self.staging_api_url = staging_api_url
        self.staging_web_url = staging_web_url
        self.max_age_seconds = max_age_seconds
        self.dry_run = dry_run
        self.strict = strict
        self.stage_registry = stage_registry or build_default_stage_registry()
        self.approved_stage_ids = (
            list(approved_stage_ids) if approved_stage_ids is not None else None
        )
        self.execution_mode = execution_mode

    @staticmethod
    def generate_run_id() -> str:
        """Generate a unique qualification run identifier."""
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"qual-{stamp}-{uuid.uuid4().hex[:8]}"

    def _resolve_commit_sha(self) -> str:
        """Resolve target commit SHA without falling back silently if explicitly passed empty."""
        if self.commit_sha is not None:
            return self.commit_sha.strip()
        inspector = StagingPreflightInspector(repo_root=self.repo_root, env=self.env)
        return inspector._resolve_commit_sha()

    def _early_halt_report(
        self,
        *,
        run_id: str,
        requested_at: str,
        started_at: str | None,
        commit_sha: str,
        repository: str,
        release_tag: str,
        env_model: QualificationEnvironment,
        status: QualificationStatus,
        started: bool,
        error_message: str,
        remediations: list[str] | None = None,
        preflight_status: CheckStatus = CheckStatus.NOT_RUN,
        evidence_status: CheckStatus = CheckStatus.NOT_RUN,
        gate_status: CheckStatus = CheckStatus.NOT_RUN,
        gate_passed: bool = False,
        gate_report: StagingGateEvaluationReport | None = None,
        evidence_items: list[QualificationEvidence] | None = None,
        failed_checks: list[str] | None = None,
        blocked_checks: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> StagingQualificationReport:
        """Construct a fail-closed early-halt qualification report."""
        completed_at = datetime.now(UTC).isoformat()
        safe_err = sanitize_text(error_message, self.env)
        is_blocked = status in (QualificationStatus.BLOCKED, QualificationStatus.NOT_CONFIGURED)
        is_failed = status == QualificationStatus.FAIL

        return StagingQualificationReport(
            schema_version="1.0.0",
            run_id=run_id,
            repository=repository,
            commit_sha=commit_sha,
            release_tag=release_tag,
            environment=env_model,
            run_metadata=QualificationRunMetadata(
                run_id=run_id,
                repository=repository,
                commit_sha=commit_sha,
                release_tag=release_tag,
                environment=self.environment.strip().lower() or "unknown",
                dry_run=self.dry_run,
                strict_mode=self.strict,
                requested_at=requested_at,
                started_at=started_at,
                completed_at=completed_at,
            ),
            overall_status=status,
            execution_mode=self.execution_mode,
            qualification_requested=True,
            qualification_started=started,
            qualification_completed=True,
            qualification_passed=False,
            qualification_blocked=is_blocked,
            qualification_failed=is_failed,
            live_qualification_authorized=False,
            production_deployment_authorized=False,
            production_deployment_performed=False,
            container_images_published=False,
            v26_preflight_status=preflight_status,
            v26_evidence_status=evidence_status,
            v26_gate_status=gate_status,
            v26_gate_passed=gate_passed,
            v26_gate_report=gate_report,
            evidence=evidence_items or [],
            failed_checks=failed_checks or ([safe_err] if is_failed else []),
            blocked_checks=blocked_checks or ([safe_err] if is_blocked else []),
            warnings=warnings or [],
            remediations=remediations or [],
            error_message=safe_err,
            metadata={
                "orchestrator": "StagingQualificationOrchestrator",
                "volume": "V27",
                "dry_run": self.dry_run,
            },
        )

    def _load_preflight_report(
        self, resolved_sha: str
    ) -> tuple[StagingPreflightReport | None, QualificationStatus, str | None]:
        """Step 4: Load V26 preflight report from instance, path, or local inspector."""
        if self.preflight_report is not None:
            return self.preflight_report, QualificationStatus.PASS, None

        if self.preflight_report_path is not None:
            if not self.preflight_report_path.is_file():
                return (
                    None,
                    QualificationStatus.BLOCKED,
                    f"V26 preflight report not found at {self.preflight_report_path}",
                )
            try:
                raw = self.preflight_report_path.read_text(encoding="utf-8")
                return (
                    StagingPreflightReport.model_validate_json(raw),
                    QualificationStatus.PASS,
                    None,
                )
            except Exception as exc:
                return (
                    None,
                    QualificationStatus.FAIL,
                    f"Malformed V26 preflight report: {sanitize_text(str(exc), self.env)}",
                )

        inspector = StagingPreflightInspector(
            repo_root=self.repo_root,
            commit_sha=resolved_sha,
            environment="staging",
            strict=self.strict,
            env=self.env,
        )
        return inspector.run_preflight(), QualificationStatus.PASS, None

    def _load_evidence_report(
        self, resolved_sha: str
    ) -> tuple[InfrastructureEvidenceReport | None, QualificationStatus, str | None]:
        """Step 5: Load V26 infrastructure evidence from instance, path, or collector."""
        if self.evidence_report is not None:
            return self.evidence_report, QualificationStatus.PASS, None

        if self.evidence_report_path is not None:
            if not self.evidence_report_path.is_file():
                return (
                    None,
                    QualificationStatus.BLOCKED,
                    f"V26 infrastructure evidence report not found at {self.evidence_report_path}",
                )
            try:
                raw = self.evidence_report_path.read_text(encoding="utf-8")
                return (
                    InfrastructureEvidenceReport.model_validate_json(raw),
                    QualificationStatus.PASS,
                    None,
                )
            except Exception as exc:
                return (
                    None,
                    QualificationStatus.FAIL,
                    f"Malformed V26 evidence report: {sanitize_text(str(exc), self.env)}",
                )

        collector = InfrastructureEvidenceCollector(
            repo_root=self.repo_root,
            commit_sha=resolved_sha,
            environment="staging",
            strict=self.strict,
            env=self.env,
        )
        return collector.collect_full_evidence(), QualificationStatus.PASS, None

    def _validate_credential_isolation(self) -> tuple[bool, str | None]:
        """Ensure staging credentials and database URLs never collide with production secrets."""
        staging_smoke_pw = (
            self.env.get("STAGING_SMOKE_PASSWORD") or self.env.get("SMOKE_TEST_PASSWORD") or ""
        ).strip()
        staging_db = (
            self.env.get("STAGING_DATABASE_URL") or self.env.get("REGIMEX_DATABASE_URL") or ""
        ).strip()
        staging_redis = (
            self.env.get("STAGING_REDIS_URL") or self.env.get("REGIMEX_REDIS_URL") or ""
        ).strip()

        prod_secrets = (
            self.env.get("PRODUCTION_SECRET_KEY", "").strip(),
            self.env.get("PRODUCTION_API_TOKEN", "").strip(),
            self.env.get("PROD_DATABASE_URL", "").strip(),
            self.env.get("PROD_REDIS_URL", "").strip(),
        )

        if staging_smoke_pw and any(p and staging_smoke_pw == p for p in prod_secrets):
            return False, "Staging smoke password collides with production credential"
        if staging_db and any(p and staging_db == p for p in prod_secrets):
            return False, "Staging database URL collides with production database credential"
        if staging_redis and any(p and staging_redis == p for p in prod_secrets):
            return False, "Staging Redis URL collides with production Redis credential"

        return True, None

    def _execute_stage_bounded(
        self,
        entry: RegisteredQualificationStage,
        ctx: QualificationContext,
    ) -> QualificationStageResult:
        """Execute a single approved stage with bounded timeout and secret-safe errors."""
        started_at = datetime.now(UTC).isoformat()
        t0 = time.monotonic()
        defn = entry.definition

        if self.dry_run and defn.requires_live_staging:
            check_res = QualificationCheckResult(
                check_id=f"{defn.stage_id}.dry_run",
                stage_id=defn.stage_id,
                name=defn.name,
                status=QualificationStatus.NOT_RUN,
                mandatory=defn.mandatory,
                message="Dry-run mode: live staging network execution skipped",
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
                duration_seconds=0.0,
                details={"dry_run": True, "requires_live_staging": True},
            )
            return QualificationStageResult(
                stage_id=defn.stage_id,
                name=defn.name,
                status=QualificationStatus.NOT_RUN,
                mandatory=defn.mandatory,
                requires_live_staging=defn.requires_live_staging,
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
                duration_seconds=0.0,
                checks=[check_res],
                message="Dry-run mode: live staging stage skipped without network requests",
            )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(entry.handler, ctx)
                result = future.result(timeout=defn.timeout_seconds)
        except concurrent.futures.TimeoutError:
            duration = round(time.monotonic() - t0, 4)
            err_msg = (
                f"Qualification stage '{defn.stage_id}' timed out after {defn.timeout_seconds}s"
            )
            return QualificationStageResult(
                stage_id=defn.stage_id,
                name=defn.name,
                status=QualificationStatus.FAIL,
                mandatory=defn.mandatory,
                requires_live_staging=defn.requires_live_staging,
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
                duration_seconds=duration,
                checks=[
                    QualificationCheckResult(
                        check_id=f"{defn.stage_id}.timeout",
                        stage_id=defn.stage_id,
                        name=defn.name,
                        status=QualificationStatus.FAIL,
                        mandatory=defn.mandatory,
                        message=err_msg,
                        started_at=started_at,
                        completed_at=datetime.now(UTC).isoformat(),
                        duration_seconds=duration,
                        error=err_msg,
                    )
                ],
                message=err_msg,
                error=err_msg,
            )
        except Exception as exc:
            duration = round(time.monotonic() - t0, 4)
            safe_err = sanitize_text(str(exc), self.env)
            return QualificationStageResult(
                stage_id=defn.stage_id,
                name=defn.name,
                status=QualificationStatus.FAIL,
                mandatory=defn.mandatory,
                requires_live_staging=defn.requires_live_staging,
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat(),
                duration_seconds=duration,
                checks=[
                    QualificationCheckResult(
                        check_id=f"{defn.stage_id}.exception",
                        stage_id=defn.stage_id,
                        name=defn.name,
                        status=QualificationStatus.FAIL,
                        mandatory=defn.mandatory,
                        message=f"Stage raised an exception: {safe_err}",
                        started_at=started_at,
                        completed_at=datetime.now(UTC).isoformat(),
                        duration_seconds=duration,
                        error=safe_err,
                    )
                ],
                message=f"Stage failed unexpectedly: {safe_err}",
                error=safe_err,
            )

        # Sanitize all returned stage and check fields
        sanitized_checks = [
            chk.model_copy(
                update={
                    "message": sanitize_text(chk.message, self.env),
                    "error": sanitize_text(chk.error, self.env) if chk.error else None,
                    "remediation": (
                        sanitize_text(chk.remediation, self.env) if chk.remediation else None
                    ),
                    "details": sanitize_mapping(chk.details, self.env),
                }
            )
            for chk in result.checks
        ]
        return result.model_copy(
            update={
                "message": sanitize_text(result.message, self.env),
                "error": sanitize_text(result.error, self.env) if result.error else None,
                "checks": sanitized_checks,
            }
        )

    def run_qualification(self) -> StagingQualificationReport:
        """Execute the 13-step controlled staging qualification orchestration."""
        run_id = self.generate_run_id()
        requested_at = datetime.now(UTC).isoformat()
        raw_sha = self._resolve_commit_sha()
        resolved_repo = (
            self.repository.strip()
            if self.repository is not None
            else self.env.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY).strip()
        )
        release_tag = f"regimex-{raw_sha[:8]}" if validate_commit_sha(raw_sha) else "unknown"
        base_env_model = QualificationEnvironment(
            name=self.environment.strip().lower() or "unknown",
            isolated_from_production=not _is_production_environment(self.environment),
        )

        # ---------------------------------------------------------------------
        # Step 1: Validate requested environment
        # ---------------------------------------------------------------------
        env_norm = self.environment.strip().lower()
        if _is_production_environment(env_norm):
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=None,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=False,
                error_message=(
                    f"Production environment '{self.environment}' rejected: staging qualification "
                    "must never target production."
                ),
                remediations=["Run qualification explicitly with --environment staging."],
            )
        if env_norm not in ALLOWED_STAGING_ENVIRONMENTS:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=None,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=False,
                error_message=(
                    f"Invalid environment '{self.environment}': only 'staging' is permitted."
                ),
                remediations=["Specify --environment staging."],
            )

        # ---------------------------------------------------------------------
        # Step 2: Validate repository identity
        # ---------------------------------------------------------------------
        if resolved_repo != EXPECTED_REPOSITORY:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=None,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=False,
                error_message=(
                    f"Repository identity mismatch: expected '{EXPECTED_REPOSITORY}', "
                    f"got '{resolved_repo}'."
                ),
                remediations=[f"Verify repository identity is '{EXPECTED_REPOSITORY}'."],
            )

        # ---------------------------------------------------------------------
        # Step 3: Validate full 40-character commit SHA
        # ---------------------------------------------------------------------
        if not validate_commit_sha(raw_sha):
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=None,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag="unknown",
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=False,
                error_message=(
                    f"Invalid commit SHA '{raw_sha}': expected a 40-character hexadecimal SHA."
                ),
                remediations=["Pass a valid 40-character commit SHA via --commit-sha."],
            )

        started_at = datetime.now(UTC).isoformat()

        # ---------------------------------------------------------------------
        # Step 4: Load V26 preflight report
        # ---------------------------------------------------------------------
        preflight, pf_load_status, pf_err = self._load_preflight_report(raw_sha)
        if preflight is None:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=pf_load_status,
                started=True,
                error_message=pf_err or "V26 preflight report unavailable",
                remediations=["Run scripts/staging_preflight.py to generate a valid report."],
            )

        if preflight.repository != EXPECTED_REPOSITORY:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                error_message=(
                    f"V26 preflight repository mismatch: expected '{EXPECTED_REPOSITORY}', "
                    f"found '{preflight.repository}'."
                ),
                remediations=["Regenerate V26 preflight report for luccy93/RegimeX."],
            )

        if preflight.commit_sha.lower() != raw_sha.lower():
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                error_message=(
                    f"V26 preflight commit SHA mismatch: requested '{raw_sha}', "
                    f"report has '{preflight.commit_sha}'."
                ),
                remediations=["Regenerate V26 preflight report for the target commit SHA."],
            )

        # ---------------------------------------------------------------------
        # Step 5: Load V26 infrastructure evidence report
        # ---------------------------------------------------------------------
        evidence, ev_load_status, ev_err = self._load_evidence_report(raw_sha)
        if evidence is None:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=ev_load_status,
                started=True,
                preflight_status=preflight.overall_status,
                error_message=ev_err or "V26 infrastructure evidence report unavailable",
                remediations=["Run scripts/staging_evidence.py to collect V26 evidence."],
            )

        if evidence.repository != EXPECTED_REPOSITORY:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                error_message=(
                    f"V26 evidence repository mismatch: expected '{EXPECTED_REPOSITORY}', "
                    f"found '{evidence.repository}'."
                ),
                remediations=["Regenerate V26 infrastructure evidence for luccy93/RegimeX."],
            )

        if evidence.commit_sha.lower() != raw_sha.lower():
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                error_message=(
                    f"V26 evidence commit SHA mismatch: requested '{raw_sha}', "
                    f"report has '{evidence.commit_sha}'."
                ),
                remediations=["Collect V26 infrastructure evidence for the target commit SHA."],
            )

        # ---------------------------------------------------------------------
        # Step 6: Evaluate V26 readiness gates
        # ---------------------------------------------------------------------
        gate_evaluator = StagingReadinessGateEvaluator(
            repo_root=self.repo_root,
            max_age_seconds=self.max_age_seconds,
            strict=self.strict,
            env=self.env,
        )
        gate_report = gate_evaluator.evaluate_gates(preflight=preflight, evidence=evidence)

        v26_evidence_items = [
            QualificationEvidence(
                evidence_id="v26-preflight",
                source="StagingPreflightInspector",
                timestamp=preflight.timestamp,
                commit_sha=preflight.commit_sha,
                repository=preflight.repository,
                environment=preflight.environment,
                status=QualificationStatus(preflight.overall_status.value),
                is_live=False,
                is_fresh=gate_report.evidence_is_fresh,
                details={"is_ready": preflight.is_ready},
            ),
            QualificationEvidence(
                evidence_id="v26-infrastructure-evidence",
                source="InfrastructureEvidenceCollector",
                timestamp=evidence.timestamp,
                commit_sha=evidence.commit_sha,
                repository=evidence.repository,
                environment=evidence.environment,
                status=QualificationStatus(evidence.overall_status.value),
                is_live=False,
                freshness_seconds=gate_report.evidence_freshness_seconds,
                is_fresh=gate_report.evidence_is_fresh,
                details={"is_ready": evidence.is_ready},
            ),
            QualificationEvidence(
                evidence_id="v26-readiness-gates",
                source="StagingReadinessGateEvaluator",
                timestamp=gate_report.evaluated_at,
                commit_sha=gate_report.commit_sha,
                repository=gate_report.repository,
                environment=gate_report.environment,
                status=QualificationStatus(gate_report.overall_status.value),
                is_live=False,
                freshness_seconds=gate_report.evidence_freshness_seconds,
                is_fresh=gate_report.evidence_is_fresh,
                details={"is_ready": gate_report.is_ready},
            ),
        ]

        if not gate_report.is_ready:
            mapped_gate_status = QualificationStatus(gate_report.overall_status.value)
            if mapped_gate_status == QualificationStatus.WARNING:
                mapped_gate_status = QualificationStatus.FAIL
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=base_env_model,
                status=mapped_gate_status,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                gate_status=gate_report.overall_status,
                gate_passed=False,
                gate_report=gate_report,
                evidence_items=v26_evidence_items,
                failed_checks=list(gate_report.failed_policies),
                blocked_checks=list(gate_report.blocked_policies),
                warnings=list(gate_report.warnings),
                remediations=list(gate_report.remediations),
                error_message=(
                    f"V26 readiness gates did not pass "
                    f"(status={gate_report.overall_status.value}); staging qualification aborted."
                ),
            )

        # ---------------------------------------------------------------------
        # Step 7: Validate staging target configuration (strict isolation)
        # ---------------------------------------------------------------------
        api_url = (
            self.staging_api_url
            if self.staging_api_url is not None
            else self.env.get("STAGING_API_URL")
        )
        web_url = (
            self.staging_web_url
            if self.staging_web_url is not None
            else self.env.get("STAGING_WEB_URL")
        )
        db_configured = bool(
            (
                self.env.get("STAGING_DATABASE_URL") or self.env.get("REGIMEX_DATABASE_URL") or ""
            ).strip()
        )
        redis_configured = bool(
            (self.env.get("STAGING_REDIS_URL") or self.env.get("REGIMEX_REDIS_URL") or "").strip()
        )
        smoke_creds_configured = evidence.smoke_credentials.status == CheckStatus.PASS

        env_model = QualificationEnvironment(
            name="staging",
            api_url=sanitize_text(api_url.strip(), self.env) if api_url else None,
            web_url=sanitize_text(web_url.strip(), self.env) if web_url else None,
            database_configured=db_configured,
            redis_configured=redis_configured,
            smoke_credentials_configured=smoke_creds_configured,
            isolated_from_production=True,
        )

        cred_ok, cred_err = self._validate_credential_isolation()
        if not cred_ok:
            env_model = env_model.model_copy(update={"isolated_from_production": False})
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                gate_status=gate_report.overall_status,
                gate_passed=True,
                gate_report=gate_report,
                evidence_items=v26_evidence_items,
                error_message=cred_err or "Production credential isolation violation",
                remediations=["Use strictly isolated credentials for staging qualification."],
            )

        if not api_url or not api_url.strip() or not web_url or not web_url.strip():
            missing_targets: list[str] = []
            if not api_url or not api_url.strip():
                missing_targets.append("STAGING_API_URL")
            if not web_url or not web_url.strip():
                missing_targets.append("STAGING_WEB_URL")
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=env_model,
                status=QualificationStatus.NOT_CONFIGURED,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                gate_status=gate_report.overall_status,
                gate_passed=True,
                gate_report=gate_report,
                evidence_items=v26_evidence_items,
                error_message=(
                    f"Missing staging target configuration: {', '.join(missing_targets)}"
                ),
                remediations=[
                    "Explicitly configure STAGING_API_URL and STAGING_WEB_URL "
                    "(never falls back to production)."
                ],
            )

        for label, url_val in (("STAGING_API_URL", api_url), ("STAGING_WEB_URL", web_url)):
            url_ok, url_err = _validate_target_url(url_val, label, self.env)
            if not url_ok:
                is_prod_rej = bool(url_err and "Production target rejected" in url_err)
                env_model = env_model.model_copy(
                    update={"isolated_from_production": not is_prod_rej}
                )
                return self._early_halt_report(
                    run_id=run_id,
                    requested_at=requested_at,
                    started_at=started_at,
                    commit_sha=raw_sha,
                    repository=resolved_repo,
                    release_tag=release_tag,
                    env_model=env_model,
                    status=QualificationStatus.FAIL,
                    started=True,
                    preflight_status=preflight.overall_status,
                    evidence_status=evidence.overall_status,
                    gate_status=gate_report.overall_status,
                    gate_passed=True,
                    gate_report=gate_report,
                    evidence_items=v26_evidence_items,
                    error_message=url_err or f"Invalid {label}",
                    remediations=[f"Provide a valid non-production HTTP/HTTPS URL for {label}."],
                )

        # ---------------------------------------------------------------------
        # Step 8 & 9: Validate release identity and qualification policy
        # ---------------------------------------------------------------------
        sel_ok, selected_stages, sel_err = self.stage_registry.validate_selection(
            self.approved_stage_ids
        )
        if not sel_ok:
            return self._early_halt_report(
                run_id=run_id,
                requested_at=requested_at,
                started_at=started_at,
                commit_sha=raw_sha,
                repository=resolved_repo,
                release_tag=release_tag,
                env_model=env_model,
                status=QualificationStatus.FAIL,
                started=True,
                preflight_status=preflight.overall_status,
                evidence_status=evidence.overall_status,
                gate_status=gate_report.overall_status,
                gate_passed=True,
                gate_report=gate_report,
                evidence_items=v26_evidence_items,
                error_message=sel_err or "Qualification stage policy validation failed",
                remediations=["Execute only explicitly approved stages in the stage registry."],
            )

        # ---------------------------------------------------------------------
        # Step 10: Execute only explicitly approved qualification stages
        # ---------------------------------------------------------------------
        ctx = QualificationContext(
            run_id=run_id,
            environment="staging",
            repository=resolved_repo,
            commit_sha=raw_sha,
            release_tag=release_tag,
            dry_run=self.dry_run,
            strict=self.strict,
            env=self.env,
            preflight_report=preflight,
            evidence_report=evidence,
            gate_report=gate_report,
            staging_api_url=api_url.strip(),
            staging_web_url=web_url.strip(),
            execution_mode=self.execution_mode,
        )

        stage_results: list[QualificationStageResult] = []
        stage_status_map: dict[str, QualificationStatus] = {}
        all_checks: list[QualificationCheckResult] = []

        for entry in selected_stages:
            defn = entry.definition
            unmet_prereqs = [
                p for p in defn.prerequisites if stage_status_map.get(p) != QualificationStatus.PASS
            ]
            if unmet_prereqs:
                blocked_msg = (
                    f"Stage '{defn.stage_id}' blocked by prerequisite(s): "
                    f"{', '.join(unmet_prereqs)}"
                )
                blocked_res = QualificationStageResult(
                    stage_id=defn.stage_id,
                    name=defn.name,
                    status=QualificationStatus.BLOCKED,
                    mandatory=defn.mandatory,
                    requires_live_staging=defn.requires_live_staging,
                    started_at=datetime.now(UTC).isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    duration_seconds=0.0,
                    checks=[],
                    message=blocked_msg,
                    error=blocked_msg,
                )
                stage_results.append(blocked_res)
                stage_status_map[defn.stage_id] = QualificationStatus.BLOCKED
                continue

            s_res = self._execute_stage_bounded(entry, ctx)
            stage_results.append(s_res)
            stage_status_map[defn.stage_id] = s_res.status
            all_checks.extend(s_res.checks)

        # ---------------------------------------------------------------------
        # Step 11: Collect evidence
        # ---------------------------------------------------------------------
        evidence_items = list(v26_evidence_items)
        for s_res in stage_results:
            evidence_items.append(
                QualificationEvidence(
                    evidence_id=f"stage-{s_res.stage_id}",
                    source=f"QualificationStage:{s_res.stage_id}",
                    timestamp=s_res.completed_at or datetime.now(UTC).isoformat(),
                    commit_sha=raw_sha,
                    repository=resolved_repo,
                    environment="staging",
                    status=s_res.status,
                    execution_mode=(ExecutionMode.MOCKED if self.dry_run else self.execution_mode),
                    is_live=(
                        s_res.requires_live_staging
                        and not self.dry_run
                        and self.execution_mode == ExecutionMode.LIVE_STAGING
                        and s_res.status != QualificationStatus.NOT_RUN
                    ),
                    is_fresh=True,
                    details={"checks_count": len(s_res.checks)},
                )
            )

        # ---------------------------------------------------------------------
        # Step 12: Evaluate qualification results
        # ---------------------------------------------------------------------
        failed_checks: list[str] = []
        blocked_checks: list[str] = []
        warnings: list[str] = list(gate_report.warnings)
        remediations: list[str] = []

        for s_res in stage_results:
            if s_res.status == QualificationStatus.FAIL and s_res.mandatory:
                failed_checks.append(f"{s_res.stage_id}: {s_res.message}")
            elif s_res.status == QualificationStatus.BLOCKED and s_res.mandatory:
                blocked_checks.append(f"{s_res.stage_id}: {s_res.message}")
            elif s_res.status == QualificationStatus.NOT_CONFIGURED and s_res.mandatory:
                blocked_checks.append(f"{s_res.stage_id}: {s_res.message}")
            elif s_res.status == QualificationStatus.WARNING:
                warnings.append(f"{s_res.stage_id}: {s_res.message}")

            for chk in s_res.checks:
                if chk.status == QualificationStatus.FAIL and chk.mandatory:
                    msg = f"{chk.check_id}: {chk.message}"
                    if msg not in failed_checks:
                        failed_checks.append(msg)
                elif (
                    chk.status in (QualificationStatus.BLOCKED, QualificationStatus.NOT_CONFIGURED)
                    and chk.mandatory
                ):
                    msg = f"{chk.check_id}: {chk.message}"
                    if msg not in blocked_checks:
                        blocked_checks.append(msg)
                elif chk.status == QualificationStatus.WARNING:
                    msg = f"{chk.check_id}: {chk.message}"
                    if msg not in warnings:
                        warnings.append(msg)
                if chk.remediation and chk.remediation not in remediations:
                    remediations.append(chk.remediation)

        mandatory_statuses = [s.status for s in stage_results if s.mandatory]
        has_not_run_mandatory = any(st == QualificationStatus.NOT_RUN for st in mandatory_statuses)

        if any(st == QualificationStatus.FAIL for st in mandatory_statuses) or failed_checks:
            overall_status = QualificationStatus.FAIL
        elif any(st == QualificationStatus.BLOCKED for st in mandatory_statuses):
            overall_status = QualificationStatus.BLOCKED
        elif any(st == QualificationStatus.NOT_CONFIGURED for st in mandatory_statuses):
            overall_status = QualificationStatus.NOT_CONFIGURED
        elif self.strict and warnings:
            overall_status = QualificationStatus.FAIL
        elif has_not_run_mandatory:
            overall_status = QualificationStatus.NOT_RUN
        elif warnings:
            overall_status = QualificationStatus.WARNING
        else:
            overall_status = QualificationStatus.PASS

        completed_at = datetime.now(UTC).isoformat()
        qualification_passed = (
            not self.dry_run
            and overall_status in (QualificationStatus.PASS, QualificationStatus.WARNING)
            and not failed_checks
            and not blocked_checks
        )
        qualification_blocked = overall_status in (
            QualificationStatus.BLOCKED,
            QualificationStatus.NOT_CONFIGURED,
        )
        qualification_failed = overall_status == QualificationStatus.FAIL

        # ---------------------------------------------------------------------
        # Step 13: Generate final qualification report
        # ---------------------------------------------------------------------
        return StagingQualificationReport(
            schema_version="1.0.0",
            run_id=run_id,
            repository=resolved_repo,
            commit_sha=raw_sha,
            release_tag=release_tag,
            environment=env_model,
            run_metadata=QualificationRunMetadata(
                run_id=run_id,
                repository=resolved_repo,
                commit_sha=raw_sha,
                release_tag=release_tag,
                environment="staging",
                dry_run=self.dry_run,
                strict_mode=self.strict,
                requested_at=requested_at,
                started_at=started_at,
                completed_at=completed_at,
            ),
            overall_status=overall_status,
            execution_mode=self.execution_mode,
            qualification_requested=True,
            qualification_started=True,
            qualification_completed=True,
            qualification_passed=qualification_passed,
            qualification_blocked=qualification_blocked,
            qualification_failed=qualification_failed,
            live_qualification_authorized=False,
            production_deployment_authorized=False,
            production_deployment_performed=False,
            container_images_published=False,
            v26_preflight_status=preflight.overall_status,
            v26_evidence_status=evidence.overall_status,
            v26_gate_status=gate_report.overall_status,
            v26_gate_passed=gate_report.is_ready,
            v26_gate_report=gate_report,
            stages=stage_results,
            checks=all_checks,
            evidence=evidence_items,
            failed_checks=failed_checks,
            blocked_checks=blocked_checks,
            warnings=warnings,
            remediations=remediations,
            error_message=None,
            metadata={
                "orchestrator": "StagingQualificationOrchestrator",
                "volume": "V27",
                "dry_run": self.dry_run,
                "stages_executed": len(stage_results),
            },
        )
