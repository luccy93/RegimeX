# Functional Requirements

**RegimeX — Open-Source Market Intelligence Platform**

> All requirements in this document describe planned future capabilities. None are implemented in V01 or V02. Implementation begins in V04+.

---

## FR-DISC — Market Discovery

| ID | Requirement | Priority |
|----|------------|---------|
| FR-DISC-001 | The platform shall provide a searchable catalogue of all supported markets and instruments. | High |
| FR-DISC-002 | The catalogue shall include instrument metadata: symbol, name, exchange, asset class, base currency, and data availability range. | High |
| FR-DISC-003 | Users shall be able to filter the catalogue by asset class (equity, crypto, commodity, forex). | High |
| FR-DISC-004 | Users shall be able to filter by market geography (US, India, global). | Medium |
| FR-DISC-005 | The platform shall display data availability status per instrument (date range, provider, last updated). | High |
| FR-DISC-006 | The discovery API shall support fuzzy symbol search. | Medium |
| FR-DISC-007 | The platform shall clearly indicate when an instrument is not yet supported. | High |

---

## FR-DATA — Market Data

| ID | Requirement | Priority |
|----|------------|---------|
| FR-DATA-001 | The platform shall ingest historical OHLCV (Open, High, Low, Close, Volume) data for supported instruments. | Critical |
| FR-DATA-002 | Ingested data shall conform to the canonical OHLCV schema defined in `DATA_CONTRACTS.md`. | Critical |
| FR-DATA-003 | The ingestion pipeline shall be provider-independent — switching data providers shall not require changes to business logic. | Critical |
| FR-DATA-004 | The platform shall support at least one open market data provider at launch (V05). | Critical |
| FR-DATA-005 | The platform shall detect and log data gaps (missing trading days or bars). | High |
| FR-DATA-006 | The platform shall detect and flag statistical outliers in ingested price data. | High |
| FR-DATA-007 | Ingestion shall be idempotent — re-running ingestion for the same symbol and date range shall not produce duplicate records. | Critical |
| FR-DATA-008 | All ingested data shall be timestamped with the ingestion time and the data source version. | High |
| FR-DATA-009 | The platform shall support adjusted and unadjusted OHLCV data, with adjustment type recorded explicitly. | High |
| FR-DATA-010 | Data quality checks shall run automatically after every ingestion batch and produce a quality report. | High |
| FR-DATA-011 | The platform shall record and expose the data lineage for every stored record. | Medium |
| FR-DATA-012 | The platform shall support dataset versioning — each dataset snapshot is identified by a fingerprint. | High |
| FR-DATA-013 | Users shall be able to export market data in CSV and Parquet formats. | Medium |
| FR-DATA-014 | The platform shall handle corporate actions (splits, dividends) with explicit documentation of the handling strategy. | High |

---

## FR-FE — Feature Engineering

| ID | Requirement | Priority |
|----|------------|---------|
| FR-FE-001 | The platform shall provide a feature registry: a discoverable catalogue of all available quantitative features. | Critical |
| FR-FE-002 | Every feature in the registry shall have documentation covering: description, inputs, outputs, computation method, assumptions, and look-ahead bias status. | Critical |
| FR-FE-003 | All feature computation shall be strictly point-in-time — features computed for timestamp T shall use only data available at or before T. | Critical |
| FR-FE-004 | The platform shall include a baseline technical feature library: returns (1d, 5d, 21d, 63d), realized volatility (rolling), EWMA volatility, volume ratio, RSI, ATR, Bollinger Band width, momentum. | High |
| FR-FE-005 | The platform shall include statistical features: rolling autocorrelation, rolling skewness, rolling kurtosis, rolling correlation between assets. | High |
| FR-FE-006 | Features shall be versioned — a feature identified by name and version always produces the same output given the same inputs. | Critical |
| FR-FE-007 | The platform shall provide a look-ahead bias detection tool that can validate any feature implementation against synthetic data. | Critical |
| FR-FE-008 | Users shall be able to compose feature pipelines from the feature registry. | Medium |
| FR-FE-009 | Feature computation shall be parallelizable across symbols and date ranges. | Medium |
| FR-FE-010 | The platform shall support external feature contributions through a defined `Feature` interface. | Medium |

---

## FR-RD — Regime Detection

