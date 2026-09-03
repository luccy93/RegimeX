# Software Requirements Specification

**RegimeX — Open-Source Market Intelligence Platform**

---

## Document Control

| Field | Value |
|-------|-------|
| **Document** | Software Requirements Specification (SRS) |
| **Project** | RegimeX |
| **Product** | Open-Source Market Intelligence Platform |
| **Version** | 0.1 |
| **Status** | Draft — V02 |
| **Volume** | V02 — Enterprise Requirements |
| **Last Updated** | 2026-09-03 |
| **Requirement ID Convention** | `FR-NNN` — Functional Requirement |

### Related V01 Documents

| Document | Purpose |
|----------|---------|
| [`V01/PRODUCT_FOUNDATION.md`](../V01/PRODUCT_FOUNDATION.md) | Product vision, positioning, target users |
| [`V01/PROJECT_SCOPE.md`](../V01/PROJECT_SCOPE.md) | In-scope and out-of-scope boundaries |
| [`V01/PRINCIPLES.md`](../V01/PRINCIPLES.md) | Product, engineering, and quantitative principles |
| [`V01/PRODUCT_ROADMAP.md`](../V01/PRODUCT_ROADMAP.md) | 30-volume development roadmap |

### Companion V02 Documents

| Document | Relationship to this SRS |
|----------|--------------------------|
| [`FUNCTIONAL_REQUIREMENTS.md`](./FUNCTIONAL_REQUIREMENTS.md) | Detailed FR tables by domain (source for Section 10) |
| [`NONFUNCTIONAL_REQUIREMENTS.md`](./NONFUNCTIONAL_REQUIREMENTS.md) | NFR tables (performance, reliability, security, scalability) |
| [`DATA_CONTRACTS.md`](./DATA_CONTRACTS.md) | Canonical data schemas (source for Section 12) |
| [`API_CONTRACTS.md`](./API_CONTRACTS.md) | API versioning, error model, authentication contracts |
| [`USER_STORIES.md`](./USER_STORIES.md) | User stories by actor type |
| [`GLOSSARY.md`](./GLOSSARY.md) | Authoritative domain term definitions |

### Requirement ID Convention

```text
FR-NNN   — Functional Requirement (this document)
```

All FR identifiers in this document are unique, sequential, and non-duplicated. Cross-domain traceability is maintained in Section 15.

> ⚠️ **None of the capabilities described in this SRS are implemented.** Implementation begins in V04+. This document defines the functional contract — what the platform must do — before any engineering decisions are locked in.

---

## 1. Purpose

This Software Requirements Specification establishes the functional contract for the RegimeX platform. It defines, with precision and testability, what the platform must do across all product areas — from market data ingestion through regime detection, risk analytics, backtesting, research tooling, AI-assisted research, API access, and the web experience.

These requirements will guide:

- **Architecture design** — defining module boundaries, data flows, and integration patterns (V03)
- **Implementation** — providing the specification that all engineering volumes (V04–V21) build against
- **Testing** — forming the basis for acceptance criteria, unit tests, integration tests, and end-to-end test cases
- **API design** — defining the behavioral contract that the REST API must fulfill
- **Frontend behavior** — specifying the observable behaviors the web platform must support
- **ML and quantitative functionality** — constraining model interfaces, reproducibility, and uncertainty handling
- **Operational validation** — providing observable requirements that production monitoring can verify
- **Future releases** — serving as the baseline from which V1.0+ enhancements are scoped and tracked

This document is not an implementation specification. It does not describe how requirements will be implemented — it describes what the implemented system must do and how it must behave from the perspective of its users and operators.

---

## 2. Scope

This SRS covers the full functional scope of the RegimeX platform as defined in [`V01/PROJECT_SCOPE.md`](../V01/PROJECT_SCOPE.md).

RegimeX is intended to become an open-source market intelligence and quantitative research platform. Its full scope encompasses the following product areas, none of which are implemented in V01 or V02:

| Product Area | Description |
|-------------|-------------|
| **Market Discovery** | Discovery of supported markets, instruments, and data availability |
| **Market Data** | Provider-independent ingestion and normalized storage of historical OHLCV market data |
| **Quantitative Feature Engineering** | Point-in-time, reproducible feature computation from market data |
| **Market Regime Detection** | Detection of market regimes using multiple configurable algorithms |
| **Regime Intelligence** | Analysis of regime history, transition probabilities, and regime-conditional statistics |
| **Regime Transitions** | Detection, characterization, and early-warning signals for regime transitions |
| **Risk Analytics** | Regime-aware computation of volatility, drawdown, VaR, CVaR, and correlation metrics |
| **Backtesting** | Event-driven historical strategy simulation with realistic cost models and walk-forward validation |
| **Research Workflows** | Reproducible, parameterized, versioned quantitative research |
| **Grounded AI-Assisted Research** | AI research assistant grounded in actual platform data |
| **Public Web Experience** | Browser-based access to market intelligence, regime dashboards, and research analytics |
| **API Platform** | Versioned REST API for programmatic access to all platform capabilities |
| **Developer Extensions** | SDK, plugin interfaces, and extension points for providers, algorithms, and features |
| **Open-Source Collaboration** | Contribution workflows, community infrastructure, and open-source release process |

### Explicitly Out of Scope

The following are permanently outside the scope of RegimeX. See Section 17 for the full exclusion list.

- Personalized financial or investment advice
- Guaranteed return claims or market predictions
- Automated trade execution or broker integration
- Fabrication of market information not grounded in data

---

## 3. Product Overview

RegimeX is designed around a sequential analytical pipeline: raw market data is ingested and normalized, quantitative features are computed point-in-time, regime detection algorithms classify market states, and the resulting regime intelligence informs risk analytics, backtesting, and research. The web platform and API expose these capabilities to end users and developer integrations.

**Conceptual Platform Flow:**

```text
Market Data Sources (External Providers)
         ↓
  Data Ingestion Layer
  (provider-independent ingestion, normalization, quality validation)
         ↓
  Validated Market Data Store
  (versioned, auditable, idempotent)
         ↓
  Feature Engineering
  (point-in-time, reproducible, look-ahead-bias-free)
         ↓
  Regime Detection
  (multiple configurable algorithms, standard interface)
         ↓
  Regime Intelligence
  (timeline, transitions, persistence, regime-conditional stats)
         ↓
  Risk Analytics                    Backtesting Engine
  (regime-aware risk metrics)       (event-driven, walk-forward)
         ↓                                  ↓
  Research Experience (API, SDK, Notebooks, Research Workspace)
         ↓
  AI-Assisted Research
  (grounded, uncertainty-disclosing, non-advisory)
         ↓
  Public Web Platform + API Platform
  (dashboards, analytics, versioned REST API)
```

The implementation architecture — module boundaries, technology selections, interface specifications — will be formally defined in V03 — System Architecture.

---

## 4. System Context

RegimeX operates as a platform interacting with the following external entities. This section describes the conceptual system boundary — not implementation choices.

### External Entity Map

| Entity | Interaction |
|--------|------------|
| **Market Data Providers** | RegimeX ingests historical and reference market data from external providers via provider adapter interfaces. Providers are abstracted — switching providers does not require changes to platform business logic. |
| **AI / LLM Providers** | The AI Research Assistant queries an external LLM provider to generate grounded responses. Provider-independence is a design goal. |
| **Public Users** | Interact with the platform through the web interface without authentication, accessing public regime intelligence and market dashboards. |
| **Authenticated Users** | Researchers, quantitative researchers, and developers interact via the web platform and API with authenticated sessions. |
| **Web Clients** | Browser-based clients consuming the web platform interface. |
| **API Clients** | Programmatic consumers of the RegimeX REST API, including the Python SDK and third-party integrations. |
| **Persistent Storage** | The platform writes and reads market data, features, regime outputs, risk metrics, backtest results, and experiment configurations to a persistent storage layer. |
| **Cache Layer** | Frequently-accessed, freshness-sensitive data (current regime, recent analytics) may be served from a cache to meet performance requirements. |
| **Background Processing** | Long-running operations (regime detection, backtesting, bulk ingestion) are executed as asynchronous background jobs. |

No specific vendor is committed to for any external entity in this document. Technology selections will be captured as Architecture Decision Records (ADRs) in V03.

---

## 5. User Classes

Six user classes interact with RegimeX. Each class has distinct capabilities, access levels, and interaction modes.

### UC-1: Public User

A member of the general public accessing publicly available market intelligence. No account is required.

- Can view current regime dashboard for supported instruments
- Can explore historical regime timelines (limited lookback)
- Can access volatility and risk overviews
- Cannot access advanced analytics, research tools, or API
- Cannot configure detection parameters

### UC-2: Researcher (Market Researcher)

An analyst, journalist, or researcher studying market history and behavior.

- Requires authenticated account
- Can access full historical regime data
- Can export regime history, statistics, and risk metrics
- Can compare regime timelines across instruments
- Cannot run custom regime detection or backtesting

### UC-3: Quantitative Researcher

A quant, data scientist, or financial engineer conducting reproducible research.

- Requires authenticated account
- Can configure and run regime detection with custom parameters
- Can run backtests with regime attribution
- Can access the research workspace for parameterized analysis
- Can browse and use the feature registry
- Can use the AI research assistant
- Can access the API with Researcher-tier rate limits

### UC-4: Developer

A software engineer integrating RegimeX into applications or contributing extensions.

- Requires authenticated account (API key)
- Full API access within rate limits
- Access to Python SDK and documentation
- Can implement custom regime detector plugins
- Can implement custom market data provider adapters
- Can contribute features to the platform

### UC-5: Open-Source Contributor

A community member contributing to the RegimeX open-source project.

- Interacts through GitHub (issues, pull requests)
- Uses local development environment following contributor guide
- Contributes code, algorithms, documentation, or tests
- Subject to contribution workflow and code review requirements

### UC-6: Platform Administrator

An operator responsible for deploying and managing a RegimeX instance.

- Manages users, API keys, and access control
- Configures ingestion schedules and environment settings
- Monitors platform health through logs, metrics, and dashboards
- Can trigger administrative operations (re-ingestion, cache invalidation)
- Self-hosts the full platform stack

---

## 6. Assumptions

The following assumptions underlie the requirements in this specification. They represent reasonable beliefs about the operating environment — not guaranteed facts.

| ID | Assumption |
|----|-----------|
| A-001 | Market data availability depends on external providers. The platform assumes at least one open-access OHLCV data source is available for US equities during initial implementation. |
| A-002 | Historical data coverage varies by asset class and provider. Not all assets will have equal historical depth. |
| A-003 | Different asset classes may require different feature sets. The feature registry must accommodate asset-class-specific feature implementations. |
| A-004 | ML and statistical models produce probabilistic outputs with inherent uncertainty. Regime labels are estimates, not ground truth. |
| A-005 | AI-generated text explanations require grounding in actual platform data to remain factually accurate. Ungrounded AI outputs are a reliability risk. |
| A-006 | Public analytics capabilities may be a reduced subset of authenticated research capabilities. The boundary will be determined before V16. |
| A-007 | External data provider availability, coverage, and API stability may change. The provider abstraction layer mitigates but does not eliminate this risk. |
| A-008 | Backtest results are sensitive to data quality. Gaps, corporate action errors, and outliers in input data can materially affect backtest outcomes. |
| A-009 | Computing infrastructure for production deployment is not provided by the platform — the platform is designed for self-hosting on standard Linux infrastructure. |
| A-010 | Users are responsible for interpreting platform outputs within their own analytical and legal context. The platform does not provide advice. |

---

## 7. Constraints

The following constraints are binding on all implementation decisions.

| ID | Constraint |
|----|-----------|
| C-001 | RegimeX shall not provide personalized financial or investment advice under any circumstances. |
| C-002 | RegimeX shall not guarantee investment returns or claim market prediction capability. |
| C-003 | RegimeX shall not fabricate, hallucinate, or generate market data not sourced from validated provider inputs. |
| C-004 | No look-ahead bias is permitted in any feature computation, regime detection, or backtesting workflow. Violations are critical defects. |
| C-005 | No data leakage is permitted between training datasets and validation/test datasets in any model training workflow. |
| C-006 | Reproducibility must be preserved for all research workflows — identical inputs, algorithm version, and configuration must yield identical outputs. |
| C-007 | The platform must communicate uncertainty explicitly. Confidence estimates, caveats, and reliability limits must be surfaced alongside outputs. |
| C-008 | External data provider limitations (rate limits, coverage gaps, API changes) may constrain data freshness and availability. The platform must handle these gracefully. |
| C-009 | The platform must remain provider-independent in its core logic wherever practical. Vendor lock-in in core business logic is prohibited. |
| C-010 | No credentials, API keys, or secrets may appear in source code or version control history. |

---

## 8. Dependencies

The following conceptual dependencies exist. Technology selections for each are deferred to V03 Architecture Decision Records.

| Dependency | Purpose | Notes |
|-----------|---------|-------|
| **Market Data Sources** | Historical OHLCV ingestion | At least one open-access provider required for V05 |
| **Storage Layer** | Persistent data store for market data, features, regimes, risk, backtests, experiments | Technology TBD in V03 |
| **Computational / ML Capabilities** | Feature computation, model training and inference | Python scientific stack expected; specifics TBD |
| **AI / LLM Provider** | Grounded AI research assistant | Provider TBD; must support context injection |
| **Authentication Infrastructure** | User accounts, API keys, JWT tokens | Technology TBD in V17 |
| **Web Client Framework** | Browser-based UI | Technology TBD in V18; ADR required |
| **API Infrastructure** | REST API framework | FastAPI planned per V16 roadmap entry |
| **Background Processing** | Async job execution for regime detection, backtesting | Technology TBD in V03 |
| **Cache Layer** | Low-latency read access for frequently-queried data | Technology TBD; Redis-class system expected |
| **Container Runtime** | Containerized deployment | Docker + Docker Compose per V24 |

---

## 9. Functional Requirements

The requirements below define the complete functional contract for RegimeX. Requirements are grouped by product domain. Each requirement includes a unique ID, priority, actor, description, and acceptance criteria.

**Priority Legend:**

| Priority | Definition |
|----------|-----------|
| **P0 — Critical** | Core platform capability. Platform cannot function without it. |
| **P1 — High** | Important feature required for a usable production release. |
| **P2 — Medium** | Valuable but can be deferred to a later release within the roadmap. |
| **P3 — Future** | Desirable long-term capability; intentionally deferred beyond initial release. |

---

### Domain A — Market Discovery

---

#### FR-001 — Supported Instrument Catalogue

**Priority:** P0 — Critical
**Actor:** All users
**Description:**
The system shall maintain a catalogue of all supported market instruments. The catalogue shall be queryable by users and API clients.

**Acceptance Criteria:**
- The catalogue returns a complete list of all instruments for which the platform has data.
- Each instrument entry includes: symbol, name, exchange, asset class, base currency, and data availability date range.
- The catalogue is queryable without authentication.
- An instrument not present in the catalogue cannot be queried for data, features, or regime analysis.

---

#### FR-002 — Instrument Search

**Priority:** P1 — High
**Actor:** Public User, Researcher, Quantitative Researcher, Developer
**Description:**
The system shall provide a search interface for discovering instruments by symbol, name, asset class, or market geography.

**Acceptance Criteria:**
- A search by partial symbol returns all matching instruments.
- A search by asset class filter returns only instruments of that class.
- A search by geography filter returns only instruments traded in the specified market.
- Empty search results are clearly communicated (not treated as errors).
- Search returns results within response time targets (see NFR-PERF).

---

#### FR-003 — Data Availability Display

