"""
RegimeX Feature Engineering — Domain Model Unit Tests
=====================================================
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.models import (
    FeatureCategory,
    FeatureInputData,
    FeatureRecord,
    MissingValuePolicy,
)
from app.modules.market_data.domain.models import DataInterval
from pydantic import ValidationError


class TestFeatureEnums:
    def test_feature_categories(self):
        assert FeatureCategory.RETURN.value == "return"
        assert FeatureCategory.VOLATILITY.value == "volatility"
        assert FeatureCategory.MOMENTUM.value == "momentum"
        assert FeatureCategory.TREND.value == "trend"
        assert FeatureCategory.VOLUME.value == "volume"
        assert FeatureCategory.RANGE.value == "range"

    def test_missing_value_policy(self):
        assert MissingValuePolicy.PRESERVE.value == "preserve"
        assert MissingValuePolicy.DROP_WARMUP.value == "drop_warmup"


class TestFeatureRecord:
    def test_valid_record(self):
        ts = datetime.now(tz=UTC)
        record = FeatureRecord(timestamp=ts, values={"return_1": 0.02, "volatility_20": None})
        assert record.timestamp == ts
        assert record.values["return_1"] == 0.02
        assert record.values["volatility_20"] is None

    def test_naive_timestamp_rejected(self):
        naive_ts = datetime(2024, 1, 1, 10, 0)
        with pytest.raises(ValidationError):
            FeatureRecord(timestamp=naive_ts, values={"return_1": 0.01})

    def test_record_is_frozen(self):
        record = FeatureRecord(timestamp=datetime.now(tz=UTC), values={"return_1": 0.01})
        with pytest.raises(ValidationError):
            record.timestamp = datetime.now(tz=UTC)  # type: ignore


class TestFeatureInputData:
    def test_valid_input_data(self, base_timestamp: datetime):
        ts1 = base_timestamp
        ts2 = base_timestamp + timedelta(days=1)
        data = FeatureInputData(
            timestamps=(ts1, ts2),
            opens=(100.0, 101.0),
            highs=(102.0, 103.0),
            lows=(99.0, 100.0),
            closes=(101.0, 102.0),
            volumes=(1000.0, 1500.0),
        )
        assert data.length == 2

    def test_mismatched_lengths_rejected(self, base_timestamp: datetime):
        with pytest.raises(ValidationError):
            FeatureInputData(
                timestamps=(base_timestamp,),
                opens=(100.0, 101.0),  # length 2 vs 1
                highs=(102.0,),
                lows=(99.0,),
                closes=(101.0,),
            )

    def test_unsorted_timestamps_rejected(self, base_timestamp: datetime):
        ts1 = base_timestamp
        ts2 = base_timestamp - timedelta(days=1)  # descending!
        with pytest.raises(ValidationError):
            FeatureInputData(
                timestamps=(ts1, ts2),
                opens=(100.0, 101.0),
                highs=(102.0, 103.0),
                lows=(99.0, 100.0),
                closes=(101.0, 102.0),
            )

    def test_from_ohlcv_records(self, linear_trending_bars):
        data = FeatureInputData.from_ohlcv_records(linear_trending_bars)
        assert data.length == len(linear_trending_bars)
        assert data.volumes is not None

    def test_from_empty_records_rejected(self):
        with pytest.raises(ValueError, match="empty records"):
            FeatureInputData.from_ohlcv_records([])


class TestFeatureDefinition:
    def test_valid_definition(self):
        spec = FeatureDefinition(
            name="return_1",
            category=FeatureCategory.RETURN,
            description="1-day return",
            formula="P_t / P_{t-1} - 1",
            required_fields=("close",),
            lookback=1,
            min_observations=2,
            version="1.0.0",
        )
        assert spec.name == "return_1"
        assert spec.lookback == 1

    def test_invalid_name_rejected(self):
        with pytest.raises(ValidationError):
            FeatureDefinition(
                name="1_invalid_name",
                category=FeatureCategory.RETURN,
                description="desc",
                formula="f",
                lookback=1,
                min_observations=1,
            )


class TestFeatureSet:
    def test_feature_set_methods(self, base_timestamp: datetime):
        ts1 = base_timestamp
        ts2 = base_timestamp + timedelta(days=1)
        r1 = FeatureRecord(timestamp=ts1, values={"return_1": None, "vol_10": None})
        r2 = FeatureRecord(timestamp=ts2, values={"return_1": 0.05, "vol_10": None})

        fset = FeatureSet(
            symbol="REGX",
            interval=DataInterval.ONE_DAY,
            feature_names=("return_1", "vol_10"),
            records=(r1, r2),
        )

        assert fset.record_count == 2
        assert not fset.is_empty
        assert fset.get_timestamps() == (ts1, ts2)
        assert fset.get_series("return_1") == (None, 0.05)

        matrix = fset.to_matrix()
        assert matrix == [[None, None], [0.05, None]]

    def test_get_series_unknown_feature_raises(self, base_timestamp: datetime):
        fset = FeatureSet(
            symbol="REGX",
            interval=DataInterval.ONE_DAY,
            feature_names=("return_1",),
            records=(),
        )
        with pytest.raises(KeyError):
            fset.get_series("non_existent")
