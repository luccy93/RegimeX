# RegimeX System Architecture & Observability

This document describes the high-level architecture of the **RegimeX Open-Source Quantitative Market Intelligence Platform**, highlighting the **Operational Observability and Health Layer** introduced in V23.

---

## 1. High-Level Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Next.js Web Client (apps/web)                        │
│   Markets | Regimes | Analytics | AI Research | Risk | Backtest | Health│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON API (v1)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (apps/api)                          │
│                                                                        │
│  ┌───────────────────────┐              ┌───────────────────────────┐  │
│  │   Market Data (V04)   │              │   Regime Detection (V07)  │  │
│  │ Providers, Ingestion  │              │ KMeans, GMM, HMM, Ensemble│  │
│  └───────────┬───────────┘              └─────────────┬─────────────┘  │
│              │                                        │                │
│              ▼                                        ▼                │
│  ┌───────────────────────┐              ┌───────────────────────────┐  │
│  │  Data Quality (V06)   │              │  Regime Analytics (V09)   │  │
│  │ QualityReport, Rules  │              │ Transitions, Durations    │  │
│  └───────────┬───────────┘              └─────────────┬─────────────┘  │
│              │                                        │                │
│              ▼                                        ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │           Health & Observability Layer (V23 Commit 02)           │  │
│  │                                                                  │  │
│  │  Data Health Monitor          Model Health Monitor               │  │
│  │  • Freshness (Calendar aware) • Invariant Verification           │  │
│  │  • Completeness               • Confidence & Stability           │  │
│  │  • Validity integration       • Prediction Drift (JSD / TV)      │  │
│  │  • Provider Availability      • Continuous Feature Drift (PSI)   │  │
│  │  • Pipeline Stages            • Model Execution Metrics          │  │
│  │                                                                  │  │
│  │  Prometheus Metrics Registry (Bounded Cardinality)               │  │
│  │  In-Memory History Repository (Thread-Safe Deques)                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Telemetry and Operational Monitoring Foundation

### 2.1 Distinction from Trading Decisions
The observability system provides continuous telemetry on platform performance and operational correctness. It operates strictly as an infrastructure health tool:
- It **does not** produce trading recommendations or price forecasts.
- It evaluates whether the data pipeline and machine learning models are functioning reliably according to specification.

### 2.2 Core Monitoring Domains
1. **Data Health**:
   - Tracks data arrival delays with market calendar context (NYSE, NSE, Crypto 24/7).
   - Monitors observation completeness (missing and duplicate timestamps).
   - Integrates with the V06 data quality validation pipeline without duplicating business logic.
   - Monitors vendor API health (request volume, failure rate, consecutive streaks, latency).
   - Monitors pipeline execution across the six standard stages.

2. **Model Health**:
   - Validates prediction outputs against mathematical invariants: valid regime IDs ($0 \dots K-1$), finite values, valid probability distributions summing to 1.0.
   - Monitors model output certainty and identifies low-confidence regimes.
   - Measures operational stability and rapid regime switching (chattering).
   - Tracks empirical regime distribution shifts using Jensen-Shannon Divergence and Total Variation distance.
   - Measures continuous feature drift using the Population Stability Index (PSI).

---

## 3. Telemetry Integration & Standard Metrics

Prometheus metrics are exposed at `/metrics` with strict enforcement of bounded label sets:
- **Data Health**: `regimex_data_health_checks_total`, `regimex_data_health_failures_total`, `regimex_data_freshness_seconds`, `regimex_data_quality_violations_total`.
- **Model Health**: `regimex_model_health_checks_total`, `regimex_model_health_failures_total`, `regimex_model_prediction_failures_total`, `regimex_model_low_confidence_total`, `regimex_model_drift`, `regimex_data_drift`.

For comprehensive details on threshold configurations, API contracts, and mathematical implementations, refer to [`docs/observability.md`](file:///c:/Users/Devendraprasad/Downloads/RegimeX/docs/observability.md).
