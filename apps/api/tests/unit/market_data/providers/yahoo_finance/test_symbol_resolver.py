"""
Unit tests for YahooFinanceSymbolResolver.
"""

from __future__ import annotations

import pytest
from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import AssetClass, Instrument
from app.modules.market_data.infrastructure.providers.yahoo_finance.symbol_resolver import (
    YahooFinanceSymbolResolver,
)


class TestYahooFinanceSymbolResolver:
    @pytest.fixture()
    def resolver(self) -> YahooFinanceSymbolResolver:
        return YahooFinanceSymbolResolver()

    def test_us_equity_standard(self, resolver: YahooFinanceSymbolResolver) -> None:
        inst = Instrument(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY_US,
            exchange="NASDAQ",
            currency="USD",
            description="",
        )
        assert resolver.supports_instrument(inst)
        assert resolver.to_provider_symbol(inst) == "AAPL"

    def test_us_equity_share_class_dot(self, resolver: YahooFinanceSymbolResolver) -> None:
        inst = Instrument(
            symbol="BRK.B",
            asset_class=AssetClass.EQUITY_US,
            exchange="NYSE",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(inst) == "BRK-B"

    def test_indian_equity_nse(self, resolver: YahooFinanceSymbolResolver) -> None:
        inst = Instrument(
            symbol="RELIANCE",
            asset_class=AssetClass.EQUITY_IN,
            exchange="NSE",
            currency="INR",
            description="",
        )
        assert resolver.supports_instrument(inst)
        assert resolver.to_provider_symbol(inst) == "RELIANCE.NS"

    def test_indian_equity_bse(self, resolver: YahooFinanceSymbolResolver) -> None:
        inst = Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY_IN,
            exchange="BSE",
            currency="INR",
            description="",
        )
        assert resolver.supports_instrument(inst)
        assert resolver.to_provider_symbol(inst) == "TCS.BO"

    def test_indian_equity_unsupported_exchange(self, resolver: YahooFinanceSymbolResolver) -> None:
        inst = Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY_IN,
            exchange="CALCUTTA",
            currency="INR",
            description="",
        )
        assert not resolver.supports_instrument(inst)
        with pytest.raises(ProviderSymbolNotFoundError):
            resolver.to_provider_symbol(inst)

    def test_index_alias_mapping(self, resolver: YahooFinanceSymbolResolver) -> None:
        spx = Instrument(
            symbol="SPX",
            asset_class=AssetClass.INDEX,
            exchange="INDEX",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(spx) == "^GSPC"

        nifty = Instrument(
            symbol="NIFTY50",
            asset_class=AssetClass.INDEX,
            exchange="NSE",
            currency="INR",
            description="",
        )
        assert resolver.to_provider_symbol(nifty) == "^NSEI"

    def test_index_caret_preservation(self, resolver: YahooFinanceSymbolResolver) -> None:
        vix = Instrument(
            symbol="^VIX",
            asset_class=AssetClass.INDEX,
            exchange="CBOE",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(vix) == "^VIX"

    def test_crypto_symbol_formatting(self, resolver: YahooFinanceSymbolResolver) -> None:
        btc = Instrument(
            symbol="BTC",
            asset_class=AssetClass.CRYPTO,
            exchange="CRYPTO",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(btc) == "BTC-USD"

        btc_pair = Instrument(
            symbol="BTC-USD",
            asset_class=AssetClass.CRYPTO,
            exchange="CRYPTO",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(btc_pair) == "BTC-USD"

    def test_fx_symbol_formatting(self, resolver: YahooFinanceSymbolResolver) -> None:
        eurusd = Instrument(
            symbol="EURUSD",
            asset_class=AssetClass.FX,
            exchange="FX",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(eurusd) == "EURUSD=X"

    def test_commodity_symbol_formatting(self, resolver: YahooFinanceSymbolResolver) -> None:
        gold = Instrument(
            symbol="GC=F",
            asset_class=AssetClass.COMMODITY,
            exchange="COMEX",
            currency="USD",
            description="",
        )
        assert resolver.to_provider_symbol(gold) == "GC=F"
