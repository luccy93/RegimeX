"""Unit tests verifying GitHub Actions protected production deployment workflow invariants.

Ensures .github/workflows/deploy.yml adheres to strict security, exact-SHA CI verification,
production environment protection, immutable release identification, and migration boundaries
required by RegimeX V25 Commit 02.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEPLOY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


@pytest.fixture(scope="module")
def workflow_content() -> str:
    """Read raw deploy workflow content."""
    assert DEPLOY_WORKFLOW_PATH.is_file(), (
        f"Deploy workflow file not found at {DEPLOY_WORKFLOW_PATH}"
    )
    return DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_dict(workflow_content: str) -> dict[Any, Any]:
    """Parse deploy workflow YAML into a dictionary."""
    data = yaml.safe_load(workflow_content)
    assert isinstance(data, dict), "Workflow YAML must parse as a top-level mapping"
    return data


def test_deploy_workflow_exists_and_parses(workflow_dict: dict[Any, Any]) -> None:
    """Verify deploy workflow file exists, parses as valid YAML, and has expected name."""
    assert workflow_dict.get("name") == "Production Deployment"
    assert "jobs" in workflow_dict


def test_deploy_workflow_permissions_least_privilege(workflow_dict: dict[Any, Any]) -> None:
    """Verify workflow permissions are strictly limited to contents: read and actions: read."""
    permissions = workflow_dict.get("permissions")
    assert isinstance(permissions, dict)
    assert permissions.get("contents") == "read"
    assert permissions.get("actions") == "read"
    # Ensure write permissions are not broadly granted at workflow level
    assert "write" not in str(permissions)


def test_deploy_workflow_triggers_protected(workflow_dict: dict[Any, Any]) -> None:
    """Verify deploy workflow only triggers via workflow_run (CI on main) or workflow_dispatch."""
    triggers = workflow_dict.get("on") or workflow_dict.get(True)
    assert isinstance(triggers, dict), "Workflow must define trigger mapping"

    # Must NOT trigger on pull_request or pull_request_target
    assert "pull_request" not in triggers, "Deploy workflow must never trigger on pull_request"
    assert "pull_request_target" not in triggers, (
        "Deploy workflow must never trigger on pull_request_target"
    )

    # Must support workflow_run from CI on main
    assert "workflow_run" in triggers
    wf_run = triggers["workflow_run"]
    assert "CI" in wf_run.get("workflows", [])
    assert "main" in wf_run.get("branches", [])
    assert "completed" in wf_run.get("types", [])

    # Must support manual dispatch
    assert "workflow_dispatch" in triggers


def test_deploy_workflow_concurrency(workflow_dict: dict[Any, Any]) -> None:
    """Verify strict concurrency preventing simultaneous production deployments."""
    concurrency = workflow_dict.get("concurrency")
    assert isinstance(concurrency, dict)
    assert concurrency.get("group") == "production-deployment"
    assert concurrency.get("cancel-in-progress") is False, (
        "Production deployment concurrency must NOT cancel in-progress runs"
    )


def test_deploy_workflow_jobs_structure(workflow_dict: dict[Any, Any]) -> None:
    """Verify presence and dependency ordering of deployment jobs."""
    jobs = workflow_dict.get("jobs", {})
    expected_jobs = {"verify", "migration-preflight", "deploy"}
    assert expected_jobs.issubset(set(jobs.keys()))

    # Verify dependency chain
    assert "verify" in jobs["migration-preflight"].get("needs", [])
    deploy_needs = jobs["deploy"].get("needs", [])
    assert "verify" in deploy_needs
    assert "migration-preflight" in deploy_needs


def test_deploy_workflow_production_environment(workflow_dict: dict[Any, Any]) -> None:
    """Verify deployment jobs use the protected 'production' environment."""
    jobs = workflow_dict.get("jobs", {})

    # migration-preflight and deploy jobs must bind to the production environment
    for job_name in ("migration-preflight", "deploy"):
        job = jobs[job_name]
        env_cfg = job.get("environment")
        if isinstance(env_cfg, dict):
            assert env_cfg.get("name") == "production"
        else:
            assert env_cfg == "production"


def test_exact_sha_ci_verification_in_verify_job(workflow_dict: dict[Any, Any]) -> None:
    """Verify the verify job enforces exact-SHA CI success before deployment."""
    verify_job = workflow_dict["jobs"]["verify"]
    steps = verify_job.get("steps", [])
    step_runs = "\n".join(s.get("run", "") for s in steps if "run" in s)

    # Verifies triggering workflow and conclusion
    assert "TRIGGER_WORKFLOW" in step_runs or "CI" in step_runs
    assert "TRIGGER_CONCLUSION" in step_runs or "success" in step_runs
    assert "DEPLOY_SHA" in step_runs
    assert "target_sha" in str(verify_job.get("outputs", {}))


def test_immutable_release_identification(workflow_dict: dict[Any, Any]) -> None:
    """Verify release identification uses Git SHA, run ID, and SHA-based tags."""
    verify_job = workflow_dict["jobs"]["verify"]
    outputs = verify_job.get("outputs", {})
    assert "target_sha" in outputs
    assert "release_timestamp" in outputs
    assert "api_tag" in outputs
    assert "web_tag" in outputs

    deploy_job = workflow_dict["jobs"]["deploy"]
    deploy_runs = "\n".join(s.get("run", "") for s in deploy_job.get("steps", []) if "run" in s)
    assert "Release SHA:" in deploy_runs
    assert "Run ID:" in deploy_runs
    assert "API Image Tag:" in deploy_runs


def test_migration_boundary_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify database migration preflight checks Alembic configuration and forward-only policy."""
    migration_job = workflow_dict["jobs"]["migration-preflight"]
    steps = migration_job.get("steps", [])
    migration_runs = "\n".join(s.get("run", "") for s in steps if "run" in s)

    assert "alembic upgrade head" in migration_runs
    assert "apps/api/alembic.ini" in migration_runs
    assert "apps/api/alembic/versions" in migration_runs


