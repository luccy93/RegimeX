# Module Boundaries & Responsibilities

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

This specification establishes the strict functional boundaries, interface contracts, data ownership, and prohibited responsibilities for each internal domain module in RegimeX.

RegimeX enforces a strict **layered and inward-directed dependency rule**:
- High-level domain logic must never depend on low-level infrastructure, specific database engines, network transports (HTTP), or third-party proprietary vendors.
- Dependencies flow strictly from outer layers (API, CLI, Workers) toward inner domain layers (`regimex.core`, `regimex.data`, `regimex.features`, etc.).
- Circular imports between modules are strictly forbidden and validated in CI.

---

## 2. Module Dependency Hierarchy

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             API / Presentation                              │
│                (regimex.api, regimex.admin, regimex.identity)               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            Orchestration Workflows                          │
│                     (regimex.research, regimex.ai)                          │
└───────────────────┬──────────────────────────────────┬──────────────────────┘
                    │                                  │
┌───────────────────▼──────────────────┐ ┌─────────────▼──────────────────────┐
│           Risk Analytics             │ │         Strategy Backtest          │
│          (regimex.risk)              │ │        (regimex.backtest)          │
└───────────────────┬──────────────────┘ └─────────────┬──────────────────────┘
                    │                                  │
                    └──────────────────┬───────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                             Regime Intelligence                             │
│                  (regimex.regime, regimex.regime.detectors)                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                             Feature Engineering                             │
│                              (regimex.features)                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           Data & Quality Assurance                          │
│                       (regimex.data, regimex.quality)                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                                Core Platform                                │
│                     (regimex.core, regimex.observability)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Market Discovery (`regimex.discovery`)
- **Responsibility:** Maintain the canonical catalogue of supported financial instruments, exchanges, asset classes, sectors, trading calendars, and market holidays.
- **Inputs:** Raw instrument listings, symbol search queries, asset class filters.
- **Outputs:** Canonical `Instrument` definitions, exchange metadata, trading session schedules.
- **Dependencies:** `regimex.core`
- **Owned Data:** Instrument catalogue, exchange schedules, trading holiday tables.
- **Public Interfaces:** `InstrumentCatalog.search(query, asset_class)`, `ExchangeCalendar.is_trading_day(exchange, date)`.
- **Prohibited Responsibilities:** Must not ingest market prices, execute quantitative math, or query external provider APIs directly.

---

### 3.2 Market Data (`regimex.data`)
- **Responsibility:** Ingest, normalize, validate, and store external historical OHLCV market data into the canonical RegimeX format.
- **Inputs:** Ingestion requests with symbol, date range, adjustment type, and provider source.
- **Outputs:** Canonical `OHLCVRecord` streams, dataset version fingerprints.
- **Dependencies:** `regimex.core`, `regimex.discovery`, `regimex.quality`
- **Owned Data:** Canonical historical OHLCV price and volume tables, provider sync logs.
- **Public Interfaces:** `MarketDataProvider.fetch(...)`, `MarketDataRepository.get(symbol, start, end)`, `MarketDataRepository.save(records)`.
- **Prohibited Responsibilities:** Must not calculate mathematical features (volatility, momentum), detect market regimes, or evaluate portfolio strategies.

---

### 3.3 Data Quality (`regimex.quality`)
- **Responsibility:** Enforce integrity, sanity, and completeness constraints on market data and feature inputs before analytical processing.
- **Inputs:** Ingested OHLCV records, exchange calendar specifications, feature vectors.
- **Outputs:** `QualityReport`, validation pass/fail flags, anomaly markers, gap alerts.
- **Dependencies:** `regimex.core`, `regimex.discovery`
- **Owned Data:** Data quality audit logs, anomaly detection threshold parameters.
- **Public Interfaces:** `DataValidator.validate_ohlcv(records, calendar)`, `DataQualityGate.verify(records)`.
- **Prohibited Responsibilities:** Must not mutate or fabricate price data to "fix" gaps; must not perform regime inference.

---

