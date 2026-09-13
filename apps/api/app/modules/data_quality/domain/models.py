"""
RegimeX Data Quality — Canonical Domain Models
===============================================
Defines the structured representations of data quality checks, issues,
reports, statistics, and gate statuses.

Architectural Position:
- Pure domain layer: standard library and Pydantic v2 only.
- No database, no HTTP, no external dependencies.
- Models are immutable (frozen) to guarantee thread safety and audit integrity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class QualitySeverity(StrEnum):
    """Severity levels for data quality violations."""

    CRITICAL = "critical"  # Causes QualityStatus.FAIL (structural / integrity error)
    WARNING = "warning"  # Causes QualityStatus.WARN (gap, staleness, unexpected hour)
    INFO = "info"  # Diagnostic / informational notice


class QualityStatus(StrEnum):
    """Overall validation status of a market data dataset."""

    PASS = "pass"  # noqa: S105
    WARN = "warn"  # Warnings present, but no critical failures
    FAIL = "fail"  # One or more critical failures; data cannot be trusted


class QualityCategory(StrEnum):
    """Domain categories for data quality rules."""

    SCHEMA = "schema"
    TIMESTAMP = "timestamp"
    OHLC = "ohlc"
    VOLUME = "volume"
    DUPLICATE = "duplicate"
    ORDERING = "ordering"
    GAPS = "gaps"
    CALENDAR = "calendar"
    STALENESS = "staleness"


class QualityIssue(BaseModel):
    """
    A single detected data quality issue.

    Attributes:
        rule_id: Stable rule identifier (e.g. 'DQ-OHLC-001').
        category: Broad quality category.
        severity: Issue severity (CRITICAL, WARNING, INFO).
        message: Human-readable description of the violation.
        symbol: Ticker or symbol of the affected instrument.
        timestamp: Observation timestamp where the violation occurred, if applicable.
        observed_value: What value was actually found (sanitized).
        expected_condition: Description of the expected constraint.
        details: Additional context or diagnostics.
    """

    model_config = {"frozen": True}

    rule_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            pattern=r"^DQ-[A-Z]+-[0-9]{3}$",
            description="Stable rule identifier, e.g. 'DQ-OHLC-001'",
        ),
    ]
    category: QualityCategory
    severity: QualitySeverity
    message: Annotated[str, Field(min_length=1, max_length=500)]
    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    timestamp: datetime | None = Field(
        default=None,
        description="UTC timestamp of the affected bar, if specific to a bar.",
    )
    observed_value: Any | None = Field(
        default=None,
        description="Observed value that triggered the rule.",
    )
    expected_condition: str | None = Field(
        default=None,
        description="Expected constraint condition (e.g. 'high >= low').",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary diagnostic metadata.",
    )


class QualityStatistics(BaseModel):
    """Aggregated numerical statistics for a validation run."""

    model_config = {"frozen": True}

    total_records: int = Field(ge=0, description="Total number of input bars evaluated.")
    valid_records: int = Field(ge=0, description="Number of bars without critical violations.")
    critical_count: int = Field(ge=0, description="Count of critical severity issues.")
    warning_count: int = Field(ge=0, description="Count of warning severity issues.")
    info_count: int = Field(ge=0, description="Count of informational notices.")
    start_timestamp: datetime | None = Field(
        default=None,
        description="Earliest timestamp in evaluated dataset.",
    )
    end_timestamp: datetime | None = Field(
        default=None,
        description="Latest timestamp in evaluated dataset.",
    )
    execution_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Pipeline execution duration in milliseconds.",
    )


class QualityReport(BaseModel):
    """
    Final validation verdict and quality assessment for a dataset.

    Produced by MarketDataValidationPipeline and passed to future storage / feature layers.
    """

    model_config = {"frozen": True}

    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    status: QualityStatus
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when the validation pipeline ran.",
    )
    statistics: QualityStatistics
    issues: tuple[QualityIssue, ...] = Field(
        default=(),
        description="Chronological or prioritized collection of detected issues.",
    )

    @property
    def is_valid(self) -> bool:
        """True when the dataset passes quality gates (PASS or WARN, not FAIL)."""
        return self.status != QualityStatus.FAIL

    @property
    def has_warnings(self) -> bool:
        """True when warnings are present."""
        return self.status == QualityStatus.WARN

    @property
    def issue_count(self) -> int:
        """Total count of issues."""
        return len(self.issues)

    @property
    def failed_rule_ids(self) -> tuple[str, ...]:
        """Tuple of distinct rule IDs that triggered critical failures."""
        return tuple(
            sorted({i.rule_id for i in self.issues if i.severity == QualitySeverity.CRITICAL})
        )
