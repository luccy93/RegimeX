# RegimeX — Portfolio Risk Analytics Engine

**Volume 13 — Technical Specification & Mathematical Formulation**  
**Module:** `apps/api/app/modules/portfolio_risk/`

---

## 1. Executive Summary

The **Portfolio Risk Analytics Engine** provides the mathematical and architectural core for computing risk metrics across discrete return and price series.

Operating downstream of the RegimeX market data, feature engineering, and regime transition pipelines, the risk engine delivers:
- Point-in-time arithmetic and log return series derivation.
- Descriptive central tendency and dispersion statistics.
- Realized and annualized volatility scaling.
- Benchmark-conditional downside semi-variance and semi-deviation.
- Running peak-to-trough historical drawdown and recovery dynamics.
- Loss-oriented Value at Risk (VaR) via deterministic historical simulation.
- Expected Shortfall (CVaR / Conditional VaR) tail loss aggregation.
- Multi-asset portfolio return aggregation with strict timestamp alignment.

---

## 2. Mathematical Formulations & Statistical Conventions

### 2.1 Return Series Formulations

Given a discrete, chronological sequence of strictly positive prices $\{P_t\}_{t=0}^N$ sampled at timestamps $\{T_t\}_{t=0}^N$:

1. **Arithmetic Return**:
   $$r_t = \frac{P_t - P_{t-1}}{P_{t-1}} = \frac{P_t}{P_{t-1}} - 1$$

2. **Log Return**:
   $$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

**Invariants**:
- Prices must be strictly positive: $P_t > 0$.
- Non-positive prices raise `InvalidPriceSeriesError`.
- Non-finite values ($\text{NaN}, \pm\infty$) raise `NonFiniteValueError`.

### 2.2 Return Descriptive Statistics

Given return observations $\{r_t\}_{t=1}^N$ with $N \ge 2$:

- **Arithmetic Mean**:
  $$\bar{r} = \frac{1}{N} \sum_{t=1}^N r_t$$

- **Median Return**:
  $$\tilde{r} = \operatorname{median}(\{r_t\})$$

