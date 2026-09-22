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
