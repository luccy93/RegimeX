# Baseline KMeans Regime Model Documentation

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume 08 — Commit 01: Baseline KMeans Regime Model**

---

## 1. Purpose & Overview

Volume 08 introduces the first unsupervised statistical machine-learning model into RegimeX: the **Deterministic KMeans Baseline Regime Detector**.

The detector operates on normalized numerical features computed by the Volume 07 Feature Engineering Pipeline, partitioning market observations into $K$ discrete, canonicalized market regime clusters.

```text
Validated Market Data (V05/V06)
          ↓
Feature Pipeline (V07)
          ↓
     FeatureSet
          ↓
FeatureMatrixBuilder (V08)
          ↓
    FeatureMatrix
          ↓
StandardScaler (in-sample fitted)
          ↓
KMeans Clustering (deterministic seed)
          ↓
Cluster Canonicalization (invariant feature signatures)
          ↓
RegimeDetectionResult (canonical labels & distance heuristics)
```

> **Notice:** V08 Commit 01 establishes a baseline geometric clustering model for statistical benchmarking. Advanced probabilistic models (Gaussian Mixture Models, Hidden Markov Models), transition probability engines, and ensemble intelligence are outside this commit and scheduled for subsequent volumes.

---

## 2. Architecture & Layer Boundaries

The regime detection subsystem adheres strictly to RegimeX Clean Architecture principles:

| Layer | Path | Responsibilities & Constraints |
| :--- | :--- | :--- |
| **Domain** | `apps/api/app/modules/regime_detection/domain/` | Pure Python and Pydantic v2 domain models (`RegimeModelConfig`, `FeatureMatrix`, `ClusterProfile`, `FitResult`, `RegimeDetectionResult`), `RegimeDetector` ABC, and typed error hierarchy. **Zero dependencies on scikit-learn, numpy, or pandas.** |
| **Application** | `apps/api/app/modules/regime_detection/application/` | `FeatureMatrixBuilder` (V07 `FeatureSet` to `FeatureMatrix` conversion with warm-up dropping) and `RegimeDetectionService` (application orchestration). **Zero scikit-learn imports.** |
| **Infrastructure** | `apps/api/app/modules/regime_detection/infrastructure/models/kmeans.py` | `KMeansRegimeDetector`: Concrete adapter encapsulating `StandardScaler` and `sklearn.cluster.KMeans`. Translates raw cluster indexes into canonical domain structures. |

---

## 3. Preprocessing, Feature Matrix & Missing-Value Policy

### Point-in-Time Alignment
Features produced by the V07 Feature Pipeline preserve chronological order and timezone-aware timestamps. The `FeatureMatrixBuilder` validates:
- Timestamps are strictly ascending ($t_i > t_{i-1}$) and timezone-aware.
- Matrix dimensions strictly match ($N \times M$).
- Every value is finite (NaN, $+\infty$, and $-\infty$ are explicitly rejected with `InvalidFeatureMatrixError`).

### Warm-Up Missing Value Policy
Rolling-window indicators (e.g., 20-day volatility, moving average ratios) generate unavailable (`None`) values during their warm-up period.
- **KMeans Exclusion Rule:** Rows with any `None` feature value are dropped.
- **No Synthetic Fabrication:** RegimeX **never** applies `fillna(0)` or fabricated zeroes to missing indicators. Replacing missing volatility or return values with zero would corrupt cluster centroids and fabricate false low-volatility signals.
- **Timestamp Tracking:** The remaining valid observations retain their original timestamps, preserving point-in-time integrity.

---

## 4. Anti-Leakage Feature Scaling

Market features encompass heterogeneous physical units and scales:
- Returns ($[-0.10, +0.10]$)
- Annualized Volatility ($[0.05, 0.80]$)
- Volume Ratios ($[0.2, 5.0]$)

Unscaled Euclidean distance in KMeans would be disproportionately dominated by large-scale features.

### Leakage Protection Guarantees:
1. `StandardScaler` is fitted **strictly in-sample** during `fit(feature_matrix)`.
2. Model parameters ($\mu_{\text{train}}, \sigma_{\text{train}}$) are frozen and persisted in the detector.
3. During inference (`predict(feature_matrix)` and `predict_proba(feature_matrix)`), the scaler executes `transform()` **without refitting**.
4. Future observations or out-of-sample data evaluated by the model have zero ability to mutate training scaling parameters.

---

## 5. Deterministic Cluster Canonicalization