### 3.4 Feature Engineering (`regimex.features`)
- **Responsibility:** Compute mathematical indicators, momentum signals, rolling volatility estimators, and statistical features with strict point-in-time enforcement (zero look-ahead bias).
- **Inputs:** Point-in-time filtered historical OHLCV data, feature parameter configurations.
- **Outputs:** `FeatureValue` series, feature matrices, feature registry metadata.
- **Dependencies:** `regimex.core`, `regimex.data` (read-only repository interface)
- **Owned Data:** Feature definitions, feature parameter schemas, computed feature cache tables.
- **Public Interfaces:** `FeatureRegistry.get(feature_id)`, `FeaturePipeline.compute(feature_set, data, as_of)`.
- **Prohibited Responsibilities:** Must not access data beyond the `as_of` timestamp; must not assign regime classifications or make trading decisions.

---

### 3.5 Regime Detection (`regimex.regime`)
- **Responsibility:** Fit statistical and machine learning models (HMM, GMM, KMeans, Changepoint) to feature matrices and infer underlying market regimes.
- **Inputs:** Standardized feature matrices, detector hyperparameters, model fitting date ranges.
- **Outputs:** Fitted model artifacts, discrete `RegimeLabel` series, regime probabilities (`predict_proba`), model metadata.
- **Dependencies:** `regimex.core`, `regimex.features`
- **Owned Data:** Registered detector algorithms, trained model weights, historical regime inference run records.
- **Public Interfaces:** `RegimeDetector.fit(X)`, `RegimeDetector.predict(X)`, `RegimeDetector.predict_proba(X)`, `RegimeDetectorRegistry`.
- **Prohibited Responsibilities:** Must not calculate risk metrics (VaR/CVaR), simulate order execution, or execute HTTP endpoints.

---

### 3.6 Regime Intelligence (`regimex.regime.intelligence`)
- **Responsibility:** Compute analytical insights from regime timelines, including state transition matrices, regime duration/persistence, and regime-conditional asset behavior.
- **Inputs:** Historical regime classification timelines, corresponding return series.
- **Outputs:** State transition probability matrices, regime persistence statistics, regime characterization summaries.
- **Dependencies:** `regimex.core`, `regimex.regime`
- **Owned Data:** Computed transition matrices, regime statistical profile caches.
- **Public Interfaces:** `RegimeIntelligence.transition_matrix(timeline)`, `RegimeIntelligence.persistence_statistics(timeline)`.
- **Prohibited Responsibilities:** Must not retrain underlying ML models; must not execute backtests.

---

### 3.7 Risk Analytics (`regimex.risk`)
- **Responsibility:** Compute portfolio and asset risk metrics, both unconditional and conditional upon detected market regimes.
- **Inputs:** Asset return series, regime timelines, confidence level parameters ($\alpha$).
- **Outputs:** Value at Risk (VaR), Conditional VaR (CVaR), Maximum Drawdown, drawdown duration, regime-conditional volatility profiles.
- **Dependencies:** `regimex.core`, `regimex.data` (read-only), `regimex.regime` (read-only)
- **Owned Data:** Risk metric definitions, computed historical risk snapshots.
- **Public Interfaces:** `RiskEngine.compute_metrics(returns, regime_timeline, config)`.
- **Prohibited Responsibilities:** Must not manage order books, execute simulated trades, or communicate investment advice.

---

### 3.8 Strategy Backtesting (`regimex.backtest`)
- **Responsibility:** Execute realistic, event-driven historical simulations of quantitative strategies with strict chronologically isolated bars and transaction cost models.
- **Inputs:** Strategy callbacks (`on_bar`), asset price bars, cost model configurations, optional regime timeline for attribution.
- **Outputs:** Simulated order fills, portfolio equity curves, trade logs, risk-adjusted returns (Sharpe, Sortino, Calmar), regime performance attribution.
- **Dependencies:** `regimex.core`, `regimex.data` (read-only), `regimex.regime` (read-only for attribution)
- **Owned Data:** Backtest run configurations, simulated trade logs, performance metrics.
- **Public Interfaces:** `BacktestEngine.run(strategy, universe, date_range, cost_model)`, `RegimeAttributor.attribute(...)`.
- **Prohibited Responsibilities:** Must not look forward in the simulation event loop; must not execute live trades or connect to live brokerages.

---

