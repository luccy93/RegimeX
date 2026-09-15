# RegimeX Volume 09 — Historical Regime Intelligence

**Technical Specification & Architecture**  
**Module:** `apps/api/app/modules/regime_intelligence/`  
**Current Phase:** Volume 09 Commit 01 (`feat(regime): add regime intelligence layer`)

---

## 1. Overview & Purpose

Volume 08 answers the classification question:
> *Which statistical cluster/regime does an observation belong to?*

Volume 09 answers the descriptive analytical question:
> *What does this detected regime look like historically?*

The **Regime Intelligence Layer** consumes canonical regime assignments produced by Volume 08 (and their underlying Volume 07 feature observations) and computes **descriptive, explainable historical analytics**.

```text
V07 Feature Pipeline
         ↓
V08 Regime Detector (KMeans Baseline)
         ↓
Regime Assignments (Canonical Labels & Probabilities)
         ↓
V09 Regime Intelligence Layer
    ├── Regime Profiles (Descriptive Summaries)
    ├── Empirical Frequency Analytics
    ├── Duration & Persistence Properties
    ├── Feature Distribution Characteristics
    ├── Deterministic Regime Ranking
    └── Active Trailing Regime Context
```

> [!IMPORTANT]
> **Descriptive Analytics, Not Predictive Signals:**  
> The Regime Intelligence Layer provides strictly descriptive, backward-looking historical analytics. It does **not** forecast future regime transitions, predict asset prices, generate trading signals, or provide investment advice.

---

## 2. Architecture & Layering

The module follows Clean Architecture principles in accordance with Volume 03 architectural specifications:

```text
apps/api/app/modules/regime_intelligence/
├── domain/                         # Pure Python & Pydantic v2 (zero 3rd-party math libs)
│   ├── __init__.py
│   ├── models.py                   # RegimeAssignment, FeatureStatistic, RegimeProfile, etc.
│   ├── errors.py                   # Typed RegimeIntelligenceError hierarchy
│   └── interfaces.py               # Protocol definitions for analyzers and services
│
├── application/                    # Application use cases & facades (zero ML internals)
│   ├── __init__.py
│   └── service.py                  # RegimeIntelligenceService facade & V08 adapter
│
├── infrastructure/                 # Mathematical implementations & algorithms
│   ├── __init__.py
│   └── analytics/
│       ├── __init__.py
│       ├── duration.py             # Run-length encoding and duration statistics
│       ├── statistics.py           # Numerically safe sample descriptive statistics
│       └── profiling.py            # Comprehensive profile construction engine
│
└── api/                            # HTTP routes (reserved for future commit)
    └── __init__.py
```

### Dependency Rules:
1. **Domain Isolation:** `domain/` contains pure Python and Pydantic v2 domain models and typed errors. Zero dependencies on `pandas`, `numpy`, `scikit-learn`, or database ORMs.
2. **Infrastructure Ownership:** Numerical calculations and run-length algorithms reside strictly in `infrastructure/analytics/`.
3. **Application Decoupling:** `RegimeIntelligenceService` orchestrates validation, profiling, ranking, and context retrieval without depending on model training mechanics.
4. **No Re-training:** The intelligence layer never instantiates or re-fits ML models.

---

## 3. Core Domain Concepts

### 3.1 Regime Assignment (`RegimeAssignment`)
Point-in-time observation binding:
- `timestamp`: Timezone-aware UTC datetime.
- `regime_id`: Canonical integer identifier ($0 \le k < K$).
- `regime_label`: Canonical label (e.g., `REGIME_0`, `REGIME_1`).
- `features`: Dictionary of observed feature names to numerical values (or `None`).
- `confidence`: Optional continuous confidence score ($0 \le c \le 1$).
- `model_metadata`: Model provenance metadata.

### 3.2 Regime Profile (`RegimeProfile`)
Historical descriptive characterization of a single regime over the analyzed period:
- `regime_id` & `regime_label`: Canonical identifiers.
- `observation_count`: Total observations in this regime.
- `frequency`: $\text{frequency} = \frac{\text{observation\_count}}{\text{total\_observations}}$, where $0 \le \text{frequency} \le 1.0$.
- `percentage`: $\text{frequency} \times 100.0$.
- `first_seen` & `last_seen`: Earliest and latest UTC observation timestamps.
- `run_count`: Total number of contiguous spells/runs.
- `average_duration`: Mean consecutive observations per spell ($\text{duration\_observations}$).
- `median_duration`: Median consecutive observations per spell.
- `min_duration` & `max_duration`: Minimum and maximum observed run lengths.
- `feature_statistics`: Mapping of feature name to `FeatureStatistic`.

### 3.3 Current Regime Context (`CurrentRegimeContext`)
Point-in-time snapshot of the latest active market regime:
- `current_regime_id`: Active regime index at the latest observation.
- `current_regime_label`: Active regime canonical label.
- `current_timestamp`: Observation timestamp of the latest bar.
- `observations_in_current_run`: Trailing contiguous run length ($L \ge 1$).
- `historical_frequency`: Historical frequency for comparison.
- `historical_average_duration`: Historical baseline mean duration.
- `historical_max_duration` & `historical_min_duration`: Historical duration bounds.
- `historical_run_count`: Total historical spells.
- `current_features`: Latest observed feature values.

