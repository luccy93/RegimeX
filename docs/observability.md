# RegimeX Observability: Model and Data Health Monitoring

This document details the **Model Health and Data Health Monitoring layer** built as part of RegimeX V23.

---

## 1. Operational Monitoring vs. Investment Performance

> [!IMPORTANT]
> **CRITICAL OPERATIONAL SCOPE**
>
> The RegimeX Observability system is an **operational diagnostic and health monitoring infrastructure**, NOT a trading-signal engine, price forecasting tool, or investment advisory system.
>
> - **Health Status** (e.g., `HEALTHY`, `DEGRADED`, `UNHEALTHY`) describes software engineering and data pipeline integrity: observation freshness, schema compliance, finite output invariants, and mathematical stability.
> - A `HEALTHY` model simply means the model executes without numerical exceptions, respects output probability bounds, and operates within expected drift limits. It **does NOT imply** that any market regime prediction is profitable, safe to trade, or an indicator of future market direction.
> - Telemetry and health APIs must never be interpreted as financial advice.

---

## 2. Health Monitoring Architecture

```text
Observability Framework
├── Data Health Domain
│   ├── Freshness (Trading calendar-aware for NYSE, NSE, 24/7 continuous crypto)
│   ├── Completeness (Expected vs received bars, missing & duplicate rows)
│   ├── Validity (Direct integration with V06 QualityReport)
│   ├── Upstream Provider Status (Latency, error rate, failure streaks)
│   └── Pipeline Stages (Provider → Ingestion → Validation → Normalization → Storage → Features)
│
└── Model Health Domain
    ├── Prediction Validity (Regime ID in [0, K-1], finite values, probability simplex sum ≈ 1)
    ├── Execution Health (Prediction count, latency, failure rate)
    ├── Confidence Monitoring (Distribution, low-confidence frequency)
    ├── Operational Stability (Regime switching frequency, persistence streaks)
    ├── Regime Distribution (Empirical percentages and Shannon entropy)
    └── Statistical Drift (Jensen-Shannon divergence, Total Variation, PSI for features)
```

---

## 3. Data Health Monitoring

### 3.1 Data Freshness & Calendar Awareness

Freshness evaluates the age of the latest available market observation:
$$\text{freshness} = t_{\text{evaluation}} - t_{\text{latest observation}}$$

To prevent false alarms during market holidays, weekends, or overnight pauses, the evaluation integrates with the V06 `TradingCalendar` infrastructure (`nyse`, `nse`, `24/7`):
- **Market Open**: If the session is actively trading, observations exceeding `REGIMEX_DATA_FRESHNESS_THRESHOLD` (default 300s) are classified as `DEGRADED`; those exceeding `REGIMEX_DATA_STALE_THRESHOLD` (default 3600s) are classified as `STALE`.
- **Market Closed**: If the exchange is closed, the latest observation is compared against the most recently completed scheduled session. If it aligns with the session close, the status remains `HEALTHY`. A feed is only marked `DEGRADED` or `STALE` if scheduled trading sessions were missed.

### 3.2 Data Completeness

Tracks expected vs. received observations according to schedule:
- `expected_rows`: Scheduled trading intervals.
- `received_rows`: Actual recorded bars.
- `missing_rows`: Gaps in observation index.
- `duplicate_rows`: Multiple observations for the same timestamp.

### 3.3 Data Validity Integration

Consumes the authoritative V06 `QualityReport` output without duplicating validation rules:
- Checks schema validity, timestamp monotonicity, and OHLC constraints ($L \le O, C \le H$).
- Reports critical anomaly counts, warning counts, and failed rule IDs.
- Critical issues immediately transition validity health to `UNHEALTHY`.

### 3.4 Provider Health

Monitors upstream market data vendor APIs (e.g., Yahoo Finance, Alpha Vantage):
- Request count, success count, failure count, and consecutive failure streaks.
- Exponentially smoothed or rolling average latency (ms).
- Statuses: `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`.
- Bounded identifiers: credentials, API keys, and sensitive tokens are strictly excluded from health monitoring logs and telemetry.

### 3.5 Pipeline Stage Tracking

Tracks operational status across the 6 core stages:
1. `provider`
2. `ingestion`
3. `validation`
4. `normalization`
5. `storage`
6. `features`

Overall pipeline status degrades if any individual stage reports `DEGRADED` or `UNHEALTHY`.

---

## 4. Model Health Monitoring

### 4.1 Supported Regime Models

The health monitor natively supports all RegimeX model implementations:
- **KMeans** (`kmeans`)
- **Gaussian Mixture Models** (`gmm`)
- **Hidden Markov Models** (`hmm`)
- **Regime Model Ensemble** (`ensemble`)

### 4.2 Prediction Validity & Output Invariants

Model predictions are verified against mathematical invariants:
1. **Regime Index Invariant**: Every regime ID $r_t \in \{0, 1, \dots, K-1\}$.
2. **Finiteness Invariant**: Predictions and probabilities must be finite (zero `NaN`, `+Inf`, `-Inf`).
3. **Probability Simplex Invariant**:
   - Probabilities bounded in $[0.0, 1.0]$.
   - Probability vector sums to 1.0 within tolerance: $|\sum_{k=0}^{K-1} p_{t,k} - 1.0| \le 10^{-3}$.

> [!WARNING]
> Invalid model outputs are never silently patched or imputed. Invariant violations are explicitly recorded as model health failures and reflected in operational telemetry.

### 4.3 Model Confidence & Stability