A fundamental property of KMeans is that raw cluster indices ($k \in \{0, \dots, K-1\}$) are arbitrary and sensitive to initialization order or random seed. In raw scikit-learn, "Cluster 0" on run A might correspond to "Cluster 2" on run B.

### RegimeX Invariant Signature Rule:
To guarantee deterministic, reproducible regime semantics:
1. For each identified cluster $k$, the unscaled mean of each feature across assigned observations is computed: $\bar{x}_{k, f}$.
2. A deterministic cluster signature is formed by ordering the feature means by canonical (alphabetical) feature name:
   $$\text{Signature}_k = \left( \bar{x}_{k, f_1}, \bar{x}_{k, f_2}, \dots, \bar{x}_{k, f_M} \right)$$
3. Clusters are sorted lexicographically by their invariant signature.
4. Canonical regime IDs are assigned to the sorted clusters:
   - Rank 0 $\to$ `canonical_regime_id = 0`, `canonical_regime_label = "REGIME_0"`
   - Rank 1 $\to$ `canonical_regime_id = 1`, `canonical_regime_label = "REGIME_1"`
   - Rank $K-1$ $\to$ `canonical_regime_id = K - 1`, `canonical_regime_label = f"REGIME_{K-1}"`
5. Downstream consumers interact exclusively with canonical regime identifiers, ensuring bit-for-bit invariance across seeds and runs.

---

## 6. Uncertainty & Probability Contract (`predict_proba`)

In accordance with ADR-0005 and V03 Interface Specifications:
- **No Fabricated Posteriors:** KMeans is a deterministic geometric partitioning algorithm, not a Bayesian generative model.
- **Distance-Derived Heuristic:** `predict_proba()` computes continuous confidence vectors using a normalized softmin of Euclidean distances to scaled cluster centroids:
  $$p(r) = \frac{\exp(-d_r / \tau)}{\sum_{j=0}^{K-1} \exp(-d_j / \tau)}$$
  where $d_r = \| x_{\text{scaled}} - c_r \|_2$ and $\tau = \max(\bar{d}, 10^{-6})$ provides temperature scaling.
- **Contract Guarantees:**
  - Shape: $(N, K)$.
  - Non-negative: $p_{i, r} \ge 0.0$.
  - Row normalization: $\sum_{r=0}^{K-1} p_{i, r} = 1.0 \pm 10^{-6}$.
  - Column alignment: Column $r$ corresponds strictly to canonical regime $r$.

---

## 7. Model Lifecycle & Error Hierarchy

```text
       ┌──────────┐
       │ UNFITTED │
       └────┬─────┘
            │ fit(feature_matrix)
            ▼
       ┌──────────┐
       │  FITTED  │ ◄─── fit() again (replaces state)
       └────┬─────┘
            │ predict() / predict_proba()
            ▼
  [RegimeDetectionResult]
```

### Typed Error Hierarchy:
- `RegimeDetectionError` (base, HTTP 500)
  - `ModelNotFittedError` (HTTP 400): Raised on `predict()` / `predict_proba()` before `fit()`.
  - `InvalidModelConfigurationError` (HTTP 422): Raised on invalid hyperparameters ($K < 2$, $\text{max\_iter} \le 0$).
  - `InsufficientTrainingDataError` (HTTP 422): Raised when $N_{\text{samples}} < K$ or $N_{\text{samples}} < 2$.
  - `InvalidFeatureMatrixError` (HTTP 422): Raised on shape mismatches, NaNs, infinities, or missing feature columns.
  - `UnsupportedPredictionError` (HTTP 400): Raised on unsupported prediction modes.
  - `ModelTrainingError` (HTTP 500): Raised on internal algorithmic convergence failures.
  - `ModelPredictionError` (HTTP 500): Raised on inference calculation failures.

---

## 8. In-Sample vs. Out-of-Sample Distinction

> [!IMPORTANT]
> A KMeans model fitted across an entire historical dataset is an **in-sample clustering baseline**. It clusters historical market phases into statistical states; it is **not** a predictive market-timing oracle. Walk-forward cross-validation and out-of-sample persistence evaluation belong to research and backtesting workflows (V10/V11).

---

## 9. Verification & Test Suite Summary

The baseline KMeans implementation is validated by 192 dedicated unit tests in `apps/api/tests/unit/regime_detection/`.

### Commit 01 Foundation Tests (55 tests)

