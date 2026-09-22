# Volume 12 — Regime Transition Probability Engine

**RegimeX — Open-Source Market Intelligence Platform**

---

## 1. Overview & Purpose

Volume 12 introduces the **Regime Transition Probability Engine**, establishing a statistically grounded foundation for analyzing how market regimes evolve over time.

While previous volumes focused on classifying static market states and forming consensus:
- **V08**: KMeans geometric clustering baseline
- **V09**: Regime intelligence (profiles, durations, run lengths)
- **V10**: Probabilistic GMM density mixtures & HMM temporal dynamics
- **V11**: Consensus multi-model ensemble with agreement confidence scoring

**Volume 12** shifts focus to **temporal state transitions**, quantifying empirical transition dynamics between identified regimes.

```text
V08 KMeans / V10 GMM / V10 HMM
            ↓
V11 Regime Model Ensemble
            ↓
V11 Consensus Confidence
            ↓
V12 Regime Transition Probability Engine (Historical Transitions & Matrices)
```

---

## 2. Commit Roadmap

| Commit | Scope | Status | Official Commit Message |
| :--- | :--- | :---: | :--- |
| **Commit 01** | **Regime Transition Probability Engine** | **COMPLETE** | `feat(regime): implement transition probability engine` |
| **Commit 02** | **Transition Analytics & Persistence Dynamics** | **COMPLETE** | `feat(regime): add transition analytics` |

> [!IMPORTANT]
> **Strict Architectural Volume Boundaries:**
> - **V11**: Ensemble orchestration, canonical alignment, and consensus confidence scoring.
> - **V12 Commit 01**: Historical transition extraction, transition count matrix, row-normalized transition probability matrix, temporal validation, sample size preservation, deterministic query APIs, and ensemble integration.
> - **V12 Commit 02**: Transition analytics layer: regime persistence, incoming/outgoing frequency, deterministic destination rankings, Shannon transition entropy, diversity metrics, regime change matrix, and global/regime analytical summaries.
> - **Volume 13+**: Risk computation, portfolio optimization, strategy backtesting, AI assistants, FastAPI endpoints, and frontend components.

---

## 3. Volume 12 Commit 01 Architecture

### 3.1 Transition Definition & Semantics

A transition is evaluated between consecutive valid chronological observations $(S_{t-1}, S_t)$:

1. **State Transitions (Markov Chain Context)**:
   In Markov chain theory, every consecutive pair represents a step transition:
   - **Persistence / Self-Transition**: $S_{t-1} = i \to S_t = i$.
   - **Regime Shift**: $S_{t-1} = i \to S_t = j$ where $i \neq j$.
   Both are tracked in the **Transition Count Matrix** ($K \times K$) and normalized into the **Transition Probability Matrix** ($K \times K$), where diagonal entries $P(i \to i)$ represent empirical state persistence.

2. **Discrete Transition Events (`TransitionRecord`)**:
   Point-in-time state changes where $S_t \neq S_{t-1}$ are explicitly captured as `TransitionRecord` models with origin regime, destination regime, and the timezone-aware timestamp when the new regime commenced.

### 3.2 Transition Count & Probability Matrix

For $K$ canonical regimes $\{0, 1, \dots, K-1\}$, the engine computes:

1. **Transition Count Matrix $C_{i,j}$**:
   $$C_{i,j} = \sum_{t=1}^{N-1} \mathbb{I}(S_{t-1} = i \land S_t = j)$$

2. **Empirical Maximum Likelihood Estimation (MLE) Probabilities $P(i \to j)$**:
   $$P(i \to j) = \frac{C_{i,j}}{\sum_{k=0}^{K-1} C_{i,k}} = \frac{C_{i,j}}{N_i}$$
   where $N_i = \sum_{k=0}^{K-1} C_{i,k}$ is the total number of transitions originating from regime $i$.

3. **Simplex Invariant**:
   For any row with $N_i > 0$:
   $$\sum_{j=0}^{K-1} P(i \to j) = 1.0 \pm 10^{-6}$$
   For absorbing or unobserved regimes ($N_i = 0$), all row probabilities are strictly $0.0$.

### 3.3 Sample Size Transparency

To prevent sample-size illusions (e.g. confusing $3/4 = 0.75$ with $750/1000 = 0.75$), every transition probability preserves its supporting counts:
```python
prob = result.get_transition_probability(source_regime=0, target_regime=1)
print(prob.probability)  # 0.75
print(prob.count)        # 3
print(prob.sample_size)  # 4
```

### 3.4 Smoothing Policy

