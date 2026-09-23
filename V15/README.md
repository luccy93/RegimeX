# Volume 15: Strategy Comparison Analytics

## 1. Executive Summary

Volume 15 introduces the production-grade, deterministic **Strategy Comparison Analytics** layer for the RegimeX quantitative platform.

Operating directly downstream of the Volume 14 Event-Driven Backtesting Engine and the Volume 13 Portfolio Risk Engine, Volume 15 enables quantitative researchers to systematically contrast multiple backtest simulations over a mathematically consistent, common evaluation period.

```text
V14 BacktestResult(s)
        ↓
StrategyComparisonInput(s)
        ↓
Strict Validation (Unique IDs, Equity > 0, UTC Datetimes, Finite Metrics)
        ↓
Common Period Alignment [max(all starts), min(all ends)]
        ↓
Metric Extraction & V13 PortfolioRiskEngine Delegation
        ↓
Trade Accounting (Weighted Average Cost Basis, Exit PnL, Win/Loss Rates)
        ↓
Deterministic Pairwise Comparisons (A - B Deltas, Zero-Safe Relative Differences)
        ↓
Immutable StrategyComparisonResult
```

> [!IMPORTANT]
> **Descriptive Analytics Disclaimer**:
> Strategy comparison describes historical backtest results. It does not determine which strategy should be selected or used for future trading. No ranking, score, "winner", automated strategy selection, or predictive recommendation is implemented.

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(backtest): add strategy comparison analytics` | **DONE** |

---

## 3. Architecture & Domain Contracts

### 3.1 Input Abstraction: `StrategyComparisonInput`
Defined in `apps/api/app/modules/backtesting/domain/models.py`:
- `strategy_id: str`: Unique, non-empty, whitespace-stripped identifier.
- `display_name: str`: Human-readable label (defaults to `strategy_id` if empty).
- `backtest_result: BacktestResult`: Immutable simulation output produced by V14.
- Invariants:
  - Input collection must contain $\ge 1$ strategy ($N=0$ raises `EmptyComparisonError`).
  - IDs must be unique within a comparison run (duplicates raise `DuplicateStrategyIdError`).
  - Initial capital must be strictly positive and finite ($E_0 > 0$, else `InvalidEquityError` / `NonFiniteValueError`).

### 3.2 Common Evaluation Period: `ComparisonPeriod`
To guarantee mathematical comparability without lookahead or temporal distortion, strategies are aligned to their overlapping intersection:
$$\text{comparison\_start} = \max_{s \in S} (s.\text{start\_timestamp})$$
$$\text{comparison\_end} = \min_{s \in S} (s.\text{end\_timestamp})$$

- If $\text{comparison\_start} > \text{comparison\_end}$: No temporal intersection exists $\to$ raises `IncompatibleEvaluationPeriodError`.
- If $\text{comparison\_start} == \text{comparison\_end}$: Instantaneous window $\to$ raises `IncompatibleEvaluationPeriodError`.
- When an individual strategy's start or end extends beyond the common intersection, its equity curve and fills are sliced strictly within $[\text{comparison\_start}, \text{comparison\_end}]$, and `is_truncated = True` is recorded.
- Equity curves must retain $\ge 3$ snapshots ($\ge 2$ return observations) within the window; otherwise, `InsufficientComparisonDataError` is raised.

### 3.3 Completed Trade Definition
In alignment with Volume 14 `SimulatedPortfolio`, a **completed trade** is defined as an execution fill that reduces or closes an existing open position (an exit fill), realizing gross profit or loss against the weighted-average cost basis established by preceding entry fills:
$$\text{trade\_pnl} = (p_{\text{exit}} - p_{\text{avg\_entry}}) \times q_{\text{exit}}$$
- `winning_trades`: Count of exit fills where $\text{trade\_pnl} > 0$.
- `losing_trades`: Count of exit fills where $\text{trade\_pnl} < 0$.
- `win_rate`: $\frac{\text{winning\_trades}}{\text{completed\_trades}}$ if $\text{completed\_trades} > 0$ else `None`.
- `average_trade_pnl`: $\frac{\sum \text{trade\_pnl}}{\text{completed\_trades}}$ if $\text{completed\_trades} > 0$ else `None`.
- Transaction fees and commissions are tracked independently in `total_fees` and `fees_delta` without corrupting gross trade PnL.

---

## 4. Descriptive Metrics & V13 Delegation

### 4.1 Single Strategy Summary (`StrategySummary`)
Exposes standardized descriptive statistics over the common period:
- **Capital & Wealth Dynamics**: `initial_equity`, `final_equity`, `absolute_pnl` ($E_{\text{end}} - E_{\text{start}}$), `total_return` ($\frac{E_{\text{end}}}{E_{\text{start}}} - 1$), `annualized_return`.
- **Accounting Breakdown**: `realized_pnl`, `unrealized_pnl`, `total_fees`.
- **Trade Execution Statistics**: `TradeStatistics` (`order_count`, `fill_count`, `completed_trade_count`, `winning_trades`, `losing_trades`, `win_rate`, `total_realized_pnl`, `average_trade_pnl`, `largest_winning_trade`, `largest_losing_trade`).
- **Risk Analytics (Delegated to V13 `PortfolioRiskEngine`)**:
  - `volatility`: Sample standard deviation of discrete returns with Bessel correction ($ddof=1$).
  - `annualized_volatility`: $\sigma_{\text{period}} \times \sqrt{\text{periods\_per\_year}}$.
  - `maximum_drawdown`: Signed negative peak-to-trough drop ($\le 0$).
  - `drawdown_magnitude`: Absolute magnitude $|\text{max\_drawdown}| \ge 0$.
  - `peak_timestamp`, `trough_timestamp`, `recovery_timestamp`, `is_recovered`.
  - `var_95`: Historical loss-oriented Value at Risk at $\alpha=0.95$.
  - `expected_shortfall_95`: Conditional Value at Risk at $\alpha=0.95$.
  - `return_mean`, `return_median`, `return_min`, `return_max`.

### 4.2 Pairwise Differences (`PairwiseComparison`)
For each strategy pair $(S_A, S_B)$ where $A < B$ in canonical deterministic sequence:
- **Absolute Deltas**: $\Delta = M_A - M_B$:
  - `final_equity_delta`
  - `pnl_delta`
  - `return_delta`
  - `annualized_return_delta`
  - `volatility_delta`
  - `annualized_volatility_delta`
  - `drawdown_delta` (signed delta)
  - `drawdown_magnitude_delta`
  - `var_delta`
  - `es_delta`
  - `fees_delta`
  - `trade_count_delta`
  - `win_rate_delta`
- **Safe Relative Differences**: $\frac{M_A - M_B}{|M_B|}$:
  - `relative_return_difference` (`None` if $M_B == 0$)
  - `relative_fee_difference` (`None` if $M_B == 0$)
  - `relative_drawdown_difference` (`None` if $M_B == 0$)
  - `relative_equity_difference` (`None` if $M_B == 0$)
  - Guarantees zero `NaN`, `+Inf`, or `ZeroDivisionError` generation.

---

## 5. Metric Direction Semantics

To guide interpretation without imposing subjective ranking:

| Metric | Interpretation |
| :--- | :--- |
| `total_return` | Higher value denotes greater realized cumulative return. |
| `annualized_return` | Higher value denotes greater annualized compound return. |
| `volatility` | Higher value denotes greater variability/dispersion of periodic returns. |
| `maximum_drawdown` | More negative value denotes deeper peak-to-trough capital decline. |
| `drawdown_magnitude` | Higher value denotes greater peak-to-trough decline magnitude. |
| `var_95` | Higher value denotes larger estimated downside tail loss at 95% confidence. |
| `expected_shortfall_95` | Higher value denotes larger expected tail loss conditional on exceeding VaR. |
| `total_fees` | Higher value denotes greater cumulative execution commissions and transaction costs. |
| `win_rate` | Higher value denotes higher proportion of profitable completed exit trades. |

---

## 6. Deterministic Ordering & Immutability

1. **Ordering Rule**: Strategy summaries strictly preserve input sequence order. Pairwise comparisons are generated systematically using canonical lexicographic pairs:
   $$(S_0, S_1), (S_0, S_2), \dots, (S_0, S_{n-1}), (S_1, S_2), \dots, (S_{n-2}, S_{n-1})$$
   Zero dependence on unordered sets or non-deterministic hash maps.
2. **Single Strategy Handling**: For $N=1$, `strategies` contains the single strategy summary and `pairwise_comparisons = ()`.
3. **Immutability Guarantee**: All domain models (`StrategyComparisonResult`, `StrategySummary`, `PairwiseComparison`, `TradeStatistics`, `ComparisonPeriod`) are configured with `ConfigDict(frozen=True)` and use immutable tuples for collections. Direct mutation or attribute reassignment raises `ValidationError`.

---

## 7. Quality Gates & Verification

All quality gates pass without warnings or errors:
- **Unit & Integration Tests**: 106 backtesting unit tests passing (1,092 total across platform).
- **Linter**: `ruff check app tests` clean.
- **Formatter**: `ruff format --check app tests` clean.
- **Type Checker**: `mypy app tests` strict clean.
- **Frontend Quality**: `npm run lint` and `npm run type-check` in `apps/web` clean.
