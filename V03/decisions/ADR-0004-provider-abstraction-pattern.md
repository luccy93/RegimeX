# ADR-0004: Provider Abstraction Pattern

**Status:** Accepted  
**Date:** 2026-09-03  
**Volume:** V03 — System Architecture  
**Deciders:** RegimeX Core Architecture Team  

---

## 1. Context

RegimeX is designed to deliver multi-market intelligence across diverse asset classes (equities, indices, commodities, crypto) and global regions. To achieve this, the platform must consume market data from an evolving array of commercial and open-source data providers (e.g., Yahoo Finance, Alpha Vantage, Polygon.io, Tiingo, Indian NSE direct feeds, crypto exchanges).

Each data vendor exhibits unique operational characteristics:
- Proprietary REST schemas, column naming, and response hierarchies.
- Divergent rate-limiting headers, throttling algorithms, and quota models.
- Differing corporate action adjustment logic (split-adjusted vs dividend-adjusted vs unadjusted).
- Variable timestamp formats, timezone conventions, and holiday calendars.
- Restrictive licensing agreements that constrain data redistribution.

If the core analytical modules (feature engineering, regime detection, risk computation, backtesting) were directly coupled to provider-specific client libraries or endpoints, introducing or replacing a data source would require extensive refactoring across the platform.

---

## 2. Decision

> **All external market-data providers must be accessed exclusively through the Provider Abstraction Pattern, isolating vendor protocols behind standardized adapters and canonical domain contracts.**

### Core Implementation Directives:
1. **Vendor Isolation:** The core domain engine interacts strictly with the abstract `MarketDataProvider` interface. Direct HTTP calls, vendor SDK imports, and vendor authentication logic are strictly isolated within `regimex/data/providers/<provider_name>.py`.
2. **Canonical Data Model:** Every provider adapter must normalize incoming external data into the canonical `OHLCVRecord` schema (`symbol`, `exchange`, `timestamp` in UTC ISO 8601, `open`, `high`, `low`, `close`, `volume`, `adjustment_type`).
3. **Provider-Specific Error Translation:** Upstream HTTP errors, timeouts, or vendor authentication failures must be caught at the adapter boundary and translated into strongly typed RegimeX domain exceptions (`ProviderRateLimitError`, `SymbolNotFoundError`, `ProviderUnavailableError`).
4. **Testing with Synthetic Mocks:** Automated unit, integration, and CI test suites must use synthetic mock providers (`MockMarketDataProvider`) implementing the identical interface, allowing full offline testing with zero live API calls or network flakiness.
5. **Seamless Provider Replacement:** An operator or researcher can switch the primary data provider for an instrument or asset class via simple configuration change without altering downstream feature pipelines or regime models.
6. **Community Extensibility:** Community contributors can author and maintain custom provider adapters (e.g., for specialized regional exchanges) by implementing the well-documented adapter interface.
7. **Licensing & Redistribution Safeguards:** Provider adapters must record upstream licensing metadata. The platform architecture prohibits bulk public raw data redistribution that violates vendor redistribution constraints (complying with NFR-108).

*Note: Specific provider selections for initial releases will be decided in V05 (Market Data Engine).*

---

## 3. Alternatives Considered

| Alternative | Description | Why Rejected |
|-------------|-------------|--------------|
| **Direct Vendor SDK Calls in Domain** | Importing third-party client libraries (e.g., `yfinance`, `polygon-api-client`) directly in feature and backtesting modules. | Tight vendor coupling; any vendor API deprecation breaks core analytical engines; violates zero vendor lock-in principle. |
| **External Standalone Data Proxy** | Running an independent data proxy microservice outside RegimeX. | Increases operational complexity for self-hosters; introduces network overhead for local developers without clear architectural benefit. |
| **Generic Pandas DataReader** | Relying on unmaintained community data loaders. | Poor reliability, lack of explicit error translation, absent time-series normalization, no licensing enforcement. |

---

## 4. Consequences

### Positive
- **Complete Vendor Agnosticism:** Core business logic remains 100% independent of commercial data providers.
- **High Test Reliability:** CI pipelines run deterministic tests using mock providers without incurring API costs or rate-limiting delays.
- **Ecosystem Extensibility:** Open-source developers can contribute new adapters with minimal effort.
- **Graceful Failure Handling:** Vendor outages trigger isolated retry/backoff routines without crashing the core service.

### Negative / Trade-offs
- **Adapter Maintenance Overhead:** Each supported vendor requires ongoing maintenance as third-party APIs update.
- **Normalization Ingestion Overhead:** Minor in-memory serialization and transformation step during ingestion.

---

## 5. Requirements Addressed

- **V01 Project Scope:** Open-source, multi-provider market intelligence platform.
- **V02 Functional Requirements:**
  - `FR-005`: Provider-independent market data ingestion.
  - `FR-006`: Provider abstraction architecture.
  - `FR-007`: Normalized canonical data format.
  - `FR-010`: Provider health and error monitoring.
- **V02 Non-Functional Requirements:**
  - `NFR-023`: Market data provider outage handling.
  - `NFR-034`: Idempotent data ingestion operations.
  - `NFR-078`: Provider interface stability.
  - `NFR-085`–`NFR-088`: Data completeness, correctness, duplicate detection, and UTC timestamp integrity.
  - `NFR-107`: External provider rate limit compliance.
  - `NFR-108`: Data redistribution restriction enforcement.
