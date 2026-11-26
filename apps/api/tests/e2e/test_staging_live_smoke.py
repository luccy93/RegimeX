"""Opt-in live staging smoke-test suite (V27 Commit 02).

NEVER runs during ordinary unit-test or CI runs. Requires explicit opt-in via:
    REGIMEX_STAGING_LIVE_TESTS=1

Even when opted in, refuses to execute if:
- Environment is not explicitly 'staging'
- STAGING_API_URL or STAGING_WEB_URL is missing or identifies production
- Required staging credentials are missing
- V26 readiness gate has failed
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from app.core.staging_evidence import InfrastructureEvidenceCollector
from app.core.staging_gates import StagingReadinessGateEvaluator
from app.core.staging_qualification import StagingQualificationOrchestrator
from app.core.staging_readiness import StagingPreflightInspector
from app.core.staging_smoke import StagingLiveTestGuard, build_smoke_stage_registry
from app.schemas.staging_readiness import QualificationStatus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
LIVE_TESTS_ENABLED = StagingLiveTestGuard.is_live_opted_in(os.environ)


@pytest.mark.e2e
@pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="Opt-in live staging tests disabled (set REGIMEX_STAGING_LIVE_TESTS=1)",
)
def test_live_staging_service_qualification() -> None:
    """Execute read-only service qualification against an explicitly configured live staging."""
    env = os.environ.copy()
    inspector = StagingPreflightInspector(repo_root=REPO_ROOT, environment="staging", env=env)
    preflight = inspector.run_preflight()
    collector = InfrastructureEvidenceCollector(repo_root=REPO_ROOT, environment="staging", env=env)
    evidence = collector.collect_full_evidence()
    gate_report = StagingReadinessGateEvaluator(repo_root=REPO_ROOT, env=env).evaluate_gates(
        preflight=preflight,
        evidence=evidence,
    )

    guard = StagingLiveTestGuard.evaluate(
        env=env,
        environment=env.get("REGIMEX_STAGING_ENV", "staging"),
        gate_report=gate_report,
    )
    if not guard.allowed:
        pytest.fail(f"Live staging guard refused execution ({guard.status.value}): {guard.reason}")

    orch = StagingQualificationOrchestrator(
        repo_root=REPO_ROOT,
        environment="staging",
        preflight_report=preflight,
        evidence_report=evidence,
        stage_registry=build_smoke_stage_registry(),
        env=env,
    )
    report = orch.run_qualification()
    assert report.overall_status in (QualificationStatus.PASS, QualificationStatus.WARNING)
    assert report.qualification_passed is True
    assert report.live_qualification_authorized is False
    assert report.production_deployment_authorized is False
