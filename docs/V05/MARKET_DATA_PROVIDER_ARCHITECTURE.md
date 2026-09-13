# Market Data Provider Architecture

**RegimeX — Open-Source Market Intelligence Platform**
**Volume:** V05 — Market Data Engine
**Document:** V05 Commit 01 — Provider Abstraction Layer
**Status:** Implemented

---

## 1. Overview

This document describes the Market Data Provider Abstraction Layer implemented
in V05 Commit 01. It explains the design decisions, component responsibilities,
and how future contributors can extend the platform with new data providers.

The abstraction was mandated by ADR-0002 and ADR-0004 (V03) and is the
foundational prerequisite for all market data ingestion, feature engineering,
regime detection, and backtesting work in subsequent volumes.

---

## 2. Why an Abstraction Layer?

Financial market data is distributed by dozens of commercial and open-source
providers. Each has distinct:

- REST schemas, query parameters, response shapes
- Rate-limiting strategies and quota models
- Timestamp formats and timezone conventions
- Corporate-action adjustment logic
- Licensing and redistribution constraints

Without an abstraction, every provider change cascades into the analytics,
feature, and backtesting layers. With it:

```
     RegimeX Analytics / Feature / Regime layers
                         │
                         ▼
              MarketDataProvider (ABC)        ← only this contract
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   YahooAdapter   PolygonAdapter   FutureAdapter   ← isolated in infrastructure/
```

Domain and analytical code never imports from a provider adapter.

---

## 3. Canonical Domain Models

All provider adapters must translate vendor responses into these RegimeX-native
types. Downstream modules (features, regime, risk, backtesting) consume only
these types — never vendor-specific objects.

### 3.1 AssetClass

```python
class AssetClass(StrEnum):
    EQUITY_US = "equity_us"
    EQUITY_IN = "equity_in"
    INDEX     = "index"
    CRYPTO    = "crypto"
    FX        = "fx"
    COMMODITY = "commodity"
```

### 3.2 DataInterval

```python
class DataInterval(StrEnum):
    ONE_MIN     = "1m"
    FIVE_MIN    = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN  = "30m"
    ONE_HOUR    = "1h"
    FOUR_HOUR   = "4h"
    ONE_DAY     = "1d"
    ONE_WEEK    = "1w"
```

Not every provider supports every interval. Provider capability differences
are declared explicitly via `ProviderCapabilities` — no hard-coded logic.

### 3.3 Instrument

```python
class Instrument(BaseModel):
    symbol:      str        # RegimeX canonical id, e.g. "AAPL", "RELIANCE"
    asset_class: AssetClass
    exchange:    str        # e.g. "NASDAQ", "NSE", "BINANCE"
    currency:    str        # ISO 4217, e.g. "USD", "INR"
    description: str        # optional human-readable name
```

`symbol` and `exchange` are always uppercased. Provider-specific symbol
mappings (e.g. `"RELIANCE.NS"` for Yahoo Finance) remain inside adapters.

### 3.4 OHLCVRecord

```python
class OHLCVRecord(BaseModel):
    symbol:            str
    timestamp:         datetime   # must be timezone-aware (UTC)
    open:              float      # > 0
    high:              float      # >= open, >= close, >= low
    low:               float      # <= open, <= close
    close:             float      # > 0
    volume:            float      # >= 0
    interval:          DataInterval
    adjustment_policy: AdjustmentPolicy
    source_provider_id: str       # provenance — which adapter produced this
    ingested_at:       datetime   # UTC ingestion timestamp
```

**Validated invariants** (enforced at construction, not at the quality-pipeline level):

| Rule | Rejection |
|------|-----------|
| `timestamp` is timezone-aware | `ValidationError` |
| `open`, `high`, `low`, `close` > 0 | `ValidationError` |
| `volume` ≥ 0 | `ValidationError` |
| `high` ≥ `low`, `high` ≥ `open`, `high` ≥ `close` | `ValidationError` |
| `low` ≤ `open`, `low` ≤ `close` | `ValidationError` |

> **Scope note:** Full data-quality validation (gap repair, duplicate removal,
> trading-calendar alignment, anomaly detection) belongs to the V06 data quality
> pipeline (`regimex.quality`). This model enforces structural correctness only.

### 3.5 MarketDataQuery

```python
class MarketDataQuery(BaseModel):
    instrument:        Instrument
    start:             datetime          # timezone-aware, inclusive
    end:               datetime          # timezone-aware, exclusive, > start
    interval:          DataInterval      # default: ONE_DAY
    adjustment_policy: AdjustmentPolicy # default: SPLIT_ADJUSTED
```

### 3.6 MarketDataResult

