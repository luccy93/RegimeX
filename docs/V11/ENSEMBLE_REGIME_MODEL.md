# Regime Model Ensemble — Architecture & Consensus Specification

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V11 — Ensemble Regime Engine  
**Document Status:** Authoritative Technical Specification (V11 Commit 02 — Final)

---

## 1. Executive Summary & Purpose

Financial market regimes exhibit multi-faceted behavior that spans multiple statistical paradigms:
1. **Geometric Clustering (KMeans, V08)**: Groups observations based on Euclidean proximity to cluster centroids.
2. **Generative Density Mixtures (GMM, V10)**: Models observations as convex combinations of multivariate Gaussian densities with Bayesian posterior probabilities.
3. **Temporal Markov Chains (Gaussian HMM, V10)**: Encodes state transition matrices and state persistence across sequential time series.

Relying on any single paradigm exposes quantitative strategies to algorithm-specific biases and failure modes. Volume 11 introduces the **Regime Model Ensemble** (`RegimeModelEnsemble`), a production-grade orchestration engine that aligns heterogeneous model regimes into a canonical coordinate space and aggregates their predictions via deterministic consensus voting with interpretable confidence scoring.

```text
Feature Matrix X
       │
       ├──→ KMeans Baseline (Geometric Centroids) ──→ Raw State y_km
       ├──→ Gaussian Mixture Model (Density EM)   ──→ Raw State y_gmm
       └──→ Gaussian Hidden Markov Model (HMM)    ──→ Raw State y_hmm
                                                             │
                                                             ▼
                                                Regime Alignment Engine
                                                             │
                                                             ▼
                                                 Canonical States c_m
                                                             │
                                                             ▼
                                                    Ensemble Aggregator
                                                             │
                                                             ▼
                                            Consensus Regime y* + Confidence
```

---

## 2. Regime Identity Alignment

### 2.1 The Label Switching Problem
Unsupervised models discover clusters without semantic label ordering. Even when trained on identical data:
$$\text{KMeans Regime 0} \neq \text{GMM Component 0} \neq \text{HMM State 0}$$

Directly aggregating raw outputs without alignment yields corrupted consensus.

### 2.2 Mathematical Formulation of Centroid Alignment
Let $\mathcal{R}_{\text{ref}} = \{ (\mathbf{c}_j, j) \}_{j=0}^{K-1}$ be the reference model's canonical cluster profiles, where $\mathbf{c}_j \in \mathbb{R}^D$ is the mean feature vector of canonical regime $j$.

For a candidate model $m$ with cluster profiles $\mathcal{S}_m = \{ (\mathbf{s}_i, i) \}_{i=0}^{K-1}$:

1. **Cost Matrix Construction**:
   $$C_{ij} = \| \mathbf{s}_i - \mathbf{c}_j \|_2 = \sqrt{\sum_{d=1}^D (s_{i, d} - c_{j, d})^2}$$
   where features $d \in \{1, \dots, D\}$ are matched in strict lexicographical order of feature names.

2. **Optimal Bipartite Matching**:
   When $|\mathcal{S}_m| = |\mathcal{R}_{\text{ref}}| = K$, the alignment mapping $\pi: \{0, \dots, K-1\} \to \{0, \dots, K-1\}$ minimizes total Euclidean matching distance:
   $$\min_{\pi} \sum_{i=0}^{K-1} C_{i, \pi(i)}$$
   solved in polynomial time $O(K^3)$ using the Kuhn-Munkres (Hungarian) algorithm via `scipy.optimize.linear_sum_assignment`.

3. **Deterministic Tie-Breaking**:
   If multiple candidate pairings yield identical distances within numerical tolerance ($\epsilon = 10^{-12}$), ties are broken deterministically by sorting candidate pairs by $(\text{distance}, \text{target\_id}, \text{source\_id})$.

4. **Greedy Nearest-Neighbor Fallback**:
   When cluster counts differ ($|\mathcal{S}_m| \neq |\mathcal{R}_{\text{ref}}|$), each source cluster $i$ is assigned to the nearest canonical regime:
   $$\pi(i) = \operatorname{argmin}_{j} C_{ij}$$
   with deterministic tie-breaking to the lowest canonical regime ID.

---

## 3. Deterministic Consensus Aggregation

### 3.1 Weighted Voting
For each observation timestamp $t$, participating models $\mathcal{M}_{\text{avail}} \subseteq \mathcal{M}$ cast votes with normalized weights $w_m \ge 0$, where $\sum_{m \in \mathcal{M}_{\text{avail}}} w_m = 1.0$.

