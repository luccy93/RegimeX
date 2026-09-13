"""
RegimeX Data Quality — OHLC Integrity Rules
============================================
Rule IDs:
  - DQ-OHLC-001: High price less than Open, Close, or Low
  - DQ-OHLC-002: Low price greater than Open, Close, or High
  - DQ-OHLC-003: Non-positive price values (<= 0)
"""

from __future__ import annotations

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext


class OHLCIntegrityRule(DataQualityRule):
    """Validates financial consistency across Open, High, Low, and Close prices."""

    @property
    def rule_id(self) -> str:
        return "DQ-OHLC-001"

    @property
    def name(self) -> str:
        return "OHLC Price Integrity Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.OHLC

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.CRITICAL

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []

        for record in context.records:
            open_val = record.open
            high_val = record.high
            low_val = record.low
            close_val = record.close
            ts = record.timestamp

            # DQ-OHLC-003: Non-positive prices
            if open_val <= 0 or high_val <= 0 or low_val <= 0 or close_val <= 0:
                issues.append(
                    QualityIssue(
                        rule_id="DQ-OHLC-003",
                        category=self.category,
                        severity=QualitySeverity.CRITICAL,
                        message=(
                            f"Non-positive price found: O={open_val}, H={high_val}, "
                            f"L={low_val}, C={close_val}"
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value={
                            "open": open_val,
                            "high": high_val,
                            "low": low_val,
                            "close": close_val,
                        },
                        expected_condition="All prices must be strictly positive (> 0)",
                    )
                )

            # DQ-OHLC-001: High less than other prices
            if high_val < low_val or high_val < open_val or high_val < close_val:
                issues.append(
                    QualityIssue(
                        rule_id="DQ-OHLC-001",
                        category=self.category,
                        severity=QualitySeverity.CRITICAL,
                        message=(
                            f"High price {high_val} is less than O={open_val}, "
                            f"L={low_val}, or C={close_val}"
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=high_val,
                        expected_condition="high >= max(open, close, low)",
                        details={
                            "open": open_val,
                            "high": high_val,
                            "low": low_val,
                            "close": close_val,
                        },
                    )
                )

            # DQ-OHLC-002: Low greater than other prices
            if low_val > high_val or low_val > open_val or low_val > close_val:
                issues.append(
                    QualityIssue(
                        rule_id="DQ-OHLC-002",
                        category=self.category,
                        severity=QualitySeverity.CRITICAL,
                        message=(
                            f"Low price {low_val} is greater than O={open_val}, "
                            f"H={high_val}, or C={close_val}"
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=low_val,
                        expected_condition="low <= min(open, close, high)",
                        details={
                            "open": open_val,
                            "high": high_val,
                            "low": low_val,
                            "close": close_val,
                        },
                    )
                )

        return issues