```python
class MarketDataResult(BaseModel):
    query:       MarketDataQuery        # echoed for result correlation
    provider_id: str                    # which provider produced this
    fetched_at:  datetime               # UTC, when provider responded
    records:     tuple[OHLCVRecord, ...]  # ascending chronological order
```

---

## 4. Provider Interface

`MarketDataProvider` (abstract base class) is the single contract all adapters
must satisfy. Located at:

```
apps/api/app/modules/market_data/domain/provider.py
```

```python
class MarketDataProvider(ABC):

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    async def metadata(self) -> ProviderMetadata: ...

    @abstractmethod
    async def capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    async def supports(self, instrument: Instrument) -> bool: ...

    @abstractmethod
    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]: ...

    @abstractmethod
    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult: ...
```

### Why async?

The entire RegimeX backend is event-loop-native (FastAPI + Celery workers).
Making provider methods `async` ensures adapters can perform network I/O
without blocking the event loop.

Adapters wrapping synchronous vendor SDKs must use `asyncio.to_thread()` inside
their `async` implementations:

```python
import asyncio

async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
    data = await asyncio.to_thread(self._sync_vendor_call, query)
    return self._normalise(data, query)
```

---

## 5. Provider Capability Model

Each provider declares its capabilities via `ProviderCapabilities`:

```python
class ProviderCapabilities(BaseModel):
    supported_asset_classes:      frozenset[AssetClass]
    supported_intervals:          frozenset[DataInterval]
    supported_exchanges:          frozenset[str]
    supported_adjustment_policies: frozenset[AdjustmentPolicy]
    supports_intraday:            bool
    supports_symbol_search:       bool
    max_history_days:             int | None
    rate_limit_per_minute:        int | None
```

The platform can route queries to the correct provider without inspecting
adapter internals:

```python
caps = await provider.capabilities()
if DataInterval.ONE_HOUR not in caps.supported_intervals:
    raise ProviderDataError("Provider does not support intraday data")
```

---

## 6. Provider Registry

Located at:

```
apps/api/app/modules/market_data/application/registry.py
```

The `ProviderRegistry` maps `provider_id → MarketDataProvider` instance.

```python
registry = ProviderRegistry()
registry.register(my_provider)          # raises ConflictError on duplicate
provider = registry.get("my_provider")  # raises NotFoundError if unknown
ids = registry.list_providers()         # sorted list of registered ids
```

**Dependency injection:** Application services receive the registry via FastAPI
dependency injection. Tests construct isolated `ProviderRegistry()` instances
— they do not mutate `default_registry`.

**Scope:** The registry is intentionally limited to market-data providers. It
is not a general service locator.

---

## 7. Error Hierarchy

All provider adapters must catch vendor-specific exceptions at the adapter
boundary and re-raise as the appropriate `ProviderError` subtype:

```
RegimeXError
└── ProviderError                      (base — all provider failures)
    ├── ProviderConfigurationError     (missing/invalid adapter config)
    ├── ProviderUnavailableError       (network failure, 5xx)
    ├── ProviderRateLimitError         (429, quota exhausted)
    ├── ProviderAuthenticationError    (401/403, invalid credentials)
    ├── ProviderDataError              (malformed/unexpected response)
    └── ProviderSymbolNotFoundError    (instrument not in provider)
```

**Isolation rule:** Vendor SDK exception types (`httpx.HTTPError`,
`requests.ConnectionError`, vendor-specific exceptions) must **never** appear
in the arguments or attributes of these domain exceptions.

```python
# CORRECT — in an adapter:
try:
    raw = await self._http_client.get(url)
except httpx.TimeoutException as exc:
    raise ProviderUnavailableError(
        f"Provider {self.provider_id!r} timed out after {timeout}s",
        provider_id=self.provider_id,
    ) from exc   # original exc in __cause__ for debugging, not exposed

# WRONG — do not do this:
raise httpx.TimeoutException(...)   # leaks HTTP client type
```

`ProviderRateLimitError` carries an optional `retry_after_seconds` attribute
that adapters may populate from the provider's `Retry-After` header.

`ProviderSymbolNotFoundError` carries the `symbol` that was not found.

---

## 8. Provider Isolation

```
apps/api/app/modules/market_data/
    domain/          ← canonical models, provider ABC, domain errors
    application/     ← ProviderRegistry, use-case services
    infrastructure/  ← concrete adapters (added in V05 Commit 02+)
    api/             ← HTTP endpoints (future)
```

**Prohibited in `domain/`:**

- HTTP client imports (`httpx`, `requests`, `aiohttp`)
- Vendor SDK imports (`yfinance`, `polygon`, etc.)
- ORM imports (`sqlalchemy`, `asyncpg`)
- Infrastructure layer imports

