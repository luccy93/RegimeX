"""
RegimeX AI Research — Symbol Resolution
=======================================
Deterministic instrument symbol extraction and resolution against the platform market catalog.
Ensures the assistant never hallucinates ticker symbols or operates over unsupported instruments.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.market_data.application.service import MarketDataService

# Regex matching standard financial tickers (e.g. 'SPY', 'QQQ', 'AAPL', 'BTC-USD', 'EUR-USD')
SYMBOL_TOKEN_PATTERN = re.compile(r"\b([A-Z]{1,10}(?:-[A-Z]{1,10})?)\b")

# Common English words in uppercase that should not be mistaken for tickers
EXCLUDED_WORDS: frozenset[str] = frozenset(
    {
        # Single-letter and two-letter words
        "A",
        "I",
        "AN",
        "IN",
        "ON",
        "AT",
        "TO",
        "OF",
        "OR",
        "IS",
        "AS",
        "BY",
        "IF",
        "SO",
        "NO",
        "DO",
        "MY",
        "HE",
        "WE",
        "US",
        "UP",
        # Pronouns
        "YOU",
        "YOUR",
        "THEY",
        "THEM",
        "THEIR",
        "SHE",
        "HER",
        "IT",
        "ITS",
        "OUR",
        "WHO",
        "ME",
        # Articles & Conjunctions
        "THE",
        "AND",
        "BUT",
        "FOR",
        "NOR",
        "YET",
        "THAN",
        "THAT",
        "THIS",
        "THESE",
        "THOSE",
        # Verbs & Auxiliaries
        "ARE",
        "WAS",
        "WERE",
        "BE",
        "BEEN",
        "BEING",
        "HAVE",
        "HAS",
        "HAD",
        "DOES",
        "DID",
        "CAN",
        "COULD",
        "WILL",
        "WOULD",
        "SHALL",
        "SHOULD",
        "MAY",
        "MIGHT",
        "MUST",
        "TELL",
        "SHOW",
        "GIVE",
        "EXPLAIN",
        "KNOW",
        "GET",
        "SEE",
        "LOOK",
        "FIND",
        # Question words
        "WHAT",
        "HOW",
        "WHY",
        "WHEN",
        "WHERE",
        "WHICH",
        # Prepositions & Adverbs
        "WITH",
        "FROM",
        "OVER",
        "UNDER",
        "BETWEEN",
        "DURING",
        "BEFORE",
        "AFTER",
        "ABOUT",
        "NOT",
        "ALL",
        "ANY",
        "SOME",
        "MANY",
        "MUCH",
        "MORE",
        "MOST",
        "VERY",
        "JUST",
        "ALSO",
        "ONLY",
        "NOW",
        "THEN",
        "TODAY",
        "NEXT",
        "LAST",
        "PAST",
        # Common domain words that aren't tickers
        "REGIME",
        "REGIMES",
        "MARKET",
        "MARKETS",
        "ASSET",
        "ASSETS",
        "STOCK",
        "STOCKS",
        "DATA",
        "PRICE",
        "PRICES",
        "CHART",
        "CHARTS",
        "INFO",
        "STATE",
        "STATES",
        "MODEL",
        "MODELS",
        "RISK",
        "TEST",
        "RUN",
        "BUY",
        "SELL",
        "HOLD",
        # Common acronyms that aren't tickers
        "VAR",
        "ES",
        "GMM",
        "HMM",
        "ML",
        "AI",
        "API",
        "USD",
        "PNL",
        "DD",
        "NEW",
        "OLD",
        "TOP",
        "LOW",
        "HIGH",
    }
)


class SymbolResolver:
    """
    Resolves instrument symbols against the active platform market catalog.
    """

    def __init__(self, market_service: MarketDataService) -> None:
        self._market_service = market_service

    async def resolve(
        self,
        question: str,
        explicit_symbol: str | None = None,
    ) -> tuple[str | None, str | None]:
        """
        Extract and validate instrument symbol against the market catalog.

        Returns:
            (canonical_symbol, unrecognized_symbol)
            - If valid catalog symbol resolved: (symbol, None)
            - If an explicit ticker was mentioned but not in catalog: (None, mentioned_token)
            - If no ticker was mentioned or requested: (None, None)
        """
        # Fetch active catalog
        markets = await self._market_service.list_markets()
        catalog_symbols: dict[str, str] = {m.symbol.upper(): m.symbol for m in markets}

        # 1. Check explicit symbol parameter if provided
        if explicit_symbol:
            clean = explicit_symbol.strip().upper()
            if clean in catalog_symbols:
                return catalog_symbols[clean], None
            return None, clean

        # 2. Extract potential ticker tokens from the question text
        candidates: list[str] = []
        for match in SYMBOL_TOKEN_PATTERN.finditer(question):
            token = match.group(1).upper()
            if token not in EXCLUDED_WORDS:
                candidates.append(token)

        # Check candidates against catalog
        for candidate in candidates:
            if candidate in catalog_symbols:
                return catalog_symbols[candidate], None

        # If candidates were extracted but none match catalog, record first as unrecognized
        if candidates:
            return None, candidates[0]

        return None, None
