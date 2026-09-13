"""
RegimeX Data Quality — Staleness Detection Rule
===============================================
Rule ID: DQ-STALE-001
Category: STALENESS
Severity: WARNING

Detects datasets whose latest observation exceeds the configured freshness threshold.
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class StalenessDetectionRule(DataQualityRule):
    """Checks whether the latest observation in the dataset is stale."""

    @property
    def rule_id(self) -> str:
        return "DQ-STALE-001"

    @property
    def name(self) -> str:
        return "Data Freshness / Staleness Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.STALENESS

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.WARNING

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        if context.is_empty:
            return issues

        latest_record = max(context.records, key=lambda r: r.timestamp)
        threshold_hours = float(context.options.get("staleness_threshold_hours", 72.0))
        max_staleness = timedelta(hours=threshold_hours)

        age = context.reference_time - latest_record.timestamp

        if age > max_staleness:
            age_hours = age.total_seconds() / 3600.0
            issues.append(
                QualityIssue(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.default_severity,
                    message=(
                        f"Dataset for {context.symbol} is stale. "
                        f"Latest bar is {age_hours:.1f} hours old "
                        f"(threshold: {threshold_hours:.1f}h) relative to reference clock."
                    ),
                    symbol=context.symbol,
                    timestamp=latest_record.timestamp,
                    observed_value=f"{age_hours:.1f} hours",
                    expected_condition=f"Latest observation age <= {threshold_hours}h",
                    details={
                        "latest_timestamp": latest_record.timestamp.isoformat(),
                        "reference_time": context.reference_time.isoformat(),
                        "age_hours": round(age_hours, 2),
                        "threshold_hours": threshold_hours,
                    },
                )
            )

        return issues