**Priority:** P1 — High
**Actor:** All users
**Description:**
The system shall display, for each supported instrument, the available historical data range, the data source, and the date of last update.

**Acceptance Criteria:**
- For every instrument in the catalogue, the data availability start date and end date are displayed.
- The data source identifier is displayed.
- The last ingestion timestamp is displayed.
- An instrument with no data is clearly marked as having no data available.

---

#### FR-004 — Unsupported Instrument Communication

**Priority:** P0 — Critical
**Actor:** All users
**Description:**
The system shall clearly and explicitly communicate when a requested instrument is not supported. No unsupported instrument shall be presented as available or return partial results without indication.

**Acceptance Criteria:**
- Requesting data for an unsupported symbol returns a structured error, not partial data.
- The error message identifies the symbol as unsupported.
- The error response is consistent with the error model defined in `API_CONTRACTS.md`.

---

### Domain B — Market Data

---

#### FR-005 — Historical OHLCV Ingestion

**Priority:** P0 — Critical
**Actor:** Platform (internal — ingestion pipeline)
**Description:**
The system shall ingest historical OHLCV (Open, High, Low, Close, Volume) data for supported instruments from at least one configured data provider.

**Acceptance Criteria:**
- Ingestion retrieves complete OHLCV bars for the requested symbol, exchange, and date range.
- Ingested records conform to the canonical OHLCV schema defined in `DATA_CONTRACTS.md`.
- Ingestion produces an audit log entry for each completed batch.
- Ingested data is retrievable immediately after successful ingestion.

---

#### FR-006 — Provider-Independent Ingestion

**Priority:** P0 — Critical
**Actor:** Platform (internal — engineering constraint)
**Description:**
The data ingestion pipeline shall operate through a provider-abstraction interface. Switching data providers shall not require changes to core business logic.

**Acceptance Criteria:**
- A new provider adapter can be added without modifying ingestion pipeline business logic.
- The provider adapter interface is documented.
- At least one provider adapter passes the provider interface compliance test suite.

---

#### FR-007 — Data Gap Detection

**Priority:** P1 — High
**Actor:** Platform (internal — data quality)
**Description:**
The system shall detect missing trading days or bars in ingested data and record them explicitly.

**Acceptance Criteria:**
- Missing trading days within an expected date range are detected and logged.
- A data quality report is produced after each ingestion batch identifying any gaps.
- Gaps are never silently filled with estimated values without explicit documentation of the interpolation strategy.

---

#### FR-008 — Statistical Outlier Flagging

**Priority:** P1 — High
**Actor:** Platform (internal — data quality)
**Description:**
The system shall detect and flag statistical outliers in ingested price and volume data.

**Acceptance Criteria:**
- Outlier detection runs automatically after each ingestion batch.
- Flagged records include the reason for flagging (e.g., price exceeds N standard deviations).
- Flagged records are retained in storage — not deleted — with the outlier flag set.
- The outlier detection methodology is documented.

---

#### FR-009 — Idempotent Ingestion

**Priority:** P0 — Critical
**Actor:** Platform (internal — data integrity)
**Description:**
Ingestion shall be idempotent. Re-running ingestion for the same symbol, exchange, and date range shall not produce duplicate records.

**Acceptance Criteria:**
- Running ingestion twice for the same symbol and date range produces exactly the same stored records as running it once.
- No duplicate `(symbol, exchange, timestamp, adjustment_type)` records exist after re-ingestion.
- Idempotency is verified by automated tests.

---

#### FR-010 — Adjusted and Unadjusted Data Support

**Priority:** P1 — High
**Actor:** Quantitative Researcher, Developer
**Description:**
The system shall support both adjusted and unadjusted OHLCV data. The adjustment type shall be recorded explicitly on every record.

**Acceptance Criteria:**
- The `adjustment_type` field is set on every stored OHLCV record.
- Adjusted and unadjusted prices can be retrieved independently.
- Adjusted and unadjusted data are never mixed within a single computation without explicit documentation.

---

#### FR-011 — Dataset Versioning

**Priority:** P1 — High
**Actor:** Quantitative Researcher, Platform (internal)
**Description:**
The system shall version market data datasets. Each dataset snapshot shall be identified by a content fingerprint.

**Acceptance Criteria:**
- Every ingestion run produces a dataset version fingerprint.
- Feature computations and regime detection runs record the dataset version fingerprint used.
- Given the same dataset version, the same computation produces the same result.

---

#### FR-012 — Data Export

**Priority:** P2 — Medium
**Actor:** Researcher, Quantitative Researcher
**Description:**
Users shall be able to export market data for supported instruments in standard formats.

**Acceptance Criteria:**
- Data export is available in CSV and Parquet formats.
- Exported data conforms to the canonical OHLCV schema.
- Export includes all metadata fields (adjustment type, data source, timestamps).

---

#### FR-013 — Corporate Action Handling

**Priority:** P1 — High
**Actor:** Platform (internal — data quality)
**Description:**
The system shall document and apply a defined strategy for handling corporate actions (stock splits, dividends) in market data.

**Acceptance Criteria:**
- The corporate action handling strategy is documented.
- Split and dividend adjustments are applied consistently across all records for the affected instrument.
- The adjustment factor applied to each record is stored explicitly.

---

### Domain C — Feature Engineering

---

#### FR-014 — Feature Registry

**Priority:** P0 — Critical
**Actor:** All users (discovery), Quantitative Researcher (use)
**Description:**
The system shall maintain a feature registry: a discoverable catalogue of all available quantitative features.

**Acceptance Criteria:**
- The feature registry is queryable by all authenticated users.
- Each feature entry includes: feature ID, name, version, description, inputs, outputs, computation method, assumptions, and look-ahead bias status.
- The registry is queryable via the API.

---

#### FR-015 — Point-in-Time Feature Computation

**Priority:** P0 — Critical
**Actor:** Platform (internal — quantitative integrity constraint)
**Description:**
All feature computation shall be strictly point-in-time. A feature computed for timestamp T shall use only data available at or before T.

**Acceptance Criteria:**
- No feature implementation uses data from timestamps after the computation timestamp.
- The look-ahead bias detection tool (FR-020) validates all feature implementations.
- Any feature violating point-in-time constraints is classified as a critical defect.

---

#### FR-016 — Technical Feature Library

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall provide a baseline library of technical quantitative features computed from OHLCV market data.

**Acceptance Criteria:**
- The library includes at minimum: returns (1-day, 5-day, 21-day, 63-day), realized volatility (rolling), EWMA volatility, volume ratio, RSI, ATR, Bollinger Band width, momentum indicators.
- All features are registered in the feature registry with full documentation.
- All features pass point-in-time compliance tests.

---

#### FR-017 — Statistical Feature Library

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall provide a baseline library of statistical quantitative features.

**Acceptance Criteria:**
- The library includes at minimum: rolling autocorrelation, rolling skewness, rolling kurtosis, rolling cross-asset correlation.
- All features are registered in the feature registry.
- All features pass point-in-time compliance tests.

---

#### FR-018 — Feature Versioning

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher, Platform (internal)
**Description:**
Features shall be versioned. A feature identified by name and version shall always produce the same output given the same inputs and software version.

**Acceptance Criteria:**
- Every feature has a version identifier.
- Changing a feature's computation logic increments its version.
- Feature computation results record the feature version used.
- Two computations using the same feature version and the same input data produce identical results.

---

#### FR-019 — Configurable Feature Windows

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
Features that use a rolling lookback window shall support configurable window lengths.

**Acceptance Criteria:**
- Window length is a configurable parameter for all applicable features.
- Different window configurations produce different feature IDs in the registry.
- Configuration is validated at computation time.

---

#### FR-020 — Look-Ahead Bias Detection Tool

**Priority:** P0 — Critical
**Actor:** Developer, Contributor
**Description:**
The system shall provide a tool that validates any feature implementation against synthetic data designed to detect look-ahead bias.

**Acceptance Criteria:**
- The tool can be run against any registered feature.
- The tool uses synthetic data where future values are known to be distinct from past values.
- A feature that uses future data is detected and flagged by the tool.
- The tool is runnable as part of the CI pipeline.

---

#### FR-021 — External Feature Contributions

**Priority:** P2 — Medium
**Actor:** Developer, Contributor
**Description:**
The system shall support third-party feature implementations through a defined `Feature` interface.

**Acceptance Criteria:**
- The `Feature` interface is documented.
- A third-party feature can be registered in the feature registry by implementing the interface.
- Third-party features are subject to the same look-ahead bias validation as built-in features.

---

### Domain D — Regime Detection

---

#### FR-022 — RegimeDetector Standard Interface

**Priority:** P0 — Critical
**Actor:** Platform (internal — architectural constraint)
**Description:**
The system shall define and enforce a standard `RegimeDetector` interface that all regime detection algorithms must implement.

**Acceptance Criteria:**
- The `RegimeDetector` interface exposes at minimum: `fit()`, `predict()`, `predict_proba()`, and `metadata()` methods.
- All built-in algorithms pass an interface compliance test suite.
- Third-party algorithm contributions must pass the same compliance tests.

---

#### FR-023 — HMM Regime Detector

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The system shall implement a Hidden Markov Model (HMM) regime detector as the first production algorithm.

**Acceptance Criteria:**
- The HMM detector conforms to the `RegimeDetector` interface.
- The HMM detector passes the interface compliance test suite.
- The HMM detector produces outputs conforming to the regime output schema in `DATA_CONTRACTS.md`.
- The number of regimes (K) is configurable.

---

#### FR-024 — GMM Regime Detector

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall implement a Gaussian Mixture Model (GMM) regime detector.

**Acceptance Criteria:**
- The GMM detector conforms to the `RegimeDetector` interface.
- The GMM detector passes the interface compliance test suite.
- K is configurable.

---

#### FR-025 — Changepoint Detection Regime Detector

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall implement at least one changepoint-based regime detector.

**Acceptance Criteria:**
- The detector conforms to the `RegimeDetector` interface.
- The algorithm is documented with its assumptions and known limitations.
- The detector passes the interface compliance test suite.

---

#### FR-026 — Ensemble Regime Detector

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall implement an ensemble regime detector that combines signals from multiple algorithms into a single unified output.

**Acceptance Criteria:**
- The ensemble detector conforms to the `RegimeDetector` interface.
- Ensemble configuration specifies which component detectors are combined and their weighting strategy.
- Ensemble output includes individual component detector contributions.
- Uncertainty/disagreement across component detectors is quantified and surfaced.

---

#### FR-027 — Regime Output Schema Compliance

**Priority:** P0 — Critical
**Actor:** Platform (internal — data integrity)
**Description:**
All regime detection outputs shall conform to the canonical regime output schema defined in `DATA_CONTRACTS.md`.

**Acceptance Criteria:**
- Every regime output record includes: regime label, confidence score, probability distribution, algorithm ID, algorithm version, parameter set, feature set ID, dataset version, computation timestamp, and run ID.
- Schema validation runs automatically after every regime detection run.

---

#### FR-028 — Configurable Detection Parameters

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
Algorithm parameters shall be configurable via structured configuration. Different parameter configurations produce independently identifiable detection runs.

**Acceptance Criteria:**
- Parameters are specified in a structured configuration format (e.g., YAML or JSON).
- Configuration is validated before detection begins.
- Configuration is stored with detection results for reproducibility.
- Two runs with identical configuration and identical input data produce identical results.

---

#### FR-029 — Algorithm Documentation

**Priority:** P0 — Critical
**Actor:** All users
**Description:**
All regime detection algorithms shall be documented with their assumptions, inputs, outputs, and known failure modes.

**Acceptance Criteria:**
- Every algorithm in the registry has a documentation entry.
- Documentation covers: what the algorithm does, assumptions made, data inputs required, known failure modes, and guidance on parameter selection.
- No algorithm is available in the registry without complete documentation.

---

#### FR-030 — Regime Detection Persistence

**Priority:** P0 — Critical
**Actor:** Platform (internal — reproducibility)
**Description:**
All regime detection outputs shall be persisted with full metadata for later retrieval and reproducibility.

**Acceptance Criteria:**
- Detection outputs are stored and retrievable by run ID.
- All metadata required for reproducibility (configuration, dataset version, feature set ID) is stored with results.
- Results remain retrievable after the computation session ends.

---

#### FR-031 — Batch and Point-in-Time Detection Modes

**Priority:** P1 — High
**Actor:** Quantitative Researcher, Platform (internal)
**Description:**
The regime detection pipeline shall support two operational modes: batch (historical analysis over a date range) and point-in-time (current regime assignment as of the most recent data).

**Acceptance Criteria:**
- Batch mode processes a full historical date range and produces regime assignments for every date.
- Point-in-time mode produces the regime assignment for the most recent available data point.
- Both modes use the same algorithm and configuration interface.

---

### Domain E — Regime Intelligence

---

#### FR-032 — Regime Timeline Construction

**Priority:** P0 — Critical
**Actor:** Researcher, Quantitative Researcher
**Description:**
The system shall construct a regime timeline from detection outputs — a complete, ordered record of regime periods for a given instrument, algorithm, and configuration.

**Acceptance Criteria:**
- The timeline represents consecutive regime periods with start date, end date, regime label, and average confidence.
- The timeline is queryable by instrument, algorithm, and date range.
- The timeline is consistent with the underlying detection outputs.

---

#### FR-033 — Regime Persistence Metrics

**Priority:** P1 — High
**Actor:** Researcher, Quantitative Researcher
**Description:**
The system shall compute regime persistence metrics: average regime duration, standard deviation of duration, and median duration per regime label.

**Acceptance Criteria:**
- Persistence metrics are computed from the regime timeline.
- Metrics are available per regime label.
- Metrics are consistent with the underlying timeline data.

---

#### FR-034 — Regime Transition Matrix

**Priority:** P1 — High
**Actor:** Researcher, Quantitative Researcher
**Description:**
The system shall compute a regime transition matrix: the probability of transitioning from regime A to regime B in the next period.

**Acceptance Criteria:**
- The transition matrix is computed from observed regime sequences.
- Each entry represents the empirical transition probability.
- Row sums equal 1.0 (within floating-point tolerance).
- The matrix is queryable via API.

---

#### FR-035 — Regime-Conditional Asset Statistics

**Priority:** P1 — High
**Actor:** Researcher, Quantitative Researcher
**Description:**
The system shall compute regime-conditional asset statistics: the distribution of returns, volatility, Sharpe ratio, and maximum drawdown, computed separately per regime label.

**Acceptance Criteria:**
- Statistics are computed separately for each detected regime label.
- Statistics are available for any instrument with sufficient historical regime assignments.
- The methodology for each statistic is documented.

---

#### FR-036 — Historical Regime Query

**Priority:** P1 — High
**Actor:** Researcher, Quantitative Researcher, Developer
**Description:**
The system shall support point-in-time historical regime queries: "what regime was active on date D for symbol S using algorithm A?"

**Acceptance Criteria:**
- A valid query with instrument, date, and algorithm returns the regime label and confidence for that date.
- A query for a date with no detection data returns an appropriate error, not a default or estimated value.
- Results are traceable to the detection run that produced them.

---

#### FR-037 — Regime Data Export

**Priority:** P2 — Medium
**Actor:** Researcher, Quantitative Researcher
**Description:**
Users shall be able to export the regime history for a supported instrument in standard formats.

**Acceptance Criteria:**
- Regime history export is available in JSON and CSV formats.
- Exported data includes all metadata fields from the regime output schema.
- Export is bounded to a user-specified date range.

---

### Domain F — Risk Analytics

---

#### FR-038 — Volatility Computation

**Priority:** P1 — High
**Actor:** Researcher, Quantitative Researcher
**Description:**
The system shall compute realized volatility using multiple estimators.