### 3.9 Research Workspace (`regimex.research`)
- **Responsibility:** Manage end-to-end reproducible research experiments, parameter sweeps, and comparative analysis across datasets, features, models, and backtests.
- **Inputs:** Research parameter sets, experiment configurations, user workspace identifiers.
- **Outputs:** Versioned `ResearchRun` artifacts, experiment comparison reports, data provenance snapshots.
- **Dependencies:** `regimex.core`, `regimex.data`, `regimex.features`, `regimex.regime`, `regimex.risk`, `regimex.backtest`
- **Owned Data:** Research run metadata, experiment configurations, user saved workspace states.
- **Public Interfaces:** `ResearchRunner.execute(run_config)`, `ExperimentRegistry.compare(run_ids)`.
- **Prohibited Responsibilities:** Must not expose public HTTP routes directly; must not bypass domain validation rules.

---

### 3.10 AI Research Assistant (`regimex.ai`)
- **Responsibility:** Provide grounded quantitative analysis, query interpretation, and natural language explanations strictly contextualized by verified platform data.
- **Inputs:** User analytical questions, user session context, verified analytical outputs from core modules.
- **Outputs:** Grounded AI responses with explicit data provenance, confidence metrics, and financial disclaimers.
- **Dependencies:** `regimex.core`, `regimex.regime` (read-only), `regimex.risk` (read-only), `regimex.data` (read-only)
- **Owned Data:** Prompt templates, retrieval grounding schemas, conversation session logs.
- **Public Interfaces:** `AIAssistant.ask(question, session_id)`, `ContextRetriever.build_grounding_context(query)`.
- **Prohibited Responsibilities:** Must never generate ungrounded financial assertions; must strictly decline personalized investment advice; must not execute direct arbitrary database queries.

---

### 3.11 Identity & Access (`regimex.identity`)
- **Responsibility:** Manage user accounts, role-based authorization (RBAC), authentication credential hashing, API keys, and session lifecycle.
- **Inputs:** Credentials, API key issuance requests, session tokens.
- **Outputs:** JWT tokens, hashed API keys, user identity contexts (`UserPrincipal`).
- **Dependencies:** `regimex.core`
- **Owned Data:** User credentials (bcrypt/Argon2 hashed), API key hashes, user role assignments.
- **Public Interfaces:** `Authenticator.authenticate(token_or_key)`, `Authorizer.check_permission(user, permission)`.
- **Prohibited Responsibilities:** Must not manage market data, financial models, or analytics.

---

### 3.12 API Layer (`regimex.api`)
- **Responsibility:** Expose HTTP REST endpoints, validate inbound JSON payloads and query parameters, enforce rate limits, authenticate requests, format standardized JSON envelopes, and handle errors.
- **Inputs:** Inbound HTTP requests (REST, WebSockets).
- **Outputs:** Outbound HTTP responses with standard JSON envelope (`success`, `data`, `meta`, `error`).
- **Dependencies:** `regimex.core`, `regimex.identity`, all domain modules (via application services)
- **Owned Data:** API routing tables, OpenAPI schema specifications.
- **Public Interfaces:** FastAPI application factory `create_app()`, route routers.
- **Prohibited Responsibilities:** Must not contain business or financial calculation logic; acts strictly as an orchestration and transport gateway.

---

### 3.13 Administration (`regimex.admin`)
- **Responsibility:** Provide administrative controls for user management, system configuration, ingestion scheduling, background job monitoring, and audit log inspection.
- **Inputs:** Administrative commands, configuration changes, user role updates.
- **Outputs:** Audit log entries, system status summaries, updated platform settings.
- **Dependencies:** `regimex.core`, `regimex.identity`, `regimex.observability`
- **Owned Data:** Platform configuration parameters, system operational audit logs.
- **Public Interfaces:** `AdminService.update_system_config(...)`, `AdminService.audit_log_query(...)`.
- **Prohibited Responsibilities:** Must not alter historical market data or falsify audit trails.

---

### 3.14 Observability (`regimex.observability`)
- **Responsibility:** Provide platform-wide structured logging, metrics emission, distributed tracing context propagation, and health check endpoints.
- **Inputs:** Application log events, metric counter/timer increments, trace context headers.
- **Outputs:** Structured JSON log streams, Prometheus scrape endpoints, trace spans, health check status (`/health`, `/ready`).
- **Dependencies:** `regimex.core`
- **Owned Data:** Metric definitions, internal health probe state.
- **Public Interfaces:** `logger.info(...)`, `metrics.counter_increment(...)`, `tracer.span(...)`, `HealthChecker.check()`.
- **Prohibited Responsibilities:** Must not block business execution threads if telemetry sinks are slow or unavailable.
