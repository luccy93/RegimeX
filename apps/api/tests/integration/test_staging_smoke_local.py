"""Local ASGI integration tests for RegimeX staging smoke suite (V27 Commit 02).

Executes the read-only backend, API contract, and service smoke stages directly
against the real FastAPI application via httpx.ASGITransport without requiring
any external staging host or network access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from app.core.staging_qualification import QualificationContext
from app.core.staging_smoke import StagingSmokeSuite
from app.main import create_app
from app.schemas.staging_readiness import (
    AuthStatus,
    CategorySummary,
    CheckStatus,
    DockerReadinessEvidence,
    GHCRAccessEvidence,
    GitHubAccessEvidence,
    GPUCapabilityEvidence,
    InfrastructureEvidenceReport,
    QualificationStatus,
    ReleaseManifestEvidence,
    RollbackReadinessEvidence,
    SmokeCredentialEvidence,
    StagingGateEvaluationReport,
    StagingPreflightReport,
)
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VALID_SHA = "7cd7701a6c51205cab70271c857c1609e68d7b01"


class _SyncASGITransport(httpx.BaseTransport):
    """Bridge synchronous httpx.Client calls to FastAPI ASGI app in-process."""

    def __init__(self, tc: TestClient) -> None:
        self._tc = tc

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path_with_query = request.url.raw_path.decode("ascii")
        resp = self._tc.request(
            request.method,
            path_with_query,
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            status_code=resp.status_code,
            headers=resp.headers,
            content=resp.content,
        )


def _make_context() -> QualificationContext:
    summary = CategorySummary(
        category="host",
        status=CheckStatus.PASS,
        total_checks=1,
        passed_checks=1,
        failed_checks=0,
        blocked_checks=0,
        warning_checks=0,
        not_configured_checks=0,
        not_run_checks=0,
        checks=[],
    )
    pf = StagingPreflightReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        host=summary,
        runtime=summary,
        security=summary,
        release=summary,
    )
    ev = InfrastructureEvidenceReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        timestamp=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
        docker=DockerReadinessEvidence(
            status=CheckStatus.PASS, engine_accessible=True, compose_available=True
        ),
        github=GitHubAccessEvidence(
            status=CheckStatus.PASS, cli_available=True, auth_status=AuthStatus.AUTHENTICATED
        ),
        ghcr=GHCRAccessEvidence(status=CheckStatus.PASS, auth_status=AuthStatus.AUTHENTICATED),
        release_manifest=ReleaseManifestEvidence(
            status=CheckStatus.PASS, immutable_digests_verified=True
        ),
        smoke_credentials=SmokeCredentialEvidence(status=CheckStatus.PASS),
        rollback=RollbackReadinessEvidence(status=CheckStatus.PASS),
        gpu=GPUCapabilityEvidence(status=CheckStatus.WARNING, mandatory=False),
    )
    gate = StagingGateEvaluationReport(
        schema_version="1.0.0",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        evaluated_at=datetime.now(UTC).isoformat(),
        overall_status=CheckStatus.PASS,
        is_ready=True,
    )
    return QualificationContext(
        run_id="qual-local-integration",
        environment="staging",
        repository="luccy93/RegimeX",
        commit_sha=VALID_SHA,
        release_tag=f"regimex-{VALID_SHA[:8]}",
        dry_run=False,
        strict=False,
        env={"REGIMEX_AI_PROVIDER": "mock"},
        preflight_report=pf,
        evidence_report=ev,
        gate_report=gate,
        staging_api_url="http://staging-local.internal:8000",
        staging_web_url="http://staging-local.internal:3000",
    )


@pytest.mark.integration
def test_local_fastapi_backend_and_contract_smoke_stages() -> None:
    """Run real FastAPI ASGI smoke checks for health, API contract, and services."""
    app = create_app()
    with TestClient(app, base_url="http://staging-local.internal:8000") as tc:
        transport = _SyncASGITransport(tc)
        suite = StagingSmokeSuite(api_transport=transport, repo_root=REPO_ROOT)
        ctx = _make_context()

        backend_res = suite.run_backend_health_stage(ctx)
        assert backend_res.status == QualificationStatus.PASS

        contract_res = suite.run_api_contract_stage(ctx)
        assert contract_res.status == QualificationStatus.PASS

        service_res = suite.run_service_stage(ctx)
        assert service_res.status in (QualificationStatus.PASS, QualificationStatus.WARNING)
