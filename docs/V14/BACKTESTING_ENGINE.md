# RegimeX — Event-Driven Backtesting Engine

**Volume 14 — Technical Specification & Mathematical Formulation**  
**Module:** `apps/api/app/modules/backtesting/`

---

## 1. Executive Summary

The **Event-Driven Backtesting Engine** provides a deterministic simulation environment for evaluating quantitative trading strategies over historical market data.

By processing historical observations chronologically through discrete event queues, the engine enforces strict point-in-time constraints, preventing lookahead leakage and survivorship bias.

```text
Historical Market Data
        ↓
Validated Chronological Events
        ↓
Strategy Decision (Isolated Context, Zero Lookahead)
        ↓
Order Generation (MARKET Orders)
        ↓
Simulated Execution (Proportional Slippage & Commission)
        ↓
Fills & Portfolio Accounting (Conservation Invariants)
        ↓
Equity Snapshot Series
        ↓
Portfolio Risk Analytics (V13 Engine)
```

---

## 2. Event-Driven Architecture

### 2.1 Event Pipeline & State Transitions
At each simulation step $t$:
1. **Clock Advance**: The simulation clock advances to the event's UTC timestamp $T_t$.
2. **Pending Order Processing**: If operating in `NEXT_OPEN` mode, orders placed at step $t-1$ are executed at bar $t$'s opening price $P_{\text{open}, t}$.
3. **Market Event Dispatch**: The bar's market observation (`open`, `high`, `low`, `close`, `volume`) is appended to historical buffers.
4. **Strategy Decisioning**: The strategy receives the `MarketEvent` and an isolated `StrategyContext` exposing only information known at or before $T_t$.
5. **Immediate Order Execution**: If operating in `CURRENT_CLOSE` mode, emitted orders execute at bar $t$'s closing price $P_{\text{close}, t}$.
6. **Portfolio Accounting**: Resulting `FillEvent` records update cash balances, position sizes, and realized profit/loss.
7. **Mark-to-Market Snapshot**: All active positions are revalued using the latest closing prices, producing an `EquitySnapshot`.

---

## 3. Strategy Interface & Anti-Lookahead Guarantees

### 3.1 Restricted Strategy Context
Strategies interact with the simulation strictly through the `StrategyContext` protocol:
- `current_timestamp`: Current discrete simulation time (UTC).
- `current_prices`: Latest observed prices for symbols seen up to step $t$.
- `current_positions`: Defensive copy of active open positions.
- `available_cash`: Unencumbered cash available for purchases.
- `portfolio_equity`: Total marked-to-market wealth.
- `get_history(symbol, count)`: Immutable tuple of historical `MarketEvent` records strictly $\le T_t$.
- `current_regime` / `get_regime_history()`: Past regime labels up to $T_t$.

### 3.2 Anti-Lookahead Protections
- **Causal Historical Slicing**: Strategies receive past slices `[:t+1]`. Indexing beyond $t$ is structurally impossible.
- **Immutable Domain Events**: Event records (`MarketEvent`, `OrderRequest`, `FillEvent`) are frozen Pydantic models. Strategies cannot modify market prices or history.
- **Independence of Future Data**: Appending future market observations after step $t$ has zero mathematical effect on trades, fills, or snapshots at or before step $t$.

---

## 4. Execution Timing Conventions

The engine supports two explicit execution price conventions:

1. **`CURRENT_CLOSE` (Default)**:
   - Strategy observes bar $t$ (including `close`) and places an order.
   - The order executes at bar $t$ `close` (adjusted for slippage), representing a Market-On-Close (MOC) settlement.
   - Ideal for end-of-day rebalancing models.

2. **`NEXT_OPEN`**:
   - Strategy observes bar $t$ and places an order.
   - The order is queued and executes at bar $t+1$ `open` (adjusted for slippage).
   - Eliminates same-bar execution assumptions.

---

## 5. Transaction Costs & Slippage Formulation

### 5.1 Proportional Slippage
Given reference market price $P_{\text{market}}$ and slippage rate $s \ge 0$:
- **BUY Orders**:
  $$P_{\text{exec}} = P_{\text{market}} \times (1 + s)$$
- **SELL Orders**:
  $$P_{\text{exec}} = P_{\text{market}} \times (1 - s)$$

Unit slippage cost is $|P_{\text{exec}} - P_{\text{market}}| \times Q$.

### 5.2 Proportional Commission
Given execution price $P_{\text{exec}}$, quantity $Q$, and commission rate $c \ge 0$:
$$\text{Commission} = P_{\text{exec}} \times Q \times c$$

Total cash impact:
- **BUY**: Cash decreases by $P_{\text{exec}} \times Q + \text{Commission}$.
- **SELL**: Cash increases by $P_{\text{exec}} \times Q - \text{Commission}$.

