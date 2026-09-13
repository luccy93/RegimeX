# Yahoo Finance Market Data Provider Adapter

## Overview

The Yahoo Finance provider adapter (`YahooFinanceProvider`) is the initial concrete market data provider implementation in RegimeX. It implements the `MarketDataProvider` domain interface established in V05 Commit 01.

> [!IMPORTANT]
> **Community-First Provider, Not the Exclusive Source:**
> Yahoo Finance via `yfinance` is selected for its zero-friction developer onboarding (no API key required for historical OHLCV data). RegimeX remains strictly provider-independent. The domain and application layers interact exclusively with `MarketDataProvider` domain models.

---

## Architecture & Boundary Isolation

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI / Application Layer                │
│       Depends(market_data_provider_dep) -> MarketDataProvider   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MarketDataProvider (ABC)                   │
│                Domain Layer (Pure Python & Pydantic)            │
│               MarketDataQuery  ──►  MarketDataResult            │
└────────────────────────────────▲────────────────────────────────┘
                                 │ implements
┌────────────────────────────────┴────────────────────────────────┐
│             YahooFinanceProvider (Infrastructure Adapter)       │
│                                                                 │
│  1. Translates MarketDataQuery via YahooFinanceSymbolResolver   │
│  2. Calls vendor synchronously in asyncio.to_thread() pool      │
│  3. Bounded retries with exponential backoff                    │
│  4. Translates vendor exceptions to ProviderError hierarchy     │
│  5. Maps raw DataFrame into canonical OHLCVRecord tuple         │
│  6. Returns MarketDataResult (Pandas never leaks)               │
└─────────────────────────────────────────────────────────────────┘
```

### Pandas Boundary
Pandas is restricted strictly to `apps/api/app/modules/market_data/infrastructure/providers/yahoo_finance/mapper.py`.
Domain models (`OHLCVRecord`, `MarketDataResult`) contain pure Python datatypes (`datetime`, `float`, `str`, `Decimal`). No pandas DataFrame or Series escapes the infrastructure adapter.

---

## Provider Identification & Capabilities

- **Provider ID:** `yahoo_finance` (deterministic snake_case, unique registry key)
- **Display Name:** `"Yahoo Finance"`
- **Version:** `"1.0.0"`

### Supported Capabilities
- **Asset Classes:**
  - `AssetClass.EQUITY_US` (US Equities: NASDAQ, NYSE, AMEX, BATS, ARCA, OTC)
  - `AssetClass.EQUITY_IN` (Indian Equities: NSE, BSE)
  - `AssetClass.INDEX` (Major world indices, e.g. `^GSPC`, `^NSEI`, `^NDX`)
  - `AssetClass.CRYPTO` (Crypto pairs with quote currency, e.g. `BTC-USD`, `ETH-USD`)
  - `AssetClass.FX` (Forex currency pairs, e.g. `EURUSD=X`)
  - `AssetClass.COMMODITY` (Commodity futures, e.g. `GC=F`, `CL=F`)
- **Intervals:**
  - Sub-daily: `1m`, `5m`, `15m`, `30m`, `1h`
  - Daily: `1d`
  - Weekly: `1w`
  - *Note:* `4h` is unsupported by Yahoo Finance and raises `ProviderConfigurationError`.
- **Adjustment Policies:**
  - `AdjustmentPolicy.RAW` (`auto_adjust=False`)
  - `AdjustmentPolicy.FULLY_ADJUSTED` (`auto_adjust=True`)
  - `AdjustmentPolicy.SPLIT_ADJUSTED` (Maps to `auto_adjust=True`, since Yahoo Finance download API bundles split and dividend adjustments)
- **Intraday Support:** `True` (Yahoo Finance supplies intraday bars for recent periods)
- **Symbol Search:** `False` (Yahoo Finance has no official offline symbol directory; `get_supported_symbols()` returns `[]`)
- **Rate Limit:** Unstated / vendor-dependent (`None`)

---

## Configuration

The adapter is configured via environment variables prefixed with `REGIMEX_YAHOO_FINANCE_`:

| Environment Variable | Type | Default | Description |
|----------------------|------|---------|-------------|
| `REGIMEX_YAHOO_FINANCE_TIMEOUT_SECONDS` | int | `30` | Network request timeout in seconds |
| `REGIMEX_YAHOO_FINANCE_MAX_RETRIES` | int | `2` | Maximum retry attempts for transient failures |
| `REGIMEX_YAHOO_FINANCE_BACKOFF_FACTOR` | float | `0.5` | Exponential backoff base factor (seconds) |
| `REGIMEX_YAHOO_FINANCE_USER_AGENT` | str | `None` | Optional custom User-Agent header |
| `REGIMEX_YAHOO_FINANCE_PROXY` | str | `None` | Optional HTTP/HTTPS proxy URL |

> [!NOTE]
> **No API Key Required:** No `YFINANCE_API_KEY` or synthetic credentials exist.

---

## Symbol Mapping

The `YahooFinanceSymbolResolver` translates canonical RegimeX instruments into Yahoo Finance tickers:

| Asset Class | RegimeX Instrument | Exchange | Yahoo Finance Ticker |
|-------------|--------------------|----------|----------------------|
| Equity US | `AAPL` | `NASDAQ` | `AAPL` |
| Equity US | `BRK.B` | `NYSE` | `BRK-B` |
| Equity IN | `RELIANCE` | `NSE` | `RELIANCE.NS` |
| Equity IN | `TCS` | `BSE` | `TCS.BO` |
| Index | `SPX` | `INDEX` | `^GSPC` |
| Index | `NIFTY50` | `NSE` | `^NSEI` |
| Crypto | `BTC` (currency=USD) | `CRYPTO` | `BTC-USD` |
| FX | `EURUSD` | `FX` | `EURUSD=X` |
| Commodity | `GC=F` | `COMEX` | `GC=F` |

If an instrument cannot be resolved (e.g. unsupported asset class or invalid exchange), `ProviderSymbolNotFoundError` is raised.

---

## Error Handling & Translation

Vendor and library exceptions are caught at the adapter boundary and mapped into the RegimeX domain error hierarchy:

| Vendor Failure Condition | RegimeX Exception | HTTP Status Mapping |
|--------------------------|-------------------|---------------------|
| HTTP 429 / Rate Limit Exceeded | `ProviderRateLimitError` | 429 Too Many Requests |
| Connection timeout, DNS failure, 5xx | `ProviderUnavailableError` | 503 Service Unavailable |
| Ticker not found, delisted | `ProviderSymbolNotFoundError` | 404 Not Found |
| Missing OHLCV columns, NaN prices | `ProviderDataError` | 502 Bad Gateway |
| Unsupported interval/adjustment policy | `ProviderConfigurationError` | 400 Bad Request |

---

## Code Example: Requesting Data via Abstraction

```python
from datetime import UTC, datetime, timedelta
from app.modules.market_data.domain import (
    AssetClass,
    DataInterval,
    Instrument,
    MarketDataQuery,
    MarketDataProvider,
)
from app.modules.market_data.application.registry import default_registry

