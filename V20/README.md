# RegimeX — Volume 20: Analytics, Risk, and Backtesting Workspaces

## Official Commits

- **Commit 01:** `feat(web): add regime analytics workspace` (`c535172`)
- **Commit 02:** `feat(web): add risk and backtesting dashboards`

> **Scope Declaration:**
> Volume 20 establishes the complete quantitative analytics suite for the RegimeX frontend console:
> 1. **Regime Analytics Workspace** (`/app/regimes`)
> 2. **Portfolio Risk Analytics Workspace** (`/app/risk`)
> 3. **Systematic Backtesting Simulation Workspace** (`/app/backtesting`)

---

## 1. Overview & Objectives

Volume 20 transforms backend quantitative domain engines (V08–V15) into descriptive, reproducible, and production-grade analytical workspaces.

These analytical consoles expose:
- **V11/V12/V19/V20:** Empirical Markov regime classifications, persistence probabilities, run durations, feature statistics, transition matrices, and transition dispersion entropy.
- **V13:** Historical portfolio risk profiling, realized annual volatility, peak-to-trough underwater drawdown tracks, multi-tier Value at Risk (VaR), and Conditional VaR / Expected Shortfall.
- **V14/V15:** Deterministic event-driven backtesting execution, realistic transaction friction (commissions & slippage), equity curve trajectory with initial capital baseline, win/loss trade attribution, and immutable performance reports with metric definitions.

These are **reproducible research and diagnostic workspaces**, strictly decoupled from live trading, broker execution, or predictive speculation.

---

## 2. Routes & URL-Driven Context

| Route | Primary Query Parameter | Description |
| :--- | :--- | :--- |
| `/app/regimes` | `?symbol=SPY` | Regime profiles, distribution, frequency, persistence, durations, transition matrices |
| `/app/risk` | `?symbol=SPY` | Historical risk profiling, realized volatility, drawdown tracks, multi-quantile VaR & Expected Shortfall |
| `/app/backtesting` | `?symbol=SPY&strategy=BUY_AND_HOLD` | Event-driven simulation, equity curves, trade statistics, strategy risk, performance audit reports |

### Navigation Invariants
- **Bidirectional URL Synchronization:** All route changes and parameter updates (`symbol`, `strategy`) reflect immediately in the URL search params.
- **Deterministic Defaults:** If no instrument is specified, workspaces deterministically select the first instrument from the discoverable market catalog.
- **Browser History Integration:** Full support for browser `Back`, `Forward`, and `Refresh` without losing state or desynchronizing UI controls.

---

## 3. Information Architecture & Consoles

### 3.1 Regime Analytics Workspace (`/app/regimes`)
- **Regime Workspace Header:** Market discovery selector, active instrument summary, temporal window, sample observations.
- **Current Regime Context:** Current regime assignment, empirical model confidence gauge, and point-in-time feature vector.
- **Regime Distribution:** Proportional horizontal observation track and regime share percentages.
- **Frequency & Persistence:** 1-step persistence probability $P(S_{t+1}=k \mid S_t=k)$, run counts, and total observations.
- **Duration Characteristics:** Average vs. maximum run duration, discrete duration disclosures.
- **Feature Statistics Matrix:** Cross-regime distributions (mean, median, standard deviation, extrema) with zero-imputation avoidance.
- **Markov Transition Matrix:** Empirical 1-step Markov transition probabilities, regime changes, destination rankings, and Shannon transition entropy.
- **Methodology & Provenance:** Model algorithm, feature definitions, and diagnostic boundaries.

### 3.2 Risk Analytics Workspace (`/app/risk`)
- **Risk Header:** Market selector, instrument metadata, 252-period annualization basis, target benchmark return.
- **Risk Profile Overview:**
  - Annualized Volatility ($\sigma_{\text{ann}} = \sigma_{\text{period}} \times \sqrt{252}$)
  - Maximum Drawdown (depth, peak-to-trough magnitude, recovery lifecycle status)
  - 1-Day Value at Risk (95% confidence loss-oriented threshold)
  - 1-Day Expected Shortfall (95% conditional tail expectation)
  - Downside Deviation & Semi-Variance (evaluated relative to $T=0.0\%$)
  - Sample Mean & Median Daily Return