---

## 6. Portfolio Accounting & Long-Only Baseline

### 6.1 Position Invariants
For each asset $i$:
- **Position Size**: $Q_i \ge 0$ (short selling is prohibited unless explicitly configured).
- **Average Entry Price**:
  $$P_{\text{avg, new}} = \frac{Q_{\text{old}} \cdot P_{\text{avg, old}} + Q_{\text{buy}} \cdot P_{\text{exec}}}{Q_{\text{old}} + Q_{\text{buy}}}$$
- **Market Valuation**:
  $$\text{Market Value}_i = Q_i \times P_{\text{market}, i}$$
- **Unrealized PnL**:
  $$\text{Unrealized PnL}_i = (P_{\text{market}, i} - P_{\text{avg}, i}) \times Q_i$$
- **Realized PnL on Exit**:
  $$\text{Realized PnL}_{\text{trade}} = (P_{\text{exec}} - P_{\text{avg}}) \times Q_{\text{sell}}$$

### 6.2 Conservation Invariant
At every simulation step $t$:
$$\text{Equity}_t = \text{Cash}_t + \sum_{i} \text{Market Value}_{i, t}$$
$$\text{Equity}_t = \text{Initial Cash} + \text{Realized PnL}_t + \text{Unrealized PnL}_t - \text{Total Fees}_t$$

---

## 7. Integration with V13 Portfolio Risk Engine

To maintain clean architectural boundaries and eliminate code duplication, `BacktestResult` integrates directly with Volume 13:
- `to_price_series()`: Generates a validated `PriceSeries` from the chronological equity curve.
- `to_return_series(return_type)`: Generates a validated `ReturnSeries` using `PortfolioRiskEngine.compute_arithmetic_returns` or `compute_log_returns`.
- `compute_risk_metrics()`: Invokes `PortfolioRiskEngine.analyze_risk()` on the equity series to calculate realized volatility, peak-to-trough drawdown, Historical VaR ($90\%, 95\%, 99\%$), and Expected Shortfall.

---

## 8. Validation Suite & Integrity Verification

The backtesting engine is hardened with an exhaustive validation suite (`apps/api/tests/unit/backtesting/`):

1. **Lookahead Protection (`test_lookahead_protection.py`)**:
   - Validates that strategies receive only historical data slices strictly $\le T_t$.
   - Confirms that adversarial attempts to inspect future slices, mutate history buffers, or alter past events raise exceptions or fail harmlessly.
   - Proves future independence: extreme market movements (e.g. 90% crashes or 1,000% rallies) after step $t$ do not alter trades, fills, or positions at or before $t$.

2. **Execution Timing Correctness (`test_execution_timing.py`)**:
   - `CURRENT_CLOSE`: Verified to fill at the exact bar close.
   - `NEXT_OPEN`: Verified to queue orders at $T_t$ and fill at $T_{t+1}$ open price.
   - End-of-series isolation: Orders placed on the final bar under `NEXT_OPEN` are safely retained in pending state without corrupting cash balances.

3. **Transaction Costs & Monotonicity (`test_transaction_costs.py`)**:
   - Monotonicity: Higher slippage rates strictly decrease net ending equity under identical trading sequences.
   - Commission scaling: Commission fees scale proportionally with executed principal and are deducted from available cash.

4. **Accounting Invariants (`test_accounting_invariants.py`)**:
   - Dynamic cost basis: Proves correct weighted-average cost basis across multiple sequential purchases.
   - Partial sell accounting: Proves correct realized PnL recognition on fractional position liquidation.
   - Long-only enforcement: Rejects oversell attempts with `InsufficientPositionError`.
   - Cash protection: Rejects purchases exceeding available cash with `InsufficientFundsError`.
   - Conservation equation: $\text{equity} = \text{cash} + \text{market\_value} = \text{initial\_cash} + \text{realized\_pnl} + \text{unrealized\_pnl} - \text{fees}$ holds at all snapshots.

5. **Deterministic Replay (`test_determinism.py`)**:
   - Identical inputs and seeds produce bit-for-bit identical outputs across orders, fills, positions, cash, fees, equity curves, and risk metrics.

6. **Input Validation (`test_input_validation.py`)**:
   - Rejects non-chronological events, duplicate timestamps, naive datetimes, non-positive prices, NaNs, infinities, and unobserved symbol orders.

7. **V13 Risk Engine Integration (`test_v13_integration.py`)**:
   - Verifies end-to-end delegation to `PortfolioRiskEngine.analyze_risk()`.
   - Enforces mathematical risk invariants: $\text{volatility} \ge 0$, $\text{max\_drawdown} \in [0, 1]$, and $\text{ES}_\alpha \ge \text{VaR}_\alpha$.
