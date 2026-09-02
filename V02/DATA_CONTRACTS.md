# Data Contracts

**RegimeX — Open-Source Market Intelligence Platform**

> Data contracts define the canonical schemas for all data entities in RegimeX. These schemas govern data storage, API responses, feature computation inputs, and inter-module communication. Schemas are defined structurally here — implementation (SQL DDL, Python types, Pydantic models) begins in V05+.

---

## DC-OHLCV — Market Data Schema

The canonical schema for daily OHLCV market data.

### Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `symbol` | `string` | No | Instrument symbol (e.g., `AAPL`, `NIFTY50`, `BTC-USD`) |
| `exchange` | `string` | No | Exchange identifier (e.g., `NASDAQ`, `NSE`, `COINBASE`) |
| `timestamp` | `datetime (UTC)` | No | Bar timestamp — market session date at 00:00:00 UTC for daily data |
| `open` | `decimal` | No | Opening price |
| `high` | `decimal` | No | Intraday high price |
| `low` | `decimal` | No | Intraday low price |
| `close` | `decimal` | No | Closing price |
| `volume` | `integer` | No | Trading volume |
| `adjusted_close` | `decimal` | Yes | Corporate-action-adjusted closing price (null if unavailable) |
| `adjustment_factor` | `decimal` | Yes | Factor applied to derive `adjusted_close` from `close` |
| `adjustment_type` | `enum` | No | `NONE` \| `SPLIT_ADJUSTED` \| `TOTAL_RETURN` |
| `currency` | `string` | No | ISO 4217 currency code (e.g., `USD`, `INR`) |
| `asset_class` | `enum` | No | `EQUITY` \| `CRYPTO` \| `COMMODITY` \| `FOREX` \| `FIXED_INCOME` |
| `data_source` | `string` | No | Provider identifier (e.g., `yahoo_finance`, `alpha_vantage`) |
| `data_source_version` | `string` | No | Provider adapter version |
| `ingested_at` | `datetime (UTC)` | No | Timestamp when this record was written to storage |
| `dataset_version` | `string` | No | Dataset snapshot fingerprint (SHA-256 of source content) |

### Constraints

- `(symbol, exchange, timestamp, adjustment_type)` is a unique composite key
- `open`, `high`, `low`, `close` must be positive
- `high >= low`, `high >= open`, `high >= close`
- `volume >= 0`
- `timestamp` must be a valid trading day for the instrument's exchange

### Notes

- Intraday data is a future extension — this schema covers daily bars
- `adjusted_close` may be null for providers that do not supply adjustment data
- When `adjustment_type = NONE`, `adjusted_close = close` and `adjustment_factor = 1.0`

---

## DC-FEATURE — Feature Schema

The canonical schema for computed quantitative features.

### Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `feature_id` | `string` | No | Feature registry identifier (e.g., `returns_1d_v1`) |
| `feature_name` | `string` | No | Human-readable feature name |
| `feature_version` | `string` | No | Feature implementation version (semver) |
| `symbol` | `string` | No | Instrument symbol |
| `exchange` | `string` | No | Exchange identifier |
| `timestamp` | `datetime (UTC)` | No | Point-in-time timestamp — feature uses only data at or before this timestamp |
| `value` | `decimal` | Yes | Computed feature value (null if computation fails or data is insufficient) |
| `is_valid` | `boolean` | No | Whether the value is considered valid (e.g., `false` if warm-up period not met) |
| `invalid_reason` | `string` | Yes | If `is_valid = false`, explains why |
| `computed_at` | `datetime (UTC)` | No | Timestamp when this feature value was computed |
| `input_dataset_version` | `string` | No | Dataset version fingerprint of the OHLCV data used |
| `lookback_bars` | `integer` | No | Number of historical bars consumed in this computation |

### Constraints

- `(feature_id, symbol, exchange, timestamp)` is a unique composite key
- `timestamp` must be ≤ `computed_at`
- `is_valid = false` must have a non-null `invalid_reason`

---

## DC-REGIME — Regime Output Schema

The canonical schema for regime detection outputs.

### Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `regime_id` | `uuid` | No | Unique identifier for this regime detection record |
| `symbol` | `string` | No | Instrument symbol |
| `exchange` | `string` | No | Exchange identifier |
| `timestamp` | `datetime (UTC)` | No | Bar timestamp for which regime is assigned |
| `regime_label` | `integer` | No | Detected regime label (0-indexed integer; label semantics are model-specific) |
| `regime_confidence` | `decimal` | No | Model confidence for this regime assignment (0.0–1.0) |
| `regime_probabilities` | `json` | No | Full probability distribution over all K regimes: `{"0": 0.7, "1": 0.2, "2": 0.1}` |
| `algorithm_id` | `string` | No | Algorithm registry identifier (e.g., `hmm_v1`) |
| `algorithm_version` | `string` | No | Algorithm implementation version |
| `algorithm_parameters` | `json` | No | Full parameter set used for this detection run |
| `feature_set_id` | `string` | No | Identifier for the feature set used as input |
| `input_dataset_version` | `string` | No | Dataset version fingerprint of underlying market data |
| `computed_at` | `datetime (UTC)` | No | When this regime output was computed |
| `run_id` | `uuid` | No | Detection run identifier — all outputs from a single detection run share a `run_id` |

### Constraints

- `(symbol, exchange, timestamp, algorithm_id, run_id)` is a unique composite key
- `regime_confidence ∈ [0.0, 1.0]`
- Sum of values in `regime_probabilities` must equal 1.0 (within floating point tolerance)
- `timestamp` must be ≤ `computed_at`

---

## DC-RISK — Risk Metrics Schema

The canonical schema for risk analytics outputs.

### Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `risk_id` | `uuid` | No | Unique identifier for this risk record |
| `symbol` | `string` | No | Instrument symbol |
| `exchange` | `string` | No | Exchange identifier |
| `timestamp` | `datetime (UTC)` | No | Point-in-time timestamp for this risk snapshot |
| `metric_name` | `string` | No | Risk metric identifier (e.g., `realized_vol_21d`, `var_95_hist`, `max_drawdown`) |
| `metric_value` | `decimal` | Yes | Computed metric value |
| `is_valid` | `boolean` | No | Whether the metric is valid |
| `window_bars` | `integer` | Yes | Lookback window in bars (if applicable) |
| `confidence_level` | `decimal` | Yes | Confidence level for VaR/CVaR metrics (e.g., 0.95) |
| `regime_label` | `integer` | Yes | If computed conditional on a regime, the regime label; null for unconditional |
| `algorithm_id` | `string` | Yes | Regime algorithm used for regime-conditional computation |
| `computed_at` | `datetime (UTC)` | No | When this metric was computed |
| `assumptions` | `json` | No | Explicit assumptions used: estimator type, window, confidence level |

---

## DC-BACKTEST — Backtest Result Schema

The canonical schema for backtest results.

### Fields

**Run Metadata**

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `backtest_id` | `uuid` | No | Unique identifier for this backtest run |
| `strategy_id` | `string` | No | Strategy registry identifier |
| `strategy_version` | `string` | No | Strategy implementation version |
| `strategy_parameters` | `json` | No | Full parameter set used |
| `universe` | `json` | No | List of `{symbol, exchange}` objects in the backtest universe |
| `start_date` | `date` | No | Backtest start date (inclusive) |
| `end_date` | `date` | No | Backtest end date (inclusive) |
| `initial_capital` | `decimal` | No | Starting capital |
| `cost_model` | `json` | No | Transaction cost model configuration |
| `input_dataset_version` | `string` | No | Dataset fingerprint of market data used |
| `regime_run_id` | `uuid` | Yes | Regime detection run used for regime attribution (if any) |
| `run_at` | `datetime (UTC)` | No | When the backtest was executed |

**Performance Summary**

| Field | Type | Description |
|-------|------|-------------|
| `total_return` | `decimal` | Total return over the backtest period |
| `cagr` | `decimal` | Compound Annual Growth Rate |
| `sharpe_ratio` | `decimal` | Annualized Sharpe Ratio (risk-free rate is configurable, default 0) |
| `sortino_ratio` | `decimal` | Annualized Sortino Ratio |
| `calmar_ratio` | `decimal` | CAGR / Maximum Drawdown |
| `max_drawdown` | `decimal` | Maximum peak-to-trough drawdown |
| `max_drawdown_duration_days` | `integer` | Duration of maximum drawdown in calendar days |
| `win_rate` | `decimal` | Fraction of trades with positive return |
| `profit_factor` | `decimal` | Gross profit / Gross loss |
| `total_trades` | `integer` | Total number of round-trip trades |
| `benchmark_total_return` | `decimal` | Benchmark return over same period (if benchmark provided) |

**Time Series Outputs** *(stored as separate time-series records linked by `backtest_id`)*

| Series | Description |
|--------|-------------|
| `equity_curve` | `(timestamp, equity_value)` daily portfolio value |
| `drawdown_series` | `(timestamp, drawdown_pct)` daily drawdown from peak |
| `regime_attribution` | `(regime_label, total_return, sharpe, trade_count)` per regime |
| `trade_log` | `(entry_date, exit_date, symbol, direction, pnl, cost)` per trade |
