# Volume 13 — Portfolio Risk Analytics

**RegimeX — Open-Source Market Intelligence Platform**

---

## 1. Overview & Purpose

Volume 13 introduces the **Portfolio Risk Analytics Engine** for RegimeX.

While previous volumes focused on state classification and dynamics:
- **V08**: KMeans geometric baseline
- **V09**: Regime intelligence (profiles, durations, run lengths)
- **V10**: Probabilistic GMM density mixtures & HMM temporal dynamics
- **V11**: Consensus multi-model ensemble with agreement confidence scoring
- **V12**: Historical transition extraction & transition analytics

**Volume 13** shifts focus to **portfolio risk measurement**, establishing mathematically grounded, loss-oriented risk quantities for single asset and multi-asset return sequences.

```text
Market Data (V05)
       ↓
Validation & Storage (V06)
       ↓
Feature Engineering (V07)
       ↓
Regime Intelligence Stack (V08–V11)
       ↓
Transition Engine (V12)
       ↓
Volume 13: Portfolio Risk Analytics Engine
       ├── Return Series (Arithmetic & Log)
       ├── Return Statistics (Mean, Median, Sample Std ddof=1, Min, Max)
       ├── Volatility (Realized Period & Configurable Annualization)
       ├── Downside Risk (Sortino Semi-deviation below Target)
       ├── Maximum Drawdown (Running Peak, Troughs, Recovery)
       ├── Value at Risk (Loss-oriented Historical VaR)
       ├── Expected Shortfall (CVaR / Conditional Tail Loss)
       └── Multi-Asset Portfolio Returns (Time-aligned Weighted Returns)
```

---

## 2. Commit Roadmap

| Commit | Scope | Status | Official Commit Message |
| :--- | :--- | :---: | :--- |
| **Commit 01** | **Portfolio Risk Analytics** | **COMPLETE** | `feat(risk): implement portfolio risk analytics` |
| **Commit 02** | **Risk Metric Validation Suite** | **COMPLETE** | `test(risk): add risk metric validation suite` |

> [!IMPORTANT]
> **Strict Architectural Boundaries:**
> - **V13 Commit 01**: Foundational portfolio risk engine, single-asset and multi-asset returns, descriptive statistics, realized volatility, downside deviation, maximum drawdown, loss-oriented historical VaR, historical Expected Shortfall.
> - **V13 Commit 02**: Comprehensive validation suite, mathematical invariants, cross-metric consistency, anti-lookahead drawdown leakage protection, numerical stability, and portfolio alignment hardening.
> - **Volume 13 is COMPLETE.**
> - **V14+**: Event-driven backtesting engine, strategy performance analytics, portfolio optimization, AI assistants, FastAPI endpoints, and frontend components.

---

## 3. Volume 13 Commit 01 Architecture

### 3.1 Return Conventions

1. **Arithmetic Return**:
   $$r_t = \frac{P_t}{P_{t-1}} - 1$$
   Strictly validated for positive prices ($P_t > 0$) and finite values.

2. **Log Return**:
   $$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$
   Continuously compounded return formulation.

### 3.2 Return Statistics

- **Sample Standard Deviation ($ddof=1$)**:
  $$s = \sqrt{\frac{1}{N - 1} \sum_{t=1}^N (r_t - \bar{r})^2}$$
  Preserves Bessel's correction for unbiased sample variance estimation. Requires $N \ge 2$.
- **Mean & Median**: Point estimates of central tendency.
- **Minimum & Maximum**: Extremum range indicators.

### 3.3 Volatility & Annualization

- **Period Volatility**: Sample standard deviation of observed returns ($ddof=1$).
- **Annualized Volatility**:
  $$\sigma_{\text{ann}} = \sigma_{\text{period}} \times \sqrt{P}$$
  where $P = \text{periods\_per\_year}$ is an explicit, caller-configured factor (e.g., 252 for daily US equities, 365 for crypto, 52 for weekly, 12 for monthly). $\sqrt{252}$ is never hardcoded.

### 3.4 Downside Risk (Semi-Deviation)