### 3.4 Historical Regime Summary (`RegimeHistorySummary`)
Top-level immutable container:
- `analysis_start` & `analysis_end`: Temporal bounds.
- `total_observations`: Total observation count.
- `regimes_observed`: Ordered tuple of distinct regime IDs.
- `regime_profiles`: Dictionary of `RegimeProfile` keyed by `regime_id`.
- `current_regime`: `CurrentRegimeContext` for the latest observation.
- `model_name`, `model_version`, `algorithm`: Provenance metadata.
- `feature_names`: Ordered tuple of feature column names.

---

## 4. Analytical Foundations

### 4.1 Frequency Analytics
For each regime $k \in \{0, \dots, K-1\}$:
$$\text{frequency}_k = \frac{N_k}{N_{\text{total}}}$$
Guarantees:
- $0.0 \le \text{frequency}_k \le 1.0$ for all $k$.
- $\sum_{k=0}^{K-1} \text{frequency}_k = 1.0 \pm 10^{-6}$ whenever $N_{\text{total}} > 0$.
- When $N_{\text{total}} = 0$, $\text{frequency}_k = 0.0$.

### 4.2 Duration Analytics
A regime run is defined as a maximal contiguous subsequence of identical regime assignments:
$$\dots, R_t = k, R_{t+1} = k, \dots, R_{t+L-1} = k$$
where $R_{t-1} \neq k$ and $R_{t+L} \neq k$. The run duration is $L$.

**Duration Semantics:**
- Duration is measured strictly in **discrete observation units** (`duration_observations`).
- No calendar day conversion is applied without explicit trading calendar semantics.
- Summary metrics:
  - $\text{average\_duration} = \frac{1}{M_k} \sum_{i=1}^{M_k} L_i$
  - $\text{median\_duration} = \text{median}(\{L_1, \dots, L_{M_k}\})$
  - $\text{min\_duration} = \min(\{L_i\})$, $\text{max\_duration} = \max(\{L_i\})$
  - Invariant: $\text{min\_duration} \le \text{median\_duration} \le \text{max\_duration}$ and $\text{min\_duration} \le \text{average\_duration} \le \text{max\_duration}$.

### 4.3 Feature Descriptive Statistics
For each feature $X$ within regime $k$:
- **Observation Count:** Valid, non-null observations ($N_{k, X}$).
- **Arithmetic Mean:** $\bar{X} = \frac{1}{N_{k, X}} \sum_{i=1}^{N_{k, X}} X_i$.
- **Median:** 50th percentile of valid observations.
- **Sample Standard Deviation:** Computed using Bessel's correction ($ddof=1$):
  $$s = \sqrt{\frac{1}{N_{k, X} - 1} \sum_{i=1}^{N_{k, X}} (X_i - \bar{X})^2}$$
  - When $N_{k, X} = 1$ or all values are identical: $s = 0.0$.
  - When $N_{k, X} = 0$: represented as `None`.
- **Min / Max:** Extreme observed values.
- **No Data Fabrication:** Missing values (`None`) are never replaced with zero (`fillna(0)`).

---

## 5. Deterministic Regime Ranking

The intelligence service supports deterministic ranking of profiles via `rank_regimes`:

### Supported Metrics:
- `"frequency"` (or `"observation_count"`)
- `"average_duration"`
- `"median_duration"`
- `"min_duration"`
- `"max_duration"`
- `"run_count"`
- Feature statistics: `"feature_mean:<name>"`, `"feature_median:<name>"`, `"feature_std:<name>"`, `"feature_min:<name>"`, `"feature_max:<name>"`

### Tie-Breaking Rule:
All metric rankings employ a secondary sort key: `regime_id` ascending. This ensures mathematically stable, reproducible ordering regardless of platform or runtime dictionary iteration order.

Unrecognized metrics raise a typed `UnsupportedRankingMetricError`.

---

## 6. Defensive Validation & Temporal Integrity

- **Timezone Awareness:** All timestamps must be timezone-aware UTC. Naive datetimes are strictly rejected with `InvalidRegimeHistoryError`.
- **Strict Monotonicity:** Timestamps must be strictly ascending ($t_i > t_{i-1}$).
- **Duplicate Rejection:** Consecutive identical timestamps are rejected with `InvalidRegimeHistoryError`.
- **Regime ID Validation:** Regime IDs must be non-negative integers ($r \ge 0$). Malformed IDs raise `InvalidRegimeAssignmentError`.
- **Numerical Safety:** Domain models and statistics engines reject or filter out `NaN`, `+inf`, and `-inf`.

---

## 7. Model Provenance & Reproducibility

Every `RegimeHistorySummary` captures:
- `model_name`: Detection model identifier (e.g., `kmeans-baseline`).
- `model_version`: Semantic version of the model (e.g., `1.0.0`).
- `algorithm`: Algorithm identifier (e.g., `kmeans_baseline`).
- `feature_names`: Column names evaluated in deterministic order.
- `computed_at`: UTC execution timestamp.

---

## 8. Explicit Scope Boundaries & Exclusions

In accordance with Volume 09 Commit 01 scope guardrails, the following components are **strictly excluded**:
- ❌ **Transition Probabilities & Markov Matrices:** No $P(S_t = j \mid S_{t-1} = i)$ modeling.
- ❌ **Transition Forecasting:** No forward-looking regime predictions.
- ❌ **Economic Overclaiming:** Regimes are labeled with neutral statistical terminology (`REGIME_0`, `REGIME_1`). No subjective "bull", "bear", or "crash" labels.
- ❌ **Trading Signals:** No buy, sell, or hedge recommendations.
- ❌ **Advanced Models:** Zero GMM, HMM, or ensemble model implementations.
- ❌ **Public REST Endpoints:** API routes deferred to subsequent commits.