**Acceptance Criteria:**
- At minimum three estimators are supported: close-to-close, Parkinson, Yang-Zhang.
- Each estimator is documented with its assumptions.
- Volatility is configurable by lookback window.
- Results are labeled with the estimator used.

---

#### FR-039 — Drawdown Analytics

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall compute rolling drawdown analytics including drawdown magnitude, duration, and recovery time.

**Acceptance Criteria:**
- Drawdown series, maximum drawdown, and maximum drawdown duration are computed.
- Recovery time (time from trough to recovery of prior peak) is computed where applicable.
- Results are computable for any supported instrument and date range.

---

#### FR-040 — Value at Risk (VaR)

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall compute Value at Risk using historical simulation.

**Acceptance Criteria:**
- VaR is configurable by confidence level.
- The estimator methodology (historical simulation) is documented.
- Assumptions (confidence level, lookback window) are recorded with every result.

---

#### FR-041 — Conditional VaR (CVaR / Expected Shortfall)

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall compute Conditional VaR (Expected Shortfall) at a configurable confidence level.

**Acceptance Criteria:**
- CVaR is computed consistently with the corresponding VaR.
- Confidence level is configurable.
- Results label their assumptions explicitly.

---

#### FR-042 — Rolling Correlation Matrices

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The system shall compute rolling pairwise correlation matrices for a configurable asset universe.

**Acceptance Criteria:**
- Correlation is computable for any pair of supported instruments.
- The lookback window is configurable.
- Results are timestamped with the computation date.

---

#### FR-043 — Regime-Conditional Risk Metrics

**Priority:** P0 — Critical
**Actor:** Researcher, Quantitative Researcher
**Description:**
All risk metrics shall be computable conditional on regime — producing separate risk statistics for each detected regime label.

**Acceptance Criteria:**
- Risk metrics (volatility, drawdown, VaR, CVaR) can be computed separately for each regime.
- Regime-conditional computation requires a linked regime detection run.
- Results clearly identify the regime label they correspond to.
- Regime-conditional outputs explicitly document assumptions and the regime algorithm used.

---

#### FR-044 — Risk Output Disclaimer

**Priority:** P0 — Critical
**Actor:** All users
**Description:**
All risk analytics outputs shall be accompanied by a clear statement that they are analytical research outputs, not investment advice.

**Acceptance Criteria:**
- Every risk output surface (API response, web display) includes an explicit disclaimer.
- The disclaimer is not dismissible or hidden by default.

---

### Domain G — Backtesting

---

#### FR-045 — Event-Driven Simulation Loop

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The backtesting engine shall execute strategy simulation in an event-driven, bar-by-bar loop, processing one time period at a time in chronological order.

**Acceptance Criteria:**
- The simulation loop processes bars strictly in chronological order.
- Strategies receive only data available at the time of the bar being processed.
- Future bars are never accessible to the strategy at any point during simulation.

---

#### FR-046 — Strategy Interface

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher, Developer
**Description:**
The platform shall define a `Strategy` interface that all backtest strategies must implement.

**Acceptance Criteria:**
- The interface exposes at minimum: `on_bar()` and `on_signal()` hooks.
- The interface is documented.
- A strategy that does not conform to the interface cannot be executed.

---

#### FR-047 — Transaction Cost Models

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The backtesting engine shall support configurable transaction cost models.

**Acceptance Criteria:**
- Supported cost models include at minimum: flat commission, percentage commission, and bid-ask spread.
- Cost model parameters are configurable per backtest run.
- All costs are applied on order execution, not deferred.
- Cost model configuration is stored with backtest results for reproducibility.

---

#### FR-048 — Order Types

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The backtesting engine shall support at minimum market and limit order types.

**Acceptance Criteria:**
- Market orders execute at the open price of the next bar after signal generation.
- Limit orders execute only when the specified price is reached.
- Order fill logic is documented.

---

#### FR-049 — Portfolio State Management

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The engine shall maintain a portfolio state throughout the simulation.

**Acceptance Criteria:**
- Portfolio state includes: positions per instrument, cash balance, and equity curve.
- Portfolio state is updated after every filled order.
- Equity curve is computed at each bar.

---

#### FR-050 — Walk-Forward Validation

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The platform shall support walk-forward validation, partitioning the backtest data into in-sample and out-of-sample segments.

**Acceptance Criteria:**
- Walk-forward partitioning is configurable (number of windows, window size).
- In-sample and out-of-sample results are reported separately.
- In-sample and out-of-sample periods do not overlap.

---

#### FR-051 — Backtest Result Schema Compliance

**Priority:** P0 — Critical
**Actor:** Platform (internal — data integrity)
**Description:**
All backtest results shall conform to the canonical backtest result schema defined in `DATA_CONTRACTS.md`.

**Acceptance Criteria:**
- Every completed backtest produces a result record containing all required schema fields.
- Schema validation runs automatically after every backtest.
- Results are stored and retrievable by backtest ID.

---

#### FR-052 — Performance Metrics

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
Backtest results shall include a comprehensive set of performance metrics.

**Acceptance Criteria:**
- Results include at minimum: total return, CAGR, Sharpe ratio, Sortino ratio, Calmar ratio, maximum drawdown, maximum drawdown duration, win rate, profit factor, and total trade count.
- Benchmark comparison is supported when a benchmark instrument is specified.

---

#### FR-053 — Regime Attribution in Backtesting

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
Backtest results shall include performance attribution by detected regime.

**Acceptance Criteria:**
- Attribution is computed per regime label: total return, Sharpe ratio, and trade count per regime.
- Attribution requires a linked regime detection run.
- Attribution results are consistent with the underlying regime timeline.

---

#### FR-054 — Look-Ahead Bias Prevention in Backtesting

**Priority:** P0 — Critical
**Actor:** Platform (internal — quantitative integrity)
**Description:**
The backtesting engine shall prevent look-ahead bias in strategy signal generation.

**Acceptance Criteria:**
- Strategies cannot access bar data for timestamps after the current simulation bar.
- Data access violations are detected and raise errors during simulation.
- The prevention mechanism is verified by automated tests.

---

#### FR-055 — Backtest Reproducibility

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
A backtest shall be fully reproducible from its stored configuration.

**Acceptance Criteria:**
- A stored backtest configuration (strategy parameters, cost model, date range, dataset version) produces identical results when re-executed.
- Configuration is stored with every backtest result.
- A reproducibility test is included in the test suite.

---

### Domain H — Research Experience

---

#### FR-056 — Parameterized Analysis Runs

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The platform shall support parameterized analysis runs — re-running an analysis with different parameter values without modifying source code.

**Acceptance Criteria:**
- Analysis runs are defined by a configuration that specifies all parameters.
- Changing parameters produces a new run record, not an overwrite of the previous run.
- Results from different parameter configurations are independently retrievable.

---

#### FR-057 — Run Metadata and Provenance

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher, Platform (internal — reproducibility)
**Description:**
Every analysis run shall record its full provenance: configuration, data version fingerprints, software versions, and execution timestamps.

**Acceptance Criteria:**
- Every run record includes: configuration snapshot, dataset version, algorithm version, feature version, software version, and execution timestamp.
- This metadata is sufficient to reproduce the run.
- Metadata is stored with results and retrievable by run ID.

---

#### FR-058 — Jupyter Notebook Integration

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The platform shall support integration with Jupyter notebooks through its Python SDK.

**Acceptance Criteria:**
- All platform capabilities accessible via the Python SDK are usable from within a Jupyter notebook.
- SDK documentation includes notebook usage examples.
- SDK functions return data structures compatible with common Python data science libraries.

---

#### FR-059 — Run Comparison

**Priority:** P2 — Medium
**Actor:** Quantitative Researcher
**Description:**
The platform shall provide utilities for comparing results across multiple parameterized runs.

**Acceptance Criteria:**
- Runs sharing the same analysis type can be listed and compared.
- Comparison highlights differences in configuration and outputs.
- Comparison data is exportable.

---

### Domain I — AI Research Assistant

---

#### FR-060 — Grounded Natural Language Research Queries

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The AI research assistant shall answer natural language questions about market regimes, risk, and analytics using actual RegimeX platform data as its grounding source.

**Acceptance Criteria:**
- The assistant can respond to questions about current regime, historical regimes, regime statistics, and risk metrics for supported instruments.
- All responses reference actual data retrieved from the platform.
- Responses that cannot be grounded in platform data explicitly state this limitation.

---

#### FR-061 — Response Citation

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
Every AI assistant response shall cite the specific platform data (regime labels, dates, risk metrics, detection run IDs) that supports each factual claim.

**Acceptance Criteria:**
- Citations are presented alongside the response text.
- Citations include sufficient metadata for the user to independently verify the referenced data.
- Responses without any supporting platform data are not presented as factual.

---

#### FR-062 — Uncertainty Disclosure

**Priority:** P0 — Critical
**Actor:** Quantitative Researcher
**Description:**
The AI assistant shall explicitly state its confidence level and limitations in every response that involves probabilistic or uncertain information.

**Acceptance Criteria:**
- Responses to questions about regime states include the associated confidence score.
- Responses acknowledge the limitations of the underlying detection model.
- Phrases expressing certainty ("the market is in X regime") are accompanied by confidence qualifications.

---

#### FR-063 — Fabrication Prohibition

**Priority:** P0 — Critical
**Actor:** Platform (internal — AI safety constraint)
**Description:**
The AI assistant shall not generate market signals, predictions, or factual claims that are not grounded in actual platform data.

**Acceptance Criteria:**
- The assistant refuses to claim regime states not present in platform data.
- The assistant refuses to generate future price predictions.
- The system includes automated tests that verify refusal of fabrication prompts.

---

#### FR-064 — Financial Advice Prohibition

**Priority:** P0 — Critical
**Actor:** All users
**Description:**
The AI assistant shall not provide personalized financial or investment advice under any circumstances.

**Acceptance Criteria:**
- The assistant explicitly states it does not provide investment advice when asked.
- No response constructs a personalized investment recommendation.
- The prohibition is enforced through system prompting and validated by automated tests.

---

#### FR-065 — Conversation History

**Priority:** P2 — Medium
**Actor:** Quantitative Researcher
**Description:**
The AI assistant shall maintain conversation history within a research session, allowing follow-up questions to reference prior context.

**Acceptance Criteria:**
- Follow-up questions that reference prior context in the same session are answered with that context intact.
- Conversation history does not persist across separate sessions by default.

---

#### FR-066 — Response Provenance Display

**Priority:** P1 — High
**Actor:** Quantitative Researcher
**Description:**
The platform shall display the data sources used to generate each AI assistant response alongside the response itself.

**Acceptance Criteria:**
- Provenance information is presented in the UI for each response.
- Provenance lists the platform queries executed to retrieve grounding data.
- Provenance is linkable to the underlying platform data records.

---

### Domain J — Public Web Platform

---

#### FR-067 — Public Access Without Registration

**Priority:** P1 — High
**Actor:** Public User
**Description:**
The web platform shall allow public users to access basic market intelligence without creating an account.

**Acceptance Criteria:**
- The current regime dashboard is accessible without authentication.
- Publicly accessible features are clearly distinguished from authenticated features.
- No account or login is required to view the current regime and recent regime history for supported instruments.

---

#### FR-068 — Current Regime Dashboard

**Priority:** P0 — Critical
**Actor:** Public User, Researcher
**Description:**
The web platform shall provide a current regime dashboard for supported instruments displaying the current regime label, confidence, duration of current regime, and recent transition history.

**Acceptance Criteria:**
- The dashboard displays the current regime label and its associated confidence score.
- The dashboard displays how long the current regime has been active.
- Recent regime changes are visible in the dashboard.
- Data displayed is sourced from the API, not hardcoded.

---

#### FR-069 — Historical Regime Timeline Visualization

**Priority:** P1 — High
**Actor:** Public User, Researcher
**Description:**
The platform shall provide an interactive historical regime timeline visualization.

**Acceptance Criteria:**
- The timeline is navigable across available history.
- Regime periods are visually distinguishable.
- Clicking a regime period displays its associated statistics.
- The visualization renders accurately across supported browsers.

---

#### FR-070 — Risk Metrics Display

**Priority:** P1 — High
**Actor:** Researcher
**Description:**
The web platform shall display risk metrics per instrument and per detected regime.

**Acceptance Criteria:**
- Risk metrics displayed include at minimum: realized volatility, maximum drawdown, and VaR.
- Regime-conditional risk metrics are displayed alongside unconditional metrics.
- Every risk metric display includes a disclaimer that these are research analytics, not investment advice.

---

#### FR-071 — Responsive Web Experience

**Priority:** P1 — High
**Actor:** Public User, Researcher
**Description:**
The web platform shall be usable on desktop and tablet screen sizes without degradation.

**Acceptance Criteria:**
- Key dashboards render correctly at desktop (1280px+) and tablet (768px+) viewport widths.
- Navigation is fully functional at both sizes.

---

#### FR-072 — Accessibility

**Priority:** P1 — High
**Actor:** All web users
**Description:**
The web platform shall meet WCAG 2.1 Level AA accessibility requirements.

**Acceptance Criteria:**
- All interactive elements are keyboard-navigable.
- Color is not the sole means of conveying information.
- Text contrast ratios meet AA thresholds.
- Screen reader accessibility is maintained for primary user flows.

---

### Domain K — API Platform

---

#### FR-073 — Versioned REST API

**Priority:** P0 — Critical
**Actor:** Developer
**Description:**
The platform shall expose a versioned REST API using a URL path prefix convention.

**Acceptance Criteria:**
- All endpoints use a version prefix (e.g., `/api/v1/`).
- The API version is always explicit in the URL.
- Breaking changes require a new version prefix.
- The current version is v1.

---

#### FR-074 — API Endpoint Coverage

**Priority:** P0 — Critical
**Actor:** Developer
**Description:**
The API shall provide endpoints covering all platform domains: market discovery, market data, features, regime detection and intelligence, risk analytics, backtesting, and platform health.

**Acceptance Criteria:**
- Every platform domain has at least one corresponding API endpoint.
- Endpoint structure is consistent with `API_CONTRACTS.md`.
- All endpoints are documented in the OpenAPI specification.

---

#### FR-075 — Consistent Response Envelope

**Priority:** P0 — Critical
**Actor:** Developer
**Description:**
All API responses shall use the consistent response envelope schema defined in `API_CONTRACTS.md`.

**Acceptance Criteria:**
- All successful responses include: `success`, `data`, and `meta` fields.
- `meta` includes `request_id`, `timestamp`, and `api_version`.
- List responses include pagination metadata.

---

#### FR-076 — Structured Error Responses

**Priority:** P0 — Critical
**Actor:** Developer
**Description:**
All API errors shall conform to the error response schema defined in `API_CONTRACTS.md`.

**Acceptance Criteria:**
- All error responses include: `success: false`, `error.code`, `error.message`, `error.request_id`.
- Error codes are from the defined error code catalogue.
- No unstructured error messages are returned to clients.

---

#### FR-077 — API Authentication

**Priority:** P0 — Critical
**Actor:** Developer
**Description:**
The API shall enforce authentication on all non-public endpoints.

**Acceptance Criteria:**
- Authenticated endpoints return 401 for unauthenticated requests.
- API key authentication is supported for developer clients.
- JWT authentication is supported for web platform sessions.
- Public endpoints are documented and function without credentials.

---

#### FR-078 — API Rate Limiting

**Priority:** P1 — High
**Actor:** Platform (internal — operational constraint)
**Description:**
The API shall enforce rate limiting per authenticated user.

