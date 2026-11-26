"""Pydantic schemas and domain models for RegimeX staging readiness preflight.

Defines check statuses, category summaries, infrastructure evidence models, and
the machine-readable preflight report schema.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CheckStatus(StrEnum):
    """Evaluation status for an individual readiness check or category."""

    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_RUN = "NOT_RUN"
    WARNING = "WARNING"


class CheckCategory(StrEnum):
    """Categorization for staging readiness checks."""

    HOST = "host"
    RUNTIME = "runtime"
    SECURITY = "security"
    RELEASE = "release"


class AuthStatus(StrEnum):
    """Authentication and access status for external registries and VCS."""

    AUTHENTICATED = "AUTHENTICATED"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class CheckResult(BaseModel):
    """Result of an individual readiness verification check."""

    model_config = ConfigDict(extra="forbid")

    name: str
    category: str
    status: CheckStatus
    mandatory: bool = True
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    remediation: str | None = None


class CategorySummary(BaseModel):
    """Aggregated summary for a category of staging readiness checks."""

    model_config = ConfigDict(extra="forbid")

    category: str
    status: CheckStatus
    total_checks: int
    passed_checks: int
    failed_checks: int
    blocked_checks: int
    warning_checks: int
    not_configured_checks: int
    not_run_checks: int
    checks: list[CheckResult] = Field(default_factory=list)


class StagingPreflightReport(BaseModel):
    """Machine-readable report summarizing staging readiness preflight."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    environment: str = "staging"
    repository: str
    commit_sha: str
    branch: str | None = None
    timestamp: str
    overall_status: CheckStatus
    is_ready: bool
    strict_mode: bool = False
    host: CategorySummary
    runtime: CategorySummary
    security: CategorySummary
    release: CategorySummary
    failed_checks: list[str] = Field(default_factory=list)
    blocked_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remediations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Render report as formatted JSON string."""
        return self.model_dump_json(indent=indent)


class ReadinessEvidence(BaseModel):
    """Base model for component-level staging readiness evidence."""

    model_config = ConfigDict(extra="forbid")

    status: CheckStatus
    details: dict[str, Any] = Field(default_factory=dict)
    remediation: str | None = None


class DockerReadinessEvidence(ReadinessEvidence):
    """Concrete evidence gathered from staging Docker engine and Compose."""

    engine_accessible: bool
    engine_version: str | None = None
    compose_available: bool
    compose_version: str | None = None
    storage_driver: str | None = None
    available_storage_gb: float | None = None
    ports_available: dict[int, bool] = Field(default_factory=dict)
    volumes_ready: bool = False
    healthcheck_support: bool = True


class GitHubAccessEvidence(ReadinessEvidence):
    """Evidence of GitHub repository access and API authorization."""

    cli_available: bool
    auth_status: AuthStatus
    account: str | None = None
    repository_accessible: bool = False
    read_permission: bool = False


class GHCRAccessEvidence(ReadinessEvidence):
    """Evidence of GitHub Container Registry (GHCR) pull access."""

    registry_url: str = "ghcr.io"
    auth_status: AuthStatus
    pull_capability_verified: bool = False


class ReleaseManifestEvidence(ReadinessEvidence):
    """Verification evidence for release manifest authenticity and immutable digests."""

    manifest_path: str | None = None
    commit_sha: str | None = None
    repository: str | None = None
    images: dict[str, str] = Field(default_factory=dict)
    immutable_digests_verified: bool = False
    provenance_verified: bool = False


class SmokeCredentialEvidence(ReadinessEvidence):
    """Verification of staging smoke-test credentials and secret isolation."""

    username_configured: bool = False
    password_configured: bool = False
    credentials_masked: bool = True
    production_secret_leak_detected: bool = False


class RollbackReadinessEvidence(ReadinessEvidence):
    """Verification of backup procedures, recovery runbooks, and rollback state."""

    backup_configured: bool = False
    backup_directory_ready: bool = False
    recovery_runbook_verified: bool = False
    previous_release_identified: bool = False
    previous_release_sha: str | None = None
    forward_only_migration_policy_verified: bool = True


class GPUCapabilityEvidence(ReadinessEvidence):
    """Honest evaluation of optional GPU capability on the staging host."""

    mandatory: bool = False
    gpu_available: bool = False
    device_count: int = 0
    device_names: list[str] = Field(default_factory=list)
    driver_version: str | None = None
    cuda_version: str | None = None
    container_toolkit_detected: bool = False


class InfrastructureEvidenceReport(BaseModel):
    """Machine-readable report summarizing all staging infrastructure readiness evidence."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    environment: str = "staging"
    repository: str
    commit_sha: str
    timestamp: str
    overall_status: CheckStatus
    is_ready: bool = False
    strict_mode: bool = False
    live_qualification_authorized: bool = False
    production_deployment_authorized: bool = False
    docker: DockerReadinessEvidence
    github: GitHubAccessEvidence
    ghcr: GHCRAccessEvidence
    release_manifest: ReleaseManifestEvidence
    smoke_credentials: SmokeCredentialEvidence
    rollback: RollbackReadinessEvidence
    gpu: GPUCapabilityEvidence
    failed_checks: list[str] = Field(default_factory=list)
    blocked_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remediations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Render report as formatted JSON string."""
        return self.model_dump_json(indent=indent)


class GatePolicyResult(BaseModel):
    """Result of an individual readiness gate policy evaluation."""

    model_config = ConfigDict(extra="forbid")

    policy_id: str
    policy_name: str
    status: CheckStatus
    mandatory: bool = True
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    remediation: str | None = None


class StagingGateEvaluationReport(BaseModel):
    """Auditable, machine-readable report summarizing unified staging gate evaluations."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    environment: str = "staging"
    repository: str
    commit_sha: str
    evaluated_at: str
    overall_status: CheckStatus
    is_ready: bool = False
    strict_mode: bool = False
    live_qualification_authorized: bool = False
    production_deployment_authorized: bool = False
    preflight_evaluated: bool = False
    evidence_evaluated: bool = False
    evidence_freshness_seconds: float | None = None
    evidence_is_fresh: bool = False
    gate_policies: list[GatePolicyResult] = Field(default_factory=list)
    failed_policies: list[str] = Field(default_factory=list)
    blocked_policies: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remediations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Render report as formatted JSON string."""
        return self.model_dump_json(indent=indent)


# =============================================================================
# Volume V27 — Staging Qualification Domain Models
# =============================================================================


class QualificationStatus(StrEnum):
    """Explicit evaluation status for staging qualification checks and runs."""

    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_RUN = "NOT_RUN"
    WARNING = "WARNING"


class QualificationEnvironment(BaseModel):
    """Validated staging target environment configuration (isolated from production)."""

    model_config = ConfigDict(extra="forbid")

    name: str = "staging"
    api_url: str | None = None
    web_url: str | None = None
    database_configured: bool = False
    redis_configured: bool = False
    smoke_credentials_configured: bool = False
    isolated_from_production: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class QualificationRunMetadata(BaseModel):
    """Immutable run identity and lifecycle timestamps for a qualification execution."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    repository: str
    commit_sha: str
    release_tag: str
    environment: str = "staging"
    dry_run: bool = False
    strict_mode: bool = False
    requested_at: str
    started_at: str | None = None
    completed_at: str | None = None


