"""Unit tests verifying GitHub Actions continuous integration workflow invariants.

Ensures .github/workflows/ci.yml adheres to strict security, reproducibility,
pinning, and execution contracts required by RegimeX V25.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow_content() -> str:
    """Read raw workflow content."""
    assert CI_WORKFLOW_PATH.is_file(), f"CI workflow file not found at {CI_WORKFLOW_PATH}"
    return CI_WORKFLOW_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_dict(workflow_content: str) -> dict[Any, Any]:
    """Parse CI workflow YAML into a dictionary."""
    data = yaml.safe_load(workflow_content)
    assert isinstance(data, dict), "Workflow YAML must parse as a top-level mapping"
    return data


def test_ci_workflow_exists_and_parses(workflow_dict: dict[Any, Any]) -> None:
    """Verify workflow file exists, parses as valid YAML, and has expected name."""
    assert workflow_dict.get("name") == "CI"
    assert "jobs" in workflow_dict


def test_ci_workflow_permissions_least_privilege(workflow_dict: dict[Any, Any]) -> None:
    """Verify workflow permissions are strictly limited to contents: read."""
    permissions = workflow_dict.get("permissions")
    assert permissions == {"contents": "read"}, (
        "Top-level permissions must be strictly read-only 'contents: read'"
    )


def test_ci_workflow_triggers(workflow_dict: dict[Any, Any]) -> None:
    """Verify workflow triggers on main PRs, main pushes, and workflow_dispatch."""
    triggers = workflow_dict.get("on") or workflow_dict.get(True)
    assert isinstance(triggers, dict), "Workflow must define trigger mapping"

    assert "pull_request" in triggers
    pr_branches = triggers["pull_request"].get("branches", [])
    assert "main" in pr_branches

    assert "push" in triggers
    push_branches = triggers["push"].get("branches", [])
    assert "main" in push_branches

    assert "workflow_dispatch" in triggers


def test_ci_workflow_concurrency(workflow_dict: dict[Any, Any]) -> None:
    """Verify concurrency group and cancellation configuration."""
    concurrency = workflow_dict.get("concurrency")
    assert isinstance(concurrency, dict)
    assert "${{ github.workflow }}" in concurrency.get("group", "")
    assert "${{ github.ref != 'refs/heads/main' }}" in concurrency.get("cancel-in-progress", "")


def test_ci_workflow_jobs_present(workflow_dict: dict[Any, Any]) -> None:
    """Verify all 6 required CI jobs are present."""
    jobs = workflow_dict.get("jobs", {})
    expected_jobs = {"security", "infra", "backend", "frontend", "docker-build", "ci-gate"}
    assert expected_jobs.issubset(set(jobs.keys()))


def test_backend_job_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify backend job runs on Python 3.11 with all quality checks and pytest."""
    backend = workflow_dict["jobs"]["backend"]
    assert backend.get("runs-on") == "ubuntu-latest"
    assert backend.get("timeout-minutes", 0) <= 20

    env = backend.get("env", {})
    assert env.get("REGIMEX_ENV") == "test"
    assert "SECRET_KEY" in env

    steps = backend.get("steps", [])
    step_runs = [step.get("run", "") for step in steps if "run" in step]
    all_runs = "\n".join(step_runs)

    assert "python -m ruff format --check app tests" in all_runs
    assert "python -m ruff check app tests" in all_runs
    assert "python -m mypy app tests" in all_runs
    assert "python -m pytest tests/ -q" in all_runs

    # Verify python version in setup step
    setup_steps = [s for s in steps if "setup-python" in s.get("uses", "")]
    assert len(setup_steps) == 1
    assert setup_steps[0]["with"]["python-version"] == "3.11"
    assert setup_steps[0]["with"]["cache"] == "pip"


def test_frontend_job_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify frontend job runs on Node 20 with npm ci, test, lint, type-check, and build."""
    frontend = workflow_dict["jobs"]["frontend"]
    assert frontend.get("runs-on") == "ubuntu-latest"
    assert frontend.get("timeout-minutes", 0) <= 20

    env = frontend.get("env", {})
    assert env.get("NODE_ENV") == "production"
    assert env.get("NEXT_TELEMETRY_DISABLED") == 1 or env.get("NEXT_TELEMETRY_DISABLED") == "1"

    steps = frontend.get("steps", [])
    step_runs = [step.get("run", "") for step in steps if "run" in step]
    all_runs = "\n".join(step_runs)

    assert "npm ci" in all_runs
    assert "npm run lint" in all_runs
    assert "npm run type-check" in all_runs
    assert "npm test" in all_runs
    assert "npm run build" in all_runs

    # Verify node version in setup step
    setup_steps = [s for s in steps if "setup-node" in s.get("uses", "")]
    assert len(setup_steps) == 1
    assert setup_steps[0]["with"]["node-version"] == "20"
    assert setup_steps[0]["with"]["cache"] == "npm"


def test_infra_job_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify infra job validates base Compose and prod overlay."""
    infra = workflow_dict["jobs"]["infra"]
    assert infra.get("runs-on") == "ubuntu-latest"

    steps = infra.get("steps", [])
    step_runs = [step.get("run", "") for step in steps if "run" in step]
    all_runs = "\n".join(step_runs)

    assert "docker compose -f infra/docker-compose.yml config --quiet" in all_runs
    assert (
        "docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config --quiet"
        in all_runs
    )


def test_docker_build_job_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify docker-build job builds both API and Web Dockerfiles without pushing."""
    docker_job = workflow_dict["jobs"]["docker-build"]
    assert docker_job.get("runs-on") == "ubuntu-latest"

    steps = docker_job.get("steps", [])
    build_steps = [s for s in steps if "build-push-action" in s.get("uses", "")]
    assert len(build_steps) == 2

    files_built = [s.get("with", {}).get("file") for s in build_steps]
    assert "infra/docker/api.Dockerfile" in files_built
    assert "infra/docker/web.Dockerfile" in files_built

    for step in build_steps:
        with_cfg = step.get("with", {})
        assert with_cfg.get("push") is False, "CI docker build must not push images to a registry"
        assert "tags" in with_cfg


def test_ci_gate_job_configuration(workflow_dict: dict[Any, Any]) -> None:
    """Verify ci-gate job aggregates all upstream checks and fails on any upstream issue."""
    gate = workflow_dict["jobs"]["ci-gate"]
    assert gate.get("if") == "always()"
    needs = set(gate.get("needs", []))
    expected_needs = {"security", "infra", "backend", "frontend", "docker-build"}
    assert needs == expected_needs


def test_third_party_actions_pinned_to_full_commit_sha(workflow_content: str) -> None:
    """Verify all uses: directives for third-party actions pin a 40-character commit SHA."""
    pattern = re.compile(r"uses:\s+([a-zA-Z0-9_\-\/]+)@([a-zA-Z0-9]+)")
    matches = pattern.findall(workflow_content)
    assert len(matches) > 0, "Expected at least one action reference"

    for action_name, ref in matches:
        assert len(ref) == 40 and all(c in "0123456789abcdefABCDEF" for c in ref), (
            f"Action {action_name} must be pinned to a 40-character commit SHA, found: {ref}"
        )