| ID | Requirement | Priority |
|----|------------|---------|
| FR-RD-001 | The platform shall provide a standard `RegimeDetector` interface that all detection algorithms must implement. | Critical |
| FR-RD-002 | The `RegimeDetector` interface shall expose: `fit()`, `predict()`, `predict_proba()`, and `metadata()` methods. | Critical |
| FR-RD-003 | The platform shall implement a Hidden Markov Model (HMM) regime detector as the first concrete algorithm. | Critical |
| FR-RD-004 | The platform shall implement a Gaussian Mixture Model (GMM) regime detector. | High |
| FR-RD-005 | The platform shall implement at least one changepoint detection algorithm (e.g., PELT or BOCPD). | High |
| FR-RD-006 | The platform shall implement an ensemble regime detector combining multiple algorithms. | High |
| FR-RD-007 | All regime detection outputs shall conform to the regime output schema defined in `DATA_CONTRACTS.md`. | Critical |
| FR-RD-008 | Regime outputs shall always include: regime label, confidence score, algorithm name, algorithm version, and parameter set. | Critical |
| FR-RD-009 | Algorithm parameters shall be configurable via structured configuration files. | High |
| FR-RD-010 | The platform shall support configurable number of regimes (K). | High |
| FR-RD-011 | All regime detection algorithms shall be documented with their assumptions and known failure modes. | Critical |
| FR-RD-012 | The platform shall persist regime detection outputs with full metadata for reproducibility. | Critical |
| FR-RD-013 | The regime detection pipeline shall support batch (historical) and point-in-time (current regime) computation modes. | High |

---

## FR-RI — Regime Intelligence

| ID | Requirement | Priority |
|----|------------|---------|
| FR-RI-001 | The platform shall construct a regime timeline from detection outputs — a complete ordered record of regime periods. | Critical |
| FR-RI-002 | The platform shall compute regime persistence metrics: mean duration, standard deviation, median duration per regime label. | High |
| FR-RI-003 | The platform shall compute a regime transition matrix: probability of transitioning from regime A to regime B. | High |
| FR-RI-004 | The platform shall compute regime-conditional asset statistics: returns, volatility, Sharpe ratio, and max drawdown per regime. | High |
| FR-RI-005 | The platform shall export the regime history in JSON and CSV formats. | Medium |
| FR-RI-006 | The platform shall provide structured data outputs for regime timeline visualization (for downstream chart rendering). | Medium |
| FR-RI-007 | The platform shall support querying: "what regime was active on date D for symbol S with algorithm A?" | High |

---

## FR-RISK — Risk Analytics

| ID | Requirement | Priority |
|----|------------|---------|
| FR-RISK-001 | The platform shall compute realized volatility using at least three estimators: close-to-close, Parkinson, Yang-Zhang. | High |
| FR-RISK-002 | The platform shall compute rolling drawdown: drawdown magnitude, duration, and recovery time. | High |
| FR-RISK-003 | The platform shall compute Value at Risk (VaR) using historical simulation. | High |
| FR-RISK-004 | The platform shall compute Conditional VaR (CVaR / Expected Shortfall). | High |
| FR-RISK-005 | The platform shall compute rolling pairwise correlation matrices for a configurable asset universe. | High |
| FR-RISK-006 | All risk metrics shall be computable conditional on regime — risk metrics output per regime label. | Critical |
| FR-RISK-007 | All risk computations shall explicitly document their assumptions (window length, confidence level, estimator choice). | Critical |
| FR-RISK-008 | Risk outputs shall conform to the risk metrics schema defined in `DATA_CONTRACTS.md`. | High |

---

## FR-BT — Backtesting

| ID | Requirement | Priority |
|----|------------|---------|
| FR-BT-001 | The backtesting engine shall use an event-driven simulation loop executing bar-by-bar. | Critical |
| FR-BT-002 | The platform shall provide a `Strategy` interface with `on_bar()` and `on_signal()` hooks. | Critical |
| FR-BT-003 | The engine shall support configurable transaction cost models: flat commission, percentage commission, bid-ask spread. | Critical |
| FR-BT-004 | The engine shall support market and limit order types at minimum. | High |
| FR-BT-005 | The engine shall maintain a portfolio state: positions, cash balance, and equity curve. | Critical |
| FR-BT-006 | The platform shall support walk-forward validation: the engine shall partition data into in-sample and out-of-sample segments. | Critical |
| FR-BT-007 | Backtest results shall include an equity curve, drawdown series, and trade log. | Critical |
| FR-BT-008 | Backtest results shall include performance attribution by regime. | High |
| FR-BT-009 | The engine shall explicitly prevent look-ahead bias in strategy signal generation. | Critical |
| FR-BT-010 | Backtest results shall conform to the backtest result schema defined in `DATA_CONTRACTS.md`. | High |
| FR-BT-011 | Backtest configurations (strategy params, cost model, date range) shall be reproducible from a stored configuration file. | Critical |