- **Drawdown Track & Peak-to-Trough Profile:** High-fidelity SVG chart depicting normalized underwater equity decline over time, pre-crash peak value, trough depth, and recovery timestamp.
- **Tail Risk & Return Dispersion:** Multi-tier VaR and Expected Shortfall table comparing 90%, 95%, and 99% regulatory tiers against empirical tail counts and discrete return range.
- **Analytical Methodology & Risk Disclosures:** Mathematical definitions, loss-positive orientation semantics, and non-stationarity limitations.

### 3.3 Systematic Backtesting Workspace (`/app/backtesting`)
- **Backtesting Header:**
  - Strategy selector: `BUY_AND_HOLD` (Benchmark Buy & Hold) vs. `REGIME_ADAPTIVE` (Regime Adaptive Momentum)
  - Execution Price Fill toggle: `CURRENT_CLOSE` (Bar Close) vs. `NEXT_OPEN` (Next Bar Open)
  - Starting Capital: $100,000.00
  - Transaction Friction: 5 bps Commission / 5 bps Slippage
- **Performance Summary:**
  - Final Equity (formatted in USD, net absolute PnL, total return %)
  - Annualized Return (CAGR basis)
  - PnL Decomposition (Realized vs. Unrealized)
  - Transaction Costs & Execution Friction
  - Strategy Maximum Drawdown & Volatility
- **Equity Curve & Drawdown Subplot:** Responsive SVG chart charting cumulative mark-to-market net equity with capital baseline ($100k) and synchronized underwater drawdown track.
- **Trade Execution & Win/Loss Statistics:** Order/fill reconciliation, completed trade count, win rate %, average trade PnL, largest winning vs. losing trade, and complete executed fills log.
- **Strategy Risk Diagnostics:** Volatility, max drawdown, 95% VaR, and 95% Expected Shortfall evaluated directly on strategy equity.
- **Deterministic Performance Report:** Immutable V15 audit trail with Report ID, Version, Generated timestamp, execution methodology policies, simulation limitations, and metric definitions glossary.

---

## 4. Backend Architecture & Clean Architecture Compliance

To adhere strictly to Clean Architecture invariants (tested in `test_architecture.py`):
1. **Forbidden Route Imports:** Routes under `app/api/v1/endpoints/` never import domain engines directly (`PortfolioRiskEngine`, `BacktestingEngine`, `KMeansRegimeDetector`).
2. **Application Service Abstraction:**
   - `PortfolioRiskService` (`app/modules/portfolio_risk/application/service.py`) encapsulates portfolio risk pipeline orchestration.
   - `BacktestingService` (`app/modules/backtesting/application/service.py`) encapsulates deterministic event-driven simulation runs, comparison analytics, and performance report generation.
3. **FastAPI Dependency Injection:**
   - `PortfolioRiskServiceDep`: Injected into `GET /api/v1/markets/{symbol}/risk`.
   - `BacktestingServiceDep`: Injected into `GET /api/v1/markets/{symbol}/backtest`.
4. **Deterministic Simulation Strategies:**
   - `BenchmarkBuyAndHoldStrategy`: Systematic long benchmark on the initial bar.
   - `RegimeAdaptiveStrategy`: Dynamic momentum allocation based on inferred market regime sequences.

---

## 5. Verification & Quality Gates

All quality gates passed across both frontend and backend suites:

### Frontend Quality Suite (`apps/web`)
```bash
npm test           # 162 passing tests (Node.js test runner)
npm run lint       # Next.js ESLint clean (0 errors, 0 warnings)
npm run type-check # TypeScript 5.5 compiler clean (tsc --noEmit)
npm run build      # Next.js 14 production bundle verified (all routes static/prerendered)
```

### Backend Quality Suite (`apps/api`)
```bash
python -m pytest tests/ -q               # 1,289 tests passing
python -m ruff check app tests           # Ruff linter clean
python -m ruff format --check app tests  # Code formatting clean
python -m mypy app tests                 # Mypy static type checker clean
```
