"""
RegimeX Data Quality — Duplicate Detection Rule
===============================================
Rule ID: DQ-DUP-001
Category: DUPLICATE
Severity: CRITICAL

Detects multiple observations sharing the same (symbol, timestamp, interval) key.
"""

from __future__ import annotations

from datetime import datetime

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class DuplicateDetectionRule(DataQualityRule):
    """Detects duplicate timestamps within the dataset."""

    @property
    def rule_id(self) -> str:
        return "DQ-DUP-001"

    @property
    def name(self) -> str:
        return "Duplicate Observation Detection"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.DUPLICATE

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        seen_timestamps: set[datetime] = set()
        duplicate_count = 0

        for record in context.records:
            ts = record.timestamp
            if ts in seen_timestamps:
                duplicate_count += 1
                issues.append(
                    QualityIssue(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.default_severity,
                        message=f"Duplicate observation detected at timestamp {ts.isoformat()}",
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=ts.isoformat(),
                        expected_condition="Unique timestamps per (symbol, interval)",
                        details={"duplicate_index": duplicate_count},
                    )
                )
            else:
                seen_timestamps.add(ts)

        return issues
