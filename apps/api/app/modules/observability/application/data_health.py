"""
RegimeX Observability — Data Health Monitor
===========================================
Evaluates market data freshness, completeness, validity, and operational availability.

Guarantees:
- Consumes authoritative V06 validation outputs without duplicating validation logic.
- Respects exchange trading calendars (NYSE, NSE, continuous 24/7); closed markets
  are never flagged as unhealthy simply because the exchange is closed.
- Thresholds are configurable and deterministic.
- Emits bounded telemetry metrics upon evaluation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.data_quality.domain.calendar import TradingCalendar
from app.modules.data_quality.domain.models import QualityReport, QualityStatus
from app.modules.data_quality.infrastructure.calendars import create_default_calendar_registry
from app.modules.observability.domain.enums import HealthStatus
from app.modules.observability.domain.models import (
    DataCompletenessSnapshot,
    DataFreshnessSnapshot,
    DataHealthSnapshot,
    DataValiditySnapshot,
    PipelineHealthSnapshot,
    ProviderHealthSnapshot,
)
from app.modules.observability.infrastructure.metrics import metrics


class DataHealthMonitor:
    """
    Evaluates point-in-time and time-series data health.
    """

    def __init__(
        self,
        default_calendar_id: str = "nyse",
        freshness_threshold_seconds: float = 86400.0,
        stale_threshold_seconds: float = 259200.0,
    ) -> None:
        self.default_calendar_id = default_calendar_id
        self.freshness_threshold_seconds = freshness_threshold_seconds
        self.stale_threshold_seconds = stale_threshold_seconds
        self._calendar_registry = create_default_calendar_registry()

    def get_calendar(self, calendar_id: str | None = None) -> TradingCalendar:
        """Resolve trading calendar by identifier with fallback to default."""
        cid = calendar_id or self.default_calendar_id
        try:
            return self._calendar_registry.get(cid)
        except KeyError:
            return self._calendar_registry.get(self.default_calendar_id)

    def evaluate_freshness(
        self,
        latest_observation_time: datetime | None,
        as_of: datetime | None = None,
        calendar: TradingCalendar | None = None,
        calendar_id: str | None = None,
        freshness_threshold: float | None = None,
        stale_threshold: float | None = None,
    ) -> DataFreshnessSnapshot:
        """
        Evaluate observation freshness taking into account whether the market is open.
        """
        now = as_of or datetime.now(tz=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        effective_cal_id = (calendar_id or self.default_calendar_id).lower()
        cal = calendar or self.get_calendar(effective_cal_id)
        f_thresh = freshness_threshold or self.freshness_threshold_seconds
        s_thresh = stale_threshold or self.stale_threshold_seconds

        if latest_observation_time is None:
            return DataFreshnessSnapshot(
                latest_observation_time=None,
                freshness_seconds=None,
                market_open=cal.is_market_open(now),
                calendar_id=effective_cal_id,
                status=HealthStatus.UNKNOWN,
                reason="No observations recorded for instrument",
            )

        if latest_observation_time.tzinfo is None:
            latest_observation_time = latest_observation_time.replace(tzinfo=UTC)

        age_seconds = max(0.0, (now - latest_observation_time).total_seconds())
        is_open = cal.is_market_open(now)

        # Calendar-aware freshness rules:
        # If market is currently open:
        #   - age <= f_thresh -> HEALTHY
        #   - f_thresh < age <= s_thresh -> DEGRADED
        #   - age > s_thresh -> STALE
        # If market is closed:
        #   - We verify if latest_observation_time is on or after the most recent trading session.
        #   - Weekend / holiday / overnight pauses are HEALTHY if the latest observation
        #     corresponds to the latest active session.
        if is_open:
            if age_seconds <= f_thresh:
                status = HealthStatus.HEALTHY
                reason = (
                    f"Market is open; observation age ({age_seconds:.0f}s) "
                    f"satisfies SLA (<={f_thresh:.0f}s)"
                )
            elif age_seconds <= s_thresh:
                status = HealthStatus.DEGRADED
                reason = (
                    f"Market is open; observation is delayed ({age_seconds:.0f}s > {f_thresh:.0f}s)"
                )
            else:
                status = HealthStatus.STALE
                reason = (
                    f"Market is open; observation is stale ({age_seconds:.0f}s > {s_thresh:.0f}s)"
                )
        else:
            # Market is closed. Check trading days:
            today = now.date()
            obs_day = latest_observation_time.date()

            # Find expected active trading days in [obs_day, today]
            expected_days = cal.expected_trading_days(obs_day, today)
            # Remove today if market hasn't traded today or is closed before open
            if today in expected_days and not cal.is_trading_day(today):
                expected_days.remove(today)

            # If the difference in scheduled trading days is <= 1 (meaning last closed session),
            # this is completely expected and HEALTHY
            missed_sessions = max(0, len(expected_days) - 1)

            if missed_sessions == 0 or age_seconds <= s_thresh:
                status = HealthStatus.HEALTHY
                reason = (
                    f"Market is closed ({cal.calendar_id}); latest bar from {obs_day.isoformat()} "
                    "aligns with the last scheduled trading session"
                )
            elif missed_sessions == 1:
                status = HealthStatus.DEGRADED
                reason = "Market is closed; feed missed 1 scheduled trading session"
            else:
                status = HealthStatus.STALE
                reason = (
                    f"Market is closed; feed missed {missed_sessions} scheduled trading sessions"
                )

        return DataFreshnessSnapshot(
            latest_observation_time=latest_observation_time,
            freshness_seconds=age_seconds,
            market_open=is_open,
            calendar_id=effective_cal_id,
            status=status,
            reason=reason,
        )

    def evaluate_completeness(
        self,
        expected_rows: int,
        received_rows: int,
        missing_rows: int = 0,
        duplicate_rows: int = 0,
    ) -> DataCompletenessSnapshot:
        """
        Evaluate completeness from observation counts and calendar expectations.
        """
        if expected_rows <= 0:
            ratio = 1.0 if received_rows > 0 else 0.0
            status = HealthStatus.HEALTHY if received_rows > 0 else HealthStatus.UNKNOWN
        else:
            ratio = max(0.0, min(1.0, float(received_rows / expected_rows)))
            if ratio >= 0.98 and missing_rows == 0 and duplicate_rows == 0:
                status = HealthStatus.HEALTHY
            elif ratio >= 0.85 and duplicate_rows <= 5:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

        return DataCompletenessSnapshot(
            expected_rows=max(0, expected_rows),
            received_rows=max(0, received_rows),
            missing_rows=max(0, missing_rows),
            duplicate_rows=max(0, duplicate_rows),
            completeness_ratio=ratio,
            status=status,
        )

    def evaluate_validity(self, report: QualityReport | None) -> DataValiditySnapshot:
        """
        Consume authoritative V06 validation report and format into a validity health snapshot.
        """
        if report is None:
            return DataValiditySnapshot(
                is_valid=False,
                critical_issues_count=0,
                warning_issues_count=0,
                failed_rule_ids=(),
                violations_by_category={},
                status=HealthStatus.UNKNOWN,
            )

        cat_counts: dict[str, int] = {}
        for issue in report.issues:
            cat = str(issue.category.value if hasattr(issue.category, "value") else issue.category)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            # Record violation metric
            sev = str(issue.severity.value if hasattr(issue.severity, "value") else issue.severity)
            metrics.record_quality_violations(category=cat, severity=sev, count=1)

        crit_count = report.statistics.critical_count
        warn_count = report.statistics.warning_count

        if report.status == QualityStatus.PASS:
            status = HealthStatus.HEALTHY
        elif report.status == QualityStatus.WARN:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        return DataValiditySnapshot(
            is_valid=report.is_valid,
            critical_issues_count=crit_count,
            warning_issues_count=warn_count,
            failed_rule_ids=report.failed_rule_ids,
            violations_by_category=cat_counts,
            status=status,
        )

    def evaluate_data_health(
        self,
        symbol: str,
        freshness: DataFreshnessSnapshot,
        completeness: DataCompletenessSnapshot,
        validity: DataValiditySnapshot,
        provider: ProviderHealthSnapshot | None = None,
        pipeline: PipelineHealthSnapshot | None = None,
    ) -> DataHealthSnapshot:
        """
        Combine individual health domains into an immutable DataHealthSnapshot.
        """
        statuses = [freshness.status, completeness.status, validity.status]
        if pipeline is not None:
            statuses.append(pipeline.overall_status)

        # Deterministic hierarchy: UNHEALTHY > STALE > DEGRADED > UNKNOWN > HEALTHY
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.STALE in statuses:
            overall = HealthStatus.STALE
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNKNOWN for s in statuses):
            overall = HealthStatus.UNKNOWN
        else:
            overall = HealthStatus.HEALTHY

        # Build descriptive factual summary
        summary_parts = [
            f"Symbol: {symbol}",
            f"Status: {overall.value}",
            f"Freshness: {freshness.status.value}",
            f"Completeness: {completeness.completeness_ratio * 100:.1f}%",
            (
                f"Validity: {validity.status.value} "
                f"(crit={validity.critical_issues_count}, warn={validity.warning_issues_count})"
            ),
        ]
        if provider is not None:
            summary_parts.append(f"Provider {provider.provider_id}: {provider.status.value}")

        summary = " | ".join(summary_parts)

        # Record metrics telemetry
        metrics.record_data_health(
            status=overall.value,
            provider=provider.provider_id if provider else "default",
            freshness_seconds=freshness.freshness_seconds,
            calendar_id=freshness.calendar_id,
        )

        return DataHealthSnapshot(
            symbol=symbol,
            status=overall,
            freshness=freshness,
            completeness=completeness,
            validity=validity,
            provider=provider,
            pipeline=pipeline,
            summary=summary,
        )