**Acceptance Criteria:**
- Rate limits are applied per API key or session.
- Rate limit information is returned in response headers.
- Requests exceeding the limit receive HTTP 429 with a `Retry-After` header.
- Rate limit tiers are configurable.

---

#### FR-079 — OpenAPI Documentation

**Priority:** P1 — High
**Actor:** Developer
**Description:**
The API shall expose auto-generated OpenAPI documentation accessible without special tooling.

**Acceptance Criteria:**
- An OpenAPI schema is served at a documented endpoint.
- A Swagger UI or equivalent is accessible via the browser.
- The schema accurately reflects all deployed endpoints and schemas.

---

#### FR-080 — Health and Readiness Endpoints

**Priority:** P0 — Critical
**Actor:** Platform Administrator
**Description:**
The API shall expose health and readiness endpoints for operational monitoring.

**Acceptance Criteria:**
- `GET /api/v1/health` returns 200 when the service is running.
- `GET /api/v1/ready` returns 200 only when the service is ready to handle requests (dependencies connected).
- Both endpoints are unauthenticated.

---

#### FR-081 — API Pagination

**Priority:** P1 — High
**Actor:** Developer
**Description:**
All list-returning API endpoints shall support pagination.

**Acceptance Criteria:**
- Pagination is controlled via `page` and `page_size` query parameters.
- Responses include total item count, total pages, and next/previous page indicators.
- Default and maximum page sizes are documented.

---

### Domain L — Developer Platform

---

#### FR-082 — Python SDK

**Priority:** P1 — High
**Actor:** Developer, Quantitative Researcher
**Description:**
The platform shall provide a Python SDK that wraps all API capabilities with a typed, documented interface.

**Acceptance Criteria:**
- The SDK provides typed access to all major API endpoints.
- The SDK is fully type-annotated and compatible with Python 3.10+.
- The SDK includes usage documentation and examples.
- The SDK is installable via pip.

---

#### FR-083 — SDK Documentation

**Priority:** P1 — High
**Actor:** Developer
**Description:**
The Python SDK shall be fully documented with API reference and usage examples.

**Acceptance Criteria:**
- Every public SDK function has a docstring.
- The documentation covers common usage patterns.
- Code examples in documentation are tested and working.

---

#### FR-084 — Regime Detector Plugin Interface

**Priority:** P1 — High
**Actor:** Developer, Contributor
**Description:**
The platform shall provide a stable plugin interface enabling third-party regime detection algorithms.

**Acceptance Criteria:**
- The plugin interface is documented.
- A reference example plugin is provided.
- A third-party plugin that implements the interface can be registered and used.
- The interface is stable across minor platform versions.

---

#### FR-085 — Market Data Provider Plugin Interface

**Priority:** P1 — High
**Actor:** Developer, Contributor
**Description:**
The platform shall provide a stable plugin interface enabling third-party market data provider adapters.

**Acceptance Criteria:**
- The provider adapter interface is documented.
- A reference example adapter is provided.
- A third-party adapter that implements the interface can be used for data ingestion.
- The interface is stable across minor platform versions.

---

#### FR-086 — Self-Hosting Support

**Priority:** P0 — Critical
**Actor:** Platform Administrator
**Description:**
The platform shall support full self-hosting without proprietary cloud service dependencies.

**Acceptance Criteria:**
- All platform services can be started with `docker compose up`.
- Self-hosting documentation is provided and tested on a clean environment.
- No proprietary cloud service is required for core platform functionality.
- Configuration is managed entirely through environment variables.

---

### Domain M — Open-Source Platform

---

#### FR-087 — Public Source Code

**Priority:** P0 — Critical
**Actor:** Contributor
**Description:**
The RegimeX platform source code shall be publicly available under an open-source license.

**Acceptance Criteria:**
- Source code is accessible on a public repository.
- A license file is present at the root of the repository.
- The license is declared in V02 (current volume).

---

#### FR-088 — Contribution Workflow

**Priority:** P1 — High
**Actor:** Contributor
**Description:**
The platform shall maintain a documented, functional contribution workflow including branch strategy, commit conventions, and pull request process.

**Acceptance Criteria:**
- `CONTRIBUTING.md` documents the full contribution workflow.
- Branch naming conventions are documented and enforced by reviewer guidelines.
- Conventional Commits format is used for all commits.
- Pull requests target `develop`, not `main`.

---

#### FR-089 — Issue-Based Development

**Priority:** P1 — High
**Actor:** Contributor
**Description:**
Feature work and bug fixes shall be tracked through GitHub Issues before implementation begins.

**Acceptance Criteria:**
- Issue templates exist for: bug reports, feature requests, algorithm proposals, and data provider proposals.
- All non-trivial work references a GitHub Issue.
- Issues are labeled and triaged regularly.

---

#### FR-090 — Algorithm Contribution Guide

**Priority:** P1 — High
**Actor:** Contributor
**Description:**
The platform shall provide a documented guide for contributing new regime detection algorithms.

**Acceptance Criteria:**
- The guide explains how to implement the `RegimeDetector` interface.
- The guide explains required documentation, tests, and CI requirements for a contributed algorithm.
- A reference example implementation accompanies the guide.

---

#### FR-091 — Versioned Releases

**Priority:** P1 — High
**Actor:** All users, Contributors
**Description:**
Platform releases shall be versioned using Semantic Versioning and accompanied by a changelog.

**Acceptance Criteria:**
- Every release is tagged with a version following `MAJOR.MINOR.PATCH` convention.
- A changelog documents changes since the previous release.
- Breaking changes require a MAJOR version increment.

---

## 10. External Interface Requirements

### EIR-1: Market Data Providers

**Expected Interface Behavior:**
- The platform shall interact with providers through an abstract adapter interface, not direct provider API calls in business logic.
- Provider adapters shall handle authentication, pagination, rate limiting, and error retry specific to each provider.
- Provider adapters shall map provider-specific schemas to the canonical OHLCV schema before data enters the platform.
- Adapter failures shall be communicated to the platform as structured errors, not raw provider exceptions.

### EIR-2: AI / LLM Providers

**Expected Interface Behavior:**
- The AI assistant shall send structured context payloads (retrieved platform data) alongside user queries to the LLM provider.
- LLM provider responses shall be post-processed and grounded before being presented to users.
- LLM provider failures shall result in a graceful degradation message, not an unhandled error.
- The LLM provider is accessed through an abstraction layer to support future provider changes.

### EIR-3: Web Clients

**Expected Interface Behavior:**
- The web client consumes all data from the RegimeX REST API — it does not access storage directly.
- The web client handles API authentication tokens and refreshes them transparently.
- The web client degrades gracefully when API responses are slow or unavailable.

### EIR-4: API Clients (Developers and SDK)

**Expected Interface Behavior:**
- API clients receive versioned, structured responses conforming to `API_CONTRACTS.md`.
- API clients receive predictable, machine-readable error codes for all error conditions.
- API clients receive rate limit information in response headers.
- API clients access asynchronous job results through a polling model.

### EIR-5: Persistent Storage

**Expected Behavior:**
- The storage layer accepts atomic write operations from all platform modules.
- Writes are idempotent — duplicate writes produce no side effects.
- The storage layer supports querying by all primary and composite keys defined in `DATA_CONTRACTS.md`.
- Storage failures are surfaced as structured errors to calling modules.

### EIR-6: Cache Layer

**Expected Behavior:**
- Frequently-queried, freshness-sensitive data (current regime, recent analytics) may be served from a cache.
- Cache entries have explicit TTLs appropriate to their data freshness requirements.
- A cache miss falls through to the storage layer without error.
- Cache invalidation is triggered on data updates.

---

## 11. Data Requirements

All platform data entities must satisfy the following requirements. Canonical schemas are defined in [`DATA_CONTRACTS.md`](./DATA_CONTRACTS.md).

| Requirement | Description |
|------------|-------------|
| **Timestamps** | All timestamps are stored in UTC. No ambiguous or timezone-unspecified timestamps. |
| **Symbols** | Instrument symbols follow a canonical format: `SYMBOL` for exchange-listed instruments. |
| **OHLCV Records** | Every record includes symbol, exchange, timestamp, OHLCV values, adjustment type, currency, asset class, data source, and ingestion timestamp. |
| **Dataset Versioning** | Every dataset snapshot has a fingerprint. Computations reference the fingerprint of their input data. |
| **Feature Records** | Every feature record includes feature ID, version, symbol, exchange, timestamp, value, validity flag, computation timestamp, and input dataset version. |
| **Regime Output Records** | Every regime record includes regime label, confidence, probability distribution, algorithm metadata, feature set ID, dataset version, run ID, and computation timestamp. |
| **Risk Records** | Every risk record includes metric name, value, window, confidence level, regime label (if conditional), assumptions, and computation timestamp. |
| **Backtest Records** | Every backtest includes strategy metadata, universe, date range, cost model, dataset version, performance metrics, equity curve, drawdown series, trade log, and regime attribution. |
| **Experiment Records** | Every experiment run records configuration, software versions, data versions, and execution timestamps sufficient for reproduction. |
| **Reproducibility Metadata** | For any analysis output, it must be possible to identify: input data version, algorithm version, parameter set, and execution context. |
| **Audit Traceability** | All stored records include creation timestamps. Administrative actions are logged with actor identity and timestamp. |

---

## 12. Error Handling Requirements

### EHR-1: Unavailable Market Data

- **Behavior:** When data for a requested instrument and date range is unavailable, the platform returns a structured `NOT_FOUND` or `SERVICE_UNAVAILABLE` error.
- **Prohibited:** Returning partial data without indicating it is incomplete. Silently returning zeros or interpolated values.

### EHR-2: Invalid Symbol

- **Behavior:** Requests for an unrecognized symbol return `INVALID_SYMBOL` with a clear message identifying the symbol.
- **Prohibited:** Returning data for a different symbol or silently ignoring the request.

### EHR-3: Malformed Requests

- **Behavior:** Requests failing schema validation return `VALIDATION_ERROR` with field-level detail.
- **Prohibited:** Processing a malformed request and returning unpredictable results.

### EHR-4: Stale or Incomplete Data

- **Behavior:** Computations that detect stale or incomplete input data surface the staleness to the caller in the response metadata.
- **Prohibited:** Silently proceeding with stale data as if it were current.

### EHR-5: Unavailable Regime Model

- **Behavior:** Requesting a detection run with an unregistered algorithm returns `NOT_FOUND` with the algorithm ID.
- **Prohibited:** Silently substituting a different algorithm.

### EHR-6: Failed Inference

- **Behavior:** A regime detection run that fails during inference is recorded as `failed` with a structured error reason. Partial results are not returned.
- **Prohibited:** Returning regime outputs computed from an incomplete run.

### EHR-7: Backtest Failure

- **Behavior:** A backtest that fails during simulation is recorded as `failed` with a structured error and the bar at which failure occurred.
- **Prohibited:** Returning performance metrics computed from an incomplete simulation.

### EHR-8: AI Provider Failure

- **Behavior:** When the AI provider is unavailable, the assistant returns a graceful degradation message, not an unhandled exception.
- **Prohibited:** Presenting a fabricated response when the provider is unavailable.

### EHR-9: Provider Timeout

- **Behavior:** Provider calls that exceed timeout thresholds are retried with backoff. Persistent failures are surfaced as `SERVICE_UNAVAILABLE`.
- **Prohibited:** Blocking indefinitely on a provider timeout.

### EHR-10: General Error Handling Principles

| Principle | Requirement |
|-----------|-------------|
| **Predictable errors** | All error conditions produce a response matching the error schema in `API_CONTRACTS.md`. |
| **Useful feedback** | Error messages are human-readable and identify the cause and affected resource. |
| **No silent corruption** | Errors never result in partial data being silently stored as complete data. |
| **Safe degradation** | Where possible, partial failures degrade gracefully rather than failing the entire operation. |
| **Logging** | All errors are logged with `request_id`, error code, timestamp, and sufficient context for diagnosis. |

---

## 13. Audit Requirements

RegimeX research outputs must be traceable and auditable. The following audit capabilities are required of the eventual platform implementation.

| Audit Dimension | Required Traceability |
|----------------|----------------------|
| **Model Version** | Every analysis output records the algorithm ID and version used to produce it. |
| **Feature Version** | Every feature value records the feature ID and version. |
| **Dataset Source** | Every computation records the dataset version fingerprint of its input data. |
| **Execution Timestamp** | Every stored record includes the UTC timestamp of its computation. |
| **Experiment Configuration** | Every parameterized run stores its full configuration snapshot. |
| **Backtest Configuration** | Every backtest stores: strategy parameters, cost model, universe, date range, and dataset version. |
| **Output Provenance** | Every analysis output is traceable to its exact inputs and configuration. |
| **API Access Audit** | All authenticated API requests are logged with: user identity, method, path, status, and timestamp. |
| **Administrative Actions** | Administrator actions (user creation, key revocation, configuration changes) are logged with actor and timestamp. |

> Audit infrastructure implementation is scheduled for V23 — Observability.

---

## 14. Requirements Traceability

The requirements traceability model for RegimeX follows this chain:

```text
Product Goal (V01/PRODUCT_FOUNDATION.md)
         ↓
Product Principle (V01/PRINCIPLES.md)
         ↓
Functional Requirement (this document — FR-NNN)
         ↓
Design Component (V03 — System Architecture, TBD)
         ↓
Implementation (V04–V21)
         ↓
Test Case (V22 — Testing & Reliability, TBD)
         ↓
Release Validation (V29–V30)
```

### Traceability Mapping (V02 — Requirements Layer)

The following table maps the product areas defined in V01 to the functional requirement domains in this document.

| V01 Product Area | SRS Domain | FR Range |
|-----------------|------------|----------|
| Market Discovery | Domain A | FR-001 – FR-004 |
| Market Data | Domain B | FR-005 – FR-013 |
| Feature Engineering | Domain C | FR-014 – FR-021 |
| Regime Detection | Domain D | FR-022 – FR-031 |
| Regime Intelligence | Domain E | FR-032 – FR-037 |
| Risk Analytics | Domain F | FR-038 – FR-044 |
| Backtesting | Domain G | FR-045 – FR-055 |
| Research Workspace | Domain H | FR-056 – FR-059 |
| AI Research Assistant | Domain I | FR-060 – FR-066 |
| Public Web Platform | Domain J | FR-067 – FR-072 |
| API Platform | Domain K | FR-073 – FR-081 |
| Developer Platform | Domain L | FR-082 – FR-086 |
| Open-Source Community | Domain M | FR-087 – FR-091 |

Design component and test case mappings will be populated in V03 and V22 respectively.

---

## 15. Acceptance Criteria

### General Acceptance Principles

A functional requirement is considered fulfilled only when all of the following conditions are met:

1. **Implemented** — The required behavior is present in the codebase.
2. **Tested** — The behavior is covered by automated tests (unit and/or integration) that verify the acceptance criteria stated in this document.
3. **Documented** — The capability is described in user-facing or developer-facing documentation.
4. **Observable** — Where the requirement specifies measurable behavior, that behavior is verifiable in the deployed system.
5. **Validated** — The implementation has been reviewed against the acceptance criteria stated here and confirmed to pass.

### Acceptance Criteria Status

> ⚠️ **V02 is defining requirements only.** No requirements have been implemented or validated. The acceptance criteria above define what must be true for each requirement to be considered complete in future volumes. Acceptance criteria will be marked as passed in the corresponding implementation volume.

### Priority-Based Implementation Sequence

Requirements will be implemented in priority order within each volume:

| Priority | Implementation Expectation |
|----------|--------------------------|
| **P0 — Critical** | Must be implemented before the volume they belong to is considered complete. |
| **P1 — High** | Must be implemented before the initial production release (V26). |
| **P2 — Medium** | Should be implemented before V30 (1.0 release). May be deferred to a post-1.0 release with documented justification. |
| **P3 — Future** | Deferred beyond V30 by design. Tracked in the roadmap for future volumes. |

