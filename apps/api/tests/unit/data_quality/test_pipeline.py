"""
Unit tests for MarketDataValidationPipeline orchestration.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.data_quality.application import (
    MarketDataValidationPipeline,
    ValidationConfig,
)
from app.modules.data_quality.domain.models import (
    QualityStatus,
)
from app.modules.market_data.domain.models import (
    DataInterval,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)


class TestMarketDataValidationPipeline:
    def test_clean_dataset_passes(
        self,
        clean_market_data_result: MarketDataResult,
        reference_clock: datetime,
    ) -> None:
        pipeline = MarketDataValidationPipeline()
        report = pipeline.validate(clean_market_data_result, reference_time=reference_clock)

        assert report.status == QualityStatus.PASS
        assert report.is_valid
        assert not report.has_warnings
        assert report.statistics.total_records == 3
        assert report.statistics.valid_records == 3
        assert report.statistics.critical_count == 0
        assert report.statistics.warning_count == 0
        assert len(report.issues) == 0

    def test_dataset_with_gap_yields_warning(
        self,
        clean_market_data_result: MarketDataResult,
        reference_clock: datetime,
    ) -> None:
        # Keep Jan 2 and Jan 4, omit Jan 3 (Wednesday gap)
        records = (
            clean_market_data_result.records[0],
            clean_market_data_result.records[2],
        )
        gapped_result = clean_market_data_result.model_copy(update={"records": records})

        pipeline = MarketDataValidationPipeline()
        report = pipeline.validate(gapped_result, reference_time=reference_clock)

        assert report.status == QualityStatus.WARN
        assert report.is_valid  # Warnings do not fail the dataset
        assert report.has_warnings
        assert report.statistics.warning_count >= 1
        assert any(i.rule_id == "DQ-GAP-001" for i in report.issues)

    def test_dataset_with_critical_failure_yields_fail(
        self,
        clean_market_data_result: MarketDataResult,
        reference_clock: datetime,
    ) -> None:
        # Create record with high < low
        bad_bar = OHLCVRecord.model_construct(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=UTC),
            open=185.0,
            high=170.0,
            low=184.0,
            close=175.0,
            volume=100.0,
            interval=DataInterval.ONE_DAY,
            source_provider_id="test",
        )
        bad_records = (bad_bar, clean_market_data_result.records[1])
        bad_result = clean_market_data_result.model_copy(update={"records": bad_records})

        pipeline = MarketDataValidationPipeline()
        report = pipeline.validate(bad_result, reference_time=reference_clock)

        assert report.status == QualityStatus.FAIL
        assert not report.is_valid
        assert report.statistics.critical_count >= 1
        assert "DQ-OHLC-001" in report.failed_rule_ids

    def test_empty_dataset_handling(
        self,
        clean_query: MarketDataQuery,
        reference_clock: datetime,
    ) -> None:
        empty_result = MarketDataResult(
            query=clean_query,
            provider_id="yahoo_finance",
            records=(),
        )
        pipeline = MarketDataValidationPipeline()
        report = pipeline.validate(empty_result, reference_time=reference_clock)

        assert report.status == QualityStatus.PASS
        assert report.statistics.total_records == 0
        assert report.statistics.valid_records == 0

    def test_pipeline_disables_rules_via_config(
        self,
        clean_market_data_result: MarketDataResult,
        reference_clock: datetime,
    ) -> None:
        # Introduce duplicate
        dup_records = (
            clean_market_data_result.records[0],
            clean_market_data_result.records[0],
        )
        dup_result = clean_market_data_result.model_copy(update={"records": dup_records})

        # Pipeline with duplicate rule disabled
        config = ValidationConfig(enable_duplicate=False)
        pipeline = MarketDataValidationPipeline(config=config)
        report = pipeline.validate(dup_result, reference_time=reference_clock)

        # Duplicate not caught because rule was toggled off
        assert not any(i.rule_id == "DQ-DUP-001" for i in report.issues)

    def test_pipeline_immutability(
        self,
        clean_market_data_result: MarketDataResult,
        reference_clock: datetime,
    ) -> None:
        original_records = clean_market_data_result.records
        pipeline = MarketDataValidationPipeline()
        pipeline.validate(clean_market_data_result, reference_time=reference_clock)

        # Guarantee input is identical
        assert clean_market_data_result.records == original_records