def test_third_party_actions_pinned_to_full_commit_sha(workflow_content: str) -> None:
    """Verify all uses: directives for third-party actions pin a 40-character commit SHA."""
    pattern = re.compile(r"uses:\s+([a-zA-Z0-9_\-\/]+)@([a-zA-Z0-9]+)")
    matches = pattern.findall(workflow_content)
    assert len(matches) > 0, "Expected at least one action reference"

    for action_name, ref in matches:
        assert len(ref) == 40 and all(c in "0123456789abcdefABCDEF" for c in ref), (
            f"Action {action_name} must be pinned to a 40-character commit SHA, found: {ref}"
        )


def test_automated_deployment_orchestration_and_artifact_upload(
    workflow_dict: dict[Any, Any],
) -> None:
    """Verify deployment job executes scripts/deploy.py and uploads deployment-summary.json."""
    deploy_job = workflow_dict["jobs"]["deploy"]
    steps = deploy_job.get("steps", [])

    # Verify script execution step
    exec_steps = [s for s in steps if "python scripts/deploy.py" in s.get("run", "")]
    assert len(exec_steps) == 1, "Must contain exactly one scripts/deploy.py execution step"
    exec_run = exec_steps[0]["run"]
    assert "--commit-sha" in exec_run
    assert "--run-id" in exec_run
    assert "--output-summary" in exec_run
    assert "deployment-summary.json" in exec_run
    assert "--allow-unconfigured" in exec_run

    # Verify artifact upload step
    upload_steps = [s for s in steps if "upload-artifact" in s.get("uses", "")]
    assert len(upload_steps) == 1, "Must contain artifact upload step"
    upload_step = upload_steps[0]
    assert upload_step.get("if") == "always()", (
        "Artifact upload must run unconditionally (if: always())"
    )
    with_clause = upload_step.get("with", {})
    assert with_clause.get("name") == "deployment-summary"
    assert with_clause.get("path") == "deployment-summary.json"
