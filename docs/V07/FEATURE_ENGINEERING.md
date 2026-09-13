# RegimeX Feature Engineering — Architecture & Technical Specification

> **Notice:** V07 provides deterministic, explainable, model-ready market features with strict zero look-ahead bias, but does **not** perform market-regime detection (which is reserved for V08).

---

## 1. Executive Summary & Purpose

The **Feature Engineering Layer** (`app.modules.feature_engineering`) bridges validated, normalized canonical OHLCV market data (established in V05 and V06) and downstream quantitative intelligence models (V08 regime detection, V09 risk analytics, V10 backtesting).

```text
  Raw Market Data (V05)
           ↓
  Quality Validation Pipeline (V06)
           ↓
  Normalized Storage Engine (V06)
           ↓
┌─────────────────────────────────────────────────────────┐
│     Feature Engineering Pipeline (V07 Commit 01)        │
│                                                         │
│  - Strict Point-in-Time Correctness (Zero Lookahead)    │
│  - Vectorized NumPy / Pandas Infrastructure Execution   │
│  - Pure Domain Isolation (Zero External ORM/Library)    │
│  - Explainable Mathematical Formulations                │
│  - Deterministic Calculation & Provenance Metadata      │
└─────────────────────────────────────────────────────────┘
           ↓
  FeatureSet (Model-Ready Feature Matrix)
           ↓
  Future Regime Detection Models (V08: HMM, GMM, KMeans)
```

---

## 2. Layered Architecture & Module Layout

Following the clean hexagonal architecture established in V03 and V04, the module is organized into strict layers:

```text
apps/api/app/modules/feature_engineering/

├── domain/
│   ├── __init__.py           # Domain model re-exports
│   ├── errors.py             # Feature engineering domain error hierarchy
│   ├── models.py             # FeatureCategory, MissingValuePolicy, FeatureRecord, FeatureInputData
│   ├── feature_spec.py       # FeatureDefinition specification metadata
│   ├── feature_set.py        # FeatureSet immutable collection & matrix exports
│   └── interfaces.py         # FeatureCalculator abstract contract (pure domain)
│
├── application/
│   ├── __init__.py           # Application services and pipeline re-exports
│   ├── config.py             # FeaturePipelineConfig
│   ├── feature_registry.py   # FeatureRegistry catalogue and discovery
│   ├── feature_pipeline.py   # FeaturePipeline orchestrator
│   └── services.py           # FeatureService application facade
│
└── infrastructure/
    ├── __init__.py           # Infrastructure calculator exports
    └── calculators/
        ├── __init__.py       # Concrete calculators re-export
        ├── returns.py        # Simple & multi-period return calculations
        ├── volatility.py     # Rolling sample standard deviation (annualized & unannualized)
        ├── momentum.py       # Rate of change momentum
        ├── trend.py          # SMA ratio and recursive point-in-time EMA ratio
        ├── volume.py         # Volume change and moving average volume ratio
        └── range.py          # High-Low range, Welles Wilder True Range, Normalized True Range
```

### Architectural Boundaries
* **Domain Layer Purity:** Domain models (`FeatureDefinition`, `FeatureRecord`, `FeatureSet`, `FeatureInputData`) and abstract base class `FeatureCalculator` import **zero** NumPy, Pandas, or database ORMs. They rely strictly on the standard library and Pydantic v2.
* **Infrastructure Layer Isolation:** Vectorized NumPy calculations are encapsulated strictly inside `infrastructure/calculators/`.
* **Direction of Dependencies:** Outer layers depend on inner layers (`infrastructure` and `application` depend on `domain`; `domain` has no outward dependencies).

---

## 3. Strict Point-in-Time Invariant (Zero Look-Ahead Bias)

A fundamental requirement in quantitative financial modeling is that feature calculations must **never** leak information from the future.

### Hard Invariant
For any feature $F$ and observation timestamp $t$:
$$F_t = f(P_{\le t})$$
Under no circumstances may $F_t$ depend on $P_{> t}$.

### Guardrails Enforced:
1. **Strictly Backward Rolling Windows:** Rolling statistics (e.g. `volatility_20`, `sma_ratio_10`, `volume_ratio_20`) use windows of the form $[t - W + 1, t]$. Centered windows (`center=True`) are strictly forbidden.
2. **Recursive Point-in-Time Filters:** Recursive filters such as exponential moving averages (`ema_ratio_20`) update state sequentially from $t=0$ to $t=N$ with no backward pass.
3. **No Future Fills:** Backward-fill operations (`bfill`) and full-dataset global scaling (which leaks future min/max or mean) are completely prohibited.
4. **Automated Regression Test Suite:** Verified via `tests/unit/feature_engineering/test_no_lookahead.py` and `test_leakage_hardening.py`:
   - Mutating observations at $t+1 \dots N$ results in exactly $0.0$ difference for all feature values at $\le t$.
   - Slicing data into prefixes $[0 \dots k]$ matches the first $k$ rows of the full dataset computation bit-for-bit.

