"""
RegimeX Data Quality — Calendar & Session Validation Rule
=========================================================
Rule IDs:
  - DQ-CAL-001: Observation on non-trading day (weekend / holiday)
  - DQ-CAL-002: Observation outside market trading session hours
"""

from __future__ import annotations

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext
from app.modules.market_data.domain.models import DataInterval

_INTRADAY_INTERVALS = {
    DataInterval.ONE_MIN,
    DataInterval.FIVE_MIN,
    DataInterval.FIFTEEN_MIN,
    DataInterval.THIRTY_MIN,
    DataInterval.ONE_HOUR,
    DataInterval.FOUR_HOUR,
}


class CalendarValidationRule(DataQualityRule):
    """Validates observations against exchange trading calendars and market hours."""

    @property
    def rule_id(self) -> str:
        return "DQ-CAL-001"

    @property
    def name(self) -> str:
        return "Trading Calendar & Session Check"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.CALENDAR

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.WARNING

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        calendar = context.calendar
        interval = context.query.interval
        is_intraday = interval in _INTRADAY_INTERVALS

        for record in context.records:
            ts = record.timestamp
            d = ts.date()

            # DQ-CAL-001: Non-trading day check
            if not calendar.is_trading_day(d):
                issues.append(
                    QualityIssue(
                        rule_id="DQ-CAL-001",
                        category=self.category,
                        severity=QualitySeverity.WARNING,
                        message=(
                            f"Observation on non-trading day ({d.isoformat()}) "
                            f"according to {calendar.name} calendar."
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=d.isoformat(),
                        expected_condition="Observation must occur on active trading session",
                        details={"calendar_id": calendar.calendar_id, "date": d.isoformat()},
                    )
                )

            # DQ-CAL-002: Intraday session hours check
            if is_intraday and not calendar.is_market_open(ts):
                issues.append(
                    QualityIssue(
                        rule_id="DQ-CAL-002",
                        category=self.category,
                        severity=QualitySeverity.WARNING,
                        message=(
                            f"Intraday observation at {ts.isoformat()} falls outside "
                            f"regular trading session hours for {calendar.name}."
                        ),
                        symbol=context.symbol,
                        timestamp=ts,
                        observed_value=ts.isoformat(),
                        expected_condition="Intraday timestamp must fall within regular session",
                        details={
                            "calendar_id": calendar.calendar_id,
                            "session_hours": calendar.get_session_hours().model_dump(),
                        },
                    )
                )

        return issues