- **Architecture Boundaries (`test_regime_architecture.py`):** Asserts zero forbidden imports (`sklearn`, `pandas`, `numpy`, etc.) in domain layer, zero scikit-learn in application layer, and no premature ML libraries (`hmmlearn`, `xgboost`, `torch`).
- **Domain Models (`test_models.py`):** Asserts immutability, shape validation, naive timestamp rejection, and non-finite value rejection.
- **Feature Matrix (`test_feature_matrix.py`):** Asserts warm-up row exclusion, zero-fabrication rejection, and timestamp alignment with V07 `FeatureSet`.
- **KMeans Engine (`test_kmeans.py`):** Asserts lifecycle states, fit diagnostics, prediction bounds, row-sum probability invariants, and state replacement on refit.
- **Cluster Canonicalization (`test_labeling.py`):** Proves 100% purity separation on synthetic market states and seed-invariant canonical regime mapping.
- **Determinism (`test_determinism.py`):** Proves bit-for-bit reproducibility across independent instances and canonical column normalization.
- **Sample Count Boundaries (`test_insufficient_data.py`):** Tests $N=0, 1, \lt K, = K$.
- **Anti-Leakage Hardening (`test_leakage_and_lookahead.py`):** Proves frozen scaler parameters during inference and point-in-time prefix prediction invariance.
- **Service Integration (`test_service.py`):** End-to-end integration connecting raw synthetic bars $\to$ V07 `FeaturePipeline` (17 features) $\to$ `RegimeDetectionService` $\to$ canonical `RegimeDetectionResult`.

### Commit 02 Validation & Hardening Tests (137 new tests)

- **Golden KMeans Validation (`test_kmeans_validation.py`):** 4-cluster separable synthetic market dataset, fit-result diagnostic validation (inertia, iteration count, feature means, sample counts, timestamps, algorithm field, version stability), numerical safety (very large/small/constant/near-zero-variance features), predict output shape/range/determinism, `predict_proba()` contract (shape, finite values, row normalization, column alignment, heuristic disclosure in metadata), and performance regression (< 30s for 500 rows).
- **Label Canonicalization Regression (`test_label_canonicalization.py`):** Direct lexicographic signature rule verification, secondary-feature tie-breaking using a 3-feature deterministic dataset with known exact centroids, multi-seed canonical stability (seeds 1/42/99 on 4-cluster golden dataset), stability when raw cluster numbering differs across seeds, and label format/ordering/completeness invariants.
- **Scaler Leakage Regression (`test_scaler_leakage.py`):** Captured `mean_`/`scale_` before/after predict and predict_proba on extreme OOS data ($\pm$7777–12345), 10-pass multi-call mutation guard, transform-vs-fit_transform proof using divergence of training and OOS scalers, refit scaler replacement (orders-of-magnitude shift: $[0.02, 0.15] \to [999.5, 4995]$), no stale parameter accumulation (cross-validated against fresh `StandardScaler`), and determinism of scaler parameters across identical training runs.
- **Model Lifecycle Hardening (`test_model_lifecycle.py`):** UNFITTED state on construction, typed `ModelNotFittedError` with model name in message, `fit()` self-return, 3× repeated prediction determinism, cross-instance determinism, refit sample count/timestamp/scaler/KMeans replacement, metadata completeness (algorithm_id, version, family, description, assumptions, limitations, hyperparameters, no credential exposure), and 11 configuration edge-case rejection tests.
- **Feature Matrix Validation Hardening (`test_feature_matrix_validation.py`):** Domain model: single-row, empty, duplicate timestamps, out-of-order, naive timestamps, non-UTC timezone-aware accepted, duplicate feature names, whitespace-only feature name, row/column dimension mismatch, `get_column()` correctness and KeyError. Builder: alphabetical ordering, custom order preservation, deduplication, extra feature exclusion, missing feature typed error, empty string feature name typed error, warm-up None exclusion (not zero-filled), all-None typed error, and timestamp alignment. Feature ordering: inference on wrong order raises `InvalidFeatureMatrixError`, alphabetical normalization produces consistent cross-FeatureSet results.
- **V07→V08 Integration Validation (`test_v07_v08_integration.py`):** Full pipeline (OHLCV → V07 → FeatureMatrix → KMeans → canonical result), feature subset selection through service, subsequent inference determinism, timestamp alignment through full stack, warm-up None exclusion, no-zero-fabrication, NaN-free matrix after builder, insufficient bars typed error propagation, scaler frozen during service inference, in-sample model limitation in metadata, point-in-time prefix invariance through service, service-interface abstraction, domain-only result types (no sklearn objects), algorithm version stability, and no-GMM/HMM/ensemble architecture guard.
