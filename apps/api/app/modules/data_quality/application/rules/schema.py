"""
RegimeX Data Quality — Schema Validation Rule
=============================================
Rule ID: DQ-SCHEMA-001
Category: SCHEMA
Severity: CRITICAL

Verifies that all OHLCV numbers are finite (no NaN, +Inf, -Inf) and fields are valid.
"""

from __future__ import annotations

import math

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class SchemaValidationRule(DataQualityRule):
    """Checks that OHLCV numeric fields contain valid finite numbers."""

    @property
    def rule_id(self) -> str:
        return "DQ-SCHEMA-001"

    @property
    def name(self) -> str:
        return "Finite Numeric Values Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.SCHEMA

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        for record in context.records:
            fields = {
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
            }

            for field_name, val in fields.items():
                if not math.isfinite(val):
                    issues.append(
                        QualityIssue(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.default_severity,
                            message=f"Non-finite numeric value found in {field_name}: {val}",
                            symbol=context.symbol,
                            timestamp=record.timestamp,
                            observed_value=str(val),
                            expected_condition=f"{field_name} must be a finite float",
                            details={"field": field_name, "value": str(val)},
                        )
                    )

        return issues
