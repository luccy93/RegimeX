# Volume 10 — Probabilistic Regime Models

**RegimeX — Open-Source Market Intelligence Platform**

---

## 1. Overview & Purpose

Volume 10 introduces **probabilistic regime modeling** to RegimeX, advancing from the geometric KMeans clustering baseline of Volume 08 to statistical generative models.

Probabilistic models quantify uncertainty, provide smooth continuous posterior probabilities over all market regimes, and capture complex covariance structures across market indicators.

```text
V07 Feature Engineering
           ↓
V08 KMeans Baseline (Deterministic Clustering)
           ↓
V09 Regime Intelligence Layer (Descriptive Analytics)
           ↓
V10 Probabilistic Regime Models
    ├── Commit 01: Gaussian Mixture Model (GMM) [COMPLETE]
    └── Commit 02: Hidden Markov Model (HMM)   [NOT STARTED]
```

---

## 2. Commit Roadmap

| Commit | Scope | Status | Official Commit Message |
| :--- | :--- | :---: | :--- |
| **Commit 01** | **Probabilistic Regime Models (Gaussian Mixture Model)** | **COMPLETE** | `feat(ml): add probabilistic regime models` |
| **Commit 02** | **Hidden Markov Regime Model** | **NOT STARTED** | `feat(ml): add hidden Markov regime model` |

---

## 3. Volume 10 Commit 01 Summary — Gaussian Mixture Model

### Core Deliverables
- **Domain Models & Validation (`domain/models.py`, `domain/errors.py`)**:
  - `GMMModelConfig`: Frozen, validated configuration covering `n_components`, `covariance_type`, `random_state`, `max_iter`, `tol`, `reg_covar`, `init_params`, and `feature_names`.
  - `FitResult`: Extended with optional `lower_bound` (log-likelihood lower bound) and `converged` (EM convergence flag), with `inertia=0.0` for non-inertia probabilistic models.
  - Domain exceptions: `InvalidGMMConfigurationError`, `GMMFitError`, `GMMConvergenceError`, `GMMPredictionError`.
  - Pure Python and Pydantic v2 domain models with zero vendor or machine learning dependencies.
- **Infrastructure Implementation (`infrastructure/models/gmm.py`)**:
  - `GaussianMixtureRegimeDetector`: Implements `RegimeDetector` protocol via `sklearn.mixture.GaussianMixture` and `sklearn.preprocessing.StandardScaler`.
  - **Posterior Probability Estimation**: Genuine Bayesian posterior probabilities $P(z=k \mid x)$ where every row sums to $1.0 \pm 10^{-6}$ and all probabilities satisfy $0 \le p \le 1$.
  - **Component Canonicalization**: Deterministic, data-derived sorting based on unscaled component mean feature signatures, producing neutral canonical labels (`REGIME_0`, `REGIME_1`, ...).
  - **Probability Column Remapping**: Remaps posterior probability columns to align strictly with canonical regime indices.
  - **Argmax Consistency**: Invariant $\text{predict}(X)_i = \operatorname{argmax}_k P(z=k \mid x_i)$ holds across all observations.
  - **Anti-Leakage Guarantees**: `StandardScaler` fitted strictly on in-sample data; inference transforms frozen parameters without refitting.
  - **Metadata & Parameters**: Completely JSON-serializable primitives for auditability and research reproducibility.

---

## 4. Volume 10 Commit 02 Scope Notice (NOT STARTED)

Commit 02 will introduce temporal dynamic modeling via **Hidden Markov Models (HMM)**.
- First-order Markov chain state transitions.
- Transition probability matrices ($P(S_t = j \mid S_{t-1} = i)$).
- Emission distributions and Viterbi decoding.

*Commit 02 implementation has not yet begun.*
