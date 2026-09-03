# End-to-End Conceptual Data Flow

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  
**Status:** Approved Architecture Blueprint  

---

## 1. Overview

The integrity and reproducibility of financial market analysis depends entirely on rigorous, deterministic, and verifiable data pipelines. 

RegimeX defines a unidirectional data pipeline where each stage enforces strict validation gates, captures full data provenance, and guarantees point-in-time correctness (zero look-ahead bias).

---

## 2. Global Pipeline Architecture

```text
       ┌─────────────────────────────────────────────────────────┐
       │               1. External Market Data                   │
       │    (Yahoo Finance, Alpha Vantage, Polygon, Local Feeds) │
       └────────────────────────────┬────────────────────────────┘
                                    │ Raw provider payloads
       ┌────────────────────────────▼────────────────────────────┐
       │                2. Provider Adapter                      │
       │   (Converts external formats to internal raw structs)   │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
                     [ Validation Gate 1: Syntax & Sanity ] ──► (Reject Malformed Data)
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │             3. Normalization & Typing                   │
       │    (UTC timestamps, adjustment scaling, Decimal math)   │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
                     [ Validation Gate 2: OHLCV Consistency ] ──► (Quarantine Anomalies)
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │             4. Canonical Market Data Store              │
       │     (Immutable, append-only, version-fingerprinted)     │
       └────────────────────────────┬────────────────────────────┘
                                    │ Point-in-time slice (t <= T)
       ┌────────────────────────────▼────────────────────────────┐
       │             5. Feature Engineering Pipeline             │
       │ (Returns, Realized Volatility, Momentum, Volume Math)   │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
                     [ Validation Gate 3: Feature Sanity & Bias ] ──► (Block Inf/NaN/Leaks)
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │             6. Regime Detection Models                  │
       │      (HMM, GMM, KMeans, Changepoint, Ensembles)         │
       └────────────────────────────┬────────────────────────────┘
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │             7. Regime Classification                    │
       │   (Discrete regime labels + continuous probabilities)   │
       └────────────────────────────┬────────────────────────────┘
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │             8. Regime Intelligence                      │
       │  (State transition matrices, persistence, durations)    │
       └────────────────────────────┬────────────────────────────┘
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │            9. Risk Engine & Backtesting                 │
       │  (VaR, CVaR, drawdowns, event-driven trade simulations) │
       └────────────────────────────┬────────────────────────────┘
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │           10. Research Artifacts & Results              │
       │    (Full provenance record, seeds, parameter configs)   │
       └────────────────────────────┬────────────────────────────┘
                                    │
       ┌────────────────────────────▼────────────────────────────┐
       │         11. Delivery: Web / API / AI Assistant          │
       │  (Interactive dashboards, grounded AI explanations)     │
       └─────────────────────────────────────────────────────────┘
```

---

## 3. Pipeline Stages & Validation Gates

### Stage 1 & 2 — External Data Ingestion & Provider Adaptation
- **Operation:** Asynchronous workers poll or receive scheduled data batches from upstream market data APIs. The provider adapter maps vendor-specific JSON/CSV payloads into raw internal staging structures.
- **Validation Gate 1 (Syntax & Sanity):**
  - Verifies presence of required fields: `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`.
  - Ensures timestamps are parseable ISO 8601 strings or epoch integers.
  - **Action on Failure:** Immediate rejection; logs structured vendor communication error; does not touch the database.

### Stage 3 & 4 — Normalization & Canonical Market Data Store
- **Operation:**
  - Converts all timestamps to UTC ISO 8601 representation.
  - Standardizes financial numbers into high-precision fixed-point or float formats.
  - Applies corporate actions (stock splits, dividend adjustments) based on the specified `adjustment_type`.
  - Computes a deterministic SHA-256 dataset fingerprint over the batch.
- **Validation Gate 2 (Financial Integrity & Constraints):**
  - **Hard Non-Negotiable Checks:**
    - `high >= low`
    - `high >= open` and `high >= close`
    - `low <= open` and `low <= close`
    - `open > 0`, `high > 0`, `low > 0`, `close > 0`
    - `volume >= 0`
  - **Duplicate Check:** Evaluates composite primary key `(symbol, exchange, timestamp, adjustment_type)`. If already present, executes idempotent upsert or confirms byte-for-byte identity.
  - **Calendar Completeness:** Flags unexpected missing trading days against exchange holiday calendars.
  - **Action on Failure:** Flawed records are quarantined in a dead-letter/data-quality review table; never written as valid canonical records.