async def fetch_apple_daily_bars() -> None:
    # 1. Resolve provider through registry (or FastAPI dependency)
    provider: MarketDataProvider = default_registry.get("yahoo_finance")

    # 2. Build canonical query
    query = MarketDataQuery(
        instrument=Instrument(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY_US,
            exchange="NASDAQ",
            currency="USD",
        ),
        start=datetime.now(tz=UTC) - timedelta(days=30),
        end=datetime.now(tz=UTC),
        interval=DataInterval.ONE_DAY,
    )

    # 3. Retrieve canonical data
    result = await provider.get_ohlcv(query)

    print(f"Fetched {result.record_count} bars for {result.symbol}")
    for bar in result.records:
        print(f"{bar.timestamp.isoformat()} Open={bar.open} Close={bar.close} Vol={bar.volume}")
```

---

## Testing Strategy

- **100% Offline by Default:** Unit and contract tests use mocked data and fixtures in `conftest.py`. No internet access is required during CI or standard test runs.
- **Contract Tests:** `test_contract.py` verifies compliance with `MarketDataProvider` invariants, registry registration, and no pandas leakage.
- **Optional Live Smoke Test:** `tests/integration/market_data/test_yahoo_finance_live.py` is skipped by default. Run with `REGIMEX_RUN_LIVE_TESTS=1 pytest tests/integration/market_data/test_yahoo_finance_live.py -v`.

---

## Adding Another Provider

To add another market data provider (e.g. `alpha_vantage`, `polygon`):
1. Create `apps/api/app/modules/market_data/infrastructure/providers/<provider_id>/`
2. Implement `MarketDataProvider` (inherit from ABC)
3. Implement mapper converting vendor response to `tuple[OHLCVRecord, ...]`
4. Register the new provider with `ProviderRegistry` (`registry.register(NewProvider())`)
5. No changes to `domain/` models, errors, or queries are needed!