Measures risk below a user-specified return benchmark $\tau$ (default $\tau = 0.0$):
$$\text{Downside Deviation} = \sqrt{\frac{1}{N} \sum_{t=1}^N \min(r_t - \tau, 0)^2}$$
Observations where $r_t \ge \tau$ carry zero downside penalty.

### 3.5 Maximum Drawdown (MDD)

Evaluates the deepest wealth decline from a running historical peak:
- Running peak without lookahead: $M_t = \max_{0 \le s \le t} W_s$.
- Drawdown at step $t$: $DD_t = \frac{W_t - M_t}{M_t} \le 0$.
- Maximum Drawdown: $MDD = \min_{t} DD_t$ (signed negative float).
- Identifies peak timestamp, trough timestamp, recovery timestamp, and recovery status.

### 3.6 Value at Risk (VaR) & Expected Shortfall (CVaR)

1. **Loss-Oriented Convention**:
   - $VaR_\alpha = - q_{1-\alpha}$ represents positive loss (e.g., $+0.035$ indicates a 3.5% loss).
   - $q_{1-\alpha}$ is the empirical return quantile at $1 - \alpha$.
2. **Expected Shortfall ($ES_\alpha$)**:
   - Average loss in the tail beyond VaR:
     $$ES_\alpha = -\mathbb{E}[R \mid R \le q_{1-\alpha}]$$
   - Consistent loss inequality: $ES_\alpha \ge VaR_\alpha$ in loss space.

### 3.7 Multi-Asset Portfolio Returns

Computes timestamp-aligned weighted portfolio returns:
$$r_{p,t} = \sum_{i=1}^M w_i r_{i,t}$$
- Strict timestamp matching across all constituent assets.
- Zero forward-filling and zero artificial zero-return imputation.
- Mismatched timestamps or lengths strictly raise `MismatchedAssetAlignmentError`.

---

## 4. Volume 13 Commit 02 — Risk Metric Validation Suite

Commit 02 hardens the portfolio risk engine with a comprehensive validation and reliability layer:

### 4.1 Mathematical Invariants
- **Return Extrema**: $\min(R) \le \operatorname{median}(R) \le \max(R)$ and $\min(R) \le \bar{R} \le \max(R)$.
- **Volatility Scaling**: $\sigma_{\text{ann}} = \sigma_{\text{period}} \times \sqrt{P}$, non-negative realized volatility $\ge 0$.
- **Downside Deviation**: Non-negative root-mean-square deviation below target $\tau$; returns $\ge \tau$ contribute zero penalty.
- **Drawdown Boundaries**: $DD_t \le 0$, $MDD \le 0$, $W_{\text{peak}} \ge W_{\text{trough}}$. Monotonic wealth growth produces $MDD = 0.0$.
- **Portfolio Linear Combination**: $r_{p,t} = \sum w_i r_{i,t}$ verified within numerical precision ($10^{-12}$).

### 4.2 Drawdown Anti-Leakage Invariant
- Proves running peak $M_t = \max_{0 \le s \le t} W_s$ is strictly backward-looking.
- Verifies that future massive market surges ($t_4 = 200$) never retroactively alter past drawdown events ($t_2 = 90, t_3 = 80$).
- Proves running drawdowns on dynamically truncated subseries $[0:k]$ match the full series evaluated up to $k$.

### 4.3 Cross-Metric Consistency
- Rigorously validates $ES_\alpha \ge VaR_\alpha$ across Gaussian, Student-t fat-tailed, skewed, all-negative, and small-sample distributions.
- Validates monotonic confidence ordering: $VaR_{0.99} \ge VaR_{0.95} \ge VaR_{0.90}$ and $ES_{0.99} \ge ES_{0.95} \ge ES_{0.90}$.

### 4.4 Numerical Stability
- Stable computation across extreme scales: microscopic returns ($\sim 10^{-8}$), large returns ($+500\%$, $-99\%$), identical prices, and large datasets ($N = 10,000$).
- Finite outputs guaranteed without NaN or Inf propagation.

### 4.5 Portfolio Alignment & UTC Enforcement
- Rejects misaligned constituent asset timestamps without forward filling or zero imputation.
- Rejects non-UTC or timezone-naive timestamps across all models and engine entry points.