### Stage 5 — Feature Engineering Pipeline
- **Operation:**
  - Queries canonical market data up to a specified historical point-in-time timestamp $T$.
  - Executes registered feature calculations (e.g., rolling returns, realized volatility, ATR, RSI).
  - Evaluates warm-up windows (e.g., a 21-day volatility indicator requires at least 21 historical bars).
- **Validation Gate 3 (Look-Ahead Bias & Numeric Sanity Gate):**
  - **Point-in-Time Check:** The pipeline strictly verifies that no record with timestamp $t > T$ is passed into calculation functions.
  - **Numeric Sanity:** Rejects any feature calculation resulting in `NaN`, `+Inf`, or `-Inf` without explicit `is_valid = false` flags.
  - **Action on Failure:** If look-ahead bias is detected, the job immediately aborts with a critical system error. If warm-up is insufficient, output records have `is_valid = false` and are excluded from model training.

### Stage 6 & 7 — Regime Detection & Classification
- **Operation:**
  - Standardizes the feature matrix (z-score normalization using parameters fitted strictly on in-sample data).
  - Invokes the selected `RegimeDetector` (`fit` or `predict`).
  - Generates discrete integer regime state labels alongside soft probability vectors (`predict_proba`).
- **Validation Gate 4 (Classification Sanity Gate):**
  - Verifies that probability distributions sum to $1.0 \pm 10^{-6}$.
  - Confirms state counts match configured regime cardinality $K$.
  - Asserts that model inference output lengths match the input feature matrix length exactly.

### Stage 8 & 9 — Regime Intelligence, Risk Analytics & Backtesting
- **Operation:**
  - **Intelligence:** Calculates Markovian transition probability matrices $P_{i,j} = P(S_t = j \mid S_{t-1} = i)$ and average regime duration metrics.
  - **Risk:** Partitions historical returns by regime state; computes unconditional vs regime-conditional Value at Risk (VaR), Expected Shortfall (CVaR), and maximum drawdown.
  - **Backtesting:** Iterates chronologically bar-by-bar through strategy simulation; applies execution slippage and transaction cost models.

### Stage 10 & 11 — Research Artifacts & Multi-Channel Delivery
- **Operation:**
  - Bundles the complete analytical result alongside its full reproducibility metadata:
    ```json
    {
      "run_id": "run_01j7xyz...",
      "dataset_fingerprint": "sha256_8f4a...",
      "feature_set_version": "v1.2.0",
      "algorithm_id": "hmm_v1",
      "parameters": {"n_regimes": 3, "random_state": 42},
      "created_at": "2026-09-03T18:00:00Z"
    }
    ```
  - Serves results via cached API responses, interactive web dashboards, and grounded context payloads for the AI Research Assistant.

---

## 4. Failure Handling & Recovery Flow

| Pipeline Failure Point | Root Cause | System Response | Recovery Action |
|------------------------|------------|-----------------|-----------------|
| External API Call | Network timeout or 429 rate limit | Worker pauses with exponential backoff and jitter | Retries up to 3 times before setting job to `FAILED_DEPENDENCY` |
| Validation Gate 1 / 2 | Malformed payload or broken price constraints | Discards invalid bars, writes diagnostic report to `data_quality_events` | Alert emitted; valid bars continue processing |
| Validation Gate 3 | Feature computation encounters `NaN` or data leak | Pipeline halts execution; throws `LookAheadBiasError` or sets `is_valid=False` | Job marked `FAILED`; developer notified in CI/logs |
| Model Fitting | Numerical convergence failure in optimization | Catches algorithm exception; captures solver iteration log | Returns structured `MODEL_FIT_ERROR`; preserves prior valid model |
| Asynchronous Worker | Worker node OOM crash | Message broker detects unacknowledged task | Message requeued to dead-letter queue; API returns `JOB_FAILED` |
