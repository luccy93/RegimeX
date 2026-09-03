# ADR-0002: Market Data Provider Abstraction

**Status:** Accepted  
**Date:** 2026-09-03  
**Volume:** V03 — System Architecture  
**Deciders:** RegimeX Core Architecture Team  

---

## 1. Context

Financial market data is distributed by dozens of commercial and open-source providers (e.g., Yahoo Finance, Alpha Vantage, Polygon.io, Tiingo, IEX Cloud, national exchange feeds). Each vendor utilizes distinct API formats, query parameters, rate limiting strategies, error codes, authentication schemes, and data structures (varying column naming conventions, timestamp formats, and corporate action adjustment rules).

If the core analytics, feature engineering, or regime detection engines were to directly import or invoke vendor-specific SDKs or endpoints, RegimeX would become tightly coupled to external commercial vendors. Any provider deprecation, pricing change, or API redesign would require cascading changes across the entire codebase.

Furthermore, testing analytical pipelines would require live external network connections or fragile, vendor-specific HTTP mocks.

---

## 2. Decision

> **RegimeX mandates that all external market data sources must be accessed exclusively through a vendor-neutral Provider Abstraction Layer.**

1. **Abstract Provider Contract (`MarketDataProvider`):** Core domain code interacts strictly with an abstract interface defining standard data acquisition methods (`fetch()`, `supports()`, `get_supported_symbols()`).
2. **Provider Adapters:** Vendor-specific integration logic (HTTP requests, vendor authentication headers, payload parsing, vendor rate-limiting) is isolated within dedicated adapter classes (e.g., `YahooFinanceAdapter`, `AlphaVantageAdapter`).
3. **Canonical Normalization:** Provider adapters must immediately translate heterogeneous vendor responses into the canonical `OHLCVRecord` schema (`symbol`, `exchange`, `timestamp` in UTC, `open`, `high`, `low`, `close`, `volume`, `adjustment_type`).
4. **Error Translation:** Vendor-specific network or HTTP errors (e.g., HTTP 429, invalid auth keys, missing ticker codes) must be caught at the adapter boundary and translated into strongly typed RegimeX domain exceptions (`RateLimitExceededError`, `SymbolNotFoundError`, `ProviderUnavailableError`).
5. **Source Provenance Metadata:** Every ingested record and batch must retain provenance metadata recording the source provider identifier, ingestion timestamp, and adjustment parameters.
6. **Provider Substitution & Mocking:** Swapping a provider or injecting a mock provider for unit and integration testing requires zero modifications to downstream ingestion pipelines, feature pipelines, or regime detection models.

*Note: The selection of specific concrete providers for initial release is deferred to V05 (Market Data Engine).*

---

## 3. Alternatives Considered

| Alternative | Description | Why Not Chosen |
|-------------|-------------|----------------|
| **Direct SDK Integration** | Calling third-party client libraries (e.g., `yfinance`) directly inside feature and backtesting modules. | Severely couples business logic to external APIs; introduces vendor lock-in; breaks self-hosting independence; breaks unit test isolation. |
| **Unified Data Broker Service** | Deploying a separate external microservice or third-party proxy responsible for fetching data. | Overcomplicates self-hosted deployments; adds unnecessary operational points of failure for local developers. |
| **Database-Level Data Loading** | Bypassing Python application layers and using database ETL scripts or foreign data wrappers (FDWs). | Prevents runtime validation, custom error translation, dynamic provider fallbacks, and local in-memory mock testing. |

---

## 4. Consequences

### Positive
- **Zero Vendor Lock-In:** Core business logic is 100% agnostic to external data vendors.
- **Trivial Extensibility:** Community contributors can add support for new exchanges or niche data providers by simply implementing the `MarketDataProvider` interface.
- **Robust Automated Testing:** Integration tests and CI pipelines can run deterministic test suites using synthetic `MockMarketDataProvider` implementations without incurring external API costs or network flakiness.
- **Isolated Failure Domains:** Provider-specific downtime or API changes affect only the corresponding adapter module, never downstream analytical engines.

### Negative / Trade-offs
- **Adapter Maintenance Overhead:** Each supported provider requires an adapter implementation and maintenance as external APIs evolve.
- **Normalization Tax:** Converting vendor formats into canonical objects introduces a negligible in-memory transformation step.

---

## 5. Requirements Addressed

- **V01 Project Scope:** Multi-market, multi-provider open-source market intelligence.
- **V02 Functional Requirements:**
  - `FR-005`–`FR-013`: Provider-independent market data ingestion, validation, and historical persistence.
- **V02 Non-Functional Requirements:**
  - `NFR-023`: Market data provider outage handling.
  - `NFR-034`: Idempotent data operations.
  - `NFR-078`: Plugin and provider interface stability.
  - `NFR-085`–`NFR-088`: Canonical data quality, timestamp integrity, and duplicate prevention.
  - `NFR-107`: External data provider rate limit handling.