---

## 16. Out-of-Scope Requirements

The following capabilities are explicitly and permanently outside the scope of RegimeX. These exclusions align with [`V01/PROJECT_SCOPE.md`](../V01/PROJECT_SCOPE.md).

| Excluded Capability | Rationale |
|--------------------|-----------|
| **Guaranteed return claims** | RegimeX is an analytical research platform. It makes no claims about future financial returns. |
| **Guaranteed market predictions** | Regime detection is probabilistic and historically grounded — not predictive with certainty. |
| **Personalized investment advice** | RegimeX is not a registered investment advisor and does not provide individual recommendations. |
| **Automated financial advice** | No platform feature will construct or deliver advice tailored to an individual's financial situation. |
| **Autonomous trade execution** | RegimeX does not execute trades, interface with brokers, or manage assets. |
| **Fabricated financial information** | No platform component may generate market data, regime signals, or statistics not grounded in real data. |
| **Unsupported market claims** | The platform will not surface analysis for assets outside its validated data coverage as if they were supported. |
| **Insider information or privileged data** | The platform uses only publicly accessible market data. |

---

## 17. Open Questions

The following decisions are unresolved as of V02. They will be addressed through Architecture Decision Records (ADRs) in V03.

| ID | Question | Impact |
|----|----------|--------|
| OQ-001 | Which market data provider(s) will be supported at initial release (V05)? | Determines data coverage, schema mapping effort, and licensing |
| OQ-002 | What is the initial supported asset class set? US equities only, or US + India + Crypto from V05? | Affects ingestion scope, feature coverage, and storage sizing |
| OQ-003 | Which regime detection algorithm will be prioritized as the default (first production algorithm)? | HMM planned per roadmap; confirm or update in V08 |
| OQ-004 | Which AI / LLM provider will be used for the AI Research Assistant? | Affects grounding implementation, cost, and data privacy |
| OQ-005 | What is the primary storage technology for market data (time-series database vs relational)? | Significant architecture decision; affects V06 design |
| OQ-006 | What is the data retention policy for backtest results and research runs? | Affects storage sizing and archival strategy |
| OQ-007 | What historical data coverage depth will be targeted at launch (5 years? 20 years?) | Affects ingestion effort, storage, and test dataset design |
| OQ-008 | What are the API rate limits for each user tier at launch? | Draft values in `API_CONTRACTS.md`; to be validated in V17 |
| OQ-009 | What is the boundary between public (unauthenticated) and authenticated platform features? | Determines auth requirements and UX for V17–V19 |
| OQ-010 | What open-source license will RegimeX use? | Was deferred to V02; must be decided before V04 |

---

## 18. Non-Functional Requirements

Non-functional requirements define **how** RegimeX must operate — the quality attributes that apply across all functional domains. They constrain architecture, implementation, and operational decisions from V03 onward.

> ⚠️ **None of these NFRs are implemented in V01 or V02.** Implementation begins in V04+. Where production targets depend on capacity planning or architecture decisions not yet made, targets are marked **TBD**.

**Priority Legend** is the same as Section 9.

**NFR Category Codes:**

| Code | Category |
|------|----------|
| PERF | Performance |
| SEC | Security |
| AVAIL | Availability |
| SCALE | Scalability |
| REL | Reliability |
| OBS | Observability |
| ACC | Accessibility |
| PRIV | Privacy |
| MAINT | Maintainability |
| COMPAT | Compatibility |
| DR | Disaster Recovery |
| DQ | Data Quality |
| AUDIT | Auditability |
| COMP | Compliance & Financial Disclaimer |
| OPS | Operational Constraints |

---

### Category 1 — Performance

---

#### NFR-001 — Interactive API Response Time

**Category:** Performance
**Priority:** P1 — High
**Description:**
The system shall deliver predictable response times for interactive API operations under normal production workload. Interactive operations are those that a human user waits for in real time: regime queries, instrument lookups, risk metric retrieval, and current-regime dashboards.

**Target:** p95 latency ≤ 500 ms for regime query, discovery, and risk metric endpoints under the defined production workload. Final target: TBD during architecture and capacity planning.

**Acceptance Criteria:**
- Response time is measurable via an agreed-upon load test profile.
- p95 latency for interactive endpoints is recorded in CI performance benchmarks.
- Degradation beyond the target is observable via metrics (NFR-046).
- The target is finalized and documented before V26 (Production Deployment).

---

#### NFR-002 — Market Data Retrieval Performance

**Category:** Performance
**Priority:** P1 — High
**Description:**
The system shall retrieve one year of daily OHLCV data for a single instrument within an acceptable interactive response time.

**Target:** p95 latency ≤ 1,000 ms for one-year OHLCV retrieval. Final target: TBD during capacity planning.

**Acceptance Criteria:**
- Data retrieval is benchmarked for standard instruments and date ranges.
- The target is validated against actual storage query performance before V26.

---

#### NFR-003 — Feature Computation Performance

**Category:** Performance
**Priority:** P2 — Medium
**Description:**
The system shall compute all registered features for a single instrument over a multi-year date range within an acceptable background processing time.

**Target:** Feature computation for one instrument over five years of daily data: TBD during implementation planning.

**Acceptance Criteria:**
- Feature computation time is measurable per instrument and date range.
- Computation time is tracked and reported in CI benchmarks.
- Users are not blocked waiting for feature computation — it executes asynchronously where necessary.

---

#### NFR-004 — Regime Detection Performance

**Category:** Performance
**Priority:** P2 — Medium
**Description:**
Regime detection runs over historical data are computationally intensive and shall execute as asynchronous background jobs. Users submit a detection job and poll for results. The elapsed wall-clock time for a standard detection run shall be documented as a performance benchmark.

**Target:** HMM detection for a single instrument over five years of daily data, three regimes: TBD during V08 implementation.

**Acceptance Criteria:**
- Detection runs execute asynchronously and return a job ID immediately.
- Job completion time is recorded and accessible in job metadata.
- The benchmark result is documented before V26.

---

#### NFR-005 — Backtest Execution Performance

**Category:** Performance
**Priority:** P2 — Medium
**Description:**
Backtesting is a computationally expensive asynchronous operation. The platform shall execute a standard daily backtest over a multi-year history within an acceptable elapsed time.

**Target:** Daily bar-by-bar backtest over ten years of data for a single-instrument strategy: TBD during V14 implementation.

**Acceptance Criteria:**
- Backtest runs execute asynchronously and return a job ID immediately.
- Elapsed time is recorded in backtest result metadata.
- The benchmark is documented before V26.

---

#### NFR-006 — Web Platform Initial Load

**Category:** Performance
**Priority:** P1 — High
**Description:**
The web platform shall load its primary dashboard within an acceptable time on a standard broadband connection so that users are not deterred by initial loading delay.

**Target:** Largest Contentful Paint (LCP) ≤ 2.5 seconds on a standard broadband connection (consistent with Google Core Web Vitals "Good" threshold).

**Acceptance Criteria:**
- LCP is measurable using standard browser tooling.
- LCP is measured and reported as part of the web platform CI pipeline.
- LCP target is met before V26.

---

#### NFR-007 — Concurrent Request Capacity

**Category:** Performance
**Priority:** P1 — High
**Description:**
The API shall handle concurrent requests from multiple authenticated users without degradation of interactive response times beyond the defined targets.

**Target:** Minimum concurrent authenticated user capacity: TBD during architecture and capacity planning.

**Acceptance Criteria:**
- Load tests simulate concurrent users at the target concurrency level.
- p95 response times remain within NFR-001 targets under the target concurrency.
- The concurrency target is defined and validated before V26.

---

#### NFR-008 — Background Workload Isolation

**Category:** Performance
**Priority:** P1 — High
**Description:**
Computationally expensive background workloads (regime detection, backtest execution, bulk feature computation) shall not degrade interactive API response times.

**Acceptance Criteria:**
- Background jobs execute in an isolated processing context that does not share resources with interactive API handlers.
- Interactive API p95 latency is measured both with and without background jobs running.
- Degradation of interactive response time attributable to background jobs shall not exceed 20% above the baseline target.

---

### Category 2 — Security

---

#### NFR-009 — Authentication Requirement

**Category:** Security
**Priority:** P0 — Critical
**Description:**
All non-public API endpoints shall require authenticated requests. Requests without valid credentials shall be rejected before any business logic is executed.

**Acceptance Criteria:**
- Every protected endpoint returns HTTP 401 for unauthenticated requests.
- Authentication is validated in automated API tests.
- No protected endpoint is accessible without valid credentials.

---

#### NFR-010 — Authorization and Least Privilege

**Category:** Security
**Priority:** P0 — Critical
**Description:**
The system shall enforce role-based authorization. Users and API clients shall be granted only the minimum permissions required for their role. No role shall have access to capabilities beyond those defined for that role.

**Acceptance Criteria:**
- A Researcher-tier key cannot access Administrator-only endpoints.
- A Public (unauthenticated) session cannot access Researcher-tier endpoints.
- Role boundaries are tested in automated authorization tests.

---

#### NFR-011 — Secret and Credential Management

**Category:** Security
**Priority:** P0 — Critical
**Description:**
No credentials, API keys, database passwords, or secrets of any kind shall appear in source code, configuration files tracked by version control, logs, or API responses.

**Acceptance Criteria:**
- A secret-scanning tool runs in CI and blocks merges that introduce detected secrets.
- Application configuration is loaded from environment variables or a secrets manager, not from committed files.
- No secret appears in plaintext in any log output.
- Automated tests verify that secrets are not returned in API responses.

---

#### NFR-012 — Input Validation and Sanitization

**Category:** Security
**Priority:** P0 — Critical
**Description:**
All inputs received by the platform — API request bodies, query parameters, path parameters, and uploaded data — shall be validated and sanitized before processing. Malformed inputs shall be rejected with a structured error before reaching business logic.

**Acceptance Criteria:**
- All API endpoint schemas define explicit type and format constraints.
- Schema validation runs before any business logic handler executes.
- Inputs failing validation return HTTP 400 with a `VALIDATION_ERROR` code.
- Penetration tests verify the absence of injection vulnerabilities (SQL injection, command injection) before production release.

---

#### NFR-013 — Injection Attack Prevention

**Category:** Security
**Priority:** P0 — Critical
**Description:**
The platform shall prevent injection attacks including but not limited to SQL injection, command injection, and prompt injection in the AI assistant.

**Acceptance Criteria:**
- All database queries use parameterized queries or an ORM with parameterized query support.
- No user-provided input is interpolated directly into executed queries or shell commands.
- AI assistant inputs are sanitized and not directly injected into LLM system prompts without review.
- Security testing verifies injection prevention before V26.

---

#### NFR-014 — Session Security

**Category:** Security
**Priority:** P0 — Critical
**Description:**
Authenticated sessions shall be secured through token expiry, revocability, and secure transmission.

**Acceptance Criteria:**
- JWT access tokens expire after a configurable duration (default: 1 hour).
- API keys can be revoked by administrators and users.
- Revoked tokens are rejected immediately on the next request.
- Tokens are never transmitted over unencrypted connections in production.
- Refresh tokens are single-use or otherwise protected against replay.

---

#### NFR-015 — Transport Security

**Category:** Security
**Priority:** P0 — Critical
**Description:**
All data transmitted between clients and the platform shall be encrypted in transit using TLS in production deployments.

**Acceptance Criteria:**
- The platform does not serve API or web content over unencrypted HTTP in production.
- TLS version is TLS 1.2 or later.
- TLS configuration is verified by an automated check in the deployment pipeline.

---

#### NFR-016 — Rate Limiting and Abuse Prevention

**Category:** Security
**Priority:** P1 — High
**Description:**
The platform shall enforce rate limits per authenticated identity to prevent abuse, accidental resource exhaustion, and denial-of-service.

**Acceptance Criteria:**
- Rate limits are applied per API key and per session.
- Rate limit headers are returned on every response.
- Requests exceeding the rate limit receive HTTP 429 with a `Retry-After` header.
- Rate limits are configurable without code changes.

---

#### NFR-017 — Dependency Vulnerability Management

**Category:** Security
**Priority:** P1 — High
**Description:**
The platform shall maintain a dependency vulnerability management process to identify and remediate known vulnerabilities in third-party libraries.

**Acceptance Criteria:**
- A dependency vulnerability scanning tool runs in CI.
- High and critical severity CVEs block merges until remediated.
- A process exists for triaging and tracking medium severity CVEs.

---

#### NFR-018 — Container Security

**Category:** Security
**Priority:** P1 — High
**Description:**
Container images shall be built and operated following security best practices.

**Acceptance Criteria:**
- Production container images do not run processes as root.
- Base images are pinned to specific versions, not floating `latest` tags.
- Container images are scanned for known vulnerabilities before deployment.

---

#### NFR-019 — Security Event Logging

**Category:** Security
**Priority:** P1 — High
**Description:**
Security-relevant events shall be logged with sufficient detail for investigation and incident response.

**Acceptance Criteria:**
- The following events are logged: authentication successes, authentication failures, authorization denials, API key creation, API key revocation, administrative configuration changes.
- Security logs include: event type, actor identity, timestamp, IP address, and resource affected.
- Security logs are structured (machine-parseable).
- Security logs are not accessible to non-administrator users via the API.

---

#### NFR-020 — Output Sanitization

**Category:** Security
**Priority:** P1 — High
**Description:**
All API responses and web platform output shall be sanitized to prevent content injection (e.g., XSS) in clients that render dynamic content.

**Acceptance Criteria:**
- API responses containing user-provided string data sanitize HTML metacharacters.
- The web platform Content Security Policy (CSP) header is configured to restrict script execution.
- XSS prevention is verified in security testing before V26.

---

### Category 3 — Availability

---

#### NFR-021 — API Availability Target

**Category:** Availability
**Priority:** P1 — High
**Description:**
The platform API shall maintain a defined availability target in production deployments. The availability target is not yet established — it will be determined during architecture and capacity planning with reference to hosting infrastructure.

**Target:** Initial production SLO: TBD. To be established before V26 (Production Deployment).

**Acceptance Criteria:**
- An availability SLO is defined and documented before V26.
- Uptime is monitored and reported using a health endpoint (see NFR-048).
- Availability is calculated as the fraction of time the API correctly responds to health checks.

---

#### NFR-022 — Graceful Degradation

**Category:** Availability
**Priority:** P1 — High
**Description:**
When an optional external dependency (market data provider, AI provider, cache) is unavailable, the platform shall degrade gracefully rather than becoming entirely unavailable.

**Acceptance Criteria:**
- Market data provider unavailability results in a `SERVICE_UNAVAILABLE` response for data endpoints, while regime and risk endpoints with cached data remain operational.
- AI provider unavailability results in a graceful degradation message from the AI assistant, not an unhandled error.
- Cache unavailability results in a fallthrough to the storage layer, not a service failure.
- Degradation behavior is covered by integration tests.

---

#### NFR-023 — Market Data Provider Outage Handling

**Category:** Availability
**Priority:** P1 — High
**Description:**
The platform shall handle market data provider outages without corrupting stored data or blocking unaffected capabilities.

**Acceptance Criteria:**
- A provider outage does not corrupt previously ingested data.
- Ingestion jobs that fail due to provider outages are retried with backoff.
- Failed ingestion jobs are recorded with their error reason and are retryable.
- Platform capabilities that do not require fresh data (historical regime queries, backtest result retrieval) continue operating during a provider outage.

---

#### NFR-024 — Recovery Time Expectation