- **Confidence Health**: Monitors mean confidence, variance, and frequency of predictions falling below `REGIMEX_MODEL_LOW_CONFIDENCE_THRESHOLD` (default 0.50). High proportions of low-confidence predictions trigger `DEGRADED` status.
- **Operational Stability**: Measures regime switching frequency:
  $$\text{switching\_frequency} = \frac{1}{T-1} \sum_{t=2}^T \mathbb{I}(r_t \ne r_{t-1})$$
  Frequent chattering ($> 45\%$) indicates model instability and marks the model `DEGRADED`; switching every bar ($> 70\%$) marks it `UNHEALTHY`.

### 4.4 Distribution Drift vs. Data Drift

The system strictly decouples **data drift** (input distribution shifts) from **model output drift** (prediction distribution shifts):
- **Model Output Drift**: Evaluated using base-2 **Jensen-Shannon Divergence (JSD)** and **Total Variation (TV)** distance between predictions over a rolling window and a reference baseline:
  $$JSD(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M), \quad M = \frac{1}{2}(P + Q)$$
  $JSD$ is bounded in $[0.0, 1.0]$. Drift is flagged when $JSD > \text{threshold}$.
- **Feature Data Drift**: Evaluated on continuous feature series using the **Population Stability Index (PSI)**:
  $$PSI = \sum_{b=1}^B (Q_b - P_b) \ln\left(\frac{Q_b}{P_b}\right)$$
  - $PSI < 0.10$: Stable / no drift
  - $0.10 \le PSI \le 0.25$: Moderate drift
  - $PSI > 0.25$: Significant drift

---

## 5. Health Status States

| State | Definition | Trigger Conditions |
|---|---|---|
| `HEALTHY` | All invariants and SLA metrics satisfied | Fresh data, 100% valid predictions, no drift, low switching frequency. |
| `DEGRADED` | Operational impairment without fatal corruption | Observation delayed during trading hours, moderate drift, or moderate switching frequency. |
| `UNHEALTHY` | Fatal failure, corruption, or invariant breach | Critical validation failure, $NaN$ outputs, invalid regime IDs, or broken probability vectors. |
| `STALE` | Observations have ceased during an active market | Data age exceeds stale threshold while market is open or multiple scheduled sessions missed. |
| `UNKNOWN` | Insufficient telemetry data | Instrument or model has zero recorded observations. |

---

## 6. Configuration Parameters

Configure via environment variables (`.env`):

```bash
# Data Health
REGIMEX_DATA_FRESHNESS_THRESHOLD=300       # Seconds before open-market feed is DEGRADED
REGIMEX_DATA_STALE_THRESHOLD=3600         # Seconds before open-market feed is STALE

# Model Health
REGIMEX_MODEL_HEALTH_WINDOW=100           # Rolling observation window for stability & distribution
REGIMEX_MODEL_LOW_CONFIDENCE_THRESHOLD=0.50 # Threshold for flagging low-confidence inference
REGIMEX_MODEL_DRIFT_THRESHOLD=0.25        # JSD divergence threshold for prediction drift
REGIMEX_DATA_DRIFT_THRESHOLD=0.25         # PSI threshold for continuous feature drift

# Telemetry History
REGIMEX_OBSERVABILITY_HISTORY_LIMIT=1000  # Maximum snapshots retained in memory ring buffers
```

---

## 7. Prometheus Metrics & Cardinality Policy

All metrics strictly enforce bounded cardinality to prevent memory exhaustion in time-series engines (Prometheus, VictoriaMetrics):
- **Permitted labels**: `provider`, `model`, `component`, `operation`, `status`, `severity`, `category`, `calendar_id`.
- **Strictly forbidden as labels**: `symbol`, `request_id`, `user_id`, `trace_id`, `timestamp`, feature vectors, raw error strings.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `regimex_data_health_checks_total` | Counter | `status`, `provider` | Total data health checks evaluated |
| `regimex_data_health_failures_total` | Counter | `failure_type`, `provider` | Data health checks resulting in failure |
| `regimex_data_freshness_seconds` | Gauge | `calendar_id`, `status` | Age of latest observation |
| `regimex_data_quality_violations_total` | Counter | `category`, `severity` | Data quality violations detected |
| `regimex_model_health_checks_total` | Counter | `model`, `status` | Total model health checks evaluated |
| `regimex_model_health_failures_total` | Counter | `model`, `failure_type` | Model health failures |
| `regimex_model_prediction_failures_total` | Counter | `model`, `reason` | Invariant breaches or inference exceptions |
| `regimex_model_low_confidence_total` | Counter | `model` | Predictions below confidence threshold |
| `regimex_model_drift` | Gauge | `model`, `metric` | Prediction distribution JSD drift score |
| `regimex_data_drift` | Gauge | `feature`, `metric` | Continuous feature PSI drift score |

---

## 8. Versioned API Endpoints

All endpoints are versioned under `/api/v1/health` and `/metrics`:

- `GET /api/v1/health/summary`: Consolidated platform operational health summary.
- `GET /api/v1/health/data`: List of all monitored instrument data health snapshots.
- `GET /api/v1/health/data/{symbol}`: Granular freshness, completeness, and validity for a symbol.
- `GET /api/v1/health/models`: List of health snapshots across KMeans, GMM, HMM, and Ensemble.
- `GET /api/v1/health/models/{model_id}`: Granular prediction invariants, stability, and drift for a model.
- `GET /api/v1/health/providers`: Upstream vendor API latency and failure tracking.
- `GET /api/v1/health/pipeline`: Operational status across all 6 pipeline stages.
- `GET /metrics`: Standard Prometheus metrics exposition endpoint.

> [!NOTE]
> All health endpoints are ultra-lightweight ($O(1)$ memory queries against in-memory snapshots). They never trigger model fitting, database table scans, or historical backtests.