---

## 4. Baseline Feature Catalog & Mathematical Formulations

The initial feature catalog provides 17 explainable, stationary, or standardized features across 6 categories:

### A. Return Features (`FeatureCategory.RETURN`)
* **`return_1`**: Simple 1-period discrete return:
  $$R_{t, 1} = \frac{P_t - P_{t-1}}{P_{t-1}} = \frac{P_t}{P_{t-1}} - 1$$
* **`return_5`**, **`return_10`**, **`return_20`**: Multi-period discrete returns over lag $k$:
  $$R_{t, k} = \frac{P_t - P_{t-k}}{P_{t-k}}$$
* **Warm-up:** First $k$ periods yield `None`.
* **Safety:** Zero or negative price in denominator yields `None`.

### B. Volatility Features (`FeatureCategory.VOLATILITY`)
* **`volatility_10`**, **`volatility_20`**: Rolling sample standard deviation of 1-period returns ($ddof=1$):
  $$\sigma_{t, W} = \sqrt{\frac{1}{W-1} \sum_{i=0}^{W-1} \left(R_{t-i, 1} - \bar{R}_{t, 1}\right)^2}$$
* **`volatility_20_annualized`**: Scaled by annualization factor based on trading calendar session assumptions:
  $$\sigma_{t, 20}^{\text{ann}} = \sigma_{t, 20} \times \sqrt{\text{factor}} \quad (\text{default } 252.0 \text{ for daily US equities})$$
* **Warm-up:** First $W$ rows yield `None` (requiring $W$ historical returns).
* **Safety:** Constant prices/returns yield `0.0` (never `NaN` or error).

### C. Momentum Features (`FeatureCategory.MOMENTUM`)
* **`momentum_10`**, **`momentum_20`**: Rate of change momentum:
  $$M_{t, W} = \frac{P_t - P_{t-W}}{P_{t-W}}$$
* **Scale-Invariance:** Normalized percentage avoids asset-level scale bias.
* **Warm-up:** First $W$ rows yield `None`.

### D. Trend Features (`FeatureCategory.TREND`)
* **`sma_ratio_10`**, **`sma_ratio_20`**: Ratio of close price to Simple Moving Average:
  $$\text{SMA\_ratio}_{t, W} = \frac{P_t}{\text{SMA}(P, W)_t}, \quad \text{SMA}(P, W)_t = \frac{1}{W} \sum_{i=0}^{W-1} P_{t-i}$$
* **`ema_ratio_20`**: Ratio of close price to Exponential Moving Average:
  $$\text{EMA}_0 = P_0, \quad \text{EMA}_t = \alpha P_t + (1 - \alpha) \text{EMA}_{t-1}, \quad \alpha = \frac{2}{\text{span} + 1}$$
  $$\text{EMA\_ratio}_{t} = \frac{P_t}{\text{EMA}_t}$$
* **Warm-up:** First $W-1$ rows yield `None`.

### E. Volume Features (`FeatureCategory.VOLUME`)
* **`volume_change_1`**: 1-period percentage volume change:
  $$\Delta V_t = \frac{V_t - V_{t-1}}{V_{t-1}}$$
* **`volume_ratio_20`**: Ratio of volume to 20-period moving average:
  $$V\_ratio_{t, 20} = \frac{V_t}{\text{SMA}(V, 20)_t}$$
* **Safety:** When volume is unavailable (e.g. FX instruments without volume feeds) or zero, the calculators safely return `None`. Missing volume is **never** silently fabricated as zero.

### F. Price Range Features (`FeatureCategory.RANGE`)
* **`high_low_range`**: Normalized bar range:
  $$\text{HL\_range}_t = \frac{H_t - L_t}{C_t}$$
* **`true_range`**: Welles Wilder True Range:
  $$\text{TR}_0 = H_0 - L_0$$
  $$\text{TR}_t = \max\left(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|\right) \quad \text{for } t \ge 1$$
* **`normalized_true_range`**: Normalized by close price:
  $$\text{NTR}_t = \frac{\text{TR}_t}{C_t}$$

---

## 5. Missing-Value Policy & Numerical Safety

