"""
Live integration smoke test for YahooFinanceProvider.

ATTENTION:
This test connects to the live Yahoo Finance service over the internet.
It is DISABLED by default so the test suite remains completely offline.

To run:
    REGIMEX_RUN_LIVE_TESTS=1 pytest tests/integration/market_data/test_yahoo_finance_live.py -v
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
)
from app.modules.market_data.infrastructure.providers.yahoo_finance import (
    YahooFinanceProvider,
)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("REGIMEX_RUN_LIVE_TESTS"),
    reason="Live external network test skipped by default. Set REGIMEX_RUN_LIVE_TESTS=1 to run.",
)
class TestYahooFinanceLiveSmoke:
    @pytest.mark.asyncio
    async def test_live_spy_daily_bars(self) -> None:
        """Fetch 3 days of historical SPY daily bars from Yahoo Finance."""
        end = datetime.now(tz=UTC)
        start = end - timedelta(days=7)

        spy = Instrument(
            symbol="SPY",
            asset_class=AssetClass.EQUITY_US,
            exchange="NYSE",
            currency="USD",
            description="SPDR S&P 500 ETF Trust",
        )
        query = MarketDataQuery(
            instrument=spy,
            start=start,
            end=end,
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.FULLY_ADJUSTED,
        )

        provider = YahooFinanceProvider()
        result = await provider.get_ohlcv(query)

        assert isinstance(result, MarketDataResult)
        assert result.provider_id == "yahoo_finance"
        assert not result.is_empty
        assert len(result.records) > 0

        first_bar = result.records[0]
        assert first_bar.open > 0
        assert first_bar.high >= first_bar.low
        assert first_bar.timestamp.tzinfo is not None
