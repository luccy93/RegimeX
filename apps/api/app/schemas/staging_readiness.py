"""Pydantic schemas and domain models for RegimeX staging readiness preflight.

Defines check statuses, category summaries, and the machine-readable
preflight report schema.
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
