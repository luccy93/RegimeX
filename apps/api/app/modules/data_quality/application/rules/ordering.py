"""
RegimeX Data Quality — Ordering Validation Rule
===============================================
Rule ID: DQ-ORDER-001
Category: ORDERING
Severity: CRITICAL

Verifies that market data records arrive in strictly ascending chronological order.
"""

from __future__ import annotations

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class OrderingValidationRule(DataQualityRule):
    """Enforces strictly increasing chronological ordering of observations."""

    @property
    def rule_id(self) -> str:
        return "DQ-ORDER-001"

    @property
    def name(self) -> str:
        return "Monotonic Chronological Ordering Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.ORDERING

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        records = context.records

        if len(records) < 2:
            return issues

        for i in range(1, len(records)):
            prev = records[i - 1].timestamp
            curr = records[i].timestamp

            # Monotonically increasing requires curr > prev
            if curr <= prev:
                issues.append(
                    QualityIssue(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.default_severity,
                        message=(
                            f"Out-of-order observation at index {i}: "
                            f"current ({curr.isoformat()}) <= previous ({prev.isoformat()})"
                        ),
                        symbol=context.symbol,
                        timestamp=curr,
                        observed_value=curr.isoformat(),
                        expected_condition=f"timestamp > {prev.isoformat()}",
                        details={"index": i, "previous_timestamp": prev.isoformat()},
                    )
                )

        return issues