- **Empirical MLE**: Unobserved transitions ($C_{i,j} = 0$) strictly evaluate to $0.0$.
- **No Artificial Smoothing**: Laplace, Lidstone, or Bayesian Dirichlet smoothing is deliberately not applied in Commit 01 to preserve empirical ground truth.

### 3.5 Temporal Validation & Ordering

- Timestamps must be timezone-aware UTC `datetime` objects.
- Non-monotonic or duplicate timestamps are strictly rejected by default with `InvalidTransitionSequenceError`.
- If `sort_chronologically=True`, the engine sorts observations chronologically while verifying no duplicates exist.
- Future-to-past lookahead is strictly prevented.

---

## 4. Integration with Regime Intelligence Stack

The `RegimeTransitionEngine` provides direct adapters for all preceding regime stack stages without rerunning underlying models:

```python
from app.modules.regime_transition import RegimeTransitionEngine

engine = RegimeTransitionEngine()

# 1. From V11 Ensemble Consensus Result
result_ensemble = engine.compute_from_ensemble_result(ensemble_result)

# 2. From V08/V10 RegimeDetectionResult
result_detector = engine.compute_from_detection_result(detection_result)

# 3. From V09 RegimeAssignments
result_assignments = engine.compute_from_assignments(assignments)

# 4. From raw chronological series
result_series = engine.compute_from_series(timestamps, regime_ids)
```

---

## 5. Domain Models & Error Hierarchy

### Domain Models (`domain/models.py`)
- `TransitionRecord`: Point-in-time regime change event.
- `TransitionProbability`: Pairwise probability $P(i \to j)$ with sample size and count.
- `TransitionCountMatrix`: Immutable $K \times K$ integer matrix with row totals and query methods.
- `TransitionProbabilityMatrix`: Immutable $K \times K$ float matrix with simplex validation.
- `RegimeTransitionResult`: Complete transition analysis container.

### Error Hierarchy (`domain/errors.py`)
- `RegimeTransitionError`: Base exception inheriting from `RegimeXError`.
  - `InsufficientTransitionDataError`: Raised when sequence length $< 2$.
  - `InvalidTransitionSequenceError`: Raised on temporal order violations or duplicate timestamps.
  - `InvalidRegimeValueError`: Raised on invalid/negative/non-integer regime IDs or NaNs.
  - `RegimeTransitionComputationError`: Algorithmic/numerical failure.

---

## 6. Volume 12 Commit 02 Architecture — Transition Analytics

The **Transition Analytics** layer (`RegimeTransitionAnalytics`) extends raw transition matrices with actionable downstream metrics:

### 6.1 Core Metrics & Guarantees

1. **Regime Persistence**:
   - Diagonal empirical probability $P(i \to i)$.
   - Persistence count $C_{i,i}$ preserved alongside rates.

2. **Transition Frequency & Flow**:
   - Outgoing transitions $N_i = \sum_j C_{i,j}$.
   - Incoming transitions $M_j = \sum_i C_{i,j}$.
   - Self-transitions $C_{i,i}$.
   - Regime changes $N_i - C_{i,i}$.

3. **Rate Invariants**:
   - Per-regime: $\text{persistence\_probability} + \text{change\_rate} = 1.0 \pm 10^{-5}$ (for $N_i > 0$).
   - Sequence-wide: $\text{global\_persistence\_rate} + \text{global\_change\_rate} = 1.0 \pm 10^{-5}$.

4. **Deterministic Destination Rankings (`RankedDestination`)**:
   - Sorted deterministically: Probability $\downarrow$, Count $\downarrow$, Target Regime ID $\uparrow$.
   - Includes most likely destination $j^* = \operatorname{argmax}_j P(i \to j)$.

5. **Transition Concentration & Entropy**:
   - Shannon transition entropy: $H(i) = -\sum_{j=0}^{K-1} P(i \to j) \ln P(i \to j)$ (nats, natural log base $e$).
   - Convention: $0 \ln 0 = 0$; $H(i) = 0.0$ for deterministic or unobserved transitions.

6. **Transition Diversity**:
   - Destination count: number of distinct targets $j$ observed from $i$.
   - Source count: number of distinct origins $k$ leading to destination $j$.

7. **Regime Change Matrix**:
   - Matrix with diagonal ($i = j$) zeroed out.
   - Normalized conditional shift distribution: $P_{\text{shift}}(i \to j) = \frac{C_{i,j}}{\sum_{k \neq i} C_{i,k}}$.

8. **Analytical Summaries**:
   - `TransitionRegimeAnalytics`: Per-regime intelligence breakdown.
   - `GlobalTransitionAnalytics`: Global flow summary, most persistent/fluid regimes, change rates.
   - `TransitionAnalyticsResult`: Master container providing high-performance query methods.
