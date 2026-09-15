# Volume 08 — Market Regime Detection: Baseline Models

**RegimeX — Open-Source Market Intelligence Platform**

---

## 1. Overview & Purpose

Volume 08 establishes the **Market Regime Detection** layer of RegimeX.

It consumes model-ready feature matrices produced by the Volume 07 Feature Engineering Pipeline and applies unsupervised statistical learning algorithms to segment market history into distinct regimes.

```text
Normalized OHLCV (V05/V06)
          ↓
Feature Engineering (V07)
          ↓
Feature Matrix (V08)
          ↓
Regime Detection Models (V08)
          ↓
Canonical Regime Assignments & Probabilities
          ↓
Future Regime Intelligence & Transition Analytics (V09)
```

> **Notice:** V08 Commit 01 establishes the deterministic KMeans baseline regime detector. Advanced probabilistic models and ensemble intelligence are outside this commit.

---

## 2. Commit Roadmap

| Commit | Scope | Status | Official Commit Message |
| :--- | :--- | :---: | :--- |
| **Commit 01** | **Baseline KMeans Regime Model** | **COMPLETE** | `feat(ml): implement baseline KMeans regime model` |
| **Commit 02** | **Baseline Model Validation Suite** | **COMPLETE** | `test(regime): add baseline model validation suite` |

---

## 3. Volume 08 Commit 01 Summary

- **Domain Layer (`domain/`):**
  - Pure Python and Pydantic v2 models: `RegimeModelConfig`, `FeatureMatrix`, `ClusterProfile`, `DetectorMetadata`, `FitResult`, `RegimeRecord`, `RegimeDetectionResult`.
  - Abstract base contract: `RegimeDetector` protocol (`fit()`, `predict()`, `predict_proba()`, `get_params()`, `metadata()`).
  - Domain error hierarchy: `RegimeDetectionError`, `ModelNotFittedError`, `InvalidModelConfigurationError`, `InsufficientTrainingDataError`, `InvalidFeatureMatrixError`, `UnsupportedPredictionError`, `ModelTrainingError`, `ModelPredictionError`.
  - Zero imports from scikit-learn, numpy, or pandas.
- **Application Layer (`application/`):**
  - `FeatureMatrixBuilder`: Translates V07 `FeatureSet` into pure `FeatureMatrix`, safely dropping warm-up rows without zero-fabrication and enforcing deterministic column order.
  - `RegimeDetectionService`: Application facade orchestrating feature extraction, model fitting, and regime prediction. Zero scikit-learn imports.
- **Infrastructure Layer (`infrastructure/models/kmeans.py`):**
  - `KMeansRegimeDetector`: Production adapter encapsulating `StandardScaler` and `sklearn.cluster.KMeans`.
  - Anti-leakage scaling: `StandardScaler` fitted strictly on in-sample training data; inference uses frozen parameters without refitting.
  - Deterministic cluster canonicalization: Decouples arbitrary raw cluster IDs from stable canonical regime labels (`REGIME_0`, `REGIME_1`, ...) via invariant centroid feature signatures.
  - Uncertainty disclosure: `predict_proba()` computes deterministic distance-based softmin heuristics normalized to $1.0 \pm 10^{-6}$.
- **Verification:**
  - 55 dedicated unit tests covering architecture boundaries, model immutability, missing value handling, cluster purity, determinism, sample count bounds, scaler isolation, lookahead absence, and end-to-end V07 feature pipeline integration.
  - 418 total passed backend tests (0 failures).

---

## 4. Architectural Guardrails (Scope Enforcement)

The following components are strictly excluded from Volume 08 Commits 01–02:
* ❌ No Gaussian Mixture Models (GMM) or Hidden Markov Models (HMM) (deferred).
* ❌ No ensemble models or voting meta-classifiers (deferred).
* ❌ No Markov transition probability matrices or regime persistence analytics (deferred to V09).
* ❌ No risk scoring, regime-conditional VaR, or CVaR (deferred to V10).
* ❌ No backtesting engine or trading strategies (deferred to V11).
* ❌ No AI assistants or LLM prompts (deferred to V12).
* ❌ No frontend UI regime dashboards or web routes.
* ❌ No BUY/SELL/HOLD trading recommendations or price targets.

---

## 5. Volume 08 Commit 02 Summary

- **Test Suite Additions (6 new files, 137 new tests):**
  - **Golden KMeans Validation (`test_kmeans_validation.py`):** 4-cluster separable synthetic dataset, fit diagnostics, numerical safety (large/small/constant/near-zero-variance features), predict output validation, `predict_proba()` contract (finite, normalized, deterministic, heuristic disclosure), and performance regression.
  - **Label Canonicalization Regression (`test_label_canonicalization.py`):** Direct validation of the lexicographic invariant signature rule, secondary-feature tie-breaking using a 3-feature deterministic dataset, multi-seed canonical stability on well-separated clusters (seeds 1, 42, 99), and label format invariants.
  - **Scaler Leakage Hardening (`test_scaler_leakage.py`):** Before/after `mean_` and `scale_` capture on wildly out-of-sample data, transform-not-fit_transform proof using OOS statistics divergence, refit scaler replacement (orders-of-magnitude different second fit), and cross-run scaler determinism.
  - **Model Lifecycle Hardening (`test_model_lifecycle.py`):** UNFITTED→FITTED state machine, `fit()` returns self (fluent), 3× repeated prediction determinism, independent detector cross-run determinism, refit updates (sample count, timestamps, scaler, KMeans centers), metadata completeness (algorithm_id, version, family, description, assumptions, limitations, hyperparameters, no credential exposure), and configuration edge cases (n_clusters < 2, max_iter ≤ 0, tol ≤ 0, invalid init, duplicate/empty feature names).
  - **Feature Matrix Validation Hardening (`test_feature_matrix_validation.py`):** Domain model edge cases (single row, empty, duplicate timestamps, out-of-order timestamps, naive timestamps, non-UTC timezone-aware, duplicate feature names, whitespace feature name, row/column dimension mismatch, `get_column()` correctness), FeatureMatrixBuilder hardening (alphabetical ordering, custom order, deduplication, extra feature exclusion, missing feature error, empty feature name error, warm-up None exclusion, all-None error, timestamp alignment), and feature ordering end-to-end correctness.
  - **V07→V08 Integration Validation (`test_v07_v08_integration.py`):** Full pipeline integration (raw OHLCV → V07 → FeatureMatrix → KMeans → canonical results), feature subset selection, subsequent inference determinism, timestamp alignment, warm-up None exclusion proof, no-zero-fabrication, NaN-free matrix guarantee, insufficient bars typed error, scaler frozen during service inference, in-sample model disclaimer in metadata, point-in-time prefix invariance, service-interface abstraction, domain-only result types, algorithm version stability, and no-GMM/HMM/ensemble architecture guard.
- **Total passing tests:** 555 (0 failures, 1 pre-existing skip).
