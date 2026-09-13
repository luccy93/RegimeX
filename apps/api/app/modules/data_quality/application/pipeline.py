"""
RegimeX Data Quality — Pipeline Orchestration
==============================================
Orchestrates data quality rules over canonical MarketDataResult datasets.

Design:
- Deterministic, configurable, and non-mutating.
- Computes comprehensive QualityReport with status (PASS, WARN, FAIL).
- Accepts explicit reference_time clock for deterministic unit and property testing.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from app.modules.data_quality.application.config import ValidationConfig
from app.modules.data_quality.application.rules import (
    CalendarValidationRule,
    DuplicateDetectionRule,
    GapDetectionRule,
    OHLCIntegrityRule,
    OrderingValidationRule,
    SchemaValidationRule,
    StalenessDetectionRule,
    TimestampIntegrityRule,
    VolumeValidationRule,
)
from app.modules.data_quality.domain.calendar import CalendarRegistry
from app.modules.data_quality.domain.models import (
    QualityIssue,
    QualityReport,
    QualitySeverity,
    QualityStatistics,
    QualityStatus,
)
from app.modules.data_quality.domain.rules import DataQualityRule, RuleContext
from app.modules.data_quality.infrastructure.calendars import (
    create_default_calendar_registry,
)
from app.modules.market_data.domain.models import MarketDataResult


class MarketDataValidationPipeline:
    """
    Production validation pipeline for canonical market data.

    Evaluates a MarketDataResult against schema, financial, timestamp,
    ordering, gap, calendar, and staleness rules.
    """

    def __init__(
        self,
        config: ValidationConfig | None = None,
        calendar_registry: CalendarRegistry | None = None,
        rules: list[DataQualityRule] | None = None,
    ) -> None:
        self._config = config or ValidationConfig()
        self._calendar_registry = calendar_registry or create_default_calendar_registry()

        if rules is not None:
            self._rules = rules
        else:
            self._rules = self._build_default_rules()

    def _build_default_rules(self) -> list[DataQualityRule]:
        """Instantiate enabled rules according to configuration."""
        rules: list[DataQualityRule] = []
        if self._config.enable_schema:
            rules.append(SchemaValidationRule())
        if self._config.enable_timestamp:
            rules.append(TimestampIntegrityRule())
        if self._config.enable_ohlc:
            rules.append(OHLCIntegrityRule())
        if self._config.enable_volume:
            rules.append(VolumeValidationRule())
        if self._config.enable_duplicate:
            rules.append(DuplicateDetectionRule())
        if self._config.enable_ordering:
            rules.append(OrderingValidationRule())
        if self._config.enable_calendar:
            rules.append(CalendarValidationRule())
        if self._config.enable_gap:
            rules.append(GapDetectionRule())
        if self._config.enable_staleness:
            rules.append(StalenessDetectionRule())
        return rules

    def validate(
        self,
        result: MarketDataResult,
        reference_time: datetime | None = None,
    ) -> QualityReport:
        """
        Execute the validation pipeline on a MarketDataResult.

        Args:
            result: Canonical dataset returned by a MarketDataProvider.
            reference_time: Deterministic clock time for freshness/future checks.
                            Defaults to datetime.now(tz=UTC).

        Returns:
            QualityReport containing status, statistics, and detected issues.
        """
        start_wall_time = time.perf_counter()

        ref_time = reference_time or datetime.now(tz=UTC)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=UTC)

        # Resolve trading calendar for instrument
        instrument = result.query.instrument
        calendar = self._calendar_registry.get_for_instrument(
            asset_class=instrument.asset_class,
            exchange=instrument.exchange,
        )

        # Build context
        context = RuleContext(
            query=result.query,
            records=result.records,
            calendar=calendar,
            reference_time=ref_time,
            options={
                "staleness_threshold_hours": self._config.staleness_threshold_hours,
                "future_clock_skew_seconds": self._config.future_clock_skew_seconds,
            },
        )

        # Execute rules
        all_issues: list[QualityIssue] = []
        for rule in self._rules:
            detected = rule.validate(context)
            all_issues.extend(detected)

        # Compile statistics
        total = len(result.records)
        critical_count = sum(1 for i in all_issues if i.severity == QualitySeverity.CRITICAL)
        warning_count = sum(1 for i in all_issues if i.severity == QualitySeverity.WARNING)
        info_count = sum(1 for i in all_issues if i.severity == QualitySeverity.INFO)

        # Identify unique timestamps with critical errors
        critical_timestamps = {
            i.timestamp
            for i in all_issues
            if i.severity == QualitySeverity.CRITICAL and i.timestamp is not None
        }
        valid_records = max(0, total - len(critical_timestamps))

        start_ts = min((r.timestamp for r in result.records), default=None)
        end_ts = max((r.timestamp for r in result.records), default=None)

        elapsed_ms = (time.perf_counter() - start_wall_time) * 1000.0

        stats = QualityStatistics(
            total_records=total,
            valid_records=valid_records,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            execution_duration_ms=round(elapsed_ms, 3),
        )

        # Quality Gate determination
        if critical_count > 0:
            status = QualityStatus.FAIL
        elif warning_count > 0:
            status = QualityStatus.WARN
        else:
            status = QualityStatus.PASS

        return QualityReport(
            symbol=instrument.symbol,
            status=status,
            validated_at=datetime.now(tz=UTC),
            statistics=stats,
            issues=tuple(all_issues),
        )
