"""
Unit tests for MarketIntelligenceFacade application service.
============================================================
Verifies:
1. Orchestration across MarketData -> Features -> Detection -> Intelligence.
2. Transition analytics calculation across the full pipeline.
3. Insufficient market data error handling.
4. Custom detector injection.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.market_data.application.service import MarketDataService
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    AssetClass,
    Instrument,
    MarketDataQuery,
    MarketDataResult,
    OHLCVRecord,
)
from app.modules.market_data.domain.provider import (
    MarketDataProvider,
    ProviderCapabilities,
    ProviderMetadata,
)
from app.modules.regime_intelligence.application.facade import (
    MarketIntelligenceFacade,
)
from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
)


class SyntheticBarsProvider(MarketDataProvider):
    """Generates synthetic cyclic daily bars for pipeline testing."""

    def __init__(self, n_bars: int = 80) -> None:
        self.n_bars = n_bars
        self._supported_symbols = {"SPY"}

    @property
    def provider_id(self) -> str:
        return "synthetic_provider"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="synthetic_provider",
            display_name="Synthetic Provider",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        return [
            Instrument(
                symbol="SPY",
                asset_class=AssetClass.EQUITY_US,
                exchange="NYSE",
                currency="USD",
                description="SPDR S&P 500 ETF Trust",
            )
        ]

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol in self._supported_symbols

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        if query.instrument.symbol not in self._supported_symbols:
            raise ProviderSymbolNotFoundError(
                f"Symbol {query.instrument.symbol} not supported.",
                symbol=query.instrument.symbol,
                provider_id=self.provider_id,
            )

        base_time = query.start
        bars: list[OHLCVRecord] = []
        price = 100.0

        for i in range(self.n_bars):
            bar_time = base_time + timedelta(days=i)
            if bar_time >= query.end:
                break
            ret = 0.015 * math.sin(i * 0.25)
            close = price * (1.0 + ret)
            high = max(price, close) + 0.50
            low = min(price, close) - 0.50
            volume = 10_000.0 + 1000.0 * (i % 5)

            bars.append(
                OHLCVRecord(
                    symbol=query.instrument.symbol,
                    timestamp=bar_time,
                    open=price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    interval=query.interval,
                    adjustment_policy=AdjustmentPolicy.RAW,
                    source_provider_id=self.provider_id,
                    ingested_at=datetime.now(tz=UTC),
                )
            )
            price = close

        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(bars),
        )


@pytest.mark.asyncio
async def test_facade_get_market_regime_end_to_end() -> None:
    """Facade orchestrates the full market intelligence pipeline end-to-end."""
    provider = SyntheticBarsProvider(n_bars=80)
    market_service = MarketDataService(provider=provider)
    facade = MarketIntelligenceFacade(market_service=market_service)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 4, 1, tzinfo=UTC)

    summary, confidence = await facade.get_market_regime(
        symbol="SPY",
        start=start,
        end=end,
    )

    assert summary.total_observations > 0
    assert summary.current_regime is not None
    assert summary.current_regime.current_regime_id in summary.regimes_observed
    assert len(summary.regime_profiles) == len(summary.regimes_observed)
    for p in summary.regime_profiles.values():
        assert p.observation_count > 0
        assert 0.0 <= p.frequency <= 1.0


@pytest.mark.asyncio
async def test_facade_get_transition_analytics_end_to_end() -> None:
    """Facade orchestrates transition analytics end-to-end."""
    provider = SyntheticBarsProvider(n_bars=80)
    market_service = MarketDataService(provider=provider)
    facade = MarketIntelligenceFacade(market_service=market_service)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 4, 1, tzinfo=UTC)

    result = await facade.get_transition_analytics(
        symbol="SPY",
        start=start,
        end=end,
    )

    assert result.global_analytics.total_observations > 0
    assert result.global_analytics.total_consecutive_transitions > 0
    assert len(result.regime_analytics) > 0
    for r_id in result.transition_result.probability_matrix.regimes:
        assert r_id in result.regime_analytics
        ra = result.regime_analytics[r_id]
        assert 0.0 <= ra.persistence_probability <= 1.0


@pytest.mark.asyncio
async def test_facade_unknown_symbol_raises_provider_error() -> None:
    """Querying an unknown symbol raises ProviderSymbolNotFoundError."""
    provider = SyntheticBarsProvider(n_bars=80)
    market_service = MarketDataService(provider=provider)
    facade = MarketIntelligenceFacade(market_service=market_service)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 4, 1, tzinfo=UTC)

    with pytest.raises(ProviderSymbolNotFoundError):
        await facade.get_market_regime(
            symbol="UNKNOWN",
            start=start,
            end=end,
        )


@pytest.mark.asyncio
async def test_facade_insufficient_bars_raises_error() -> None:
    """
    Fewer bars than minimum for features raises InsufficientRegimeDataError
    or InsufficientDataError.
    """
    from app.modules.feature_engineering.domain.errors import (
        InsufficientDataError,
    )

    provider = SyntheticBarsProvider(n_bars=5)
    market_service = MarketDataService(provider=provider)
    facade = MarketIntelligenceFacade(market_service=market_service)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 6, tzinfo=UTC)

    with pytest.raises((InsufficientRegimeDataError, InsufficientDataError)):
        await facade.get_market_regime(
            symbol="SPY",
            start=start,
            end=end,
        )
