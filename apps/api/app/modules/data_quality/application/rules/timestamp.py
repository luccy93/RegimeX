"""
RegimeX Data Quality — Timestamp Integrity Rules
=================================================
Rule IDs:
  - DQ-TIME-001: Timezone awareness and UTC normalization
  - DQ-TIME-002: Future timestamp detection
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class TimestampIntegrityRule(DataQualityRule):
    """Validates timezone awareness (UTC) and absence of future-dated observations."""

    @property
    def rule_id(self) -> str:
        return "DQ-TIME-001"

    @property
    def name(self) -> str:
        return "Timestamp Timezone & Future Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.TIMESTAMP

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        clock_skew = timedelta(
            seconds=float(context.options.get("future_clock_skew_seconds", 300.0))
        )
        cutoff = context.reference_time + clock_skew

        for record in context.records:
            ts = record.timestamp

            # DQ-TIME-001: Check timezone awareness and UTC offset
            if ts.tzinfo is None or ts.utcoffset() != timedelta(0):
                issues.append(
                    QualityIssue(
                        rule_id="DQ-TIME-001",
                        category=self.category,
                        severity=QualitySeverity.CRITICAL,
                        message=f"Bar timestamp is not UTC-aware: {ts!r}",
                        symbol=context.symbol,
                        timestamp=ts if ts.tzinfo is not None else None,
                        observed_value=str(ts.tzinfo),
                        expected_condition="Timestamp must be UTC-aware (tzinfo=UTC)",
                    )
                )

            # DQ-TIME-002: Check for future observations relative to reference clock
            if ts > cutoff:
                issues.append(
                    QualityIssue(
                        rule_id="DQ-TIME-002",
                        category=self.category,
                        severity=QualitySeverity.CRITICAL,
                        message=(
                            f"Observation timestamp {ts.isoformat()} is in the future "
                            f"relative to reference clock {context.reference_time.isoformat()}."
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=ts.isoformat(),
                        expected_condition=f"timestamp <= {cutoff.isoformat()}",
                        details={
                            "reference_time": context.reference_time.isoformat(),
                            "cutoff": cutoff.isoformat(),
                        },
                    )
                )

        return issues