**Category:** Availability
**Priority:** P1 — High
**Description:**
Following a service restart or infrastructure failure, the platform shall return to a healthy, request-serving state within a defined time.

**Target:** Recovery time objective (RTO): TBD. To be established during infrastructure planning in V26.

**Acceptance Criteria:**
- Recovery from a clean container restart is measurable.
- The RTO target is defined before V26.
- Automated health checks detect recovery completion.

---

#### NFR-025 — Health Check Endpoints

**Category:** Availability
**Priority:** P0 — Critical
**Description:**
The platform shall expose service-level health and readiness endpoints for orchestration and monitoring systems.

**Acceptance Criteria:**
- `GET /api/v1/health` returns HTTP 200 when the service process is running, regardless of dependency state.
- `GET /api/v1/ready` returns HTTP 200 only when all required dependencies (storage, etc.) are connected and functional.
- Both endpoints are unauthenticated and respond within 500 ms.
- Orchestration systems (e.g., Docker health checks) can use these endpoints without additional configuration.

---

### Category 4 — Scalability

---

#### NFR-026 — Stateless API Layer

**Category:** Scalability
**Priority:** P1 — High
**Description:**
The API layer shall be stateless so that multiple API instances can serve requests without shared in-process state. This enables horizontal scaling.

**Acceptance Criteria:**
- No session state is stored in API process memory.
- Any API instance can serve any authenticated request.
- Horizontal scaling of the API layer can be achieved by adding instances behind a load balancer without configuration changes.

---

#### NFR-027 — Horizontal API Scaling

**Category:** Scalability
**Priority:** P1 — High
**Description:**
The platform shall support adding API capacity by deploying additional API instances, without requiring architectural redesign.

**Acceptance Criteria:**
- The platform can run with two or more API instances behind a load balancer.
- Load balancing can be achieved without sticky sessions.
- This is validated in infrastructure testing before V26.

---

#### NFR-028 — Market Data Storage Scalability

**Category:** Scalability
**Priority:** P1 — High
**Description:**
The market data storage layer shall scale to accommodate a growing volume of historical OHLCV records without requiring schema redesign.

**Target:** The storage layer shall accommodate at least 50 million OHLCV records without query performance degradation. Final target: TBD during V06 storage design.

**Acceptance Criteria:**
- The storage schema and indexing strategy are designed to scale to the target record count.
- Performance benchmarks are run at the target record count before V26.

---

#### NFR-029 — Instrument Catalogue Scalability

**Category:** Scalability
**Priority:** P2 — Medium
**Description:**
Adding new supported instruments shall not require schema migrations or architectural changes.

**Acceptance Criteria:**
- A new instrument can be added to the catalogue by inserting a record — not by modifying schema definitions.
- Feature computation and regime detection support any instrument in the catalogue without code changes.

---

#### NFR-030 — Feature and Model Plugin Scalability

**Category:** Scalability
**Priority:** P1 — High
**Description:**
Adding new regime detection algorithms or quantitative features shall not require modifications to the core platform codebase — only plugin registration.

**Acceptance Criteria:**
- A new algorithm can be registered without modifying core regime detection consumers.
- A new feature can be registered without modifying the feature computation pipeline.
- Plugin registration is tested in the CI pipeline.

---

#### NFR-031 — Background Job Scalability

**Category:** Scalability
**Priority:** P2 — Medium
**Description:**
The background processing system shall support increasing the number of concurrent background jobs by adding worker capacity, without architectural redesign.

**Target:** Minimum concurrent background job capacity: TBD during V03 architecture.

**Acceptance Criteria:**
- The background processing architecture is designed for horizontal worker scaling.
- The target concurrent job capacity is defined before V26.

---

### Category 5 — Reliability

---

#### NFR-032 — Research Reproducibility

**Category:** Reliability
**Priority:** P0 — Critical
**Description:**
Identical inputs — same data version, algorithm version, feature version, and configuration — shall produce identical outputs across all platform computations. Research reproducibility is a fundamental product guarantee.

**Acceptance Criteria:**
- Re-running a feature computation with the same inputs produces byte-identical results.
- Re-running a regime detection run with the same configuration produces identical regime labels.
- Re-running a backtest with the same configuration produces identical performance metrics.
- Reproducibility is verified by automated tests for all core computation modules.

---

#### NFR-033 — Retry with Backoff

**Category:** Reliability
**Priority:** P1 — High
**Description:**
Transient failures in external dependencies (market data providers, AI providers, storage) shall be retried automatically using exponential backoff before propagating a failure response.

**Acceptance Criteria:**
- Retry logic is applied to all external dependency calls.
- Retry parameters (max attempts, backoff factor, jitter) are configurable.
- Retry exhaustion produces a structured error, not an unhandled exception.
- Retry behavior is tested with simulated transient failures.

---

#### NFR-034 — Idempotent Operations

**Category:** Reliability
**Priority:** P0 — Critical
**Description:**
All write operations — data ingestion, job submission, result storage — shall be idempotent. Executing the same operation multiple times shall produce the same result as executing it once.

**Acceptance Criteria:**
- Re-running data ingestion for the same symbol and date range does not produce duplicate records.
- Re-submitting an identical job does not create duplicate jobs.
- Idempotency is verified by automated tests for all write operations.

---

#### NFR-035 — Failure Isolation

**Category:** Reliability
**Priority:** P1 — High
**Description:**
A failure in one platform module shall not propagate to unrelated modules or cause cascading service failure.

**Acceptance Criteria:**
- A failed background job does not terminate the API service.
- A failed data ingestion job does not affect regime detection or backtesting endpoints.
- Module failure boundaries are validated by integration tests.

---

#### NFR-036 — Atomic Writes

**Category:** Reliability
**Priority:** P0 — Critical
**Description:**
All write operations to persistent storage shall be atomic. A partial write — resulting from a failure mid-operation — shall not leave storage in a corrupt or inconsistent state.

**Acceptance Criteria:**
- Storage write operations use transactions or equivalent atomic write guarantees.
- A simulated failure during write is tested to confirm no partial record is stored.
- Idempotent re-execution after a failed write produces a correct complete result.

---

#### NFR-037 — Background Job Recovery

**Category:** Reliability
**Priority:** P1 — High
**Description:**
Background jobs that fail during execution shall be recorded as failed with a diagnostic reason, and shall be retryable without data corruption.

**Acceptance Criteria:**
- Failed jobs are persisted with status `failed` and an error message.
- Failed jobs can be retried by an administrator or the job scheduler.
- Retrying a failed job does not corrupt results from a prior successful run of the same job.

---

#### NFR-038 — Silent Corruption Prevention

**Category:** Reliability
**Priority:** P0 — Critical
**Description:**
No failure, error, or edge case shall result in invalid data being silently stored as valid data, or invalid computation results being silently presented as valid results.

**Acceptance Criteria:**
- All data writes include validity checks before commit.
- Computation failures produce error records — not default or zero values presented as real results.
- Invalid regime outputs, feature values, and backtest results are flagged, not silently accepted.
- Automated tests verify that simulated failures produce error states, not silent incorrect results.

---

### Category 6 — Observability

---

#### NFR-039 — Structured Logging

**Category:** Observability
**Priority:** P0 — Critical
**Description:**
All platform services shall emit logs in structured JSON format. Unstructured or free-text-only logs are not acceptable for production services.

**Acceptance Criteria:**
- All log events are JSON-formatted.
- All log events include at minimum: `timestamp` (UTC ISO 8601), `level`, `service`, `message`, and `request_id` where applicable.
- Log output is parseable by standard log aggregation systems without custom parsing.

---

#### NFR-040 — API Request Logging

**Category:** Observability
**Priority:** P0 — Critical
**Description:**
Every API request shall produce a structured log event containing sufficient information to diagnose request behavior without access to client systems.

**Acceptance Criteria:**
- Every request log includes: HTTP method, path, query parameters (redacted for sensitive values), HTTP status code, response latency, and authenticated user identity (where applicable).
- `request_id` is consistent between the log entry and the API response `meta.request_id`.

---

#### NFR-041 — Key Platform Metrics

**Category:** Observability
**Priority:** P1 — High
**Description:**
The platform shall emit metrics for key operational indicators, enabling operators to assess platform health and detect problems early.

**Required Metrics:**
- API request rate (by endpoint)
- API error rate (by endpoint and error code)
- API response latency percentiles (p50, p95, p99)
- Background job queue depth
- Background job failure rate
- Data ingestion throughput (bars/second)
- Data ingestion failure rate
- Cache hit rate (if cache is deployed)
- Storage query latency

**Acceptance Criteria:**
- All listed metrics are emitted and observable via a metrics system.
- Metric names and labels follow a consistent naming convention.
- Metrics are emitted in a format compatible with standard monitoring systems.

---

#### NFR-042 — Distributed Tracing

**Category:** Observability
**Priority:** P2 — Medium
**Description:**
The platform shall support distributed tracing to link an API request to its downstream storage queries, cache lookups, and background job dispatches.

**Acceptance Criteria:**
- A trace context (trace ID, span ID) is propagated through all service calls originating from an API request.
- Traces are viewable in a trace analysis tool.
- `request_id` maps to the corresponding trace.

---

#### NFR-043 — Data Freshness Monitoring

**Category:** Observability
**Priority:** P1 — High
**Description:**
The platform shall monitor and expose the freshness of ingested market data, enabling operators to detect stale or missing data.

**Acceptance Criteria:**
- The last successful ingestion timestamp per instrument is recorded and queryable.
- An alert condition is defined for instruments whose last ingestion exceeds an expected freshness threshold.
- Freshness status is accessible via a monitoring endpoint or metric.

---

#### NFR-044 — Job Status Observability

**Category:** Observability
**Priority:** P1 — High
**Description:**
The current and historical status of background jobs (regime detection, backtest, ingestion) shall be queryable by users and operators.

**Acceptance Criteria:**
- Every job has a queryable status: `pending`, `running`, `completed`, `failed`.
- Failed jobs expose a structured error reason.
- Job queue depth and throughput are observable via metrics.

---

#### NFR-045 — Dependency Health Monitoring

**Category:** Observability
**Priority:** P1 — High
**Description:**
The platform shall monitor the health of its external dependencies (data providers, storage, AI provider) and surface dependency health to operators.

**Acceptance Criteria:**
- The `/ready` endpoint reflects dependency health.
- Unhealthy dependencies produce an observable alert condition.
- Dependency health is included in platform status dashboards.

---

#### NFR-046 — Performance Degradation Alerting

**Category:** Observability
**Priority:** P1 — High
**Description:**
The platform shall define and enforce alert conditions for performance degradation beyond defined thresholds.

**Required Alert Conditions:**
- API error rate exceeds 1% over a rolling window.
- p95 API response time exceeds 2× the defined SLO target.
- Ingestion failure rate exceeds a defined threshold.
- Background job queue depth exceeds a defined threshold.

**Acceptance Criteria:**
- Alert conditions are defined as code (not manual configuration).
- Alerts fire correctly in test environments with injected failures.
- Alert thresholds are tunable without code changes.

---

#### NFR-047 — Operational Incident Diagnostics

**Category:** Observability
**Priority:** P1 — High
**Description:**
Observability tooling shall enable an operator to answer the following questions for any production incident, without requiring access to source code or production systems directly:

- What failed?
- When did it fail?
- Which component failed?
- What data version, model version, or job was involved?
- Can the system safely recover?

**Acceptance Criteria:**
- Logs, metrics, and traces collectively cover the five questions above.
- An incident runbook template is defined that maps these questions to observability sources.

---

#### NFR-048 — Health Endpoint Requirements

**Category:** Observability
**Priority:** P0 — Critical
**Description:**
Platform health endpoints shall be lightweight, always available, and return structured responses.

**Acceptance Criteria:**
- `GET /api/v1/health` response includes: service name, status (`healthy`/`unhealthy`), and timestamp.
- `GET /api/v1/ready` response includes: overall readiness status and per-dependency readiness.
- Both endpoints respond within 500 ms under all conditions.
- Both endpoints are unauthenticated.

---

### Category 7 — Accessibility

---

#### NFR-049 — Accessibility Standard Target

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
The RegimeX web platform shall be designed and built to target WCAG 2.1 Level AA conformance. This is a design target — conformance is not claimed until validated by accessibility testing during the web platform volumes (V18–V20).

**Acceptance Criteria:**
- WCAG 2.1 Level AA is documented as the accessibility target before web platform implementation begins.
- Accessibility requirements are incorporated into the web platform design specifications in V18.
- Automated accessibility testing tools are included in the web platform CI pipeline.

---

#### NFR-050 — Keyboard Navigation

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
All interactive elements in the web platform shall be navigable and operable using a keyboard alone.

**Acceptance Criteria:**
- All buttons, links, form controls, and navigation elements are reachable via Tab key navigation.
- Focus indicators are visible on all interactive elements.
- No keyboard trap exists anywhere in the application.

---

#### NFR-051 — Semantic HTML Structure

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
The web platform shall use semantic HTML elements to communicate document structure and interactive element roles.

**Acceptance Criteria:**
- Headings use `<h1>`–`<h6>` in a logical hierarchy.
- Navigation uses `<nav>`.
- Page landmark regions use appropriate ARIA landmark roles or semantic elements.
- Interactive elements are implemented using native HTML controls where practical.

---

#### NFR-052 — Color Contrast

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
Text content in the web platform shall meet minimum color contrast ratios to be readable by users with low vision or color deficiency.

**Target:** WCAG 2.1 Level AA contrast ratio: ≥ 4.5:1 for normal text, ≥ 3:1 for large text.

**Acceptance Criteria:**
- Contrast ratios are checked using automated accessibility tooling.
- Color is not the sole visual means of conveying information (e.g., regime states use labels, not only color).

---

#### NFR-053 — Screen-Reader Compatibility

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
Primary user flows in the web platform shall be operable and understandable with a screen reader.

**Acceptance Criteria:**
- Page titles, landmark regions, and interactive controls are announced correctly by screen readers.
- Dynamic content updates (e.g., regime state change, job completion) are communicated via ARIA live regions where applicable.
- Form validation errors are announced to screen readers.

---

#### NFR-054 — Accessible Data Visualizations

**Category:** Accessibility
**Priority:** P2 — Medium
**Description:**
Data visualizations (regime timelines, charts) shall provide text alternatives or structured data tables for users who cannot perceive the visual representation.

**Acceptance Criteria:**
- Every chart or visualization has a text description or linked data table.
- Key data points are accessible without requiring the ability to interpret the visual chart.

---

#### NFR-055 — Reduced-Motion Support

**Category:** Accessibility
**Priority:** P2 — Medium
**Description:**
The web platform shall respect the user's operating system preference for reduced motion, minimizing or disabling non-essential animations.

**Acceptance Criteria:**
- The platform implements `prefers-reduced-motion` media query support.
- Decorative animations are suppressed when reduced-motion is preferred.
- No content becomes inaccessible when animations are suppressed.

---

#### NFR-056 — Responsive Layout

**Category:** Accessibility
**Priority:** P1 — High
**Description:**
The web platform shall be usable at a range of viewport widths, supporting desktop, tablet, and large mobile viewports without horizontal scrolling or overlapping content.

**Target Viewports:** Desktop (≥ 1280px), Tablet (≥ 768px). Mobile support: TBD.

**Acceptance Criteria:**
- No horizontal scrollbar appears at the target viewport widths.
- Content does not overlap at target viewport widths.
- Navigation is fully operable at target viewport widths.

---

### Category 8 — Privacy

---

#### NFR-057 — Data Minimization

