"""RegimeX — Staging Qualification Evidence Evaluator & Release-Gate Policy Engine.

apps/api/app/core/staging_qualification_gates.py
================================================
Combines Volume V26 readiness evidence, Volume V27 qualification orchestration
results, and V27 smoke-test results to produce an auditable, deterministic
StagingQualificationAuditReport.

Invariants:
- NEVER treats MOCKED or LOCAL_INTEGRATION results as LIVE_STAGING qualification.
- Rejects tampered, contradictory, duplicate, or stale evidence.
- Optional check advisories/failures never conceal mandatory failures.
- Preserves strict governance flags (live_qualification_authorized=False,
  production_deployment_authorized=False, production_deployment_performed=False,
  container_images_published=False).
- Staging qualification never deploys to production or publishes images.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from app.core.deployment import validate_commit_sha
from app.core.staging_gates import StagingReadinessGateEvaluator
from app.core.staging_qualification import (
    EXPECTED_REPOSITORY,
    _is_production_environment,
    _is_production_url,
    sanitize_text,
)
from app.schemas.staging_readiness import (
    ExecutionMode,
    InfrastructureEvidenceReport,
    QualificationDecision,
    QualificationPolicyResult,
    QualificationStatus,
    StagingQualificationAuditReport,
    StagingQualificationReport,
)

logger = logging.getLogger("regimex.staging_qualification_gates")

SUPPORTED_SCHEMA_VERSION = "1.0.0"
DEFAULT_MAX_EVIDENCE_AGE_SECONDS = StagingReadinessGateEvaluator.DEFAULT_MAX_AGE_SECONDS

MANDATORY_SMOKE_STAGES = (
    "backend_health_qualification",
    "frontend_availability_qualification",
    "api_contract_qualification",
    "dependency_readiness_qualification",
    "service_readiness_qualification",
)


class QualificationEvidenceEvaluator:
    """Evaluates V27 qualification evidence, integrity, freshness, and release gates."""

    def __init__(
        self,
        *,
        max_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
        strict: bool = False,
        env: dict[str, str] | None = None,
    ) -> None:
        self.max_age_seconds = max_age_seconds
        self.strict = strict
        self.env = env if env is not None else os.environ.copy()

    def _validate_timestamp_freshness(
        self, timestamp_str: str | None, label: str
    ) -> tuple[QualificationStatus, float | None, str]:
        """Validate ISO-8601 timestamp format, skew bounds, and freshness window."""
        if not timestamp_str or not timestamp_str.strip():
            return QualificationStatus.FAIL, None, f"Missing timestamp for {label}"

        try:
            clean_ts = timestamp_str.strip().replace("Z", "+00:00")
            recorded = datetime.fromisoformat(clean_ts)
            if recorded.tzinfo is None:
                recorded = recorded.replace(tzinfo=UTC)
            age_sec = (datetime.now(UTC) - recorded).total_seconds()
            if age_sec < -30.0:
                return (
                    QualificationStatus.FAIL,
                    round(age_sec, 2),
                    f"Tampered/skewed future timestamp for {label} ({round(age_sec, 1)}s)",
                )
            effective_age = max(0.0, age_sec)
            if effective_age > self.max_age_seconds:
                return (
                    QualificationStatus.BLOCKED,
                    round(effective_age, 2),
                    f"{label} evidence is stale ({round(effective_age, 1)}s > "
                    f"{self.max_age_seconds}s)",
                )
            return (
                QualificationStatus.PASS,
                round(effective_age, 2),
                f"{label} evidence is fresh ({round(effective_age, 1)}s <= "
                f"{self.max_age_seconds}s)",
            )
        except Exception as exc:
            return (
                QualificationStatus.FAIL,
                None,
                f"Malformed timestamp for {label}: {sanitize_text(str(exc), self.env)}",
            )

    def _validate_integrity(
        self,
        *,
        report: StagingQualificationReport,
        claimed_mode: ExecutionMode,
        infrastructure_evidence: InfrastructureEvidenceReport | None,
    ) -> tuple[QualificationStatus, QualificationStatus, list[str]]:
        """Validate schema, SHA, repo, environment, duplicates, mode honesty, and freshness."""
        integrity_errors: list[str] = []

        # 1. Schema version
        if report.schema_version != SUPPORTED_SCHEMA_VERSION:
            integrity_errors.append(
                f"Unsupported report schema_version '{report.schema_version}' "
                f"(expected '{SUPPORTED_SCHEMA_VERSION}')"
            )

        # 2. Governance flags integrity
        if (
            report.live_qualification_authorized
            or report.production_deployment_authorized
            or report.production_deployment_performed
            or report.container_images_published
        ):
            integrity_errors.append(
                "Governance boundary violation: authorization or deployment flags set to True"
            )

        # 3. Commit SHA consistency
        if not validate_commit_sha(report.commit_sha):
            integrity_errors.append(f"Invalid commit SHA '{report.commit_sha}'")
        elif report.run_metadata.commit_sha.lower() != report.commit_sha.lower():
            integrity_errors.append("Commit SHA mismatch between report and run_metadata")

        if report.v26_gate_report is not None:
            if report.v26_gate_report.commit_sha.lower() != report.commit_sha.lower():
                integrity_errors.append("Commit SHA mismatch between V27 report and V26 gate")
            if report.v26_gate_report.repository != EXPECTED_REPOSITORY:
                integrity_errors.append(
                    f"Repository mismatch in V26 gate: '{report.v26_gate_report.repository}'"
                )

        if infrastructure_evidence is not None:
            if infrastructure_evidence.commit_sha.lower() != report.commit_sha.lower():
                integrity_errors.append("Commit SHA mismatch with infrastructure evidence")
            if infrastructure_evidence.repository != EXPECTED_REPOSITORY:
                integrity_errors.append("Repository mismatch in infrastructure evidence")
            if (
                infrastructure_evidence.live_qualification_authorized
                or infrastructure_evidence.production_deployment_authorized
            ):
                integrity_errors.append("Governance violation in V26 infrastructure evidence")

        # 4. Repository & environment identity
        if report.repository != EXPECTED_REPOSITORY or (
            report.run_metadata.repository != EXPECTED_REPOSITORY
        ):
            integrity_errors.append(
                f"Repository mismatch: expected '{EXPECTED_REPOSITORY}', got '{report.repository}'"
            )

        env_name = report.environment.name.strip().lower()
        if _is_production_environment(env_name) or env_name != "staging":
            integrity_errors.append(
                "Environment identity violation: expected 'staging', "
                f"got '{report.environment.name}'"
            )
        if report.run_metadata.environment.strip().lower() != "staging":
            integrity_errors.append("run_metadata.environment is not 'staging'")
        if not report.environment.isolated_from_production:
            integrity_errors.append("Environment reports isolated_from_production=False")

        for label, u in (
            ("api_url", report.environment.api_url),
            ("web_url", report.environment.web_url),
        ):
            if u:
                is_prod, prod_reason = _is_production_url(u, self.env)
                if is_prod:
                    integrity_errors.append(f"Production {label} rejected: {prod_reason}")

        # 5. Duplicate evidence IDs & duplicate check IDs
        ev_ids = [ev.evidence_id for ev in report.evidence]
        if len(ev_ids) != len(set(ev_ids)):
            integrity_errors.append("Duplicate evidence_id entries detected")

        chk_ids = [c.check_id for c in report.checks]
        if len(chk_ids) != len(set(chk_ids)):
            integrity_errors.append("Duplicate check_id entries detected")

        # 6. Contradictory result invariants
        if report.qualification_passed and report.overall_status in (
            QualificationStatus.FAIL,
            QualificationStatus.BLOCKED,
            QualificationStatus.NOT_CONFIGURED,
            QualificationStatus.NOT_RUN,
        ):
            integrity_errors.append(
                f"Contradictory report: qualification_passed=True with "
                f"overall_status={report.overall_status.value}"
            )
        if report.overall_status == QualificationStatus.PASS and report.failed_checks:
            integrity_errors.append(
                "Contradictory report: overall_status=PASS while failed_checks is non-empty"
            )
        for st in report.stages:
            if (
                st.mandatory
                and st.status == QualificationStatus.FAIL
                and (report.overall_status == QualificationStatus.PASS)
            ):
                integrity_errors.append(
                    f"Contradictory report: mandatory stage '{st.stage_id}' failed "
                    "while overall_status=PASS"
                )

        # 7. Evidence execution mode honesty (never accept mocked/dry-run as LIVE_STAGING)
        if claimed_mode == ExecutionMode.LIVE_STAGING:
            if report.run_metadata.dry_run:
                integrity_errors.append(
                    "Contradiction: dry-run report cannot be presented as LIVE_STAGING"
                )
            for ev in report.evidence:
                if (
                    ev.evidence_id.startswith("stage-")
                    and ev.execution_mode == ExecutionMode.MOCKED
                ):
                    integrity_errors.append(
                        f"Tampered mode: evidence '{ev.evidence_id}' is MOCKED under LIVE_STAGING"
                    )
                if "mock" in ev.source.lower():
                    integrity_errors.append(
                        f"Tampered source: mocked evidence '{ev.evidence_id}' presented as live"
                    )
            for chk in report.checks:
                if chk.execution_mode == ExecutionMode.MOCKED:
                    integrity_errors.append(
                        f"Tampered check mode: '{chk.check_id}' is MOCKED under LIVE_STAGING"
                    )

        # 8. Evidence freshness validation
        ts_to_check = report.run_metadata.completed_at or report.run_metadata.requested_at
        v27_fresh_status, _, v27_fresh_msg = self._validate_timestamp_freshness(
            ts_to_check, "V27 qualification"
        )
        freshness_statuses = [v27_fresh_status]
        freshness_notes = [v27_fresh_msg]

        if report.v26_gate_report is not None:
            v26_fresh_status, _, v26_fresh_msg = self._validate_timestamp_freshness(
                report.v26_gate_report.evaluated_at, "V26 gate"
            )
            freshness_statuses.append(v26_fresh_status)
            freshness_notes.append(v26_fresh_msg)
            if not report.v26_gate_report.evidence_is_fresh:
                freshness_statuses.append(QualificationStatus.BLOCKED)
                freshness_notes.append("V26 gate flagged infrastructure evidence as stale")

        if infrastructure_evidence is not None:
            infra_fresh_status, _, infra_fresh_msg = self._validate_timestamp_freshness(
                infrastructure_evidence.timestamp, "V26 infrastructure"
            )
            freshness_statuses.append(infra_fresh_status)
            freshness_notes.append(infra_fresh_msg)

        if QualificationStatus.FAIL in freshness_statuses:
            freshness_result = QualificationStatus.FAIL
            integrity_errors.extend(
                [
                    n
                    for s, n in zip(freshness_statuses, freshness_notes, strict=False)
                    if s == QualificationStatus.FAIL
                ]
            )
        elif QualificationStatus.BLOCKED in freshness_statuses:
            freshness_result = QualificationStatus.BLOCKED
        else:
            freshness_result = QualificationStatus.PASS

        integrity_result = (
            QualificationStatus.FAIL if integrity_errors else QualificationStatus.PASS
        )
        return freshness_result, integrity_result, integrity_errors

    @staticmethod
    def _stage_status(report: StagingQualificationReport, stage_id: str) -> QualificationStatus:
        for st in report.stages:
            if st.stage_id == stage_id:
                return st.status
        return QualificationStatus.NOT_RUN

    @staticmethod
    def _check_status(report: StagingQualificationReport, check_id: str) -> QualificationStatus:
        for chk in report.checks:
            if chk.check_id == check_id:
                return chk.status
        return QualificationStatus.NOT_RUN

    def evaluate(
        self,
        *,
        report: StagingQualificationReport,
        execution_mode: ExecutionMode | None = None,
        infrastructure_evidence: InfrastructureEvidenceReport | None = None,
    ) -> StagingQualificationAuditReport:
        """Evaluate complete V26 + V27 evidence and emit a deterministic audit report."""
        effective_mode = execution_mode or report.execution_mode
        started_at = report.run_metadata.started_at or report.run_metadata.requested_at
        completed_at = report.run_metadata.completed_at or datetime.now(UTC).isoformat()

        freshness_result, integrity_result, integrity_errors = self._validate_integrity(
            report=report,
            claimed_mode=effective_mode,
            infrastructure_evidence=infrastructure_evidence,
        )

        # Component summaries
        backend_status = self._stage_status(report, "backend_health_qualification")
        frontend_status = self._stage_status(report, "frontend_availability_qualification")
        contract_status = self._stage_status(report, "api_contract_qualification")
        db_status = self._check_status(report, "smoke.deps.database_readiness")
        redis_status = self._check_status(report, "smoke.deps.redis_readiness")

        app_services: dict[str, QualificationStatus] = {
            "observability_summary": self._check_status(
                report, "smoke.service.observability_summary"
            ),
            "regime_models": self._check_status(report, "smoke.service.regime_models"),
            "feature_and_pipeline": self._check_status(
                report, "smoke.service.feature_and_pipeline"
            ),
            "ai_research_optional": self._check_status(
                report, "smoke.service.ai_research_optional"
            ),
        }

        liveness_status = self._check_status(report, "smoke.backend.liveness")
        readiness_v1 = self._check_status(report, "smoke.backend.readiness_v1")
        readiness_root = self._check_status(report, "smoke.backend.readiness_root")
        backend_ready_status = (
            QualificationStatus.PASS
            if readiness_v1 == QualificationStatus.PASS
            and readiness_root == QualificationStatus.PASS
            else (
                QualificationStatus.FAIL
                if QualificationStatus.FAIL in (readiness_v1, readiness_root)
                else (
                    QualificationStatus.BLOCKED
                    if QualificationStatus.BLOCKED in (readiness_v1, readiness_root)
                    else backend_status
                )
            )
        )

        # Mandatory policy checks
        mandatory_policies: list[QualificationPolicyResult] = []

        # 1. V26 Readiness Gate
        v26_ok = report.v26_gate_passed and (
            report.v26_gate_report is None or report.v26_gate_report.is_ready
        )
        v26_pol_status = (
            QualificationStatus.PASS
            if v26_ok
            else QualificationStatus(report.v26_gate_status.value)
        )
        if v26_pol_status == QualificationStatus.WARNING and not self.strict:
            v26_pol_status = QualificationStatus.PASS if v26_ok else QualificationStatus.BLOCKED
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-V26-GATE",
                policy_name="V26 Readiness Gate Passed",
                mandatory=True,
                status=v26_pol_status,
                message=(
                    f"V26 gate verified ({report.v26_gate_status.value})"
                    if v26_ok
                    else f"V26 readiness gate did not pass ({report.v26_gate_status.value})"
                ),
                remediation=None if v26_ok else "Resolve V26 readiness gate failures first.",
            )
        )

        # 2. Staging Environment Configuration
        env_configured = bool(
            report.environment.name == "staging"
            and report.environment.isolated_from_production
            and report.environment.api_url
            and report.environment.web_url
        )
        env_pol_status = (
            QualificationStatus.PASS
            if env_configured
            else (
                QualificationStatus.FAIL
                if not report.environment.isolated_from_production
                or _is_production_environment(report.environment.name)
                else QualificationStatus.NOT_CONFIGURED
            )
        )
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-ENV-CONFIG",
                policy_name="Explicit Staging Environment Configuration",
                mandatory=True,
                status=env_pol_status,
                message=(
                    "Isolated staging target URLs configured"
                    if env_configured
                    else (
                        "Production isolation violation"
                        if env_pol_status == QualificationStatus.FAIL
                        else "Staging target URLs (STAGING_API_URL / STAGING_WEB_URL) missing"
                    )
                ),
                remediation=(
                    None
                    if env_configured
                    else "Configure explicit non-production STAGING_API_URL and STAGING_WEB_URL."
                ),
            )
        )

        # 3. Release Identity
        rel_ok = (
            validate_commit_sha(report.commit_sha)
            and report.repository == EXPECTED_REPOSITORY
            and bool(report.release_tag)
            and report.release_tag != "unknown"
        )
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-RELEASE-ID",
                policy_name="Immutable Release Identity",
                mandatory=True,
                status=QualificationStatus.PASS if rel_ok else QualificationStatus.FAIL,
                message=(
                    f"Release identity verified ({report.release_tag} @ {report.commit_sha})"
                    if rel_ok
                    else "Release commit SHA or repository identity invalid"
                ),
            )
        )

        # 4. Backend Liveness
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-BACKEND-LIVE",
                policy_name="Backend Liveness Smoke Check",
                mandatory=True,
                status=liveness_status,
                message=f"Backend liveness status: {liveness_status.value}",
            )
        )

        # 5. Backend Readiness
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-BACKEND-READY",
                policy_name="Backend Dependency Readiness Smoke Check",
                mandatory=True,
                status=backend_ready_status,
                message=f"Backend readiness status: {backend_ready_status.value}",
            )
        )

        # 6. Frontend Availability
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-FRONTEND",
                policy_name="Frontend Availability & Config Consistency",
                mandatory=True,
                status=frontend_status,
                message=f"Frontend smoke status: {frontend_status.value}",
            )
        )

        # 7. Required Dependencies (Database mandatory; Redis mandatory only when configured)
        deps_status = db_status
        if redis_status == QualificationStatus.FAIL:
            deps_status = QualificationStatus.FAIL
        elif (
            redis_status == QualificationStatus.BLOCKED and deps_status == QualificationStatus.PASS
        ):
            deps_status = QualificationStatus.BLOCKED
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-DEPENDENCIES",
                policy_name="Database & Configured Redis Connectivity",
                mandatory=True,
                status=deps_status,
                message=(f"Database={db_status.value}, Redis={redis_status.value}"),
            )
        )

        # 8. No Critical Smoke Failures (API Contract & Services & Complete Smoke Evidence)
        service_stage_status = self._stage_status(report, "service_readiness_qualification")
        has_critical_fail = (
            contract_status == QualificationStatus.FAIL
            or service_stage_status == QualificationStatus.FAIL
            or report.overall_status == QualificationStatus.FAIL
            or bool(report.failed_checks)
        )
        missing_mandatory_stages = [
            sid
            for sid in MANDATORY_SMOKE_STAGES
            if self._stage_status(report, sid) == QualificationStatus.NOT_RUN
        ]
        if has_critical_fail:
            smoke_pol_status = QualificationStatus.FAIL
            smoke_pol_msg = "Critical smoke-test or orchestration failures detected"
        elif contract_status == QualificationStatus.BLOCKED or (
            service_stage_status == QualificationStatus.BLOCKED
        ):
            smoke_pol_status = QualificationStatus.BLOCKED
            smoke_pol_msg = "Smoke-test execution blocked"
        elif missing_mandatory_stages:
            smoke_pol_status = (
                QualificationStatus.NOT_CONFIGURED
                if report.overall_status == QualificationStatus.NOT_CONFIGURED
                else QualificationStatus.NOT_RUN
            )
            smoke_pol_msg = (
                f"Missing mandatory smoke-test evidence: {', '.join(missing_mandatory_stages)}"
            )
        else:
            smoke_pol_status = QualificationStatus.PASS
            smoke_pol_msg = "All mandatory smoke-test stages passed"

        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-SMOKE-COMPLETE",
                policy_name="Critical Smoke Tests & Evidence Completeness",
                mandatory=True,
                status=smoke_pol_status,
                message=smoke_pol_msg,
            )
        )

        # 9. Evidence Integrity & Freshness
        ev_pol_status = (
            QualificationStatus.FAIL
            if integrity_result == QualificationStatus.FAIL
            or freshness_result == QualificationStatus.FAIL
            else (
                QualificationStatus.BLOCKED
                if freshness_result == QualificationStatus.BLOCKED
                else QualificationStatus.PASS
            )
        )
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-EVIDENCE-INTEGRITY",
                policy_name="Evidence Freshness & Integrity",
                mandatory=True,
                status=ev_pol_status,
                message=(
                    "Evidence freshness and integrity verified"
                    if ev_pol_status == QualificationStatus.PASS
                    else "; ".join(integrity_errors) or "Evidence freshness check blocked"
                ),
            )
        )

        # 10. Execution Mode Verification (LIVE_STAGING required for QUALIFIED)
        is_live_mode = (
            effective_mode == ExecutionMode.LIVE_STAGING and not report.run_metadata.dry_run
        )
        mandatory_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-POL-LIVE-MODE",
                policy_name="Live Staging Execution Verification",
                mandatory=True,
                status=(QualificationStatus.PASS if is_live_mode else QualificationStatus.NOT_RUN),
                message=(
                    "Evidence gathered from LIVE_STAGING execution"
                    if is_live_mode
                    else (
                        f"Execution mode '{effective_mode.value}' cannot qualify a release "
                        "(LIVE_STAGING required)"
                    )
                ),
                remediation=(
                    None
                    if is_live_mode
                    else "Run live qualification against a configured staging environment."
                ),
            )
        )

        # Optional policies (never conceal mandatory failures)
        optional_policies: list[QualificationPolicyResult] = []
        gpu_status = (
            QualificationStatus(infrastructure_evidence.gpu.status.value)
            if infrastructure_evidence is not None
            else QualificationStatus.NOT_RUN
        )
        optional_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-OPT-GPU",
                policy_name="Optional Host GPU Acceleration",
                mandatory=False,
                status=gpu_status,
                message=(
                    "NVIDIA GPU available"
                    if infrastructure_evidence and infrastructure_evidence.gpu.gpu_available
                    else "No GPU detected; CPU fallback active (optional)"
                ),
            )
        )

        ai_status = app_services["ai_research_optional"]
        optional_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-OPT-AI",
                policy_name="Optional AI Research Integration",
                mandatory=False,
                status=ai_status,
                message=f"Optional AI integration status: {ai_status.value}",
            )
        )

        rate_status = self._check_status(report, "smoke.api.rate_limit_headers")
        optional_policies.append(
            QualificationPolicyResult(
                policy_id="QUAL-OPT-RATE-LIMIT",
                policy_name="Optional Rate-Limit Telemetry",
                mandatory=False,
                status=rate_status,
                message=f"Rate-limit telemetry status: {rate_status.value}",
            )
        )

        # Summarize failed / blocked / warnings
        failed_checks = list(dict.fromkeys([*report.failed_checks, *integrity_errors]))
        blocked_checks = list(report.blocked_checks)
        warnings = list(report.warnings)

        for pol in mandatory_policies:
            if pol.status == QualificationStatus.FAIL:
                entry = f"{pol.policy_id}: {pol.message}"
                if entry not in failed_checks:
                    failed_checks.append(entry)
            elif pol.status == QualificationStatus.BLOCKED:
                entry = f"{pol.policy_id}: {pol.message}"
                if entry not in blocked_checks:
                    blocked_checks.append(entry)

        for opt in optional_policies:
            if opt.status in (
                QualificationStatus.WARNING,
                QualificationStatus.NOT_CONFIGURED,
                QualificationStatus.FAIL,
            ):
                w_entry = f"{opt.policy_id} (optional): {opt.message}"
                if w_entry not in warnings:
                    warnings.append(w_entry)

        # Deterministic Final Decision Logic
        decision, reason = self._resolve_decision(
            report=report,
            effective_mode=effective_mode,
            integrity_result=integrity_result,
            freshness_result=freshness_result,
            mandatory_policies=mandatory_policies,
            integrity_errors=integrity_errors,
        )

        recommendations = list(dict.fromkeys(report.remediations))
        for pol in mandatory_policies:
            if pol.remediation and pol.remediation not in recommendations:
                recommendations.append(pol.remediation)
        if decision == QualificationDecision.QUALIFIED:
            recommendations.append(
                "Evidence complete. Human release manager review required before any production "
                "deployment approval."
            )

        return StagingQualificationAuditReport(
            schema_version=SUPPORTED_SCHEMA_VERSION,
            run_id=report.run_id,
            repository=report.repository,
            commit_sha=report.commit_sha,
            release_tag=report.release_tag,
            environment=report.environment.name,
            execution_mode=effective_mode,
            started_at=started_at,
            completed_at=completed_at,
            v26_readiness_result=report.v26_gate_status,
            backend_smoke_result=backend_status,
            frontend_smoke_result=frontend_status,
            api_contract_result=contract_status,
            database_result=db_status,
            redis_result=redis_status,
            application_service_results=app_services,
            evidence_freshness_result=freshness_result,
            evidence_integrity_result=integrity_result,
            mandatory_checks=mandatory_policies,
            optional_checks=optional_policies,
            failed_checks=[sanitize_text(x, self.env) for x in failed_checks],
            blocked_checks=[sanitize_text(x, self.env) for x in blocked_checks],
            warnings=[sanitize_text(x, self.env) for x in warnings],
            decision=decision,
            decision_reason=sanitize_text(reason, self.env),
            manual_recovery_recommendations=[sanitize_text(x, self.env) for x in recommendations],
            live_qualification_authorized=False,
            production_deployment_authorized=False,
            production_deployment_performed=False,
            container_images_published=False,
            metadata={
                "evaluator": "QualificationEvidenceEvaluator",
                "volume": "V27",
                "strict_mode": self.strict,
                "dry_run": report.run_metadata.dry_run,
            },
        )

    def _resolve_decision(
        self,
        *,
        report: StagingQualificationReport,
        effective_mode: ExecutionMode,
        integrity_result: QualificationStatus,
        freshness_result: QualificationStatus,
        mandatory_policies: list[QualificationPolicyResult],
        integrity_errors: list[str],
    ) -> tuple[QualificationDecision, str]:
        """Compute deterministic QualificationDecision following V27 release-gate rules."""
        # 1. Integrity / tampered / invalid identity / governance / prod isolation -> FAILED
        if integrity_result == QualificationStatus.FAIL:
            return (
                QualificationDecision.FAILED,
                "Qualification evidence failed integrity or isolation validation: "
                + "; ".join(integrity_errors),
            )

        # 2. Stale evidence or blocked/failed V26 gate -> BLOCKED (before Step 7 target URLs)
        env_pol = next(p for p in mandatory_policies if p.policy_id == "QUAL-POL-ENV-CONFIG")
        v26_pol = next(p for p in mandatory_policies if p.policy_id == "QUAL-POL-V26-GATE")
        if (
            freshness_result == QualificationStatus.BLOCKED
            or report.overall_status == QualificationStatus.BLOCKED
            or v26_pol.status in (QualificationStatus.BLOCKED, QualificationStatus.FAIL)
        ):
            return (
                QualificationDecision.BLOCKED,
                "Qualification execution or prerequisites were blocked (e.g., stale evidence, "
                "blocked/failed V26 gate, or unreachable staging target).",
            )

        # 3. Missing staging configuration -> NOT_CONFIGURED
        if (
            report.overall_status == QualificationStatus.NOT_CONFIGURED
            or env_pol.status == QualificationStatus.NOT_CONFIGURED
            or v26_pol.status == QualificationStatus.NOT_CONFIGURED
        ):
            return (
                QualificationDecision.NOT_CONFIGURED,
                "Required staging target infrastructure or configuration is absent.",
            )

        # 4. Mandatory smoke/policy failures -> NOT_QUALIFIED (even if downstream stages blocked)
        smoke_policies = [
            p
            for p in mandatory_policies
            if p.policy_id
            in (
                "QUAL-POL-BACKEND-LIVE",
                "QUAL-POL-BACKEND-READY",
                "QUAL-POL-FRONTEND",
                "QUAL-POL-DEPENDENCIES",
                "QUAL-POL-SMOKE-COMPLETE",
            )
        ]
        failed_smoke = [p for p in smoke_policies if p.status == QualificationStatus.FAIL]
        if failed_smoke:
            names = ", ".join(p.policy_id for p in failed_smoke)
            return (
                QualificationDecision.NOT_QUALIFIED,
                f"Mandatory staging qualification checks failed: {names}.",
            )

        if any(p.status == QualificationStatus.BLOCKED for p in mandatory_policies):
            return (
                QualificationDecision.BLOCKED,
                "One or more mandatory qualification policies were blocked.",
            )

        # 5. Mocked / Local Integration / Dry-run -> NEVER QUALIFIED
        if effective_mode != ExecutionMode.LIVE_STAGING or report.run_metadata.dry_run:
            return (
                QualificationDecision.NOT_QUALIFIED,
                f"Execution mode is '{effective_mode.value}' "
                f"(dry_run={report.run_metadata.dry_run}); "
                "mocked, local, or dry-run tests cannot establish live staging qualification.",
            )

        # 6. Missing mandatory live smoke evidence -> NOT_QUALIFIED
        incomplete = [p for p in smoke_policies if p.status != QualificationStatus.PASS]
        if incomplete:
            names = ", ".join(f"{p.policy_id}={p.status.value}" for p in incomplete)
            return (
                QualificationDecision.NOT_QUALIFIED,
                f"Incomplete mandatory live staging smoke evidence: {names}.",
            )

        # 7. All mandatory checks passed with valid LIVE_STAGING evidence -> QUALIFIED
        return (
            QualificationDecision.QUALIFIED,
            "All mandatory V26 and V27 checks passed with fresh, verified LIVE_STAGING evidence. "
            "Awaiting human release decision (production deployment remains unauthorized).",
        )


def format_text_audit_report(audit: StagingQualificationAuditReport) -> str:
    """Render a human-readable summary of StagingQualificationAuditReport."""
    lines: list[str] = [
        "=" * 78,
        "  REGIMEX — V27 STAGING QUALIFICATION AUDIT & RELEASE-GATE REPORT",
        "=" * 78,
        f"  Run ID:               {audit.run_id}",
        f"  Repository:           {audit.repository}",
        f"  Commit SHA:           {audit.commit_sha}",
        f"  Release Tag:          {audit.release_tag}",
        f"  Environment:          {audit.environment}",
        f"  Execution Mode:       {audit.execution_mode.value}",
        f"  Final Decision:       {audit.decision.value}",
        f"  Decision Reason:      {audit.decision_reason}",
        f"  V26 Readiness Gate:   {audit.v26_readiness_result.value}",
        f"  Evidence Freshness:   {audit.evidence_freshness_result.value}",
        f"  Evidence Integrity:   {audit.evidence_integrity_result.value}",
        f"  Backend Smoke:        {audit.backend_smoke_result.value}",
        f"  Frontend Smoke:       {audit.frontend_smoke_result.value}",
        f"  API Contract:         {audit.api_contract_result.value}",
        f"  Database / Redis:     {audit.database_result.value} / {audit.redis_result.value}",
        f"  Governance Flags:     live_qual_auth={audit.live_qualification_authorized} | "
        f"prod_deploy_auth={audit.production_deployment_authorized} | "
        f"prod_performed={audit.production_deployment_performed} | "
        f"images_published={audit.container_images_published}",
        "-" * 78,
        "  MANDATORY QUALIFICATION POLICIES",
        "-" * 78,
    ]
    for pol in audit.mandatory_checks:
        lines.append(f"  [{pol.status.value:<14}] {pol.policy_id:<28} {pol.message}")
    lines.append("-" * 78)
    lines.append("  OPTIONAL CHECKS")
    lines.append("-" * 78)
    for opt in audit.optional_checks:
        lines.append(f"  [{opt.status.value:<14}] {opt.policy_id:<28} {opt.message}")

    if audit.failed_checks:
        lines.extend(["-" * 78, "  FAILED CHECKS:"])
        for fc in audit.failed_checks:
            lines.append(f"    - {fc}")
    if audit.blocked_checks:
        lines.extend(["-" * 78, "  BLOCKED CHECKS:"])
        for bc in audit.blocked_checks:
            lines.append(f"    - {bc}")
    if audit.warnings:
        lines.extend(["-" * 78, "  WARNINGS:"])
        for w in audit.warnings:
            lines.append(f"    - {w}")
    if audit.manual_recovery_recommendations:
        lines.extend(["-" * 78, "  RECOMMENDATIONS:"])
        for rec in audit.manual_recovery_recommendations:
            lines.append(f"    -> {rec}")
    lines.append("=" * 78)
    return "\n".join(lines)


def evaluate_qualification_reports(
    *,
    qualification_report_path: Path,
    evidence_report_path: Path | None = None,
    execution_mode: ExecutionMode | None = None,
    max_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS,
    strict: bool = False,
) -> StagingQualificationAuditReport:
    """Load persisted JSON reports and evaluate the V27 release-gate audit report."""
    qual_report = StagingQualificationReport.model_validate_json(
        qualification_report_path.read_text(encoding="utf-8")
    )
    infra_ev = (
        InfrastructureEvidenceReport.model_validate_json(
            evidence_report_path.read_text(encoding="utf-8")
        )
        if evidence_report_path is not None and evidence_report_path.is_file()
        else None
    )
    evaluator = QualificationEvidenceEvaluator(max_age_seconds=max_age_seconds, strict=strict)
    return evaluator.evaluate(
        report=qual_report,
        execution_mode=execution_mode,
        infrastructure_evidence=infra_ev,
    )
