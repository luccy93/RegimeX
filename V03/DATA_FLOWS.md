# Data Flows

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

This document describes the end-to-end data flow through the RegimeX platform — from raw market data ingestion through feature engineering, regime detection, risk computation, backtesting, and API delivery.

---

## Flow 1: Market Data Ingestion

```text
External Provider API
        │
        ▼
  MarketDataProvider.fetch(symbol, start, end)
        │  (provider-specific HTTP/file logic isolated here)
        ▼
  Raw OHLCV Records (provider format)
        │
        ▼
  Provider Adapter (normalize to DC-OHLCV schema)
        │
        ▼
  DataValidator
  ├── Schema validation (field types, constraints)
  ├── Gap detection (missing trading days)
  ├── Outlier flagging (price/volume anomalies)
  └── Quality report generation
        │
        ▼
  MarketDataRepository.save(ohlcv_records)
        │  (idempotent write: upsert on unique key)
        ▼
  PostgreSQL + TimescaleDB
        │
        ▼
  Ingestion Audit Log (symbol, date_range, provider, quality_report, ingested_at)
```

**Key invariants:**
- Provider-specific logic is isolated in the adapter
- Validation runs before any data is written
- Writes are idempotent and atomic
- Dataset version fingerprint is computed and stored with each batch

---

## Flow 2: Feature Computation

```text
MarketDataRepository.get(symbol, start, end)
        │  (point-in-time data snapshot)
        ▼
  FeaturePipeline.compute(feature_set, data, as_of_timestamp)
        │
        ├── Feature 1: returns_1d_v1
        │       └── compute(data.loc[:as_of_timestamp]) → FeatureValue
        ├── Feature 2: realized_vol_21d_v1
        │       └── compute(data.loc[:as_of_timestamp]) → FeatureValue
        └── Feature N: ...
        │
        ▼
  [FeatureValue, FeatureValue, ..., FeatureValue]
  (each: feature_id, symbol, timestamp, value, is_valid, input_dataset_version)
        │
        ▼
  FeatureRepository.save(feature_values)
        │
        ▼
  PostgreSQL (feature_values table)
```

**Key invariants:**
- `as_of_timestamp` filter is applied before every feature computation
- `is_valid = false` is returned (not an error) when warm-up period is not met
- Input dataset version is recorded with every output

---

## Flow 3: Regime Detection (Batch)

```text
Trigger: User submits detection job via API or CLI
        │
        ▼
  Job Queue (Celery) ← async task
        │
        ▼
  RegimeDetectionPipeline.run(config)
        │
        ├── Load feature set from FeatureRepository
        │       (for symbol, date_range, as specified in config)
        │
        ├── Instantiate RegimeDetector(algorithm_id, parameters)
        │       from RegimeDetectorRegistry
        │
        ├── RegimeDetector.fit(feature_matrix)
        │       (trains on in-sample data per config)
        │
        ├── RegimeDetector.predict(feature_matrix)
        │       → [regime_label, regime_confidence, regime_probabilities]
        │          (one record per timestamp)
        │
        └── RegimeRepository.save(regime_outputs, run_id, metadata)
                │
                ▼
          PostgreSQL (regime_outputs table)
                │
                ▼
  Job status → "completed", result_url populated
```

**Key invariants:**
- Detection is always run with a `run_id` — all outputs from a run are linked
- Algorithm version and parameters are stored with every output
- No future features are passed to the detector for any given timestamp

---

## Flow 4: Regime Intelligence (Query)

```text
Client: GET /api/v1/regime/transitions/{symbol}?algorithm_id=hmm_v1
        │
        ▼
  RegimeRepository.get_timeline(symbol, algorithm_id, run_id)
        │  → ordered list of (timestamp, regime_label, confidence)
        ▼
  RegimeIntelligence.transition_matrix(timeline)
        │  → K×K matrix of transition probabilities
        ▼
  API Response (formatted per response envelope)
```

---

## Flow 5: Risk Computation

```text
Trigger: User requests risk metrics or regime-conditional risk
        │
        ▼
  RiskEngine.compute(symbol, metrics, date_range, regime_run_id=optional)
        │
        ├── MarketDataRepository.get(symbol, date_range)
        │       → OHLCV data
        │
        ├── [if regime_conditional]
        │   RegimeRepository.get_timeline(symbol, algorithm_id)
        │       → regime labels per timestamp
        │
        ├── For each requested metric:
        │   ├── metric.compute(data, [regime_labels])
        │   │       → RiskMetric (value, window, confidence_level, assumptions)
        │   └── ...
        │
        ▼
  RiskRepository.save(risk_metrics)
        │
        ▼
  PostgreSQL (risk_metrics table)
        │
        ▼
  API Response or Research output
```

---

## Flow 6: Backtest Execution

```text
Trigger: User submits backtest job via API
        │
        ▼
  Job Queue (Celery) ← async task
        │
        ▼
  BacktestEngine.run(config)
        │
        ├── Load OHLCV data: MarketDataRepository.get(universe, date_range)
        │
        ├── Load regime timeline (optional): RegimeRepository.get_timeline(...)
        │
        ├── Initialize Portfolio(initial_capital, cost_model)
        │
        ├── Event loop: for each bar in chronological order:
        │   ├── Strategy.on_bar(bar, portfolio_state)
        │   │       → Signal (BUY/SELL/HOLD, symbol, size)
        │   ├── Execute orders with CostModel applied
        │   ├── Update Portfolio (positions, cash, equity)
        │   └── Record equity curve point
        │
        ├── Compute performance analytics (Sharpe, drawdown, etc.)
        │
        ├── [if regime_run_id provided]
        │   RegimeAttributor.attribute(equity_curve, regime_timeline)
        │       → per-regime performance breakdown
        │
        └── BacktestRepository.save(result)
                │
                ▼
          PostgreSQL (backtest_results table)
```

---

## Flow 7: API Request (Read Path)

```text
Client HTTP Request
        │
        ▼
  FastAPI Router
        │
        ├── AuthMiddleware (validate API key or JWT)
        ├── RateLimitMiddleware (check per-user quota)
        └── Pydantic request validation
        │
        ▼
  Route Handler (delegates to module)
        │
        ▼
  Module (reads from repository, applies computation)
        │
        ▼
  Pydantic response schema (validate output)
        │
        ▼
  Response Envelope wrapper (success, data, meta)
        │
        ▼
  HTTP Response (JSON)
```

---

## Cross-Cutting Concerns

All flows above are subject to:

- **Structured logging:** every significant step is logged with request_id, symbol, timestamps
- **Error propagation:** exceptions are caught at the API boundary and formatted as error responses
- **Observability:** metrics emitted for ingestion throughput, detection latency, request rates
- **Reproducibility:** all computations record input versions and parameters