**Category:** Privacy
**Priority:** P1 — High
**Description:**
The platform shall collect and store only the user data necessary to provide the requested service. Data collection beyond operational necessity is prohibited.

**Acceptance Criteria:**
- User account data is limited to: identifier, credentials (hashed), role, and API key references.
- No behavioral tracking or analytics beyond operational logs is implemented without a documented privacy decision.
- A data inventory is maintained identifying every category of personal data stored.

---

#### NFR-058 — Research Configuration Privacy

**Category:** Privacy
**Priority:** P1 — High
**Description:**
User-created research configurations, saved strategies, watchlists, and experiment results shall be private to the creating user unless explicitly shared.

**Acceptance Criteria:**
- A user cannot read another user's private research configurations via the API.
- API authorization tests verify resource isolation.
- No research configuration data is returned in bulk listing endpoints visible to other users.

---

#### NFR-059 — AI Conversation Handling

**Category:** Privacy
**Priority:** P1 — High
**Description:**
Conversation history with the AI Research Assistant shall not be shared across user sessions or with other users. The platform shall document how conversation content is transmitted to the AI provider.

**Acceptance Criteria:**
- Conversation history is scoped to the individual user session.
- The data handling practices for AI provider transmission are documented before V21 (AI Research Assistant).
- Users can clear their conversation history.

---

#### NFR-060 — Credential Security

**Category:** Privacy
**Priority:** P0 — Critical
**Description:**
User credentials (passwords, API keys) shall never be stored in plaintext. Passwords shall be hashed using an appropriate modern hashing algorithm. API keys shall be stored only as hashes after initial issuance.

**Acceptance Criteria:**
- Password storage uses a recognized adaptive hashing algorithm (e.g., bcrypt or Argon2). Algorithm selection: TBD in V17.
- API keys are returned in plaintext only once, at creation time, and are not recoverable thereafter.
- Automated tests verify that credentials are not returned or logged in plaintext.

---

#### NFR-061 — Data Retention Policy

**Category:** Privacy
**Priority:** P2 — Medium
**Description:**
The platform shall define and enforce data retention policies covering all categories of stored data.

**Target:** Retention periods for each data category: TBD. Policy to be defined before V26.

**Acceptance Criteria:**
- A data retention policy is documented before V26.
- Automated data deletion or archiving processes are implemented per the policy.
- Deletion is verifiable and auditable.

---

#### NFR-062 — Right to Deletion

**Category:** Privacy
**Priority:** P2 — Medium
**Description:**
The platform shall support deletion of a user's account and associated personal data on request.

**Target:** Specific deletion scope and process: TBD during privacy policy development.

**Acceptance Criteria:**
- Account deletion removes the user's personal data from the primary data store.
- The scope of deletion (what is removed, what is retained in logs) is documented.

---

#### NFR-063 — Third-Party Data Handling

**Category:** Privacy
**Priority:** P1 — High
**Description:**
When user queries or data are transmitted to third-party providers (AI/LLM providers, market data providers), the transmission shall be documented and limited to the minimum necessary for the request.

**Acceptance Criteria:**
- Third-party transmission scope is documented for each integration.
- User data is not transmitted to third parties beyond what is necessary for the requested operation.
- Third-party data handling terms are reviewed before integration is deployed.

---

### Category 9 — Maintainability

---

#### NFR-064 — Modular Architecture

**Category:** Maintainability
**Priority:** P0 — Critical
**Description:**
The platform shall be organized into clearly defined, independently testable modules. Each module shall have a single primary responsibility and communicate with other modules through documented interfaces.

**Acceptance Criteria:**
- Module boundaries are defined in the V03 architecture document.
- Each module has an explicit public interface and documented internal responsibilities.
- Cross-module dependencies are documented.
- A module can be replaced without modifying other modules, provided the interface contract is preserved.

---

#### NFR-065 — Code Coverage

**Category:** Maintainability
**Priority:** P1 — High
**Description:**
Core platform modules shall maintain a minimum automated test coverage level to reduce the risk of undetected regressions.

**Target:** ≥ 85% line coverage for core modules. Coverage targets per module: TBD during V22 (Testing & Reliability).

**Acceptance Criteria:**
- Coverage is measured and reported in CI.
- Coverage below the target blocks merge for core module changes.
- Coverage target per module is defined before V22.

---

#### NFR-066 — Type Annotations

**Category:** Maintainability
**Priority:** P0 — Critical
**Description:**
All public interfaces (functions, methods, classes) in the Python codebase shall be fully type-annotated.

**Acceptance Criteria:**
- A static type checker (e.g., mypy or pyright) runs in CI.
- Type checker errors block merges.
- No untyped public interfaces exist in core modules.

---

#### NFR-067 — Code Documentation

**Category:** Maintainability
**Priority:** P0 — Critical
**Description:**
All public modules, classes, and functions shall have docstrings explaining their purpose, parameters, return values, and any exceptions raised.

**Acceptance Criteria:**
- A documentation linting tool verifies docstring presence for public symbols.
- Docstring completeness is a merge requirement for public interfaces.

---

#### NFR-068 — Code Style Enforcement

**Category:** Maintainability
**Priority:** P1 — High
**Description:**
The codebase shall use a consistent formatting and style standard enforced by automated tooling in CI.

**Acceptance Criteria:**
- A code formatter and linter run in CI and block merges on violations.
- The formatter and linter configurations are committed to the repository.
- No manual formatting decisions are required from reviewers.

---

#### NFR-069 — Dependency Management

**Category:** Maintainability
**Priority:** P1 — High
**Description:**
All project dependencies shall be explicitly versioned and managed through a dependency management tool. Unpinned or floating dependencies are not permitted in production builds.

**Acceptance Criteria:**
- All dependencies are declared with explicit version constraints.
- A lock file is committed to version control.
- Dependency upgrades are tested against the full test suite before merge.

---

#### NFR-070 — Interface Versioning

**Category:** Maintainability
**Priority:** P0 — Critical
**Description:**
Breaking changes to public interfaces — including the `RegimeDetector` interface, `Feature` interface, data provider interface, and REST API — shall be versioned and accompanied by a migration guide.

**Acceptance Criteria:**
- Breaking interface changes increment the relevant version identifier.
- A migration guide is published with the breaking change.
- The changelog records all breaking changes.

---

#### NFR-071 — Developer Onboarding

**Category:** Maintainability
**Priority:** P1 — High
**Description:**
A new developer or contributor shall be able to set up a working local development environment by following the documented setup guide.

**Target:** Local environment setup time: ≤ 15 minutes on a machine meeting documented prerequisites.

**Acceptance Criteria:**
- The setup guide is tested on a clean environment before V27 (Developer Experience).
- Setup requires only tools listed in documented prerequisites.
- All setup steps are automatable (e.g., a single script or Makefile target).

---

#### NFR-072 — Technical Debt Tracking

**Category:** Maintainability
**Priority:** P2 — Medium
**Description:**
Known technical debt, temporary workarounds, and deferred implementation decisions shall be tracked in a discoverable, structured way.

**Acceptance Criteria:**
- Technical debt items are tracked via GitHub Issues labeled `tech-debt`.
- Temporary code workarounds include a `TODO` comment referencing the tracking issue.
- Technical debt is reviewed and triaged at least once per volume.

---

### Category 10 — Compatibility

---

#### NFR-073 — Supported Browsers

**Category:** Compatibility
**Priority:** P1 — High
**Description:**
The web platform shall function correctly in the most recent stable versions of major browsers.

**Target:** Latest two major releases of Chrome, Firefox, and Safari. Edge support: TBD.

**Acceptance Criteria:**
- The platform is tested in the target browser versions before V26.
- Critical functionality does not require browser-specific APIs not available across targets.

---

#### NFR-074 — Python SDK Compatibility

**Category:** Compatibility
**Priority:** P1 — High
**Description:**
The RegimeX Python SDK shall support a defined range of Python versions.

**Target:** Python 3.10 and later. Exact upper bound: TBD during SDK implementation.

**Acceptance Criteria:**
- CI runs SDK tests against all supported Python versions.
- The supported Python version range is documented in the SDK README and `pyproject.toml`.

---

#### NFR-075 — Self-Hosting OS Compatibility

**Category:** Compatibility
**Priority:** P0 — Critical
**Description:**
The platform shall be self-hostable on standard Linux-based hosts with Docker and Docker Compose installed. No proprietary operating system, cloud service, or managed platform is required.

**Acceptance Criteria:**
- The full platform stack starts with `docker compose up` on a supported Linux distribution.
- No steps require a cloud provider account or proprietary service.
- Self-hosting is tested on at least one supported Linux distribution before V24.

---

#### NFR-076 — API Version Compatibility

**Category:** Compatibility
**Priority:** P0 — Critical
**Description:**
The REST API shall maintain backward compatibility within a major version. Clients built against a given major version shall not break due to non-breaking additions (new optional response fields, new endpoints).

**Acceptance Criteria:**
- New optional fields are added to responses without incrementing the major version.
- Existing required response fields are never removed or renamed within a major version.
- API schema changes are tested against a client compatibility test suite.

---

#### NFR-077 — Data Format Compatibility

**Category:** Compatibility
**Priority:** P1 — High
**Description:**
Exported data formats (CSV, Parquet, JSON) shall remain stable across platform versions within a major version, so that downstream tools consuming exports are not broken by platform updates.

**Acceptance Criteria:**
- Breaking changes to export schemas require a major version increment or a versioned export format identifier.
- Export format changes are documented in the changelog.

---

#### NFR-078 — Plugin Interface Stability

**Category:** Compatibility
**Priority:** P1 — High
**Description:**
Plugin interfaces (`RegimeDetector`, `Feature`, data provider adapter) shall be stable across minor platform releases. Plugin authors shall not need to update their plugins for minor version upgrades.

**Acceptance Criteria:**
- Plugin interface changes that break existing plugins require a major version increment.
- Plugin compatibility is tested in CI using a reference plugin test suite.

---

### Category 11 — Disaster Recovery

---

#### NFR-079 — Automated Database Backups

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
Production database backups shall be automated and run on a regular schedule. Manual backup processes are not acceptable for production deployments.

**Target:** Backup frequency: TBD during infrastructure planning in V26.

**Acceptance Criteria:**
- Backup jobs run automatically on the defined schedule.
- Backup success and failure are logged and monitored.
- A failed backup produces an alert.

---

#### NFR-080 — Backup Integrity Testing

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
Database backups shall be regularly tested for restoreability. An untested backup is not a reliable backup.

**Acceptance Criteria:**
- A backup restoration test is performed on a defined schedule.
- Restoration tests verify that restored data is complete and queryable.
- Test results are logged.

---

#### NFR-081 — Recovery Point Objective (RPO)

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
A maximum acceptable data loss window shall be defined and targeted by the backup strategy.

**Target:** RPO: TBD. To be established during infrastructure planning in V26.

**Acceptance Criteria:**
- The RPO target is documented before V26.
- The backup frequency is set to meet the RPO target.
- The backup strategy is reviewed against the RPO target before production deployment.

---

#### NFR-082 — Recovery Time Objective (RTO)

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
A maximum acceptable recovery time following a data loss event shall be defined.

**Target:** RTO: TBD. To be established during infrastructure planning in V26.

**Acceptance Criteria:**
- The RTO target is documented before V26.
- A restoration procedure is documented and timed against the RTO target.
- The restoration procedure is tested before production deployment.

---

#### NFR-083 — Configuration Backup

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
All platform configuration (environment configuration, ingestion schedules, access control rules) shall be recoverable following infrastructure failure.

**Acceptance Criteria:**
- Platform configuration is version-controlled (where not secret) or backed up.
- A recovery procedure for configuration restoration is documented.

---

#### NFR-084 — Data Integrity Verification

**Category:** Disaster Recovery
**Priority:** P1 — High
**Description:**
Following a restoration from backup, the platform shall be able to verify the integrity and completeness of restored data.

**Acceptance Criteria:**
- A data integrity check procedure is documented.
- The check verifies record counts, schema integrity, and a sample of key constraints defined in `DATA_CONTRACTS.md`.
- Integrity check results are logged.

---

### Category 12 — Data Quality

---

#### NFR-085 — Data Completeness Validation

**Category:** Data Quality
**Priority:** P0 — Critical
**Description:**
The platform shall validate that ingested market data is complete relative to the expected trading calendar for the instrument's exchange. Missing trading days are detected and recorded.

**Acceptance Criteria:**
- Ingestion pipeline compares received bars against the expected trading calendar.
- Missing bars are recorded in a data quality report.
- Missing bars are never silently filled with estimated values without explicit documentation.

---

#### NFR-086 — Data Correctness Validation

**Category:** Data Quality
**Priority:** P0 — Critical
**Description:**
The platform shall validate that ingested OHLCV values satisfy basic financial data integrity constraints.

**Required Checks:**
- `high ≥ low`
- `high ≥ open`
- `high ≥ close`
- `open > 0`, `high > 0`, `low > 0`, `close > 0`
- `volume ≥ 0`

**Acceptance Criteria:**
- All listed checks run automatically on every ingested record.
- Records failing validation are flagged and not accepted into the primary data store as valid.
- Validation failures are logged and surfaced in the data quality report.

---

#### NFR-087 — Duplicate Detection

**Category:** Data Quality
**Priority:** P0 — Critical
**Description:**
The platform shall detect and prevent duplicate records entering the data store. The canonical uniqueness key for OHLCV data is `(symbol, exchange, timestamp, adjustment_type)`.

**Acceptance Criteria:**
- The storage layer enforces uniqueness on the OHLCV composite key.
- Duplicate ingestion attempts are detected and handled idempotently (not inserted as duplicates).
- Duplicate detection runs before any write operation.

---

#### NFR-088 — Timestamp Integrity

**Category:** Data Quality
**Priority:** P0 — Critical
**Description:**
All timestamps stored by the platform shall be in UTC. No ambiguous, offset-naive, or local-timezone timestamps are stored in production.

**Acceptance Criteria:**
- Ingestion converts all provider timestamps to UTC before storage.
- Schema validation enforces UTC-formatted timestamps.
- Time zone conversion errors are detected and logged.

---

#### NFR-089 — Statistical Anomaly Detection

**Category:** Data Quality
**Priority:** P1 — High
**Description:**
The platform shall flag statistically anomalous OHLCV values that may indicate data errors, feed issues, or corporate action events.

**Acceptance Criteria:**
- An outlier detection algorithm runs on each ingestion batch.
- Flagged records are marked with an anomaly indicator and a reason code.
- Anomalous records are retained in storage but excluded from analytical computations unless explicitly included by the user.
- The detection methodology is documented.

---

#### NFR-090 — Stale Data Detection

**Category:** Data Quality
**Priority:** P1 — High
**Description:**
The platform shall detect and surface stale data — data that has not been updated within the expected ingestion schedule for the instrument.

**Acceptance Criteria:**
- The last successful ingestion timestamp per instrument is tracked.
- Data is considered stale when it exceeds a configurable freshness threshold.
- Stale data status is surfaced in API responses for affected instruments.
- Staleness does not cause an error for endpoints that serve historical data only.

---

#### NFR-091 — Symbol Validity

**Category:** Data Quality
**Priority:** P1 — High
**Description:**
The platform shall maintain a validated list of supported instrument symbols. Data stored under an unrecognized symbol shall not be accepted.

**Acceptance Criteria:**
- Ingestion validates the symbol against the instrument catalogue before storing data.
- Attempts to ingest data for an unsupported symbol are rejected and logged.
- Symbol validation errors are included in the data quality report.

---

#### NFR-092 — Corporate Action Consistency

**Category:** Data Quality
**Priority:** P1 — High
**Description:**
Corporate action adjustments (splits, dividends) shall be applied consistently across all records for an affected instrument. Partial or inconsistent adjustments are treated as data quality violations.