---

## FR-RW — Research Workspace

| ID | Requirement | Priority |
|----|------------|---------|
| FR-RW-001 | The platform shall support parameterized analysis runs — re-running an analysis with different parameters without modifying source code. | High |
| FR-RW-002 | Every analysis run shall record its full configuration, data version fingerprints, and software versions. | Critical |
| FR-RW-003 | The platform shall support Jupyter notebook integration for interactive quantitative research. | High |
| FR-RW-004 | Analysis results shall be persistable and retrievable by run ID. | High |
| FR-RW-005 | The platform shall provide utilities for comparing results across multiple parameterized runs. | Medium |

---

## FR-AI — AI Research Assistant

| ID | Requirement | Priority |
|----|------------|---------|
| FR-AI-001 | The AI assistant shall answer natural language questions about market regimes using platform data as its grounding source. | High |
| FR-AI-002 | Every AI response shall cite the specific platform data (regime labels, dates, risk metrics) that supports each claim. | Critical |
| FR-AI-003 | The AI assistant shall explicitly state its confidence level and limitations in every response. | Critical |
| FR-AI-004 | The AI assistant shall refuse to generate market signals or predictions not grounded in platform data. | Critical |
| FR-AI-005 | The AI assistant shall not provide personalized financial advice. | Critical |
| FR-AI-006 | The AI assistant shall maintain conversation history within a research session. | Medium |
| FR-AI-007 | Response provenance (data sources used) shall be displayable alongside every AI response. | High |

---

## FR-API — API Platform

| ID | Requirement | Priority |
|----|------------|---------|
| FR-API-001 | The platform shall expose a versioned REST API (v1/ prefix at minimum). | Critical |
| FR-API-002 | The API shall provide endpoints for: market discovery, market data retrieval, feature retrieval, regime query, risk metrics query, backtest execution and results. | Critical |
| FR-API-003 | All API responses shall conform to a consistent response envelope schema. | Critical |
| FR-API-004 | All API errors shall conform to the error response schema defined in `API_CONTRACTS.md`. | Critical |
| FR-API-005 | The API shall support API key authentication for all non-public endpoints. | Critical |
| FR-API-006 | The API shall implement rate limiting per authenticated user. | High |
| FR-API-007 | The API shall expose auto-generated OpenAPI documentation. | High |
| FR-API-008 | The API shall include health and readiness endpoints. | Critical |
| FR-API-009 | The API shall support pagination for list endpoints. | High |

---

## FR-WEB — Web Platform

| ID | Requirement | Priority |
|----|------------|---------|
| FR-WEB-001 | The web platform shall be accessible without user registration (public read-only access to market regime data). | High |
| FR-WEB-002 | The web platform shall provide a current regime dashboard: regime label, confidence, duration, and recent transition history. | Critical |
| FR-WEB-003 | The platform shall provide interactive price and volatility charts for supported instruments. | High |
| FR-WEB-004 | The platform shall provide a regime timeline visualization for historical regime exploration. | High |
| FR-WEB-005 | The platform shall display risk metrics per instrument and per regime. | High |
| FR-WEB-006 | Authenticated users shall be able to configure and save custom regime detection parameters. | Medium |
| FR-WEB-007 | The web platform shall meet WCAG 2.1 AA accessibility requirements. | High |
| FR-WEB-008 | The web platform shall be responsive and usable on desktop and tablet screen sizes. | High |

---

## FR-DEV — Developer Platform

| ID | Requirement | Priority |
|----|------------|---------|
| FR-DEV-001 | The platform shall provide a Python SDK for programmatic access to all API capabilities. | High |
| FR-DEV-002 | The SDK shall be fully type-annotated and documented. | High |
| FR-DEV-003 | The platform shall provide a plugin interface enabling third-party regime detection algorithms. | High |
| FR-DEV-004 | The platform shall provide a plugin interface enabling third-party market data providers. | High |
| FR-DEV-005 | Plugin interfaces shall be stable across minor versions. | High |
| FR-DEV-006 | The platform shall support full self-hosting without proprietary cloud service dependencies. | Critical |
