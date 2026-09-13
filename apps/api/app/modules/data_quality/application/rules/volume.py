"""
RegimeX Data Quality — Volume Validation Rule
=============================================
Rule ID: DQ-VOL-001
Category: VOLUME
Severity: CRITICAL

Verifies that traded volume is non-negative and finite.
"""

from __future__ import annotations

import math

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class VolumeValidationRule(DataQualityRule):
    """Validates that volume is finite and non-negative."""

    @property
    def rule_id(self) -> str:
        return "DQ-VOL-001"

    @property
    def name(self) -> str:
        return "Non-Negative Volume Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.VOLUME

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        for record in context.records:
            v = record.volume
            if not math.isfinite(v) or v < 0:
                issues.append(
                    QualityIssue(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.default_severity,
                        message=f"Invalid volume value observed: {v}",
                        symbol=context.symbol,
                        timestamp=record.timestamp,
                        observed_value=v,
                        expected_condition="volume >= 0 and isfinite(volume)",
                    )
                )

        return issues
