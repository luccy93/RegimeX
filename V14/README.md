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
| **02** | `feat` | `feat(backtest): add strategy comparison analytics` | Pending |

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

## 4. Architectural Boundaries

- **Zero Prohibited Imports**: Backtesting is pure Python/NumPy, with zero imports from FastAPI, database ORMs, external broker APIs, or machine learning frameworks.
- **Strict Scope Boundaries**:
  - No Sharpe/Sortino comparison or strategy ranking in Commit 01 (reserved for Commit 02).
  - No live trading, broker integrations, order routing, or AI explanations.
