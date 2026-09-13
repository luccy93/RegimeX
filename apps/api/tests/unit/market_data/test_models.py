"""
Unit tests — canonical market data domain models.

Tests cover:
- AssetClass, DataInterval, AdjustmentPolicy enum completeness
- Instrument construction and normalisation
- OHLCVRecord: valid records, timezone enforcement, OHLC relationship invariants, volume constraints
- MarketDataQuery: valid query, end <= start rejection, naive datetime rejection
- MarketDataResult: properties, empty result, record ordering contract, price_range
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from pydantic import ValidationError

from tests.unit.market_data.conftest import (
    END_DT,
    START_DT,
    make_record,
)

# =============================================================================
# AssetClass
# =============================================================================


class TestAssetClass:
    def test_all_expected_values_present(self) -> None:
        values = {c.value for c in AssetClass}
        assert "equity_us" in values
        assert "equity_in" in values
        assert "index" in values
        assert "crypto" in values
        assert "fx" in values
        assert "commodity" in values

    def test_string_comparison(self) -> None:
        assert AssetClass.EQUITY_US.value == "equity_us"


# =============================================================================
# DataInterval
# =============================================================================


class TestDataInterval:
    def test_all_expected_intervals_present(self) -> None:
        values = {i.value for i in DataInterval}
        for expected in ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"):
            assert expected in values, f"Missing interval: {expected}"

    def test_string_comparison(self) -> None:
        assert DataInterval.ONE_DAY.value == "1d"

    def test_intraday_intervals_distinct_from_daily(self) -> None:
        intraday = {
            DataInterval.ONE_MIN,
            DataInterval.FIVE_MIN,
            DataInterval.FIFTEEN_MIN,
            DataInterval.THIRTY_MIN,
            DataInterval.ONE_HOUR,
            DataInterval.FOUR_HOUR,
        }
        eod = {DataInterval.ONE_DAY, DataInterval.ONE_WEEK}
        assert intraday.isdisjoint(eod)


# =============================================================================
# AdjustmentPolicy
# =============================================================================


class TestAdjustmentPolicy:
    def test_all_policies_present(self) -> None:
        values = {p.value for p in AdjustmentPolicy}
        assert "raw" in values
        assert "split_adjusted" in values
        assert "fully_adjusted" in values


# =============================================================================
# Instrument
# =============================================================================


class TestInstrument:
    def test_valid_us_equity(self) -> None:
        inst = Instrument(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY_US,
            exchange="NASDAQ",
            currency="USD",
            description="",
        )
        assert inst.symbol == "AAPL"
        assert inst.currency == "USD"

    def test_symbol_uppercased_and_stripped(self) -> None:
        inst = Instrument(
            symbol=" aapl ",
            asset_class=AssetClass.EQUITY_US,
            exchange="nasdaq",
            currency="usd",
            description="",
        )
        assert inst.symbol == "AAPL"
        assert inst.exchange == "NASDAQ"
        assert inst.currency == "USD"

    def test_description_defaults_empty(self) -> None:
        inst = Instrument(
            symbol="BTC",
            asset_class=AssetClass.CRYPTO,
            exchange="BINANCE",
            currency="USDT",
            description="",
        )
        assert inst.description == ""

    def test_frozen_model_rejects_mutation(self) -> None:
        inst = Instrument(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY_US,
            exchange="NASDAQ",
            currency="USD",
            description="",
        )
        with pytest.raises((TypeError, ValidationError)):
            inst.symbol = "GOOG"  # type: ignore[misc]

    def test_empty_symbol_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Instrument(
                symbol="",
                asset_class=AssetClass.EQUITY_US,
                exchange="NYSE",
                currency="USD",
                description="",
            )

    def test_currency_must_be_at_least_2_chars(self) -> None:
        with pytest.raises(ValidationError):
            Instrument(
                symbol="X",
                asset_class=AssetClass.FX,
                exchange="FX",
                currency="U",  # too short
            )

    def test_indian_equity(self) -> None:
        inst = Instrument(
            symbol="RELIANCE",
            asset_class=AssetClass.EQUITY_IN,
            exchange="NSE",
            currency="INR",
            description="Reliance Industries",
        )
        assert inst.asset_class == AssetClass.EQUITY_IN
        assert inst.exchange == "NSE"


# =============================================================================
# OHLCVRecord
# =============================================================================


class TestOHLCVRecord:
    def test_valid_record_constructs(self, sample_record: OHLCVRecord) -> None:
        assert sample_record.symbol == "AAPL"
        assert sample_record.open == 185.0
        assert sample_record.close == 186.0

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            make_record(ts=datetime(2024, 1, 2))  # naive — no tzinfo

    def test_naive_ingested_at_rejected(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            OHLCVRecord(
                symbol="AAPL",
                timestamp=START_DT,
                open=100.0,
                high=105.0,
                low=99.0,
                close=102.0,
                volume=1_000.0,
                interval=DataInterval.ONE_DAY,
                adjustment_policy=AdjustmentPolicy.RAW,
                source_provider_id="test",
                ingested_at=datetime(2024, 1, 2),  # naive
            )

    def test_zero_open_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_record(open_=0.0)

    def test_negative_open_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_record(open_=-1.0)

    def test_negative_volume_rejected(self) -> None:
        with pytest.raises(ValidationError):
            make_record(volume=-100.0)

    def test_zero_volume_accepted(self) -> None:
        r = make_record(volume=0.0)
        assert r.volume == 0.0

    def test_high_less_than_low_rejected(self) -> None:
        with pytest.raises(ValidationError, match="high.*must be.*>=.*low"):
            make_record(high=180.0, low=185.0)

    def test_high_less_than_open_rejected(self) -> None:
        with pytest.raises(ValidationError, match="high.*must be.*>=.*open"):
            make_record(open_=190.0, high=185.0, low=184.0, close=186.0)

    def test_high_less_than_close_rejected(self) -> None:
        with pytest.raises(ValidationError, match="high.*must be.*>=.*close"):
            make_record(open_=185.0, high=185.0, low=184.0, close=190.0)

    def test_low_greater_than_open_rejected(self) -> None:
        with pytest.raises(ValidationError, match="low.*must be.*<=.*open"):
            make_record(open_=183.0, high=187.0, low=184.0, close=186.0)

    def test_low_greater_than_close_rejected(self) -> None:
        with pytest.raises(ValidationError, match="low.*must be.*<=.*close"):
            make_record(open_=185.0, high=187.0, low=184.0, close=183.0)

    def test_high_equals_low_accepted(self) -> None:
        # Doji candle — all prices equal
        r = make_record(open_=185.0, high=185.0, low=185.0, close=185.0)
        assert r.high == r.low

    def test_record_is_frozen(self) -> None:
        r = make_record()
        with pytest.raises((TypeError, ValidationError)):
            r.close = 999.0  # type: ignore[misc]

    def test_source_provider_id_stored(self) -> None:
        r = make_record(provider_id="test_provider_v1")
        assert r.source_provider_id == "test_provider_v1"


# =============================================================================
# MarketDataQuery
# =============================================================================


class TestMarketDataQuery:
    def test_valid_query(self, sample_query: MarketDataQuery) -> None:
        assert sample_query.start == START_DT
        assert sample_query.end == END_DT
        assert sample_query.interval == DataInterval.ONE_DAY

    def test_end_before_start_rejected(self, sample_instrument: Instrument) -> None:
        with pytest.raises(ValidationError, match="strictly after"):
            MarketDataQuery(
                instrument=sample_instrument,
                start=END_DT,
                end=START_DT,
            )

    def test_end_equals_start_rejected(self, sample_instrument: Instrument) -> None:
        with pytest.raises(ValidationError, match="strictly after"):
            MarketDataQuery(
                instrument=sample_instrument,
                start=START_DT,
                end=START_DT,
            )

    def test_naive_start_rejected(self, sample_instrument: Instrument) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            MarketDataQuery(
                instrument=sample_instrument,
                start=datetime(2024, 1, 2),  # naive
                end=END_DT,
            )

    def test_naive_end_rejected(self, sample_instrument: Instrument) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            MarketDataQuery(
                instrument=sample_instrument,
                start=START_DT,
                end=datetime(2024, 1, 10),  # naive
            )

    def test_default_interval_is_daily(self, sample_instrument: Instrument) -> None:
        q = MarketDataQuery(instrument=sample_instrument, start=START_DT, end=END_DT)
        assert q.interval == DataInterval.ONE_DAY

    def test_default_adjustment_is_split_adjusted(self, sample_instrument: Instrument) -> None:
        q = MarketDataQuery(instrument=sample_instrument, start=START_DT, end=END_DT)
        assert q.adjustment_policy == AdjustmentPolicy.SPLIT_ADJUSTED

    def test_query_is_frozen(self, sample_query: MarketDataQuery) -> None:
        with pytest.raises((TypeError, ValidationError)):
            sample_query.interval = DataInterval.ONE_HOUR  # type: ignore[misc]


# =============================================================================
# MarketDataResult
# =============================================================================


class TestMarketDataResult:
    def test_empty_result(self, sample_query: MarketDataQuery) -> None:
        result = MarketDataResult(
            query=sample_query,
            provider_id="fake_provider",
            fetched_at=datetime.now(tz=UTC),
            records=(),
        )
        assert result.is_empty
        assert result.record_count == 0
        assert result.price_range() is None

    def test_result_with_records(
        self,
        sample_query: MarketDataQuery,
        two_records: tuple[OHLCVRecord, OHLCVRecord],
    ) -> None:
        r1, r2 = two_records
        result = MarketDataResult(
            query=sample_query,
            provider_id="fake_provider",
            fetched_at=datetime.now(tz=UTC),
            records=(r1, r2),
        )
        assert not result.is_empty
        assert result.record_count == 2

    def test_symbol_property(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        result = MarketDataResult(
            query=sample_query,
            provider_id="fake_provider",
            fetched_at=datetime.now(tz=UTC),
        )
        assert result.symbol == "AAPL"

    def test_price_range(
        self,
        sample_query: MarketDataQuery,
        two_records: tuple[OHLCVRecord, OHLCVRecord],
    ) -> None:
        r1, r2 = two_records
        result = MarketDataResult(
            query=sample_query,
            provider_id="fake_provider",
            fetched_at=datetime.now(tz=UTC),
            records=(r1, r2),
        )
        lo, hi = result.price_range()  # type: ignore[misc]
        assert isinstance(lo, Decimal)
        assert isinstance(hi, Decimal)
        assert lo <= hi

    def test_naive_fetched_at_rejected(self, sample_query: MarketDataQuery) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            MarketDataResult(
                query=sample_query,
                provider_id="fake_provider",
                fetched_at=datetime(2024, 1, 2),  # naive
            )

    def test_result_is_frozen(self, sample_query: MarketDataQuery) -> None:
        result = MarketDataResult(
            query=sample_query,
            provider_id="fake_provider",
            fetched_at=datetime.now(tz=UTC),
        )
        with pytest.raises((TypeError, ValidationError)):
            result.provider_id = "other"  # type: ignore[misc]
