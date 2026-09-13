"""
Unit tests for Yahoo Finance DataFrame mapper.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from app.modules.market_data.domain.errors import ProviderDataError
from app.modules.market_data.domain.models import MarketDataQuery, OHLCVRecord
from app.modules.market_data.infrastructure.providers.yahoo_finance.mapper import (
    map_yahoo_finance_dataframe,
)


class TestYahooFinanceMapper:
    def test_valid_mapping(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        records = map_yahoo_finance_dataframe(sample_aapl_df, sample_query)
        assert isinstance(records, tuple)
        assert len(records) == 3
        assert all(isinstance(r, OHLCVRecord) for r in records)
        assert records[0].open == 185.0
        assert records[0].high == 187.0
        assert records[0].source_provider_id == "yahoo_finance"
        assert records[0].symbol == "AAPL"

    def test_chronological_ordering(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        # Shuffle dataframe rows
        shuffled = sample_aapl_df.sample(frac=1.0, random_state=42)
        records = map_yahoo_finance_dataframe(shuffled, sample_query)
        assert len(records) == 3
        assert records[0].timestamp < records[1].timestamp < records[2].timestamp

    def test_empty_dataframe(self, sample_query: MarketDataQuery) -> None:
        empty = pd.DataFrame()
        records = map_yahoo_finance_dataframe(empty, sample_query)
        assert records == ()

    def test_none_dataframe(self, sample_query: MarketDataQuery) -> None:
        records = map_yahoo_finance_dataframe(None, sample_query)
        assert records == ()

    def test_multiindex_columns_supported(
        self,
        sample_multiindex_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        records = map_yahoo_finance_dataframe(sample_multiindex_df, sample_query)
        assert len(records) == 2
        assert records[0].close == 186.0

    def test_missing_required_column_raises(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        incomplete = sample_aapl_df.drop(columns=["Volume"])
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(incomplete, sample_query)
        assert "missing required column" in str(exc_info.value).lower()
        assert exc_info.value.provider_id == "yahoo_finance"

    def test_nan_values_raise(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        with_nan = sample_aapl_df.copy()
        with_nan.loc[with_nan.index[0], "Close"] = float("nan")
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(with_nan, sample_query)
        assert "nan" in str(exc_info.value).lower()

    def test_duplicate_timestamps_raise(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        # Duplicate first row timestamp
        dup_df = pd.concat([sample_aapl_df.iloc[[0]], sample_aapl_df])
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(dup_df, sample_query)
        assert "duplicate" in str(exc_info.value).lower()

    def test_naive_timestamp_converted_to_utc(
        self,
        sample_query: MarketDataQuery,
    ) -> None:
        dates = pd.to_datetime(["2024-01-02 00:00:00", "2024-01-03 00:00:00"])
        naive_df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [99.0, 100.0],
                "Close": [104.0, 105.0],
                "Volume": [1000.0, 2000.0],
            },
            index=dates,
        )
        records = map_yahoo_finance_dataframe(naive_df, sample_query)
        assert len(records) == 2
        assert records[0].timestamp.tzinfo is not None
        assert records[0].timestamp.tzinfo == UTC

    def test_date_range_filtering(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        # Narrow query to only Jan 3
        narrow = MarketDataQuery(
            instrument=sample_query.instrument,
            start=datetime(2024, 1, 3, tzinfo=UTC),
            end=datetime(2024, 1, 4, tzinfo=UTC),
            interval=sample_query.interval,
            adjustment_policy=sample_query.adjustment_policy,
        )
        records = map_yahoo_finance_dataframe(sample_aapl_df, narrow)
        assert len(records) == 1
        assert records[0].timestamp == datetime(2024, 1, 3, tzinfo=UTC)

    def test_negative_price_raises(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        bad_df = sample_aapl_df.copy()
        bad_df.loc[bad_df.index[0], "Close"] = -10.0
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(bad_df, sample_query)
        assert "non-positive price" in str(exc_info.value).lower()

    def test_negative_volume_raises(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        bad_df = sample_aapl_df.copy()
        bad_df.loc[bad_df.index[0], "Volume"] = -500.0
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(bad_df, sample_query)
        assert "negative volume" in str(exc_info.value).lower()

    def test_ohlc_invariants_enforced(
        self,
        sample_aapl_df: pd.DataFrame,
        sample_query: MarketDataQuery,
    ) -> None:
        bad_df = sample_aapl_df.copy()
        # High < Low
        bad_df.loc[bad_df.index[0], "High"] = 180.0
        bad_df.loc[bad_df.index[0], "Low"] = 190.0
        with pytest.raises(ProviderDataError) as exc_info:
            map_yahoo_finance_dataframe(bad_df, sample_query)
        assert "invariant violated" in str(exc_info.value).lower()
