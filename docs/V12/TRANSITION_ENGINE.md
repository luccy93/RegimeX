# RegimeX — Regime Transition Probability Engine

**Volume 12 — Technical Specification & Architecture**  
**Module:** `apps/api/app/modules/regime_transition/`

---

## 1. Executive Summary

The **Regime Transition Probability Engine** provides the mathematical and architectural framework for analyzing how market regimes evolve and switch over time.

Building directly upon the foundation established in Volumes 08–11:
- **V08 KMeans**: Geometric feature space partitioning
- **V09 Intelligence**: Empirical frequency, duration, and feature profiling
- **V10 GMM & HMM**: Gaussian density mixtures and Markovian latent state modeling
- **V11 Ensemble**: Multi-model canonical consensus alignment with confidence scoring

The Transition Engine operates as a dedicated consumer of canonical regime classifications, transforming historical sequences of regime assignments into empirical Maximum Likelihood Estimation (MLE) state transition probability matrices.

---

## 2. Transition Definition & Semantics

### 2.1 Formal Transition Definition

Let $\{S_t\}_{t=1}^N$ be a chronologically ordered sequence of discrete canonical market regime assignments, where $S_t \in \{0, 1, \dots, K-1\}$ and each observation occurs at a timezone-aware UTC timestamp $T_t$.

Between any two consecutive timestamps $(T_{t-1}, T_t)$, a **step transition** occurs from $S_{t-1}$ to $S_t$.

### 2.2 Self-Transition vs. Regime Shift Semantics

To prevent conceptual conflation between regime persistence and regime shifts:

1. **State Persistence ($S_{t-1} = S_t$)**:
   - The regime remains unchanged across time step $t$.
   - In Markov chain modeling, this is represented by the diagonal entries $P(i \to i)$ of the transition probability matrix.
   - Preserved in the **Transition Count Matrix** and **Transition Probability Matrix** by default.

2. **Regime Shift ($S_{t-1} \neq S_t$)**:
   - The market switches from state $i$ to state $j$ ($i \neq j$).
   - Explicitly extracted as discrete `TransitionRecord` domain objects capturing:
     - `source_regime`: Origin regime index $i$
     - `target_regime`: Destination regime index $j$
     - `timestamp`: UTC timestamp $T_t$ at which regime $j$ took effect
     - `source_label`, `target_label`: Canonical string labels

---

## 3. Mathematical Formulation

### 3.1 Transition Count Matrix

For a system with $K$ canonical regimes, the empirical transition count matrix $\mathbf{C} \in \mathbb{N}_0^{K \times K}$ is tabulated as:

$$C_{i,j} = \sum_{t=2}^N \mathbb{I}(S_{t-1} = i \land S_t = j)$$

where:
- $\mathbb{I}(\cdot)$ is the indicator function.
- Row $i$ corresponds to the source regime (From).
- Column $j$ corresponds to the target regime (To).
- The total transitions originating from regime $i$ is:
  $$N_i = \sum_{j=0}^{K-1} C_{i,j}$$
- The total transitions in the sequence is:
  $$N_{\text{total}} = \sum_{i=0}^{K-1} N_i = N - 1$$

### 3.2 Maximum Likelihood Transition Probabilities

Under the empirical Maximum Likelihood Estimation (MLE) framework for a stationary Markov chain, transition probabilities are row-normalized empirical frequencies:

$$P(i \to j) = \begin{cases}
\dfrac{C_{i,j}}{N_i}, & \text{if } N_i > 0 \\
0.0, & \text{if } N_i = 0
\end{cases}$$

### 3.3 Simplex Invariant

For every regime $i$ where $N_i > 0$, the probability distribution forms a valid probability simplex:

$$\sum_{j=0}^{K-1} P(i \to j) = 1.0 \pm 10^{-6}$$

For unobserved regimes ($N_i = 0$), $P(i \to j) = 0.0$ for all $j \in \{0, \dots, K-1\}$, representing an absorbing or unreached state.

---

## 4. Sample Size Awareness & Statistical Integrity

### 4.1 Sample-Size Transparency

A core failure mode of quantitative transition analysis is evaluating probabilities without context on observation counts:
- $P(0 \to 1) = 0.75$ derived from $3/4$ transitions carries high estimation variance.
- $P(0 \to 1) = 0.75$ derived from $750/1000$ transitions carries high statistical confidence.

To guarantee transparency, `TransitionProbability` objects retain both the probability and supporting sample counts:
```python
@dataclass(frozen=True)
class TransitionProbability:
    source_regime: int
    target_regime: int
    count: int                             # C_{i, j}
    total_transitions_from_source: int     # N_i
    probability: float                     # C_{i, j} / N_i
```

### 4.2 Smoothing Policy

