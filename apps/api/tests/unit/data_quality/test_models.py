"""
Unit tests for data quality domain models.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualityReport,
    QualitySeverity,
    QualityStatistics,
    QualityStatus,
)
from pydantic import ValidationError


class TestQualityModels:
    def test_enums(self) -> None:
        assert QualitySeverity.CRITICAL.value == "critical"
        assert QualitySeverity.WARNING.value == "warning"
        assert QualitySeverity.INFO.value == "info"

        assert QualityStatus.PASS.value == "pass"
        assert QualityStatus.WARN.value == "warn"
        assert QualityStatus.FAIL.value == "fail"

        assert QualityCategory.OHLC.value == "ohlc"
        assert QualityCategory.SCHEMA.value == "schema"

    def test_quality_issue_creation(self) -> None:
        issue = QualityIssue(
            rule_id="DQ-OHLC-001",
            category=QualityCategory.OHLC,
            severity=QualitySeverity.CRITICAL,
            message="High less than low",
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            observed_value=180.0,
            expected_condition="high >= low",
            details={"high": 180.0, "low": 185.0},
        )
        assert issue.rule_id == "DQ-OHLC-001"
        assert issue.category == QualityCategory.OHLC
        assert issue.severity == QualitySeverity.CRITICAL
        assert issue.observed_value == 180.0

    def test_quality_issue_rule_id_pattern(self) -> None:
        with pytest.raises(ValidationError):
            QualityIssue(
                rule_id="INVALID_ID",
                category=QualityCategory.OHLC,
                severity=QualitySeverity.CRITICAL,
                message="Bad ID",
                symbol="AAPL",
            )

    def test_quality_issue_frozen(self) -> None:
        issue = QualityIssue(
            rule_id="DQ-TIME-001",
            category=QualityCategory.TIMESTAMP,
            severity=QualitySeverity.CRITICAL,
            message="Naive timestamp",
            symbol="AAPL",
        )
        with pytest.raises((ValidationError, TypeError)):
            issue.message = "Attempted modification"  # type: ignore[misc]

    def test_quality_report_properties_pass(self) -> None:
        stats = QualityStatistics(
            total_records=10,
            valid_records=10,
            critical_count=0,
            warning_count=0,
            info_count=0,
        )
        report = QualityReport(
            symbol="AAPL",
            status=QualityStatus.PASS,
            statistics=stats,
            issues=(),
        )
        assert report.is_valid
        assert not report.has_warnings
        assert report.issue_count == 0
        assert report.failed_rule_ids == ()

    def test_quality_report_properties_warn(self) -> None:
        stats = QualityStatistics(
            total_records=10,
            valid_records=10,
            critical_count=0,
            warning_count=1,
            info_count=0,
        )
        warn_issue = QualityIssue(
            rule_id="DQ-GAP-001",
            category=QualityCategory.GAPS,
            severity=QualitySeverity.WARNING,
            message="Missing bar",
            symbol="AAPL",
        )
        report = QualityReport(
            symbol="AAPL",
            status=QualityStatus.WARN,
            statistics=stats,
            issues=(warn_issue,),
        )
        assert report.is_valid
        assert report.has_warnings
        assert report.issue_count == 1
        assert report.failed_rule_ids == ()  # only critical issues populate failed_rule_ids

    def test_quality_report_properties_fail(self) -> None:
        stats = QualityStatistics(
            total_records=10,
            valid_records=9,
            critical_count=1,
            warning_count=0,
            info_count=0,
        )
        fail_issue = QualityIssue(
            rule_id="DQ-OHLC-001",
            category=QualityCategory.OHLC,
            severity=QualitySeverity.CRITICAL,
            message="High less than low",
            symbol="AAPL",
        )
        report = QualityReport(
            symbol="AAPL",
            status=QualityStatus.FAIL,
            statistics=stats,
            issues=(fail_issue,),
        )
        assert not report.is_valid
        assert not report.has_warnings
        assert report.issue_count == 1
        assert report.failed_rule_ids == ("DQ-OHLC-001",)