- **Sample Standard Deviation (Bessel's Correction, $ddof=1$)**:
  $$s = \sqrt{\frac{1}{N - 1} \sum_{t=1}^N (r_t - \bar{r})^2}$$

- **Extrema**:
  $$r_{\min} = \min_{t} r_t, \quad r_{\max} = \max_{t} r_t$$

### 2.3 Volatility & Annualization

- **Period Realized Volatility**:
  $$\sigma_{\text{period}} = s$$

- **Annualized Volatility**:
  $$\sigma_{\text{ann}} = \sigma_{\text{period}} \times \sqrt{P}$$
  where $P$ is the explicit annualization frequency (`periods_per_year`):
  - Daily US equities: $P = 252$
  - Crypto markets (24/7/365): $P = 365$
  - Weekly observations: $P = 52$
  - Monthly observations: $P = 12$

### 2.4 Downside Risk (Sortino Semi-Deviation)

For a benchmark threshold $\tau$ (`target_return`, default $\tau = 0.0$):
$$\delta_{\text{downside}} = \sqrt{\frac{1}{N} \sum_{t=1}^N \min(r_t - \tau, 0)^2}$$

### 2.5 Maximum Drawdown & Recovery

Let $W_0 = 1.0$ and $W_t = W_{t-1} \times (1 + r_t)$ represent the cumulative wealth index.
- **Historical Running Peak (Zero Lookahead)**:
  $$M_t = \max_{0 \le s \le t} W_s$$
- **Drawdown at Step $t$**:
  $$DD_t = \frac{W_t - M_t}{M_t} \le 0$$
- **Maximum Drawdown**:
  $$MDD = \min_{0 \le t \le N} DD_t \le 0$$
- **Drawdown Magnitude**:
  $$|MDD| \ge 0$$
- **Recovery Detection**:
  $$\text{Recovery Timestamp} = \min \{ T_k \mid k > t_{\text{trough}} \land W_k \ge W_{\text{peak}} \}$$

### 2.6 Value at Risk (VaR) & Expected Shortfall (CVaR)

1. **Confidence Level**: $\alpha \in (0, 1)$ (e.g. 0.90, 0.95, 0.99).
2. **Empirical Return Quantile**: $q_{1-\alpha} = \text{quantile}(\{r_t\}, 1 - \alpha, \text{method}='linear')$.
3. **Loss-Oriented VaR**:
   $$VaR_\alpha = - q_{1-\alpha}$$
   A positive value indicates loss magnitude.
4. **Historical Expected Shortfall**:
   $$ES_\alpha = -\frac{1}{N_{\text{tail}}} \sum_{r_t \le q_{1-\alpha}} r_t$$
   Satisfies $ES_\alpha \ge VaR_\alpha$ in loss space.

---

## 3. Multi-Asset Portfolio Return Aggregation

Given $M$ constituent asset return series $\{r_{i,t}\}_{t=1}^N$ and normalized weights $\{w_i\}_{i=1}^M$:
$$r_{p,t} = \sum_{i=1}^M w_i r_{i,t}$$

**Strict Constraints**:
- $\sum_{i=1}^M w_i = 1.0 \pm 10^{-5}$ when `is_normalized=True`.
- Timestamps across all assets must align identically.
- No forward-filling, back-filling, or zero imputation. Mismatches raise `MismatchedAssetAlignmentError`.

---

## 4. Validation Invariants & Anti-Leakage Guarantees

### 4.1 Mathematical Invariants
The validation suite enforces strict mathematical invariants on every analytical output:
1. **Mean & Bound Consistency**:
   $$r_{\min} \le \bar{r} \le r_{\max}$$
   $$\min(r_t) \le \tilde{r} \le \max(r_t)$$
2. **Non-Negative Realized Volatility**:
   $$\sigma_{\text{period}} \ge 0, \quad \sigma_{\text{ann}} \ge 0$$
   $$\sigma_{\text{period}} = 0 \iff r_t = c \quad \forall t$$
3. **Downside Risk Monotonicity**:
   $$\delta_{\text{downside}}(\tau) \ge 0$$
   $$\tau_1 < \tau_2 \implies \delta_{\text{downside}}(\tau_1) \le \delta_{\text{downside}}(\tau_2)$$
   $$\forall r_t \ge \tau \implies \delta_{\text{downside}}(\tau) = 0$$
4. **Drawdown Invariants**:
   $$DD_t \le 0 \quad \forall t, \quad MDD = \min_t DD_t \le 0$$
   $$|MDD| = -MDD \ge 0$$
   $$W_{\text{trough}} = W_{\text{peak}} \times (1 + MDD)$$
5. **Linear Portfolio Aggregation**:
   $$r_{p,t} = \sum_{i=1}^M w_i r_{i,t}$$
   Linear combinations preserve exact expected returns and asset allocation bounds.

### 4.2 Anti-Lookahead Drawdown Protection
Running peak calculations must strictly adhere to causal point-in-time constraints:
$$M_t = \max_{0 \le s \le t} W_s$$
- $M_t$ is monotonically non-decreasing over time: $M_t \ge M_{t-1}$.
- Future asset rallies (e.g. $W_{t+k} \gg M_t$) cannot retroactively inflate $M_t$ or diminish historical drawdowns at time $t$.
- Trough timestamp strictly occurs on or after peak timestamp: $T_{\text{trough}} \ge T_{\text{peak}}$.
- Recovery timestamp strictly succeeds trough timestamp: $T_{\text{recovery}} > T_{\text{trough}}$.

### 4.3 Cross-Metric Consistency (Tail Risk Hierarchy)
Value at Risk ($VaR_\alpha$) and Expected Shortfall ($ES_\alpha$) obey rigorous coherent risk measure relations in loss space:
1. **Expected Shortfall Dominance**:
   $$ES_\alpha \ge VaR_\alpha \quad \forall \alpha \in (0, 1)$$
   The conditional average of losses exceeding the VaR quantile must be at least as severe as the quantile threshold itself across Gaussian, Student-t, fat-tailed, and empirical distributions.
2. **Confidence Monotonicity**:
   $$\alpha_1 < \alpha_2 \implies VaR_{\alpha_1} \le VaR_{\alpha_2} \quad \text{and} \quad ES_{\alpha_1} \le ES_{\alpha_2}$$

### 4.4 Strict UTC Timezone Compliance
All timestamp inputs and output metric representations enforce UTC awareness:
- Every timestamp $T_t$ must satisfy `ts.tzinfo is not None and ts.utcoffset() == timedelta(0)`.
- Naive datetime instances and non-UTC timezone offsets (e.g. EST, CET, IST) are rejected with `TemporalOrderError` or Pydantic validation errors.
- Strict chronological sorting without duplicate timestamps is required: $T_t > T_{t-1}$.

---

## 5. Numerical Stability & Precision Standards

1. **Micro-Scale Floating Point Precision**:
   - Return sequences with micro-fluctuations on the scale of $10^{-8}$ maintain full precision without arithmetic underflow or degradation in volatility calculations.
2. **Extreme Macro Fluctuations**:
   - Extreme asymmetric market movements (e.g., single-period drops of $-99\%$ or surges of $+500\%$) compute without division by zero, wealth index divergence, or mathematical overflow.
3. **High-Frequency & Scaled Sequences**:
   - Long sequence vectors ($N \ge 10,000$ points) process deterministically with $O(N)$ algorithmic complexity and zero memory accumulation.
4. **NaN & Infinity Containment**:
   - Zero tolerance for IEEE-754 non-finite values (`float('nan')`, `float('inf')`, `float('-inf')`). The engine intercepts non-finite values at the domain boundary with `NonFiniteValueError`.