- **Commit 01 Standard**: Strictly empirical MLE.
- **Zero Fabrication**: Unobserved transitions have empirical probability $0.0$.
- **No Artificial Smoothing**: Laplace, Lidstone, or Dirichlet priors are excluded to avoid injecting subjective probability mass into empirical market history.

---

## 5. Temporal Ordering & Input Validation

The transition engine enforces strict temporal validation before extracting transitions:

1. **Timezone Awareness**: All timestamps must be timezone-aware (UTC required). Naive timestamps raise `InvalidTransitionSequenceError`.
2. **Monotonicity**: By default (`sort_chronologically=False`), timestamps must be strictly increasing: $T_t > T_{t-1}$. Unsorted series raise `InvalidTransitionSequenceError`.
3. **Duplicate Prevention**: Identical consecutive timestamps are strictly prohibited and raise `InvalidTransitionSequenceError`.
4. **Chronological Sorting**: When `sort_chronologically=True`, the engine sorts observations by timestamp before processing.
5. **Deterministic Missing Data Handling**:
   - `None` or missing regimes raise `InvalidRegimeValueError`.
   - Non-integer, float, NaN, infinite, or negative regime IDs raise `InvalidRegimeValueError`.
   - Sequences with fewer than 2 valid observations raise `InsufficientTransitionDataError`.

---

## 6. Integration Architecture

The `RegimeTransitionEngine` provides decoupled adapters that accept outputs from any preceding regime engine:

```text
┌─────────────────────────────────────────────────────────┐
│                    Regime Detection                     │
│  (KMeansRegimeDetector, GaussianHMMRegimeDetector,      │
│   GaussianMixtureRegimeDetector, RegimeModelEnsemble)   │
└───────────────────────────┬─────────────────────────────┘
                            │ Output: RegimeRecords / EnsembleRecords
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Regime Transition Engine                   │
│          (app.modules.regime_transition)                │
│                                                         │
│  1. Temporal Validation (strictly ascending UTC)        │
│  2. Transition Extraction (consecutive step pairs)      │
│  3. Transition Count Matrix (K x K counts)              │
│  4. Row Normalization (empirical MLE)                   │
│  5. Transition Result Assembly                          │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
           RegimeTransitionResult (Immutable)
            ├── count_matrix: TransitionCountMatrix
            ├── probability_matrix: TransitionProbabilityMatrix
            ├── transitions: tuple[TransitionRecord, ...]
            └── query APIs: get_transition_probability(i, j)
```

### Supported Ingestion Protocols
- `compute_from_ensemble_result(result: RegimeEnsembleResult)`: Analyzes consensus canonical ensemble regimes.
- `compute_from_detection_result(result: RegimeDetectionResult)`: Analyzes single-model canonical regimes.
- `compute_from_assignments(assignments: Sequence[RegimeAssignment])`: Analyzes V09 intelligence assignments.
- `compute_from_series(timestamps, regime_ids, labels)`: Analyzes raw series.

---

## 7. Volume Roadmap & Boundaries

```text
Volume 11: Ensemble Consensus & Multi-Model Agreement Confidence
                ↓
Volume 12 Commit 01: Regime Transition Probability Engine (Historical MLE) [COMPLETE]
                ↓
Volume 12 Commit 02: Transition Analytics & Persistence Dynamics [COMPLETE]
                ↓
Volume 13: Regime-Conditional Risk Engine
```

**Volume 12 is COMPLETE.**

---

## 8. Transition Analytics Architecture (Commit 02)

The **Transition Analytics** layer (`RegimeTransitionAnalytics`) builds directly on `RegimeTransitionResult`:

### 8.1 Domain Models
- `RankedDestination`: Target regime, target label, probability, transition count, and rank index.
- `TransitionRegimeAnalytics`: Per-regime intelligence covering:
  - Persistence probability $P(i \to i)$ and count $C_{i,i}$.
  - Outgoing, incoming, self, and regime change counts.
  - Regime change rate $1 - P(i \to i)$.
  - Most likely destination regime ID and associated probability.
  - Destination count and incoming source count.
  - Transition concentration and Shannon entropy $H(i) = -\sum P \ln P$.
  - Deterministic destination rankings tuple.
- `GlobalTransitionAnalytics`: Global flow summary:
  - Total transitions, self-transitions, regime changes.
  - Global persistence rate and global change rate ($\text{sum} = 1.0 \pm 10^{-5}$).
  - Regime change matrix (diagonal zeroed out) and conditional shift probability matrix.
  - Most persistent regime and most fluid (least persistent) regime IDs.
- `TransitionAnalyticsResult`: Complete transition analytics container with accessor queries.

### 8.2 Invariants & Precision
- Zero lookahead: Operates solely on historical transition matrices.
- Zero external ML dependencies: Pure standard library and NumPy numerical core.
- Sample-size transparency: Counts are preserved alongside probabilities.
- Deterministic ranking: Ordered by probability descending, count descending, target regime ID ascending.
