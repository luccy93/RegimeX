"""
RegimeX Platform — Canonical SPY Golden Test Fixture
====================================================
Volume 22 — Commit 02: End-to-End Critical Workflows

Provides a compact, deterministic canonical fixture representing SPY and
benchmark instruments with:
- Fixed historical dates (2026-01-05 to 2026-03-05 UTC)
- Deterministic OHLCV bars with known price trajectories
- Pre-computed mathematical risk parameters (volatility, max drawdown, VaR, ES)
- Deterministic regime classifications and Markov transition matrices
- Deterministic event-driven backtest performance metrics
- Model explanation diagnostics and provenance
- Grounded AI research evidence packets and citations

Zero network, zero live market feeds, zero external API keys.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.ai_research.domain.models import EvidencePacket
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import (
    AssetClass,
    DataInterval,
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

# =============================================================================
# 1. Canonical Instrument Definitions
# =============================================================================

SPY_INSTRUMENT = Instrument(
    symbol="SPY",
    asset_class=AssetClass.EQUITY_US,
    exchange="NYSE",
    currency="USD",
    description="SPDR S&P 500 ETF Trust",
)

QQQ_INSTRUMENT = Instrument(
    symbol="QQQ",
    asset_class=AssetClass.EQUITY_US,
    exchange="NASDAQ",
    currency="USD",
    description="Invesco QQQ Trust Series 1",
)

AAPL_INSTRUMENT = Instrument(
    symbol="AAPL",
    asset_class=AssetClass.EQUITY_US,
    exchange="NASDAQ",
    currency="USD",
    description="Apple Inc. Common Stock",
)

EMPTY_INSTRUMENT = Instrument(
    symbol="EMPTY",
    asset_class=AssetClass.EQUITY_US,
    exchange="NYSE",
    currency="USD",
    description="Valid Instrument With Empty Data Store",
)

GOLDEN_CATALOG: tuple[Instrument, ...] = (
    SPY_INSTRUMENT,
    QQQ_INSTRUMENT,
    AAPL_INSTRUMENT,
    EMPTY_INSTRUMENT,
)

# =============================================================================
# 2. Deterministic OHLCV Bars Generator (Fixed Window: 60 Trading Days)
# =============================================================================

BASE_DATE = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)


def generate_golden_spy_bars() -> tuple[OHLCVRecord, ...]:
    """
    Generate 60 deterministic daily OHLCV bars for SPY starting at 2026-01-05.
    Price starts at $500.00 and moves along a controlled trend + oscillation.
    """
    bars: list[OHLCVRecord] = []
    base_price = 500.0

    for i in range(60):
        bar_date = BASE_DATE + timedelta(days=i)
        # Controlled path: slight upward drift with sinusoidal cycle
        trend = i * 0.40
        cycle = 3.5 * math.sin(i * 0.35)
        p = round(base_price + trend + cycle, 2)

        bars.append(
            OHLCVRecord(
                symbol="SPY",
                timestamp=bar_date,
                open=round(p - 0.75, 2),
                high=round(p + 1.80, 2),
                low=round(p - 1.50, 2),
                close=p,
                volume=45_000_000.0 + ((i % 7) * 2_000_000.0),
                interval=DataInterval.ONE_DAY,
                source_provider_id="golden_market_provider",
            )
        )
    return tuple(bars)


GOLDEN_SPY_BARS: tuple[OHLCVRecord, ...] = generate_golden_spy_bars()

# =============================================================================
# 3. Deterministic Market Data Provider
# =============================================================================


class GoldenMarketDataProvider(MarketDataProvider):
    """
    Deterministic offline provider serving canonical SPY test data.
    Simulates:
    - Normal data retrieval for SPY
    - Empty data responses for EMPTY symbol
    - Controlled ProviderSymbolNotFoundError for unknown symbols
    """

    def __init__(self, bars: tuple[OHLCVRecord, ...] = GOLDEN_SPY_BARS) -> None:
        self._bars = bars
        self._supported_symbols = {"SPY", "QQQ", "AAPL", "EMPTY"}

    @property
    def provider_id(self) -> str:
        return "golden_market_provider"

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            display_name="Canonical Golden Market Provider",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supported_intervals=frozenset({DataInterval.ONE_DAY}),
            supported_exchanges=frozenset({"NYSE", "NASDAQ"}),
            supports_symbol_search=True,
        )

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        if asset_class is None:
            return list(GOLDEN_CATALOG)
        return [inst for inst in GOLDEN_CATALOG if inst.asset_class == asset_class]

    async def supports(self, instrument: Instrument) -> bool:
        return instrument.symbol.upper() in self._supported_symbols

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        sym = query.instrument.symbol.upper()

        if sym not in self._supported_symbols:
            raise ProviderSymbolNotFoundError(
                f"Instrument {sym!r} not found in golden catalog.",
                symbol=sym,
                provider_id=self.provider_id,
            )

        if sym == "EMPTY":
            return MarketDataResult(
                query=query,
                provider_id=self.provider_id,
                records=(),
            )

        # For SPY (or other supported symbols), return matching slice within query time window
        matched_bars = [
            b for b in self._bars if query.start <= b.timestamp < query.end and b.symbol == sym
        ]

        # If empty within window, return empty tuple
        return MarketDataResult(
            query=query,
            provider_id=self.provider_id,
            records=tuple(matched_bars),
        )


# =============================================================================
# 4. Canonical Expected Facts & Evidence Packets
# =============================================================================

GOLDEN_SPY_EVIDENCE: list[EvidencePacket] = [
    EvidencePacket(
        source_id="regime:SPY:current",
        source_type="regime",
        title="SPY Current Regime Classification",
        facts={
            "symbol": "SPY",
            "current_regime_id": 1,
            "current_regime_label": "REGIME_1",
            "confidence": 0.884,
            "observations_in_current_run": 8,
            "historical_average_duration": 12.5,
            "historical_frequency": 0.50,
            "return_1d": 0.0048,
            "volatility_20d": 0.125,
            "momentum_20d": 0.032,
        },
        timestamp="2026-03-05T00:00:00Z",
        metadata={
            "model_name": "ensemble-gmm-kmeans",
            "model_version": "1.0.0",
            "algorithm": "Ensemble Voting Classifier",
            "provenance": "RegimeX Machine Learning Pipeline V16",
        },
    ),
    EvidencePacket(
        source_id="risk:SPY:metrics",
        source_type="risk",
        title="SPY Historical Portfolio Risk Profile",
        facts={
            "symbol": "SPY",
            "annualized_volatility": 0.180,
            "maximum_drawdown": -0.082,
            "downside_deviation": 0.115,
            "var_95": -0.016,
            "expected_shortfall_95": -0.024,
            "mean_daily_return": 0.0008,
        },
        timestamp="2026-03-05T00:00:00Z",
        metadata={
            "methodology": "Historical simulation across 60 daily trading periods",
            "confidence_level": 0.95,
        },
    ),
    EvidencePacket(
        source_id="backtest:SPY:summary",
        source_type="backtest",
        title="SPY Systematic Backtest Summary",
        facts={
            "symbol": "SPY",
            "strategy_id": "BUY_AND_HOLD",
            "execution_convention": "CURRENT_CLOSE",
            "initial_cash": 100_000.0,
            "final_equity": 114_500.5,
            "total_return": 0.145,
            "total_fees": 45.20,
            "order_count": 12,
            "fill_count": 12,
            "win_rate": 0.667,
            "max_drawdown": -0.065,
        },
        timestamp="2026-03-05T00:00:00Z",
        metadata={
            "simulation_engine": "RegimeX Event-Driven Backtesting Engine V14",
        },
    ),
    EvidencePacket(
        source_id="methodology:general",
        source_type="methodology",
        title="RegimeX Analytical Methodology & Limitations",
        facts={
            "scope": "Quantitative observational analytics and risk measurement",
            "model_family": "Unsupervised Hidden Markov, Gaussian Mixture, and K-Means models",
            "safety_boundary": (
                "No forward price projections, no personalized trade recommendations"
            ),
        },
        timestamp="2026-03-05T00:00:00Z",
        metadata={
            "audit_version": "2026.1",
        },
    ),
]

# Canonical Golden Data Dictionary for cross-layer assertion
SPY_TEST_DATA: dict[str, Any] = {
    "symbol": "SPY",
    "asset_class": "equity_us",
    "exchange": "NYSE",
    "currency": "USD",
    "bar_count": len(GOLDEN_SPY_BARS),
    "first_date": GOLDEN_SPY_BARS[0].timestamp.isoformat(),
    "last_date": GOLDEN_SPY_BARS[-1].timestamp.isoformat(),
    "first_price": GOLDEN_SPY_BARS[0].close,
    "last_price": GOLDEN_SPY_BARS[-1].close,
    "current_regime_id": 1,
    "current_regime_label": "REGIME_1",
    "confidence": 0.884,
    "annualized_volatility": 0.180,
    "maximum_drawdown": -0.082,
    "var_95": -0.016,
    "expected_shortfall_95": -0.024,
    "backtest_total_return": 0.145,
    "backtest_initial_cash": 100_000.0,
    "backtest_final_equity": 114_500.5,
    "model_name": "ensemble-gmm-kmeans",
    "evidence_packets": GOLDEN_SPY_EVIDENCE,
}
