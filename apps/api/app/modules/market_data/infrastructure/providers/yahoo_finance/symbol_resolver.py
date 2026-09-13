"""
RegimeX Market Data — Yahoo Finance Symbol Resolver
====================================================
Maps canonical RegimeX Instrument domain models to vendor-specific
Yahoo Finance ticker strings, keeping symbol-format details out of the domain.
"""

from __future__ import annotations

import re

from app.modules.market_data.domain.errors import ProviderSymbolNotFoundError
from app.modules.market_data.domain.models import AssetClass, Instrument

# Known major index alias mappings
_INDEX_ALIASES: dict[str, str] = {
    "SPX": "^GSPC",
    "GSPC": "^GSPC",
    "S&P500": "^GSPC",
    "NDX": "^NDX",
    "NASDAQ100": "^NDX",
    "DJI": "^DJI",
    "DOW": "^DJI",
    "VIX": "^VIX",
    "RUT": "^RUT",
    "RUSSELL2000": "^RUT",
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",
    "NSEI": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "BSESN": "^BSESN",
}

# Supported US exchange identifiers
_US_EXCHANGES: frozenset[str] = frozenset({"NASDAQ", "NYSE", "AMEX", "BATS", "ARCA", "US", "OTC"})

# Supported Indian exchange identifiers
_IN_EXCHANGES: dict[str, str] = {
    "NSE": ".NS",
    "BSE": ".BO",
}


class YahooFinanceSymbolResolver:
    """
    Translates RegimeX canonical instruments into Yahoo Finance ticker symbols.
    """

    def supports_instrument(self, instrument: Instrument) -> bool:
        """
        Check if the instrument is supported by Yahoo Finance.

        Returns True if the asset class and exchange configuration can be mapped.
        """
        match instrument.asset_class:
            case AssetClass.EQUITY_US:
                return instrument.exchange.upper() in _US_EXCHANGES
            case AssetClass.EQUITY_IN:
                return instrument.exchange.upper() in _IN_EXCHANGES
            case AssetClass.INDEX:
                return True
            case AssetClass.CRYPTO:
                # Yahoo Finance supports major cryptos paired with USD or major fiat
                return bool(instrument.symbol.strip())
            case AssetClass.FX:
                return bool(instrument.symbol.strip())
            case AssetClass.COMMODITY:
                return bool(instrument.symbol.strip())
            case _:
                return False

    def to_provider_symbol(self, instrument: Instrument) -> str:
        """
        Convert a canonical Instrument to its Yahoo Finance ticker representation.

        Raises:
            ProviderSymbolNotFoundError: If the instrument cannot be mapped.
        """
        if not self.supports_instrument(instrument):
            raise ProviderSymbolNotFoundError(
                f"Instrument {instrument.symbol!r} (exchange={instrument.exchange!r}, "
                f"asset_class={instrument.asset_class.value!r}) is not supported by Yahoo Finance.",
                symbol=instrument.symbol,
                provider_id="yahoo_finance",
            )

        sym = instrument.symbol.strip().upper()

        match instrument.asset_class:
            case AssetClass.EQUITY_US:
                # Class share dots in US equities (e.g. BRK.B -> BRK-B)
                return sym.replace(".", "-")

            case AssetClass.EQUITY_IN:
                suffix = _IN_EXCHANGES[instrument.exchange.upper()]
                clean_sym = sym.removesuffix(".NS").removesuffix(".BO")
                return f"{clean_sym}{suffix}"

            case AssetClass.INDEX:
                if sym in _INDEX_ALIASES:
                    return _INDEX_ALIASES[sym]
                if sym.startswith("^"):
                    return sym
                return f"^{sym}"

            case AssetClass.CRYPTO:
                if "-" in sym:
                    return sym
                quote = instrument.currency.upper() or "USD"
                return f"{sym}-{quote}"

            case AssetClass.FX:
                clean_sym = re.sub(r"[^A-Z]", "", sym)
                if clean_sym.endswith("=X"):
                    return clean_sym
                return f"{clean_sym}=X"

            case AssetClass.COMMODITY:
                if sym.endswith("=F"):
                    return sym
                return sym

            case _:
                raise ProviderSymbolNotFoundError(
                    f"Unsupported asset class: {instrument.asset_class}",
                    symbol=instrument.symbol,
                    provider_id="yahoo_finance",
                )
