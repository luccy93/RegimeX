# Module Design

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

RegimeX source code is organized as a Python monorepo under `src/regimex/`. Each subdirectory is an independently testable module with clearly defined responsibilities and boundaries.

```text
src/regimex/
├── core/         ← Shared types, base classes, utilities
├── data/         ← Market data ingestion, storage, validation
├── features/     ← Feature engineering and feature registry
├── regime/       ← Regime detection algorithms and pipeline
├── risk/         ← Risk analytics engine
├── backtest/     ← Event-driven backtesting engine
├── research/     ← Research workspace and reproducibility
├── ai/           ← AI research assistant
├── api/          ← FastAPI application
└── web/          ← Web platform (future, V18+)
```

---

## Module: `core`

**Responsibility:** Shared infrastructure — base types, exceptions, configuration management, logging setup, and utilities used across all other modules.

**Contents:**
- `types.py` — canonical data types: `Symbol`, `Exchange`, `AssetClass`, `AdjustmentType`, `Timeframe`
- `config.py` — typed settings loaded from environment variables (using Pydantic Settings)
- `logging.py` — structured logging setup (structlog)
- `exceptions.py` — base exception hierarchy: `RegimeXError`, `DataError`, `FeatureError`, `RegimeError`
- `utils.py` — shared utilities: date helpers, fingerprinting, validation utilities
- `constants.py` — platform-wide constants

**Dependencies:** None (no imports from other `regimex` modules)

**Key rule:** `core` must never import from `data`, `features`, `regime`, or any other `regimex` module.

---

## Module: `data`

**Responsibility:** All market data interaction — provider abstraction, ingestion orchestration, data validation, storage, and retrieval.

**Contents:**
- `providers/`
  - `base.py` — abstract `MarketDataProvider` interface
  - `yahoo_finance.py` — Yahoo Finance adapter (V05, first concrete implementation)
- `schema.py` — OHLCV Pydantic model conforming to `DC-OHLCV` data contract
- `ingestion.py` — ingestion pipeline: fetch → validate → store
- `validator.py` — gap detection, outlier flagging, schema validation
- `repository.py` — abstract `MarketDataRepository` interface
- `storage/`
  - `base.py` — abstract storage interface
  - `postgres.py` — PostgreSQL + TimescaleDB implementation (V06)
- `quality.py` — data quality report generation

**Dependencies:** `core`

**Key rules:**
- Only `data` module may call external data provider APIs
- All other modules query market data through `MarketDataRepository`, not raw storage

---

## Module: `features`

**Responsibility:** Quantitative feature engineering — the feature registry, feature computation, and point-in-time enforcement.

**Contents:**
- `registry.py` — `FeatureRegistry`: discovers and catalogues all registered features
- `base.py` — abstract `Feature` interface: `compute(data, timestamp) → FeatureValue`
- `schema.py` — `FeatureValue` Pydantic model conforming to `DC-FEATURE` data contract
- `pipeline.py` — `FeaturePipeline`: applies a collection of features to a dataset
- `bias_checker.py` — look-ahead bias detection tool
- `library/`
  - `returns.py` — return features (1d, 5d, 21d, 63d)
  - `volatility.py` — volatility features (realized, EWMA, Parkinson, Yang-Zhang)
  - `momentum.py` — RSI, ATR, Bollinger Band width, momentum
  - `volume.py` — volume ratio, volume trends
  - `statistical.py` — rolling autocorrelation, skewness, kurtosis

**Dependencies:** `core`, `data` (read-only, via `MarketDataRepository`)

**Key rule:** Feature computation at timestamp T must never use data with timestamp > T.

---

## Module: `regime`

**Responsibility:** Regime detection algorithms, detection pipeline, regime output storage, and regime intelligence analytics.

**Contents:**
- `detectors/`
  - `base.py` — abstract `RegimeDetector` interface: `fit()`, `predict()`, `predict_proba()`, `metadata()`
  - `hmm.py` — Hidden Markov Model detector (V08)
  - `gmm.py` — Gaussian Mixture Model detector (V10)
  - `changepoint.py` — PELT/BOCPD changepoint detector (V10)
  - `ensemble.py` — ensemble detector (V11)
- `registry.py` — `RegimeDetectorRegistry`: catalogues available algorithms
- `schema.py` — `RegimeOutput` Pydantic model conforming to `DC-REGIME` data contract
- `pipeline.py` — orchestrates detection runs: features → detector → regime output → storage
- `repository.py` — abstract `RegimeRepository` interface
- `intelligence/`
  - `timeline.py` — regime timeline construction
  - `transitions.py` — transition matrix computation
  - `statistics.py` — regime-conditional asset statistics
  - `persistence.py` — regime persistence metrics

**Dependencies:** `core`, `features` (for feature pipeline), `data` (read-only)

