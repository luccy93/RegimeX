"""RegimeX — Staging Readiness Gate Evaluator.

apps/api/app/core/staging_gates.py
==================================
Hardens staging readiness gates by unifying preflight prerequisites and concrete
infrastructure evidence into a cohesive, fail-closed gate policy evaluation.

Invariants:
- Evaluates freshness and integrity of collected qualification evidence.
- Stale or expired evidence reports fail the integrity gate.
- Commit SHA mismatch between preflight and evidence fails closed.
- Strict enforcement of Volume V26 governance boundaries:
  `live_qualification_authorized` and `production_deployment_authorized`
  MUST REMAIN FALSE.
- All 6 core gate policies must be satisfied for staging readiness qualification.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.deployment import validate_commit_sha
from app.core.staging_readiness import StagingPreflightInspector
from app.schemas.staging_readiness import (
    CheckStatus,
    GatePolicyResult,
    InfrastructureEvidenceReport,
    StagingGateEvaluationReport,
    StagingPreflightReport,
)

logger = logging.getLogger("regimex.staging_gates")


class StagingReadinessGateEvaluator:
    """Evaluates unified readiness gate policies across preflight and infrastructure evidence."""

    DEFAULT_MAX_AGE_SECONDS = 3600  # 1 hour maximum evidence validity

    def __init__(
        self,
        repo_root: Path | None = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
        strict: bool = False,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env = env if env is not None else os.environ.copy()
        self.repo_root = (repo_root or StagingPreflightInspector._resolve_repo_root()).resolve()
        self.max_age_seconds = max_age_seconds
        self.strict = strict

    def validate_evidence_freshness(self, timestamp_str: str) -> tuple[bool, float, str]:
        """Validate whether evidence report timestamp is within the freshness window."""
        try:
            # Handle ISO formats with or without Z
            clean_ts = timestamp_str.replace("Z", "+00:00")
            recorded_time = datetime.fromisoformat(clean_ts)
            if recorded_time.tzinfo is None:
                recorded_time = recorded_time.replace(tzinfo=UTC)

            now_utc = datetime.now(UTC)
            age_seconds = (now_utc - recorded_time).total_seconds()

            if age_seconds < -30:
                # Clock skew in future
                skew_sec = abs(round(age_seconds, 1))
                return (
                    False,
                    age_seconds,
                    f"Evidence timestamp is in the future by {skew_sec}s (clock skew)",
                )

            effective_age = max(0.0, age_seconds)
            age_disp = round(effective_age, 1)
            if effective_age <= self.max_age_seconds:
                return (
                    True,
                    effective_age,
                    f"Evidence is fresh ({age_disp}s old <= {self.max_age_seconds}s limit)",
                )

            return (
                False,
                effective_age,
                f"Evidence is stale ({age_disp}s old > {self.max_age_seconds}s limit)",
            )
        except Exception as exc:
            return (False, 0.0, f"Invalid evidence timestamp format '{timestamp_str}': {exc}")

    def _evaluate_policy_preflight(self, preflight: StagingPreflightReport) -> GatePolicyResult:
        """Gate Policy 1: Host and Runtime Prerequisites Gate."""
        policy_id = "GATE-HOST-RUNTIME"
        policy_name = "Host & Runtime Prerequisites Gate"

        if preflight.overall_status == CheckStatus.FAIL:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Preflight prerequisites check reported FAIL",
                details={
                    "failed_checks": preflight.failed_checks,
                    "host_status": preflight.host.status.value,
                    "runtime_status": preflight.runtime.status.value,
                },
                remediation="Resolve all failing host/runtime checks reported in preflight",
            )

        if preflight.overall_status == CheckStatus.BLOCKED:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.BLOCKED,
                mandatory=True,
                message="Preflight prerequisites check reported BLOCKED",
                details={"blocked_checks": preflight.blocked_checks},
                remediation="Unblock required host dependencies (e.g. Docker daemon)",
            )

        if preflight.overall_status == CheckStatus.NOT_CONFIGURED:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.NOT_CONFIGURED,
                mandatory=True,
                message="Mandatory runtime environment variables are unconfigured",
                details={"remediations": preflight.remediations},
                remediation="Configure required staging environment variables (e.g. database URL)",
            )

        if preflight.overall_status == CheckStatus.WARNING and self.strict:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Preflight warnings escalated to failure in strict mode",
                details={"warnings": preflight.warnings},
                remediation="Resolve all advisory warnings for strict gate pass",
            )

        status = CheckStatus.PASS
        if preflight.overall_status == CheckStatus.WARNING:
            status = CheckStatus.WARNING

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=status,
            mandatory=True,
            message="Host and runtime prerequisites verified successfully",
            details={
                "host_passed": preflight.host.passed_checks,
                "runtime_passed": preflight.runtime.passed_checks,
            },
        )

    def _evaluate_policy_docker(self, evidence: InfrastructureEvidenceReport) -> GatePolicyResult:
        """Gate Policy 2: Staging Host Container Engine Gate."""
        policy_id = "GATE-DOCKER-CONTAINER"
        policy_name = "Staging Host Container Engine Gate"

        dock = evidence.docker
        if dock.status == CheckStatus.BLOCKED or not dock.engine_accessible:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.BLOCKED,
                mandatory=True,
                message="Docker container engine is inaccessible or daemon is down",
                details=dock.details,
                remediation=dock.remediation or "Start Docker daemon on staging host",
            )

        if dock.status == CheckStatus.FAIL or not dock.compose_available:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Docker container engine or Compose plugin failed verification",
                details=dock.details,
                remediation=dock.remediation or "Install Docker Compose v2 plugin",
            )

        if dock.status == CheckStatus.WARNING and self.strict:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Docker storage or resource warnings escalated in strict mode",
                details=dock.details,
                remediation=dock.remediation or "Ensure sufficient storage space on staging host",
            )

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=dock.status,
            mandatory=True,
            message="Staging Docker container engine and Compose v2 verified",
            details=dock.details,
        )

    def _evaluate_policy_manifest(self, evidence: InfrastructureEvidenceReport) -> GatePolicyResult:
        """Gate Policy 3: Release Manifest & Immutable Digest Gate."""
        policy_id = "GATE-IMMUTABLE-DIGESTS"
        policy_name = "Release Manifest & Immutable Digest Gate"

        man = evidence.release_manifest
        if man.status == CheckStatus.NOT_CONFIGURED:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.NOT_CONFIGURED,
                mandatory=True,
                message="Release manifest is absent or not configured",
                details=man.details,
                remediation=man.remediation or "Generate release manifest before staging gate",
            )

        if man.status == CheckStatus.FAIL or not man.immutable_digests_verified:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Release manifest failed validation: immutable digests not verified",
                details=man.details,
                remediation=(
                    man.remediation
                    or "Ensure all container images are pinned to @sha256:... immutable digests"
                ),
            )

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=CheckStatus.PASS,
            mandatory=True,
            message="Release manifest verified with authentic immutable digest pins",
            details={
                "commit_sha": man.commit_sha,
                "images_count": len(man.images),
                "provenance": man.provenance_verified,
            },
        )

    def _evaluate_policy_secrets(self, evidence: InfrastructureEvidenceReport) -> GatePolicyResult:
        """Gate Policy 4: Smoke Test Isolation & Secret Security Gate."""
        policy_id = "GATE-SECRET-ISOLATION"
        policy_name = "Smoke-Test Isolation & Secret Security Gate"

        smoke = evidence.smoke_credentials
        if smoke.production_secret_leak_detected:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="CRITICAL: Staging smoke test credentials collide with production secrets!",
                details=smoke.details,
                remediation=(
                    "Generate isolated, non-production credentials specifically for staging"
                ),
            )

        if smoke.status == CheckStatus.NOT_CONFIGURED:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.NOT_CONFIGURED,
                mandatory=True,
                message="Staging smoke test credentials are not configured",
                details=smoke.details,
                remediation=smoke.remediation
                or "Export STAGING_SMOKE_USER and STAGING_SMOKE_PASSWORD",
            )

        if smoke.status == CheckStatus.FAIL:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Smoke test credential validation failed",
                details=smoke.details,
                remediation=smoke.remediation,
            )

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=CheckStatus.PASS,
            mandatory=True,
            message="Smoke test credentials verified with verified secret isolation",
            details=smoke.details,
        )

    def _evaluate_policy_rollback(self, evidence: InfrastructureEvidenceReport) -> GatePolicyResult:
        """Gate Policy 5: Safe Rollback & Data Preservation Lifecycle Gate."""
        policy_id = "GATE-ROLLBACK-LIFECYCLE"
        policy_name = "Rollback & Forward-Only Migration Lifecycle Gate"

        rb = evidence.rollback
        if not rb.recovery_runbook_verified:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Recovery runbooks (docs/deployment.md, docs/staging.md) not verified",
                details=rb.details,
                remediation="Ensure operational recovery and staging runbooks exist",
            )

        if not rb.forward_only_migration_policy_verified:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message="Forward-only database migration policy violation detected",
                details=rb.details,
                remediation="Schema lifecycle must be forward-only; downgrades prohibited",
            )

        if not rb.backup_configured:
            status = CheckStatus.FAIL if self.strict else CheckStatus.WARNING
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=status,
                mandatory=True,
                message="Staging backup directory is not configured",
                details=rb.details,
                remediation=rb.remediation or "Configure STAGING_BACKUP_DIR",
            )

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=CheckStatus.PASS,
            mandatory=True,
            message="Rollback recovery procedures and forward-only policy verified",
            details=rb.details,
        )

    def _evaluate_policy_governance(
        self, evidence: InfrastructureEvidenceReport
    ) -> GatePolicyResult:
        """Gate Policy 6: Volume V26 Governance Boundary Gate."""
        policy_id = "GATE-V26-GOVERNANCE"
        policy_name = "Volume V26 Governance Boundary Gate"

        # V26 strictly prohibits live qualification authorization or production deployment
        if evidence.live_qualification_authorized or evidence.production_deployment_authorized:
            return GatePolicyResult(
                policy_id=policy_id,
                policy_name=policy_name,
                status=CheckStatus.FAIL,
                mandatory=True,
                message=(
                    "CRITICAL GOVERNANCE VIOLATION: Volume V26 strictly prohibits authorizing "
                    "live qualification or automated production deployment."
                ),
                details={
                    "live_qualification_authorized": evidence.live_qualification_authorized,
                    "production_deployment_authorized": evidence.production_deployment_authorized,
                },
                remediation="Ensure live qualification and deployment flags remain False in V26",
            )

        return GatePolicyResult(
            policy_id=policy_id,
            policy_name=policy_name,
            status=CheckStatus.PASS,
            mandatory=True,
            message="Volume V26 governance boundaries strictly observed (readiness only)",
            details={
                "live_qualification_authorized": False,
                "production_deployment_authorized": False,
            },
        )

    def evaluate_gates(
        self,
        preflight: StagingPreflightReport,
        evidence: InfrastructureEvidenceReport,
    ) -> StagingGateEvaluationReport:
        """Evaluate preflight report and evidence report jointly against all gates."""
        evaluated_at = datetime.now(UTC).isoformat()
        target_sha = evidence.commit_sha or preflight.commit_sha
        target_repo = evidence.repository or preflight.repository

        policies: list[GatePolicyResult] = []

        # Freshness and integrity check
        is_fresh, age_sec, freshness_msg = self.validate_evidence_freshness(evidence.timestamp)
        sha_match = bool(
            preflight.commit_sha
            and evidence.commit_sha
            and preflight.commit_sha.lower() == evidence.commit_sha.lower()
        )

        integrity_details: dict[str, Any] = {
            "evidence_age_seconds": round(age_sec, 1),
            "max_age_seconds": self.max_age_seconds,
            "preflight_sha": preflight.commit_sha,
            "evidence_sha": evidence.commit_sha,
            "sha_match": sha_match,
        }

        if not is_fresh:
            integrity_status = CheckStatus.FAIL if self.strict else CheckStatus.BLOCKED
            policies.append(
                GatePolicyResult(
                    policy_id="GATE-EVIDENCE-INTEGRITY",
                    policy_name="Evidence Freshness & Integrity Gate",
                    status=integrity_status,
                    mandatory=True,
                    message=freshness_msg,
                    details=integrity_details,
                    remediation="Re-run scripts/staging_evidence.py to collect fresh evidence",
                )
            )
        elif not sha_match and validate_commit_sha(preflight.commit_sha):
            policies.append(
                GatePolicyResult(
                    policy_id="GATE-EVIDENCE-INTEGRITY",
                    policy_name="Evidence Freshness & Integrity Gate",
                    status=CheckStatus.FAIL,
                    mandatory=True,
                    message=(
                        f"Commit SHA mismatch: preflight has '{preflight.commit_sha}', "
                        f"evidence has '{evidence.commit_sha}'"
                    ),
                    details=integrity_details,
                    remediation=(
                        "Preflight and Evidence must be gathered for the exact same commit SHA"
                    ),
                )
            )
        else:
            policies.append(
                GatePolicyResult(
                    policy_id="GATE-EVIDENCE-INTEGRITY",
                    policy_name="Evidence Freshness & Integrity Gate",
                    status=CheckStatus.PASS,
                    mandatory=True,
                    message="Evidence freshness and commit integrity verified",
                    details=integrity_details,
                )
            )

        # Evaluate the 6 core policies
        policies.append(self._evaluate_policy_preflight(preflight))
        policies.append(self._evaluate_policy_docker(evidence))
        policies.append(self._evaluate_policy_manifest(evidence))
        policies.append(self._evaluate_policy_secrets(evidence))
        policies.append(self._evaluate_policy_rollback(evidence))
        policies.append(self._evaluate_policy_governance(evidence))

        # Summarize results
        failed_policies: list[str] = []
        blocked_policies: list[str] = []
        warnings: list[str] = []
        remediations: list[str] = []

        for p in policies:
            if p.status == CheckStatus.FAIL:
                failed_policies.append(f"{p.policy_id}: {p.message}")
                if p.remediation:
                    remediations.append(p.remediation)
            elif p.status == CheckStatus.BLOCKED:
                blocked_policies.append(f"{p.policy_id}: {p.message}")
                if p.remediation:
                    remediations.append(p.remediation)
            elif p.status == CheckStatus.NOT_CONFIGURED:
                blocked_policies.append(f"{p.policy_id}: {p.message}")
                if p.remediation:
                    remediations.append(p.remediation)
            elif p.status == CheckStatus.WARNING:
                warnings.append(f"{p.policy_id}: {p.message}")
                if p.remediation and p.remediation not in remediations:
                    remediations.append(p.remediation)

        # Fail-closed gate evaluation
        if failed_policies:
            overall_status = CheckStatus.FAIL
        elif any(p.status == CheckStatus.BLOCKED for p in policies):
            overall_status = CheckStatus.BLOCKED
        elif any(p.status == CheckStatus.NOT_CONFIGURED for p in policies):
            overall_status = CheckStatus.NOT_CONFIGURED
        elif self.strict and warnings:
            overall_status = CheckStatus.FAIL
        elif warnings:
            overall_status = CheckStatus.WARNING
        else:
            overall_status = CheckStatus.PASS

        is_ready = (overall_status == CheckStatus.PASS) or (
            not self.strict
            and overall_status == CheckStatus.WARNING
            and not failed_policies
            and not blocked_policies
        )

        return StagingGateEvaluationReport(
            schema_version="1.0.0",
            environment="staging",
            repository=target_repo,
            commit_sha=target_sha,
            evaluated_at=evaluated_at,
            overall_status=overall_status,
            is_ready=is_ready,
            strict_mode=self.strict,
            live_qualification_authorized=False,
            production_deployment_authorized=False,
            preflight_evaluated=True,
            evidence_evaluated=True,
            evidence_freshness_seconds=round(age_sec, 2),
            evidence_is_fresh=is_fresh,
            gate_policies=policies,
            failed_policies=failed_policies,
            blocked_policies=blocked_policies,
            warnings=warnings,
            remediations=remediations,
            metadata={
                "gate_evaluator": "StagingReadinessGateEvaluator",
                "volume": "V26",
                "commit": "03",
            },
        )
