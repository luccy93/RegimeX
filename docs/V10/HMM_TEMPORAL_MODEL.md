# Gaussian Hidden Markov Model (HMM) — Temporal Regime Architecture

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V10 — Probabilistic & Temporal Regime Models  
**Document Status:** Authoritative Technical Specification (V10 Commit 02)

---

## 1. Executive Summary & Purpose

In financial markets, regimes do not occur as independent, identically distributed (i.i.d.) draws from static clusters. Instead, market conditions exhibit **temporal persistence** and **state transition dynamics**: a low-volatility expansion regime tends to persist over extended periods before transitioning through a volatility spike into a crisis or contraction regime.

Volume 10 Commit 02 introduces **Gaussian Hidden Markov Models (HMM)** via `GaussianHMMRegimeDetector` to capture temporal state transitions and conditional emission dynamics across multivariate quantitative features.

```text
V08 KMeans Baseline (Independent Geometric Clusters)
        ↓
V10 GMM (Independent Bayesian Mixture Posteriors)
        ↓
V10 Gaussian HMM (Temporal State Dynamics & Sequence Decoding)
```

---

## 2. Mathematical Formalism

A first-order discrete-time Hidden Markov Model with continuous Gaussian emissions is parameterized by the tuple $\lambda = (\pi, A, \mu, \Sigma)$:

```text
Hidden States:       S_1  ──→  S_2  ──→  S_3  ──→ ... ──→  S_T
                      │         │         │                 │
Emitted Features:     ↓         ↓         ↓                 ↓
                     X_1       X_2       X_3               X_T
```

### 2.1 Initial State Distribution ($\pi$)
The probability of beginning in state $i$ at timestamp $t=1$:

$$\pi_i = P(S_1 = i), \quad \sum_{i=1}^K \pi_i = 1, \quad \pi_i \ge 0$$

### 2.2 Transition Probability Matrix ($A$)
The first-order stationary probability of transitioning from hidden regime $i$ at time $t-1$ to hidden regime $j$ at time $t$:

$$A_{ij} = P(S_t = j \mid S_{t-1} = i)$$

where each row forms a valid simplex:

$$\sum_{j=1}^K A_{ij} = 1, \quad \forall i \in \{1, \dots, K\}, \quad A_{ij} \ge 0$$

> [!NOTE]
> The transition matrix $A$ operates strictly as an internal mathematical parameter of the fitted HMM model to enable sequence decoding and posterior inference. Platform-level transition analytics, historical transition matrices, and forecasting are reserved for Volume 12 (`TransitionAnalyticsService`).

### 2.3 Multivariate Gaussian Emissions
Conditional on hidden state $S_t = i$, the observation vector $X_t \in \mathbb{R}^D$ is generated from a multivariate normal distribution:

$$X_t \mid S_t = i \sim \mathcal{N}(\mu_i, \Sigma_i)$$

with probability density:

$$P(X_t \mid S_t = i) = \frac{1}{(2\pi)^{D/2} |\Sigma_i|^{1/2}} \exp\left( -\frac{1}{2} (X_t - \mu_i)^\top \Sigma_i^{-1} (X_t - \mu_i) \right)$$

---

## 3. Supported Covariance Structures

`GaussianHMMRegimeDetector` supports all standard covariance geometries via `HMMModelConfig.covariance_type`:

| Covariance Type | Description | Free Covariance Parameters | Applicable Regime Scenario |
| :--- | :--- | :--- | :--- |
| `full` (Default) | Each state has independent general symmetric positive-definite $\Sigma_k$. | $K \cdot \frac{D(D+1)}{2}$ | General regime geometries where cross-feature correlations shift per regime. |
| `tied` | All states share an identical covariance matrix $\Sigma$. | $\frac{D(D+1)}{2}$ | Regimes differ only in feature means; covariance structures remain invariant. |
| `diag` | Each state has diagonal covariance $\Sigma_k = \operatorname{diag}(\sigma_{k1}^2, \dots, \sigma_{kD}^2)$. | $K \cdot D$ | Features conditionally uncorrelated within regime; computationally robust against overfitting. |
| `spherical` | Each state has spherical isotropic variance $\Sigma_k = \sigma_k^2 I$. | $K$ | Equal variance across dimensions; low-parameter constraint. |

---

## 4. Sequence Decoding vs. Posterior Probabilities

An essential distinction between static mixture models (GMM) and temporal sequence models (HMM) lies in the difference between **global sequence decoding** and **pointwise posterior inference**:

### 4.1 Viterbi Sequence Decoding (`predict()`)
`predict()` executes the Viterbi dynamic programming algorithm to discover the single most likely path of hidden states across the entire sequence:

