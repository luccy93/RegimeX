"""
Unit tests for individual data quality rules.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from app.modules.data_quality.domain.models import (
    QualitySeverity,
)
from app.modules.data_quality.domain.rules import RuleContext
from app.modules.data_quality.infrastructure.calendars import (
    ContinuousCalendar,
)
from app.modules.market_data.domain.models import (
    DataInterval,
    OHLCVRecord,
)


class TestSchemaValidationRule:
    def test_clean_records_pass(self, clean_rule_context: RuleContext) -> None:
        rule = SchemaValidationRule()
        issues = rule.validate(clean_rule_context)
        assert len(issues) == 0

    def test_nan_price_detected(self, clean_rule_context: RuleContext) -> None:
        # Pydantic v2 enforces float type; creating an object with nan
        bad_record = OHLCVRecord.model_construct(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=float("nan"),
            high=187.0,
            low=184.5,
            close=186.0,
            volume=1000.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (bad_record,)})
        rule = SchemaValidationRule()
        issues = rule.validate(ctx)
        assert len(issues) == 1
        assert issues[0].rule_id == "DQ-SCHEMA-001"
        assert issues[0].severity == QualitySeverity.CRITICAL


class TestTimestampIntegrityRule:
    def test_clean_timestamps_pass(self, clean_rule_context: RuleContext) -> None:
        rule = TimestampIntegrityRule()
        issues = rule.validate(clean_rule_context)
        assert len(issues) == 0

    def test_future_timestamp_detected(
        self,
        clean_rule_context: RuleContext,
        reference_clock: datetime,
    ) -> None:
        # Observation in 2025 relative to 2024 reference clock
        future_record = OHLCVRecord(
            symbol="AAPL",
            timestamp=reference_clock + timedelta(days=30),
            open=185.0,
            high=187.0,
            low=184.5,
            close=186.0,
            volume=1000.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (future_record,)})
        rule = TimestampIntegrityRule()
        issues = rule.validate(ctx)
        assert any(i.rule_id == "DQ-TIME-002" for i in issues)


class TestOHLCIntegrityRule:
    def test_clean_ohlc_pass(self, clean_rule_context: RuleContext) -> None:
        rule = OHLCIntegrityRule()
        assert len(rule.validate(clean_rule_context)) == 0

    def test_high_less_than_low(self, clean_rule_context: RuleContext) -> None:
        # Circumvent model validator using model_construct to test quality gate defense-in-depth
        bad_record = OHLCVRecord.model_construct(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=185.0,
            high=180.0,  # high < low
            low=185.0,
            close=182.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (bad_record,)})
        rule = OHLCIntegrityRule()
        issues = rule.validate(ctx)
        assert any(i.rule_id == "DQ-OHLC-001" for i in issues)

    def test_non_positive_price(self, clean_rule_context: RuleContext) -> None:
        bad_record = OHLCVRecord.model_construct(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=0.0,
            high=10.0,
            low=0.0,
            close=5.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (bad_record,)})
        rule = OHLCIntegrityRule()
        issues = rule.validate(ctx)
        assert any(i.rule_id == "DQ-OHLC-003" for i in issues)


class TestVolumeValidationRule:
    def test_zero_volume_accepted(self, clean_rule_context: RuleContext) -> None:
        zero_vol_record = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=185.0,
            high=187.0,
            low=184.5,
            close=186.0,
            volume=0.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (zero_vol_record,)})
        rule = VolumeValidationRule()
        issues = rule.validate(ctx)
        assert len(issues) == 0

    def test_negative_volume_detected(self, clean_rule_context: RuleContext) -> None:
        bad_record = OHLCVRecord.model_construct(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, tzinfo=UTC),
            open=185.0,
            high=187.0,
            low=184.5,
            close=186.0,
            volume=-1000.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (bad_record,)})
        rule = VolumeValidationRule()
        issues = rule.validate(ctx)
        assert len(issues) == 1
        assert issues[0].rule_id == "DQ-VOL-001"


class TestDuplicateDetectionRule:
    def test_unique_records_pass(self, clean_rule_context: RuleContext) -> None:
        rule = DuplicateDetectionRule()
        assert len(rule.validate(clean_rule_context)) == 0

    def test_duplicates_detected(
        self,
        clean_rule_context: RuleContext,
        clean_daily_records: tuple[OHLCVRecord, ...],
    ) -> None:
        # Duplicate record 1
        dup_records = (clean_daily_records[0], clean_daily_records[0], clean_daily_records[1])
        ctx = clean_rule_context.model_copy(update={"records": dup_records})
        rule = DuplicateDetectionRule()
        issues = rule.validate(ctx)
        assert len(issues) == 1
        assert issues[0].rule_id == "DQ-DUP-001"


class TestOrderingValidationRule:
    def test_sorted_records_pass(self, clean_rule_context: RuleContext) -> None:
        rule = OrderingValidationRule()
        assert len(rule.validate(clean_rule_context)) == 0

    def test_out_of_order_detected(
        self,
        clean_rule_context: RuleContext,
        clean_daily_records: tuple[OHLCVRecord, ...],
    ) -> None:
        # Reverse records
        reversed_records = (clean_daily_records[2], clean_daily_records[1], clean_daily_records[0])
        ctx = clean_rule_context.model_copy(update={"records": reversed_records})
        rule = OrderingValidationRule()
        issues = rule.validate(ctx)
        assert len(issues) == 2
        assert all(i.rule_id == "DQ-ORDER-001" for i in issues)


class TestCalendarValidationRule:
    def test_valid_nyse_sessions_pass(self, clean_rule_context: RuleContext) -> None:
        rule = CalendarValidationRule()
        assert len(rule.validate(clean_rule_context)) == 0

    def test_weekend_observation_flagged_for_equity(
        self,
        clean_rule_context: RuleContext,
    ) -> None:
        # Saturday Jan 6 observation
        sat_record = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 6, 15, 0, tzinfo=UTC),
            open=185.0,
            high=187.0,
            low=184.5,
            close=186.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (sat_record,)})
        rule = CalendarValidationRule()
        issues = rule.validate(ctx)
        assert any(i.rule_id == "DQ-CAL-001" for i in issues)

    def test_weekend_observation_accepted_for_crypto(
        self,
        clean_rule_context: RuleContext,
        continuous_calendar: ContinuousCalendar,
    ) -> None:
        sat_record = OHLCVRecord(
            symbol="BTC-USD",
            timestamp=datetime(2024, 1, 6, 15, 0, tzinfo=UTC),
            open=40000.0,
            high=41000.0,
            low=39500.0,
            close=40500.0,
            volume=500.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(
            update={"records": (sat_record,), "calendar": continuous_calendar}
        )
        rule = CalendarValidationRule()
        issues = rule.validate(ctx)
        assert len(issues) == 0


class TestGapDetectionRule:
    def test_continuous_series_pass(self, clean_rule_context: RuleContext) -> None:
        rule = GapDetectionRule()
        assert len(rule.validate(clean_rule_context)) == 0

    def test_missing_trading_day_detected(
        self,
        clean_rule_context: RuleContext,
        clean_daily_records: tuple[OHLCVRecord, ...],
    ) -> None:
        # Include Jan 2 (Tue) and Jan 4 (Thu) — skip Jan 3 (Wed)
        skipped = (clean_daily_records[0], clean_daily_records[2])
        ctx = clean_rule_context.model_copy(update={"records": skipped})
        rule = GapDetectionRule()
        issues = rule.validate(ctx)
        assert len(issues) == 1
        assert issues[0].rule_id == "DQ-GAP-001"
        assert "2024-01-03" in issues[0].message

    def test_weekend_closure_is_not_flagged_as_gap(
        self,
        clean_rule_context: RuleContext,
    ) -> None:
        # Friday Jan 5 and Monday Jan 8 — regular weekend gap
        fri = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 5, 14, 30, tzinfo=UTC),
            open=185.0,
            high=187.0,
            low=184.5,
            close=186.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        mon = OHLCVRecord(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 8, 14, 30, tzinfo=UTC),
            open=186.0,
            high=188.0,
            low=185.0,
            close=187.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        ctx = clean_rule_context.model_copy(update={"records": (fri, mon)})
        rule = GapDetectionRule()
        issues = rule.validate(ctx)
        assert len(issues) == 0


class TestStalenessDetectionRule:
    def test_fresh_data_pass(
        self,
        clean_rule_context: RuleContext,
        reference_clock: datetime,
    ) -> None:
        # Latest bar is Jan 4 14:30; reference clock is Jan 5 21:00
        # (approx 30.5 hours difference < 72h)
        rule = StalenessDetectionRule()
        issues = rule.validate(clean_rule_context)
        assert len(issues) == 0

    def test_stale_data_flagged(
        self,
        clean_rule_context: RuleContext,
        reference_clock: datetime,
    ) -> None:
        # Set reference clock 10 days into the future (240 hours difference > 72h threshold)
        ctx = clean_rule_context.model_copy(
            update={"reference_time": reference_clock + timedelta(days=10)}
        )
        rule = StalenessDetectionRule()
        issues = rule.validate(ctx)
        assert len(issues) == 1
        assert issues[0].rule_id == "DQ-STALE-001"
        assert issues[0].severity == QualitySeverity.WARNING
