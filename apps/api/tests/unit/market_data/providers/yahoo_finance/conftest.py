"""
Test fixtures for Yahoo Finance provider tests.
Provides synthetic offline DataFrames and pre-configured queries.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance import (
    YahooFinanceConfig,
    YahooFinanceProvider,
    YahooFinanceSymbolResolver,
)


@pytest.fixture()
def sample_aapl_instrument() -> Instrument:
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY_US,
        exchange="NASDAQ",
        currency="USD",
        description="Apple Inc.",
    )


@pytest.fixture()
def sample_reliance_instrument() -> Instrument:
    return Instrument(
        symbol="RELIANCE",
        asset_class=AssetClass.EQUITY_IN,
        exchange="NSE",
        currency="INR",
        description="Reliance Industries Ltd.",
    )


@pytest.fixture()
def sample_query(sample_aapl_instrument: Instrument) -> MarketDataQuery:
    return MarketDataQuery(
        instrument=sample_aapl_instrument,
        start=datetime(2024, 1, 2, tzinfo=UTC),
        end=datetime(2024, 1, 5, tzinfo=UTC),
        interval=DataInterval.ONE_DAY,
        adjustment_policy=AdjustmentPolicy.FULLY_ADJUSTED,
    )


@pytest.fixture()
def sample_aapl_df() -> pd.DataFrame:
    """3-day synthetic OHLCV dataframe matching yfinance output."""
    dates = pd.to_datetime(
        ["2024-01-02 00:00:00+00:00", "2024-01-03 00:00:00+00:00", "2024-01-04 00:00:00+00:00"]
    )
    return pd.DataFrame(
        {
            "Open": [185.0, 184.0, 186.0],
            "High": [187.0, 186.5, 188.0],
            "Low": [184.5, 183.0, 185.5],
            "Close": [186.0, 185.5, 187.5],
            "Volume": [10000000.0, 12000000.0, 11000000.0],
        },
        index=dates,
    )


@pytest.fixture()
def sample_multiindex_df() -> pd.DataFrame:
    """MultiIndex DataFrame similar to yfinance multi-ticker download output."""
    dates = pd.to_datetime(["2024-01-02 00:00:00+00:00", "2024-01-03 00:00:00+00:00"])
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "AAPL"),
            ("High", "AAPL"),
            ("Low", "AAPL"),
            ("Close", "AAPL"),
            ("Volume", "AAPL"),
        ]
    )
    return pd.DataFrame(
        [
            [185.0, 187.0, 184.5, 186.0, 10000000.0],
            [184.0, 186.5, 183.0, 185.5, 12000000.0],
        ],
        index=dates,
        columns=columns,
    )


@pytest.fixture()
def empty_df() -> pd.DataFrame:
    return pd.DataFrame()


@pytest.fixture()
def mock_fetcher(sample_aapl_df: pd.DataFrame):
    def _fetch(
        ticker: str,
        start: datetime,
        end: datetime,
        interval: str,
        auto_adjust: bool,
        timeout: int,
        proxy: str | None,
    ) -> pd.DataFrame:
        return sample_aapl_df

    return _fetch


@pytest.fixture()
def yf_provider(mock_fetcher) -> YahooFinanceProvider:
    config = YahooFinanceConfig(timeout_seconds=5, max_retries=1, backoff_factor=0.01)
    return YahooFinanceProvider(
        config=config,
        resolver=YahooFinanceSymbolResolver(),
        fetcher=mock_fetcher,
    )