$$S_{1:T}^* = \operatorname*{arg\,max}_{S_1, \dots, S_T} P(S_1, \dots, S_T \mid X_1, \dots, X_T)$$

Viterbi accounts for transition penalties $A_{ij}$. A transition into an unlikely state is suppressed if $A_{ij} \approx 0$, even if the local emission likelihood $P(X_t \mid S_t = j)$ is high.

### 4.2 Forward-Backward Posterior Probabilities (`predict_proba()`)
`predict_proba()` calculates marginal posterior state probabilities for each individual time step using the forward-backward algorithm:

$$\gamma_t(i) = P(S_t = i \mid X_1, \dots, X_T) = \frac{\alpha_t(i) \beta_t(i)}{\sum_{j=1}^K \alpha_t(j) \beta_t(j)}$$

### 4.3 Mathematical Independence of `predict()` and `predict_proba()`
Because Viterbi optimizes the joint sequence likelihood $P(S_{1:T} \mid X_{1:T})$, the decoded state at step $t$ is **not guaranteed** to equal $\operatorname*{arg\,max}_i \gamma_t(i)$. For example, taking pointwise argmax can produce state transitions with zero transition probability ($A_{ij} = 0$). RegimeX preserves mathematical honesty: `predict()` returns the canonicalized Viterbi sequence, and `predict_proba()` returns canonicalized posterior vectors.

---

## 5. Deterministic Component Canonicalization & Remapping

### 5.1 Permutation Invariance
Hidden state indices ($0, \dots, K-1$) in HMM are arbitrary permutations sensitive to initialization seeds. Uncontrolled raw IDs produce unstable regime assignments across research runs.

### 5.2 Canonicalization Algorithm
To guarantee deterministic reproducibility:
1. **Unscale Emission Means**:
   $$\mu_k^{\text{unscaled}} = \operatorname{scaler.inverse\_transform}(\mu_k^{\text{scaled}})$$
2. **Compute Invariant Emission Signature**:
   Construct an invariant tuple of unscaled emission means sorted alphabetically by feature name:
   $$\operatorname{sig}(k) = \left( \mu_k^{\text{unscaled}}[f] \right)_{f \in \operatorname{sorted}(\text{feature\_names})}$$
3. **Lexicographical Sort & Mapping**:
   Sort raw states by $(\operatorname{sig}(k), k)$ to assign canonical indices $\{0, \dots, K-1\}$:
   $$\text{raw\_state\_id} \xrightarrow{\text{sort}} \text{canonical\_regime\_id}$$
4. **Canonical Profile Labeling**:
   Assign neutral canonical labels: `REGIME_0`, `REGIME_1`, ..., `REGIME_{K-1}`.

### 5.3 Consistent Posterior Remapping
The posterior probability matrix is column-remapped so column $c$ aligns strictly with `REGIME_c`:

$$\operatorname{canonical\_probs}[:, c] = \operatorname{raw\_probs}[:, \operatorname{canonical\_to\_raw}[c]]$$

---

## 6. Anti-Leakage Preprocessing & Temporal Ordering

1. **Strictly In-Sample Scaling**:
   `StandardScaler` is fitted strictly on in-sample training observations during `fit()`.
2. **Frozen Inference Parameters**:
   Inference (`predict` and `predict_proba`) applies frozen scaler parameters without updating means or variances.
3. **Historical Sequence Integrity**:
   Observations must be strictly chronologically ordered with timezone-aware timestamps. Feature matrices reject naive datetimes, duplicate timestamps, and inverted sequences.

---

## 7. Numerical Stability & Regularization

1. **Covariance Floor (`min_covar`)**:
   Enforces a positive minimum variance along covariance diagonals (default `1e-3`) to prevent collapse during Baum-Welch EM.
2. **Log-Domain Computation (`implementation='log'`)**:
   Underflow in forward-backward recursions is avoided by performing alpha/beta computations in log-space.
3. **Finite Value Verification**:
   Raw probabilities are inspected to guarantee absence of NaN or infinite values prior to normalization.

---

## 8. Limitations & Non-Goals

- **First-Order Markov Property**: Transitions depend only on the immediate predecessor state $S_{t-1}$. Higher-order persistence or semi-Markov dwell times require specialized models.
- **Local Likelihood Maxima**: EM converges to local maxima; parameter estimation is sensitive to random initialization.
- **No Forward Returns Guarantees**: State posterior probabilities quantify statistical likelihood under historical data; they do not forecast future market returns or provide trading signals.
- **Non-Stationarity**: Macroeconomic structural shifts may violate the constant transition matrix assumption.
