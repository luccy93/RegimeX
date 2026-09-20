# Volume 11 — Ensemble Regime Engine

**RegimeX — Open-Source Market Intelligence Platform**

---

## 1. Overview & Purpose

Volume 11 introduces the **Regime Model Ensemble**, unifying heterogeneous machine learning algorithms into a robust, deterministic market regime intelligence framework.

In quantitative financial markets, individual models capture distinct, partial perspectives of underlying market dynamics:
- **KMeans Baseline (V08)**: Geometric distance partitioning in feature space.
- **Gaussian Mixture Model (V10)**: Probabilistic Gaussian density estimation and uncertainty quantification.
- **Hidden Markov Model (V10)**: Temporal transition dynamics and state persistence.

A single model family can be susceptible to algorithm-specific idiosyncrasies, local optima, or regime boundary ambiguities. The Regime Model Ensemble combines these complementary perspectives into a robust consensus regime assignment that exhibits greater empirical stability than any individual model.

```text
V08 KMeans Baseline (Geometric Clustering) ──┐
V10 GMM (Density Mixture Posteriors) ────────┼──> Regime Alignment ──> Weighted Voting ──> Consensus Regime
V10 Gaussian HMM (Temporal Dynamics) ────────┘
```

---

## 2. Commit Roadmap

| Commit | Scope | Status | Official Commit Message |
| :--- | :--- | :---: | :--- |
| **Commit 01** | **Regime Model Ensemble (Orchestration & Consensus)** | **COMPLETE** | `feat(ml): implement regime model ensemble` |
| **Commit 02** | **Ensemble Confidence Scoring & Calibration** | **PLANNED** | `feat(ml): add ensemble confidence scoring` |

> [!IMPORTANT]
> **Strict Architectural Scope Boundaries:**
> - **V11 Commit 01**: Multi-model execution, canonical regime alignment, deterministic weighted consensus voting, agreement tracking, and model failure policies.
> - **V11 Commit 02**: Multi-model posterior probability calibration, entropy-based confidence scoring, and continuous uncertainty estimation.
> - **Volume 12**: Platform transition analytics, transition probability matrices, and regime persistence forecasting.

---

## 3. Volume 11 Commit 01 Summary — Regime Model Ensemble

### Core Deliverables

- **Domain Models & Validation (`domain/models.py`, `domain/errors.py`)**:
  - `EnsembleModelConfig`: Frozen, validated Pydantic v2 configuration governing `enabled_models`, `model_weights`, `aggregation_strategy`, `minimum_required_models`, `failure_policy`, `alignment_policy`, `tie_breaker`, `reference_model`, and `feature_names`.
  - `EnsembleRecord`: Point-in-time observation capturing consensus regime ID/label, individual component model predictions, aligned canonical predictions, agreement count, total models, and unanimity flag.
  - `RegimeEnsembleResult`: Strongly typed, immutable ensemble output providing comprehensive execution provenance, active normalized weights, and component prediction series.
  - Domain exceptions: `EnsembleError`, `InvalidEnsembleConfigurationError`, `EnsembleModelUnavailableError`, `InsufficientUsableModelsError`, `RegimeAlignmentError`, `EnsembleExecutionError`.
  - Strict domain purity: zero vendor, NumPy, or Scipy imports in the domain layer.

- **Regime Identity Alignment (`infrastructure/ensemble/alignment.py`)**:
  - `RegimeAlignmentEngine`: Resolves label switching across heterogeneous models.
  - Mathematical alignment via pairwise Euclidean distance cost matrices between component cluster centroids/emission means and a canonical reference model.
  - Solves optimal 1-to-1 matching via `scipy.optimize.linear_sum_assignment` with deterministic tie-breaking on `(distance, target_regime_id, source_cluster_id)`.
  - Supports `CANONICAL_LABEL`, `FEATURE_SIMILARITY`, and `EXPLICIT_MAPPING` policies.

- **Deterministic Aggregation (`infrastructure/ensemble/aggregation.py`)**:
  - `EnsembleAggregator`: Tallying of weighted or plurality votes across aligned component predictions.
  - Deterministic tie-breaking rules: `LOWEST_REGIME_ID` (default) or `MODEL_PRECEDENCE`.
  - Explicit agreement tracking per observation without synthetic or fake confidence scores.

- **Extensible Model Registry (`infrastructure/ensemble/registry.py`)**:
  - `RegimeModelRegistry`: Pre-registers standard detectors (`"kmeans"`, `"gmm"`, `"hmm"`) and allows dynamic registration of future custom/community detectors.

- **Ensemble Detector Implementation (`infrastructure/models/ensemble.py`)**:
  - `RegimeModelEnsemble`: Implements the `RegimeDetector` domain protocol.
  - Complete lifecycle: `UNFITTED` $\to$ `FITTED`.
  - Strict anti-leakage: fits component models strictly on in-sample training data; inference executes with frozen parameters.
  - Contract guard: `predict_proba()` explicitly returns `None` (confidence scoring deferred to Commit 02).
  - Robust failure policies: `FAIL_FAST`, `SKIP_UNAVAILABLE`, and `BEST_EFFORT`.

- **Comprehensive Test Suite (`tests/unit/regime_detection/test_ensemble.py`)**:
  - 42 targeted unit and integration tests verifying configuration constraints, label permutation alignment, weighted voting overrides, tie resolutions, model failure handling, non-confidence guarantees, and multi-model end-to-end consensus.

---

## 4. Key Architectural Concepts

### Why Raw Model Labels Cannot Be Compared Directly
Raw cluster labels produced by unsupervised models are arbitrary permutations. Even when models are trained on the same data, differences in objective functions (e.g. geometric SSE vs. Gaussian log-likelihood vs. Baum-Welch temporal likelihood) can alter internal numbering. Direct comparison of raw indices (`KMeans 0 == GMM 0`) is mathematically invalid. The `RegimeAlignmentEngine` deterministically maps all models into a shared canonical regime space prior to aggregation.

### Distinction Between Consensus and Confidence
- **Consensus (Commit 01)**: The discrete agreement or disagreement of participating models on the canonical state assignment $\hat{y}_t^* \in \{0, \dots, K-1\}$. Represented via integer vote counts and model agreement flags.
- **Confidence (Commit 02)**: The calibrated posterior probability distribution $P(Y_t = k \mid \mathcal{M}, X)$ quantifying epistemic and aleatoric uncertainty.