The architectural boundary is enforced by `tests/unit/market_data/test_architecture.py`.

---

## 9. Extension Guide — Implementing a New Provider

This guide shows how a future contributor implements a new adapter without
modifying any domain code.

### Step 1 — Create the adapter file

```
apps/api/app/modules/market_data/infrastructure/my_provider.py
```

### Step 2 — Implement the interface

```python
from datetime import datetime, timezone
from app.modules.market_data.domain import (
    AssetClass, DataInterval, Instrument,
    MarketDataProvider, MarketDataQuery, MarketDataResult,
    OHLCVRecord, ProviderCapabilities, ProviderMetadata,
    ProviderUnavailableError, ProviderSymbolNotFoundError,
)

class MyProvider(MarketDataProvider):

    PROVIDER_ID = "my_provider"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key  # loaded from environment, never hardcoded

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    async def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.PROVIDER_ID,
            display_name="My Provider",
            version="1.0.0",
            capabilities=await self.capabilities(),
        )

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supported_asset_classes=frozenset({AssetClass.EQUITY_US}),
            supported_intervals=frozenset({DataInterval.ONE_DAY}),
            supported_exchanges=frozenset({"NYSE", "NASDAQ"}),
            supports_intraday=False,
            supports_symbol_search=False,
            max_history_days=365 * 20,
            rate_limit_per_minute=60,
        )

    async def supports(self, instrument: Instrument) -> bool:
        caps = await self.capabilities()
        return instrument.asset_class in caps.supported_asset_classes

    async def get_supported_symbols(
        self, asset_class: AssetClass | None = None
    ) -> list[Instrument]:
        return []  # provider does not support symbol search

    async def get_ohlcv(self, query: MarketDataQuery) -> MarketDataResult:
        try:
            raw_data = await self._fetch_from_vendor(query)
        except VendorNetworkError as exc:            # vendor-specific type
            raise ProviderUnavailableError(          # translate to domain type
                f"My Provider is unreachable: {exc}",
                provider_id=self.PROVIDER_ID,
            ) from exc

        records = tuple(self._normalise(bar) for bar in raw_data)
        return MarketDataResult(
            query=query,
            provider_id=self.PROVIDER_ID,
            fetched_at=datetime.now(tz=timezone.utc),
            records=records,
        )
```

### Step 3 — Register during application startup

```python
# In the FastAPI lifespan or startup event:
from app.modules.market_data.application.registry import default_registry
from app.modules.market_data.infrastructure.my_provider import MyProvider

default_registry.register(MyProvider(api_key=settings.my_provider_api_key))
```

### Step 4 — Write tests using the FakeProvider pattern

Never test against the live API in unit tests. Use synthetic records and a
`FakeProvider` (see `tests/unit/market_data/conftest.py`).

---

## 10. Security Notes

- API keys must be supplied via environment variables. Never commit keys.
- `ProviderAuthenticationError` must not include the raw key in its message.
- Provider adapter configuration is validated at startup via `ProviderConfigurationError`.

---

## 11. Files Delivered — V05 Commit 01

| Layer | File | Purpose |
|-------|------|---------|
| domain | `domain/models.py` | OHLCVRecord, Instrument, Query, Result, enums |
| domain | `domain/provider.py` | MarketDataProvider ABC, ProviderCapabilities, ProviderMetadata |
| domain | `domain/errors.py` | ProviderError hierarchy |
| domain | `domain/__init__.py` | Public re-exports |
| application | `application/registry.py` | ProviderRegistry |
| application | `application/__init__.py` | Public re-exports |
| tests | `tests/unit/market_data/conftest.py` | FakeProvider, shared fixtures |
| tests | `tests/unit/market_data/test_models.py` | Domain model tests |
| tests | `tests/unit/market_data/test_provider.py` | Interface + capability tests |
| tests | `tests/unit/market_data/test_registry.py` | Registry tests |
| tests | `tests/unit/market_data/test_errors.py` | Exception hierarchy tests |
| tests | `tests/unit/market_data/test_architecture.py` | Boundary enforcement tests |
| docs | `docs/V05/MARKET_DATA_PROVIDER_ARCHITECTURE.md` | This document |

---

## 12. What Is NOT Implemented Here

| Feature | Volume |
|---------|--------|
| Concrete provider adapters (Yahoo Finance, etc.) | V05 Commit 02 |
| Data quality pipeline (gap repair, deduplication) | V06 |
| Trading calendar validation | V06 |
| Market data HTTP API endpoints | V05 / V06 |
| Celery ingestion workers | V05 |
| TimescaleDB persistence | V05 |