### Missing-Value Semantics
Warm-up observations are an inherent property of quantitative lookback indicators. RegimeX rejects blind `fillna(0)` operations because substituting zero into rolling returns or moving average ratios introduces false quantitative signals.

Two explicit policies are supported via `MissingValuePolicy`:
1. **`MissingValuePolicy.PRESERVE` (Default):**
   - Retains all observation timestamps.
   - Warm-up periods are explicitly set to `None` in `FeatureRecord.values`.
   - Preserves complete 1-to-1 temporal alignment with the underlying OHLCV bars.
2. **`MissingValuePolicy.DROP_WARMUP`:**
   - Trims all initial rows where any enabled feature is `None`.
   - Guarantees that every remaining row in the `FeatureSet` has complete, non-null numerical values ready for immediate matrix processing.

### Numerical Safety Guarantees
* **Zero Division Protection:** All denominators are guarded with tolerance checks ($|D| > 10^{-12}$). If a denominator is non-positive or near zero, calculators safely produce `None`.
* **Infinity & NaN Sanitization:** Calculated values are checked with `math.isnan` and `math.isinf`. Infinite or invalid values are never permitted to leak into domain records.
* **Extreme Scale Stability:** Validated against micro-penny assets ($P \approx 0.0001$) and high-denomination assets ($P > 600,000$).

---

## 6. Pipeline Execution & Usage Example

```python
from app.modules.feature_engineering import (
    FeaturePipeline,
    FeaturePipelineConfig,
    MissingValuePolicy,
    get_default_registry,
)

# 1. Configure pipeline
config = FeaturePipelineConfig(
    enabled_features=("return_1", "volatility_20", "sma_ratio_10"),
    missing_value_policy=MissingValuePolicy.PRESERVE,
    annualization_factor=252.0,
)

# 2. Instantiate pipeline with registry
pipeline = FeaturePipeline(config=config)

# 3. Compute deterministic FeatureSet from canonical OHLCV records
feature_set = pipeline.compute(market_data_result)

# 4. Access results
print(f"Computed {len(feature_set.feature_names)} features across {feature_set.record_count} bars.")
matrix = feature_set.to_matrix()  # 2D list: rows = observations, columns = features
```

---

## 7. Extending the Feature Catalog

To introduce a new quantitative feature:
1. Implement the pure domain contract `FeatureCalculator`:
   ```python
   from app.modules.feature_engineering.domain import (
       FeatureCalculator,
       FeatureDefinition,
       FeatureCategory,
       FeatureInputData,
   )

   class MyCustomIndicator(FeatureCalculator):
       def __init__(self, window: int = 14) -> None:
           self._window = window
           self._definition = FeatureDefinition(
               name=f"my_indicator_{window}",
               category=FeatureCategory.MOMENTUM,
               description=f"Custom indicator with {window} window",
               formula="...",
               required_fields=("close",),
               lookback=window,
               min_observations=window + 1,
           )

       @property
       def definition(self) -> FeatureDefinition:
           return self._definition

       def calculate(self, data: FeatureInputData) -> list[float | None]:
           # Vectorized implementation with zero lookahead
           ...
   ```
2. Register the calculator in `FeatureRegistry`:
   ```python
   registry.register(MyCustomIndicator(14))
   ```
No modifications to the pipeline orchestrator or domain models are required.

---

## 8. Validation & Anti-Leakage Test Hardening Matrix (V07 Commit 02)

Volume 07 Commit 02 established rigorous mathematical and programmatic guarantees across four specialized test modules:

| Test Module | Coverage & Guarantees Verified |
| :--- | :--- |
| **`test_golden_numerical.py`** | Exact hand-calculated checks for all 17 features: positive/negative/zero return offsets, sample variance $ddof=1$, recursive EMA formula step-by-step, gap up/down True Range. |
| **`test_property_invariants.py`** | Price scale invariance ($c \cdot P$ preserves return, momentum, SMA/EMA ratios, and normalized ranges), non-negativity ($\sigma \ge 0$, $HL \ge 0$, $TR \ge 0$), and constant series identity returns. |
| **`test_leakage_hardening.py`** | Tests A through F: future mutation invariance ($t+1 \dots N$), prefix slice invariance ($0 \dots k$), individual per-calculator isolation, directional rolling check, and AST audits prohibiting `center=True`, `bfill`, and dataset-wide scaling. |
| **`test_input_validation_hardening.py`** | Edge-case and error rejection: empty datasets, single-row handling, duplicate and inverted timestamps, naive datetimes, missing volume non-fabrication, and config deduplication. |
