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
| **Commit 02** | **Regime Model Validation & Compliance Hardening** | **NOT STARTED** | `test(ml): add regime model validation and compliance tests` |

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

The following components are strictly excluded from Volume 08 Commit 01:
* ❌ No Gaussian Mixture Models (GMM) or Hidden Markov Models (HMM) (deferred).
* ❌ No ensemble models or voting meta-classifiers (deferred).
* ❌ No Markov transition probability matrices or regime persistence analytics (deferred to V09).
* ❌ No risk scoring, regime-conditional VaR, or CVaR (deferred to V10).
* ❌ No backtesting engine or trading strategies (deferred to V11).
* ❌ No AI assistants or LLM prompts (deferred to V12).
* ❌ No frontend UI regime dashboards or web routes.
* ❌ No BUY/SELL/HOLD trading recommendations or price targets.
