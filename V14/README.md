# Volume 14: Event-Driven Backtesting Engine & Strategy Analytics

## 1. Executive Summary

Volume 14 introduces the production-grade, deterministic **Event-Driven Backtesting Engine** for the RegimeX platform.

Operating directly downstream of the Market Data, Feature Engineering, Regime Detection, and Portfolio Risk Analytics (V13) layers, Volume 14 allows quantitative strategies to evaluate trading decisions point-in-time without lookahead bias.

```text
Historical Market Data
        ↓
Validated Chronological Events
        ↓
Strategy Decision (Isolated Context, Zero Lookahead)
        ↓
Orders (Market Orders)
        ↓
Execution Model (Configurable Slippage & Commission)
        ↓
Fills & Portfolio Accounting (Reconciliation Invariants)
        ↓
Equity Curve (Chronological Snapshots)
        ↓
Portfolio Risk Engine (V13 Integration)
```

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(backtest): implement event-driven backtesting engine` | **DONE** |
| **02** | `test` | `test(backtest): add leakage and execution integrity tests` | **DONE** |

---

## 3. Commit 01 Implementation Details

### 3.1 Event-Driven Core & Context Isolation
- **Domain Models** (`apps/api/app/modules/backtesting/domain/models.py`):
  - `MarketEvent`: Immutable bar observation (`open, high, low, close, volume`) with strict OHLC relationship checks and UTC timezone enforcement.
  - `SignalEvent`: Directional strategy output with target weight or strength.
  - `OrderRequest`: Strongly typed market orders with positive quantity validation.
  - `FillEvent`: Executed trade report recording post-slippage fill price, commission fees, and slippage impact.
  - `Position`: Marked-to-market position tracking holding size, average entry price, and realized/unrealized PnL.
  - `EquitySnapshot`: Point-in-time portfolio valuation preserving `cash + market_value == equity`.
  - `BacktestConfig`: Configurable initial cash, commission rate, slippage rate, and execution price convention.
  - `BacktestResult`: Comprehensive immutable backtest summary with helper converters to V13 `PriceSeries` and `ReturnSeries`.
- **Strategy Protocol & Context** (`domain/interfaces.py`):
  - `StrategyContext`: Strictly isolated historical view providing only observations up to current timestamp $t$. Strategies cannot access future bars, future portfolio values, or future regime labels.
  - `Strategy`: Protocol exposing `on_market_event(event, context) -> list[OrderRequest]`.

### 3.2 Execution & Portfolio Accounting
- **Execution Model** (`infrastructure/execution.py`):
  - Proportional slippage:
    $$\text{BUY: } p_{\text{exec}} = p_{\text{market}} \times (1 + \text{slippage\_rate})$$
    $$\text{SELL: } p_{\text{exec}} = p_{\text{market}} \times (1 - \text{slippage\_rate})$$
  - Proportional commission:
    $$\text{commission} = p_{\text{exec}} \times \text{quantity} \times \text{commission\_rate}$$
- **Simulated Portfolio** (`infrastructure/portfolio.py`):
  - Strict long-only baseline enforcing non-negative positions and cash sufficiency.
  - Dynamic cost basis averaging on partial purchases.
  - Realized profit/loss calculation on partial and full position exits.
  - Conservation invariant:
    $$\text{equity} = \text{cash} + \sum \text{market\_value} = \text{initial\_cash} + \text{realized\_pnl} + \text{unrealized\_pnl} - \text{total\_fees}$$

### 3.3 Integration with V13 Portfolio Risk Engine
- Zero code duplication: Backtest results convert directly to `PriceSeries` and `ReturnSeries`, and delegate to `PortfolioRiskEngine.analyze_risk()` for computing volatility, drawdowns, Historical VaR, and Expected Shortfall.

---

## 4. Commit 02 Implementation Details (Validation & Integrity Suite)

### 4.1 Anti-Lookahead & Adversarial Strategy Verification (`test_lookahead_protection.py`)
- Verified that strategies receive only historical slices $\le T_t$.
- Tested adversarial strategies attempting to peek into future timestamps, future regime history, or mutate historical buffers.
- Proved mathematical independence from future market anomalies: injecting a 90% market crash or 1,000% rally at $T > t$ yields bit-for-bit identical portfolio state and orders at $\tau \le t$.

### 4.2 Execution Timing Rigor (`test_execution_timing.py`)
- Verified `CURRENT_CLOSE` execution matches the exact bar close.
- Verified `NEXT_OPEN` queues orders and executes at the next bar's open price.
- Verified that orders placed on the final bar under `NEXT_OPEN` safely remain pending without phantom fills or balance corruption.

### 4.3 Transaction Costs & Slippage Monotonicity (`test_transaction_costs.py`)
- Verified strict monotonicity: higher slippage monotonically degrades net equity across identical trading sequences.
- Verified proportional commission scaling and exact fee deduction from cash.
- Validated rejection of negative slippage or commission rates.

### 4.4 Portfolio Accounting Invariants (`test_accounting_invariants.py`)
- Verified dynamic weighted-average cost basis across multiple sequential buys.
- Verified step-by-step partial sells, realized PnL accounting, and position reduction down to zero.
- Enforced rejection of oversells (`InsufficientPositionError`) and insufficient funds (`InsufficientFundsError`).
- Verified conservation equation holds continuously: $\text{equity} = \text{cash} + \text{market\_value} = \text{initial\_cash} + \text{realized\_pnl} + \text{unrealized\_pnl} - \text{fees}$.

### 4.5 Determinism & Replay Integrity (`test_determinism.py`)
- Proved 100% bit-for-bit identical outputs across multiple runs on multi-asset market data.

### 4.6 Input Validation & Edge Case Handling (`test_input_validation.py`)
- Enforced rejection of non-chronological events, duplicate timestamps, naive datetimes, non-positive prices, NaN/Inf, non-positive order quantities, and unobserved symbol orders.

### 4.7 V13 Portfolio Risk Engine Integration (`test_v13_integration.py`)
- Verified seamless equity curve conversion to `PriceSeries` and `ReturnSeries`.
- Validated risk metric correctness: non-negative volatility, bounded drawdowns in $[0, 1]$, and tail risk ordering $\text{CVaR}_\alpha \ge \text{VaR}_\alpha$.

---

## 5. Architectural Boundaries

- **Zero Prohibited Imports**: Backtesting is pure Python/NumPy, with zero imports from FastAPI, database ORMs, external broker APIs, or machine learning frameworks.
- **Strict Scope Boundaries**:
  - Event-driven backtesting execution and validation only.
  - Zero live trading, broker integrations, order routing, or AI explanations.
- **Volume 14 Status**: Complete (2/2 commits delivered and validated).