class QualificationCheck(BaseModel):
    """Definition of an approved, bounded qualification check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    stage_id: str
    name: str
    description: str = ""
    mandatory: bool = True
    requires_live_staging: bool = True
    timeout_seconds: float = 15.0


class QualificationCheckResult(BaseModel):
    """Structured, secret-redacted result of a single qualification check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    stage_id: str
    name: str
    status: QualificationStatus
    mandatory: bool = True
    environment: str = "staging"
    commit_sha: str = ""
    message: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float = 0.0
    http_status: int | None = None
    evidence_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    remediation: str | None = None


class QualificationStage(BaseModel):
    """Definition of an approved qualification stage in the stage registry."""

    model_config = ConfigDict(extra="forbid")

    stage_id: str
    name: str
    description: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    requires_live_staging: bool = True
    timeout_seconds: float = 30.0
    mandatory: bool = True
    approved: bool = True


class QualificationStageResult(BaseModel):
    """Structured execution outcome of a single qualification stage."""

    model_config = ConfigDict(extra="forbid")

    stage_id: str
    name: str
    status: QualificationStatus
    mandatory: bool = True
    requires_live_staging: bool = True
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float = 0.0
    checks: list[QualificationCheckResult] = Field(default_factory=list)
    message: str = ""
    error: str | None = None


class QualificationEvidence(BaseModel):
    """Auditable evidence artifact collected during staging qualification."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    timestamp: str
    commit_sha: str
    repository: str
    environment: str
    status: QualificationStatus
    is_live: bool = False
    freshness_seconds: float | None = None
    is_fresh: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class StagingQualificationReport(BaseModel):
    """Auditable, machine-readable report for controlled staging qualification."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    run_id: str
    repository: str
    commit_sha: str
    release_tag: str
    environment: QualificationEnvironment
    run_metadata: QualificationRunMetadata
    overall_status: QualificationStatus
    qualification_requested: bool = True
    qualification_started: bool = False
    qualification_completed: bool = False
    qualification_passed: bool = False
    qualification_blocked: bool = False
    qualification_failed: bool = False
    live_qualification_authorized: bool = False
    production_deployment_authorized: bool = False
    production_deployment_performed: bool = False
    container_images_published: bool = False
    v26_preflight_status: CheckStatus = CheckStatus.NOT_RUN
    v26_evidence_status: CheckStatus = CheckStatus.NOT_RUN
    v26_gate_status: CheckStatus = CheckStatus.NOT_RUN
    v26_gate_passed: bool = False
    v26_gate_report: StagingGateEvaluationReport | None = None
    stages: list[QualificationStageResult] = Field(default_factory=list)
    checks: list[QualificationCheckResult] = Field(default_factory=list)
    evidence: list[QualificationEvidence] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    blocked_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remediations: list[str] = Field(default_factory=list)
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Render report as formatted JSON string."""
        return self.model_dump_json(indent=indent)
