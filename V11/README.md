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
| **Commit 02** | **Ensemble Confidence Scoring & Explainability** | **COMPLETE** | `feat(ml): add ensemble confidence scoring` |

> [!IMPORTANT]
> **Strict Architectural Scope Boundaries:**
> - **V11 Commit 01**: Multi-model execution, canonical regime alignment, deterministic weighted consensus voting, agreement tracking, and model failure policies.
> - **V11 Commit 02**: Deterministic consensus support confidence scoring, granular explainability metrics, and continuous support distribution via `predict_proba()`.
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
  - Robust failure policies: `FAIL_FAST`, `SKIP_UNAVAILABLE`, and `BEST_EFFORT`.

---

## 4. Volume 11 Commit 02 Summary — Ensemble Confidence Scoring

### Core Deliverables

- **Confidence Domain Model (`domain/models.py`)**:
  - `EnsembleConfidence`: Frozen, validated model exposing structured explainable metrics:
    - `score: float`: Bounded $0.0 \le \text{score} \le 1.0$.
    - `supporting_model_count: int`: Number of active models voting for consensus.
    - `active_model_count: int`: Total number of active models participating.
    - `supporting_weight: float`: Active weight sum voting for the consensus regime.
    - `total_active_weight: float`: Total weight sum across all active models.
    - `agreement_ratio: float`: Proportion of active models voting for consensus.
    - `is_unanimous: bool`: Flag indicating 100% active model agreement.
    - `disagreeing_models: tuple[str, ...]`: Identifiers of dissenting active models.
  - `EnsembleRecord`: Extended with `confidence: float` and `confidence_breakdown: EnsembleConfidence`.
  - `RegimeEnsembleResult`: Extended with `confidence_scores: tuple[float, ...]`, `get_confidence_series()`, `get_average_confidence()`, and `get_confidence_records()`.

- **Confidence Mathematical Formulation (`infrastructure/ensemble/aggregation.py`)**:
  - **Weighted Voting Formula**:
    $$\text{confidence} = \frac{\sum_{m \in \mathcal{M}_{\text{active}}, \hat{y}_m = y^*} w_m}{\sum_{m \in \mathcal{M}_{\text{active}}} w_m}$$
  - **Unweighted / Equal Weights Formula**:
    $$\text{confidence} = \frac{|\{m \in \mathcal{M}_{\text{active}} : \hat{y}_m = y^*\}|}{|\mathcal{M}_{\text{active}}|}$$
  - **Deterministic Tie Behavior**:
    When two regimes tie with equal support (e.g. 50% vs 50%), the deterministic tie-breaker selects one regime, but confidence remains strictly un-inflated:
    $$\text{confidence} = 0.50$$
  - **Unavailable-Model Handling**:
    Under `SKIP_UNAVAILABLE` or `BEST_EFFORT`, unavailable models are excluded from both numerator and denominator. The denominator is strictly $\sum_{m \in \mathcal{M}_{\text{active}}} w_m$.

- **Continuous Support Distribution via `predict_proba()` (`infrastructure/models/ensemble.py`)**:
  - Computes continuous support distribution vector across all $K$ canonical regimes:
    $$P(k) = \frac{W_k}{W_{\text{total}}}$$
  - Guarantees each row sums to $1.0 \pm 10^{-6}$ and row elements are in $[0.0, 1.0]$.
  - For the consensus regime $y^*$, $P(y^*) = \text{confidence}$.

---

## 5. Confidence Interpretation & Critical Boundaries

> [!CAUTION]
> **What Ensemble Confidence Is NOT:**
> - **NOT Prediction Probability**: It does not represent the Bayesian likelihood of market states.
> - **NOT Return Probability**: It does not forecast positive asset returns or favorable performance.
> - **NOT Trading Signals**: It does not constitute a buy, sell, or hedge recommendation.
> - **NOT Ground Truth Certainty**: It measures internal model consensus agreement, not external truth.

```text
Ensemble Confidence ≠ Prediction Probability ≠ Market Return Probability ≠ Trading Recommendation
```

### Architectural Volume Boundaries

```text
V11 Commit 01 ──> Ensemble Orchestration & Multi-Model Consensus Voting
V11 Commit 02 ──> Ensemble Consensus Support Confidence & Explainability
Volume 12     ──> Platform Regime Transition Analytics & Markov Chains
```

**Volume 11 is now COMPLETE.**