**Acceptance Criteria:**
- Adjustment type is recorded on every record.
- When adjustment data changes for an instrument, all historical records for that instrument are flagged for re-adjustment.
- Mixed adjustment types within a single computation are detected and blocked.

---

#### NFR-093 — Feature Computation Data Quality Gate

**Category:** Data Quality
**Priority:** P0 — Critical
**Description:**
Feature computation shall not proceed on data that has failed quality validation. Invalid input data shall produce an invalid feature record — not a silently incorrect feature value.

**Acceptance Criteria:**
- Feature computation checks input data validity before processing.
- Records with `is_valid = false` in the feature output schema are produced when input data is invalid.
- Invalid feature records are not used as inputs to regime detection without explicit handling.

---

### Category 13 — Auditability

---

#### NFR-094 — Analysis Output Provenance

**Category:** Auditability
**Priority:** P0 — Critical
**Description:**
Every platform analysis output (feature values, regime labels, risk metrics, backtest results) shall be fully traceable to its exact inputs and configuration. An operator or researcher shall be able to reproduce any output given the provenance record.

**Required Provenance Fields:**
- Input dataset version fingerprint
- Algorithm/model ID and version
- Feature set ID and version (where applicable)
- Parameter set (full configuration snapshot)
- Execution timestamp
- Software/platform version

**Acceptance Criteria:**
- All listed provenance fields are stored with every analysis output record.
- A reproduction test verifies that re-executing with stored provenance metadata produces identical results.

---

#### NFR-095 — API Access Audit Log

**Category:** Auditability
**Priority:** P1 — High
**Description:**
All authenticated API requests shall be logged in an access audit log with sufficient detail to support security investigation and operational review.

**Required Fields:** User identity, HTTP method, path, status code, timestamp, request ID, client IP address.

**Acceptance Criteria:**
- Access audit logs are produced for all authenticated requests.
- Access audit logs are structured and parseable.
- Audit logs are retained for a period defined in the data retention policy (see OQ-006).

---

#### NFR-096 — Administrative Action Audit Log

**Category:** Auditability
**Priority:** P1 — High
**Description:**
All administrative actions (user creation, role changes, API key management, configuration changes) shall be logged in an administrative audit trail.

**Required Fields:** Administrator identity, action type, affected resource, previous state (where applicable), new state, timestamp.

**Acceptance Criteria:**
- All listed administrative events produce audit log entries.
- Audit log entries are immutable — they cannot be deleted by any application-level user.
- Audit logs are accessible to administrators via the platform.

---

#### NFR-097 — Experiment Reproducibility Audit

**Category:** Auditability
**Priority:** P0 — Critical
**Description:**
Every parameterized research experiment shall produce an audit record sufficient to reproduce the experiment independently at a later date.

**Acceptance Criteria:**
- Experiment audit records are stored and retrievable by experiment ID.
- The audit record contains all provenance fields from NFR-094.
- A reproducibility test is included in the test suite validating that stored audit records produce identical results on re-execution.

---

#### NFR-098 — Backtest Configuration Audit

**Category:** Auditability
**Priority:** P0 — Critical
**Description:**
Every backtest run shall store its complete configuration in a form sufficient to reproduce the result independently.

**Required Configuration Elements:** Strategy ID and version, strategy parameters, universe, date range, cost model configuration, initial capital, dataset version, regime run ID (if regime attribution used), execution timestamp, platform version.

**Acceptance Criteria:**
- All listed configuration elements are stored with every backtest result.
- A backtest reproduction test verifies that stored configuration produces identical results.

---

### Category 14 — Compliance & Financial Disclaimer

---

#### NFR-099 — No Guaranteed Financial Outcomes

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
No platform output, UI surface, API response, or documentation shall represent analytical results as guaranteed financial outcomes, returns, or predictions.

**Acceptance Criteria:**
- No platform text claims guaranteed returns or predictions.
- Backtest results include a disclaimer that historical performance does not guarantee future results.
- All performance metric displays include appropriate analytical caveats.
- This requirement is tested through content review during each web platform release.

---

#### NFR-100 — No Personalized Investment Advice

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
The platform — including the AI Research Assistant — shall not construct or deliver personalized investment advice tailored to an individual user's financial situation, goals, or risk tolerance.

**Acceptance Criteria:**
- No API response or web platform surface constructs a personalized investment recommendation.
- The AI assistant explicitly declines to provide investment advice when prompted.
- System prompting for the AI assistant enforces this prohibition.
- Automated tests verify the AI assistant's refusal of investment advice prompts before V21.

---

#### NFR-101 — Uncertainty Communication

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
All probabilistic platform outputs (regime labels, confidence scores, risk estimates) shall be presented alongside their associated uncertainty measures. The platform shall not present probabilistic results as deterministic facts.

**Acceptance Criteria:**
- Regime outputs always display confidence scores alongside regime labels.
- AI assistant responses include uncertainty qualifications for probabilistic claims.
- Risk metrics display their confidence levels and assumptions.
- Uncertainty is not omissible from primary output surfaces.

---

#### NFR-102 — Observation vs. Interpretation Distinction

**Category:** Compliance & Financial Disclaimer
**Priority:** P1 — High
**Description:**
The platform shall distinguish between observed historical facts (data from validated sources) and generated interpretations (model outputs, AI-generated explanations).

**Acceptance Criteria:**
- API responses clearly label model-generated outputs as such.
- AI assistant responses distinguish cited platform data from generated interpretation.
- UI design separates factual data displays from model/AI-generated content.

---

#### NFR-103 — No Fabricated Market Information

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
No platform component shall generate, present, or store market information — prices, returns, regime labels, risk metrics — that is not derived from validated, sourced market data.

**Acceptance Criteria:**
- All stored market data records reference a validated data source identifier.
- The AI assistant is prevented from generating market facts not grounded in platform data.
- Automated tests verify that the AI assistant does not hallucinate market data.

---

#### NFR-104 — Financial Disclaimer Visibility

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
A financial disclaimer shall be displayed on all primary analytical output surfaces of the web platform and included in relevant API response metadata.

**Disclaimer Content (minimum):** *"This platform provides market research and analytics tools for informational purposes only. It does not provide financial advice, investment recommendations, or any guarantee of financial returns. Past performance does not guarantee future results. Users are solely responsible for their own investment decisions."*

**Acceptance Criteria:**
- The disclaimer is present on the web platform home page, regime dashboard, risk analytics page, and backtest results page.
- The disclaimer is not dismissible in a way that removes it from the page entirely.
- A disclaimer acknowledgment is included in the API terms of use documentation.

---

#### NFR-105 — Open-Source License Compliance

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
RegimeX shall be distributed under an open-source license that is declared in the repository. All dependencies shall have licenses compatible with the chosen RegimeX license.

**Target:** License selection: TBD (see OQ-010). Must be decided before V04.

**Acceptance Criteria:**
- A LICENSE file is present at the repository root before V04.
- Dependency license compatibility is verified by an automated tool in CI.
- The chosen license is documented in contributing guidelines.

---

#### NFR-106 — No Unverified Regulatory Claims

**Category:** Compliance & Financial Disclaimer
**Priority:** P0 — Critical
**Description:**
The platform shall not claim regulatory compliance (e.g., SEC registration, FCA authorization, MiFID II compliance) unless such compliance has been formally established.

**Acceptance Criteria:**
- No marketing copy, documentation, or UI surfaces claim regulatory authorization without verification.
- Regulatory compliance claims are reviewed by a qualified advisor before publication. Process: TBD.

---

### Category 15 — Operational Constraints

---

#### NFR-107 — External Data Provider Rate Limits

**Category:** Operational Constraints
**Priority:** P1 — High
**Description:**
The platform shall operate within the rate limits imposed by external market data providers. Ingestion pipelines shall implement provider-specific rate limiting to avoid exceeding provider quotas.

**Acceptance Criteria:**
- Provider adapter implementations include configurable rate limiting parameters.
- Rate limit errors from providers trigger backoff, not immediate retry.
- Rate limit configuration is documented per provider adapter.

---

#### NFR-108 — Data Redistribution Restrictions

**Category:** Operational Constraints
**Priority:** P0 — Critical
**Description:**
The platform shall not publicly redistribute raw market data in a manner that violates the licensing terms of the data source. Self-hosted instances are the operator's responsibility for compliance.

**Acceptance Criteria:**
- Documentation explicitly states that operators are responsible for compliance with their data provider's redistribution terms.
- The platform does not expose bulk data export endpoints that could be used for mass redistribution without explicit operator configuration and acknowledgment.
- This constraint is documented before V05 (Market Data Engine).

---

#### NFR-109 — AI Provider Cost Constraints

**Category:** Operational Constraints
**Priority:** P2 — Medium
**Description:**
The AI Research Assistant shall be designed with awareness of per-request AI provider costs. Requests shall include only the context necessary to ground the response, minimizing token usage.

**Acceptance Criteria:**
- AI provider request context is bounded to a configurable maximum token budget.
- Context retrieval strategies minimize irrelevant data in the grounding payload.
- AI request token usage is logged and monitorable.

---

#### NFR-110 — Computational Resource Limits

**Category:** Operational Constraints
**Priority:** P2 — Medium
**Description:**
Background computation jobs (regime detection, backtesting, feature computation) shall enforce resource limits to prevent runaway jobs from exhausting system resources.

**Acceptance Criteria:**
- Jobs have configurable CPU and memory limits in deployment configuration.
- Jobs that exceed time limits are terminated and recorded as failed.
- Resource limit parameters are configurable without code changes.

---

#### NFR-111 — Public API Abuse Prevention

**Category:** Operational Constraints
**Priority:** P1 — High
**Description:**
The public (unauthenticated) API surface shall be protected against abuse, including automated scraping, denial-of-service, and resource exhaustion.

**Acceptance Criteria:**
- Rate limits are applied to unauthenticated requests by IP address.
- Responses to rate-limited requests include a `Retry-After` header.
- Unauthenticated access is limited to a defined subset of read-only endpoints.

---

#### NFR-112 — Storage Growth Management

**Category:** Operational Constraints
**Priority:** P2 — Medium
**Description:**
The platform shall provide operators with visibility into storage growth and tooling to manage data retention.

**Acceptance Criteria:**
- Storage utilization metrics are available to administrators.
- Data retention policies (see NFR-061) can be enforced through platform tooling.
- Operators are warned before storage approaches capacity limits.

---

#### NFR-113 — Background Job Queue Limits

**Category:** Operational Constraints
**Priority:** P2 — Medium
**Description:**
The background job queue shall enforce a per-user concurrency limit to prevent a single user from monopolizing processing resources.

**Acceptance Criteria:**
- Per-user concurrent job limit is configurable.
- Attempts to exceed the limit return a structured error.
- Queue depth is observable via metrics.

---

## 19. SLO / SLA Policy

### Overview

This section defines the framework for RegimeX's service-level objectives and commitments.

As of V02, the platform is in pre-implementation documentation. **No production SLOs or SLAs are established yet.** All targets referenced in this document are marked as **TBD** and must be finalized through architecture and capacity planning before V26 (Production Deployment).

### Definitions

| Term | Definition |
|------|-----------|
| **SLI** (Service Level Indicator) | A quantitative measure of a specific service behavior (e.g., p95 request latency). |
| **SLO** (Service Level Objective) | An internal target for an SLI (e.g., p95 latency ≤ 500 ms). |
| **SLA** (Service Level Agreement) | An external commitment to a user or customer, usually with consequences for breach. |
| **Error Budget** | The fraction of time/requests that may fall outside the SLO without triggering remediation. |

### Internal SLO Framework

| Category | SLI | SLO Target |
|----------|-----|------------|
| API Availability | Fraction of health check requests returning 200 | TBD — to be established in V26 |
| Interactive API Latency | p95 response time for regime/discovery/risk endpoints | TBD — draft: ≤ 500 ms |
| Web Platform Load | Largest Contentful Paint | ≤ 2.5 s (see NFR-006) |
| Ingestion Reliability | Fraction of scheduled ingestion jobs completing without error | TBD |
| Background Job Completion | Fraction of submitted jobs completing within defined time | TBD |

### External SLA Commitments

> ⚠️ **RegimeX makes no external SLA commitments as of V02.** The platform is open-source and self-hosted. Self-hosting operators are responsible for their own infrastructure SLAs. If a managed offering is introduced in a future volume, SLA terms will be defined and reviewed at that time.

### TBD Targets

The following SLO targets require completion before V26:

| NFR | Target to Define |
|-----|----------------|
| NFR-001 | Interactive API p95 latency |
| NFR-002 | Market data retrieval p95 latency |
| NFR-003 | Feature computation time benchmark |
| NFR-004 | Regime detection time benchmark |
| NFR-005 | Backtest execution time benchmark |
| NFR-007 | Concurrent user capacity |
| NFR-021 | API availability SLO |
| NFR-024 | Recovery time objective |
| NFR-031 | Concurrent background job capacity |
| NFR-079 | Backup frequency |
| NFR-081 | RPO target |
| NFR-082 | RTO target |

---

## 20. NFR Traceability

The NFRs extend the traceability model established in Section 14. The full chain is:

```text
Product Goal (V01/PRODUCT_FOUNDATION.md)
         ↓
Product Principle (V01/PRINCIPLES.md)
         ↓
Functional Requirement (Section 9 — FR-001 to FR-091)
         ↓
Non-Functional Requirement (Section 18 — NFR-001 to NFR-113)
         ↓
Architecture Decision (V03 — ADRs, TBD)
         ↓
Implementation (V04–V21)
         ↓
Test Case (V22 — Testing & Reliability, TBD)
         ↓
Release Validation (V29–V30)
```

### NFR-to-FR Domain Mapping

| NFR Category | Related FR Domains |
|--------------|-------------------|
| Performance (NFR-001–008) | All domains — performance applies universally; especially B (Data), D (Regime), G (Backtest), K (API) |
| Security (NFR-009–020) | K (API Platform), M (Open-Source), L (Developer) |
| Availability (NFR-021–025) | K (API Platform), B (Market Data), I (AI Assistant) |
| Scalability (NFR-026–031) | B (Data), C (Features), D (Regime), G (Backtest), K (API), L (Developer) |
| Reliability (NFR-032–038) | B (Data), C (Features), D (Regime), G (Backtest), H (Research) |
| Observability (NFR-039–048) | All domains — cross-cutting concern |
| Accessibility (NFR-049–056) | J (Web Platform) |
| Privacy (NFR-057–063) | K (API), I (AI Assistant), J (Web Platform) |
| Maintainability (NFR-064–072) | L (Developer), M (Open-Source) |
| Compatibility (NFR-073–078) | J (Web Platform), K (API), L (Developer) |
| Disaster Recovery (NFR-079–084) | B (Market Data), D (Regime), G (Backtest) |
| Data Quality (NFR-085–093) | A (Discovery), B (Market Data), C (Features), D (Regime) |
| Auditability (NFR-094–098) | H (Research), D (Regime), G (Backtest), F (Risk) |
| Compliance & Disclaimer (NFR-099–106) | All user-facing domains |
| Operational Constraints (NFR-107–113) | B (Market Data), I (AI), K (API) |

---

## Disclaimer

RegimeX is an open-source research and analytics platform. It does not provide financial advice, personalized investment recommendations, or any guarantee of financial returns. All platform outputs described in this document are for informational and research purposes only. Users are solely responsible for any decisions made based on platform outputs.

---

*RegimeX — Open-Source Market Intelligence Platform*
*V02 — Enterprise Requirements · SRS Version 0.1 · Status: Draft*
