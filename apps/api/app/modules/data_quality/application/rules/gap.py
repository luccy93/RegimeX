"""
RegimeX Data Quality — Gap Detection Rule
=========================================
Rule ID: DQ-GAP-001
Category: GAPS
Severity: WARNING

Detects missing trading sessions or observations according to the exchange calendar.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext
from app.modules.market_data.domain.models import DataInterval

_INTERVAL_DELTA_MAP: dict[DataInterval, timedelta] = {
    DataInterval.ONE_MIN: timedelta(minutes=1),
    DataInterval.FIVE_MIN: timedelta(minutes=5),
    DataInterval.FIFTEEN_MIN: timedelta(minutes=15),
    DataInterval.THIRTY_MIN: timedelta(minutes=30),
    DataInterval.ONE_HOUR: timedelta(hours=1),
    DataInterval.FOUR_HOUR: timedelta(hours=4),
}


class GapDetectionRule(DataQualityRule):
    """Detects missing observations relative to trading calendar schedules."""

    @property
    def rule_id(self) -> str:
        return "DQ-GAP-001"

    @property
    def name(self) -> str:
        return "Trading Gap Detection"

    @property
    def category(self) -> QualityCategory:
        return QualityCategory.GAPS

    @property
    def default_severity(self) -> QualitySeverity:
        return QualitySeverity.WARNING

    def validate(self, context: RuleContext) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        records = context.records

        if len(records) < 2:
            return issues

        calendar = context.calendar
        interval = context.query.interval

        # Case 1: Daily interval - compare against expected trading calendar dates
        if interval == DataInterval.ONE_DAY:
            observed_dates: set[date] = {r.timestamp.date() for r in records}
            min_date = min(observed_dates)
            max_date = max(observed_dates)

            expected_days = calendar.expected_trading_days(min_date, max_date)
            for expected_day in expected_days:
                if expected_day not in observed_dates:
                    issues.append(
                        QualityIssue(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.default_severity,
                            message=(
                                f"Missing expected trading session on {expected_day.isoformat()} "
                                f"for {calendar.name}."
                            ),
                            symbol=context.symbol,
                            observed_value=None,
                            expected_condition=(
                                f"Observation expected for date {expected_day.isoformat()}"
                            ),
                            details={
                                "missing_date": expected_day.isoformat(),
                                "calendar_id": calendar.calendar_id,
                            },
                        )
                    )

        # Case 2: Intraday intervals - check consecutive bars on the same trading day
        elif interval in _INTERVAL_DELTA_MAP:
            expected_delta = _INTERVAL_DELTA_MAP[interval]
            # Allow up to 1.5x expected delta before flagging missing bars
            max_allowed_delta = expected_delta * 1.5

            for i in range(1, len(records)):
                prev = records[i - 1].timestamp
                curr = records[i].timestamp

                # Only check intraday gap if on the exact same date and market session
                if prev.date() == curr.date():
                    actual_delta = curr - prev
                    if actual_delta > max_allowed_delta:
                        issues.append(
                            QualityIssue(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=self.default_severity,
                                message=(
                                    f"Intraday gap detected between {prev.isoformat()} and "
                                    f"{curr.isoformat()} (delta: {actual_delta}, "
                                    f"expected: {expected_delta})."
                                ),
                                symbol=context.symbol,
                                timestamp=curr,
                                observed_value=str(actual_delta),
                                expected_condition=f"Bar delta <= {max_allowed_delta}",
                                details={
                                    "previous": prev.isoformat(),
                                    "current": curr.isoformat(),
                                    "delta_seconds": actual_delta.total_seconds(),
                                },
                            )
                        )

        return issues
