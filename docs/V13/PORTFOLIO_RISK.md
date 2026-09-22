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