**Key rule:** All detectors must implement `RegimeDetector` interface. No algorithm may use future data.

---

## Module: `risk`

**Responsibility:** Risk metric computation — regime-aware and unconditional risk analytics.

**Contents:**
- `metrics/`
  - `volatility.py` — close-to-close, Parkinson, Yang-Zhang, EWMA volatility
  - `drawdown.py` — maximum drawdown, duration, recovery time
  - `var.py` — VaR and CVaR (historical simulation, parametric)
  - `correlation.py` — rolling and regime-conditional correlation matrices
- `schema.py` — `RiskMetric` Pydantic model conforming to `DC-RISK` data contract
- `engine.py` — `RiskEngine`: orchestrates risk metric computation
- `repository.py` — abstract `RiskRepository` interface

**Dependencies:** `core`, `data` (read-only), `regime` (for regime-conditional computation, read-only)

---

## Module: `backtest`

**Responsibility:** Event-driven strategy backtesting with realistic cost models and regime attribution.

**Contents:**
- `engine.py` — `BacktestEngine`: event loop, portfolio management
- `strategy.py` — abstract `Strategy` interface: `on_bar()`, `on_signal()`
- `portfolio.py` — `Portfolio`: positions, cash, equity curve
- `orders.py` — `Order`, `Fill`: market and limit order types
- `costs/`
  - `base.py` — abstract `CostModel` interface
  - `flat_commission.py` — flat per-trade commission
  - `percentage.py` — percentage-of-trade-value commission
  - `spread.py` — bid-ask spread model
- `walk_forward.py` — walk-forward validation framework
- `schema.py` — `BacktestResult` Pydantic model conforming to `DC-BACKTEST` data contract
- `analytics.py` — performance metric computation (Sharpe, Sortino, Calmar, etc.)
- `attribution.py` — regime performance attribution

**Dependencies:** `core`, `data` (read-only), `regime` (read-only, for attribution)

**Key rule:** Strategy `on_bar()` must never receive data beyond the current bar timestamp.

---

## Module: `research`

**Responsibility:** Reproducible research run management — parameterized analysis, run storage, and result comparison.

**Contents:**
- `run.py` — `ResearchRun`: encapsulates a parameterized analysis configuration
- `runner.py` — `ResearchRunner`: executes and records research runs
- `repository.py` — run storage and retrieval
- `comparison.py` — multi-run comparison utilities
- `notebook.py` — Jupyter integration helpers

**Dependencies:** `core`, `data`, `features`, `regime`, `risk`, `backtest`

---

## Module: `ai`

**Responsibility:** Grounded AI research assistant with data retrieval, provenance tracking, and anti-hallucination safeguards.

**Contents:**
- `assistant.py` — `AIResearchAssistant`: main entry point
- `retriever.py` — retrieves relevant RegimeX data for grounding AI responses
- `prompt.py` — prompt templates enforcing uncertainty disclosure and source citation
- `response.py` — `AIResponse` schema including provenance references
- `safeguards.py` — anti-hallucination validation: rejects claims not grounded in data

**Dependencies:** `core`, `regime`, `risk`, `data` (read-only for grounding)

---

## Module: `api`

**Responsibility:** FastAPI REST API — request routing, authentication, rate limiting, OpenAPI docs, and error handling.

**Contents:**
- `app.py` — FastAPI application factory
- `routers/`
  - `instruments.py` — market discovery endpoints
  - `data.py` — market data endpoints
  - `features.py` — feature endpoints
  - `regime.py` — regime detection and intelligence endpoints
  - `risk.py` — risk metrics endpoints
  - `backtest.py` — backtesting endpoints
  - `jobs.py` — async job status endpoints
  - `health.py` — health and readiness endpoints
- `middleware/`
  - `auth.py` — API key + JWT authentication
  - `rate_limit.py` — per-user rate limiting
  - `logging.py` — request/response logging
- `schemas/` — Pydantic request/response models (separate from domain schemas)
- `errors.py` — error handler and error response formatting
- `dependencies.py` — FastAPI dependency injection

**Dependencies:** `core`, all intelligence modules (read-only)

**Key rule:** `api` module never performs business logic. It delegates to the appropriate module and formats the response.

---

## Module Dependency Graph

```text
core ← (no dependencies)
 ↑
data ← core
 ↑
features ← core, data
 ↑
regime ← core, features, data
 ↑
risk ← core, data, regime
 ↑
backtest ← core, data, regime
 ↑
research ← core, data, features, regime, risk, backtest
 ↑
ai ← core, regime, risk, data
 ↑
api ← core, data, features, regime, risk, backtest, research, ai
```

**Rules:**
- Dependencies flow upward only — no circular dependencies permitted
- `data` may not import from `features`, `regime`, `risk`, or `backtest`
- `features` may not import from `regime`, `risk`, or `backtest`
- `regime` may not import from `risk` or `backtest`