The aggregate vote for canonical regime $k$ is:
$$V(k, t) = \sum_{m \in \mathcal{M}_{\text{avail}}} w_m \cdot \mathbb{I}(\hat{y}_{m, t}^{\text{aligned}} = k)$$

The consensus regime is the argument of the maximum vote:
$$\hat{y}_t^* = \operatorname{argmax}_k V(k, t)$$

### 3.2 Tie-Breaking Mechanisms
When multiple regimes achieve equal maximum votes:
- **`LOWEST_REGIME_ID` (Default)**: Selects $\min \{ k : V(k, t) = \max_j V(j, t) \}$.
- **`MODEL_PRECEDENCE`**: Selects the regime chosen by the highest-priority model according to the order defined in `enabled_models`.

Both mechanisms are strictly deterministic and independent of dictionary hash order.

---

## 4. Model Availability & Failure Policies

| Failure Policy | Behavior on Model Failure | Condition for Consensus |
| :--- | :--- | :--- |
| **`FAIL_FAST`** | Immediately raises `EnsembleModelUnavailableError` | All enabled models must succeed |
| **`SKIP_UNAVAILABLE`** | Excludes failed model, renormalizes weights across remaining models | $|\mathcal{M}_{\text{avail}}| \ge \text{minimum\_required\_models}$ |
| **`BEST_EFFORT`** | Attempts prediction with any available models | $|\mathcal{M}_{\text{avail}}| \ge \text{minimum\_required\_models}$ |

If $|\mathcal{M}_{\text{avail}}| < \text{minimum\_required\_models}$, the ensemble raises `InsufficientUsableModelsError`.

---

## 5. Ensemble Confidence Scoring & Support Quantification

### 5.1 Confidence Semantics
Ensemble confidence explicitly measures **model agreement and active ensemble support** for the consensus regime:

$$\text{confidence} = \frac{\sum_{m \in \mathcal{M}_{\text{active}}, \hat{y}_m = y^*} w_m}{\sum_{m \in \mathcal{M}_{\text{active}}} w_m}$$

Where:
- For unanimous agreement ($\hat{y}_m = y^*$ for all $m$), $\text{confidence} = 1.0$.
- In a two-model 50/50 tie, if the tie-breaker picks regime 0, $\text{confidence} = 0.50$.
- Bounded strictly within $[0.0, 1.0]$.
- Denominator strictly includes only active, participating models; unavailable models are never included.

### 5.2 Structured Explainability Components
The ensemble output records detailed explainability data via `EnsembleConfidence`:
- `score`: Active weighted support fraction ($0.0 \le s \le 1.0$).
- `supporting_model_count`: Integer count of models agreeing with consensus.
- `active_model_count`: Total active models participating in the observation.
- `supporting_weight`: Sum of active weights casting votes for consensus.
- `total_active_weight`: Total active weight across participating models.
- `agreement_ratio`: Unweighted fraction $\frac{\text{supporting\_model\_count}}{\text{active\_model\_count}}$.
- `is_unanimous`: Boolean flag indicating 100% active model agreement.
- `disagreeing_models`: Tuple of model identifiers that voted for alternative regimes.

### 5.3 Continuous Support Probability Distribution
The `predict_proba()` method returns continuous support probability vectors across all $K$ canonical regimes:
$$P(k) = \frac{W_k}{W_{\text{total}}}$$
Where $\sum_{k=0}^{K-1} P(k) = 1.0 \pm 10^{-6}$ and $P(y^*) = \text{confidence}$.

### 5.4 Essential Non-Interpretations & Boundary Guarantees
```text
Ensemble Confidence ≠ Prediction Probability ≠ Market Return Probability ≠ Trading Recommendation
```
- **Not Statistical Ground Truth**: Quantifies internal model consensus, not market reality.
- **Not Forward Returns**: High agreement between models does not imply market profitability.
- **Strict Boundary**: Platform transition matrices and duration analytics belong exclusively to Volume 12.

---

## 6. Scope & Architecture Roadmap

```text
Volume 11 (COMPLETE)
    ├── Commit 01: Regime Model Ensemble Orchestration & Multi-Model Consensus (DONE)
    └── Commit 02: Ensemble Confidence Scoring & Structured Explainability (DONE)

Volume 12 (NEXT)
    ├── Empirical Regime Transition Analytics
    ├── Transition Probability Matrices (TPM)
    └── Regime Persistence, Duration, and Switching Dynamics
```
