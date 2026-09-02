# Glossary

**RegimeX — Open-Source Market Intelligence Platform**

> This glossary defines the authoritative meaning of domain terms used throughout RegimeX documentation, code, and APIs. When a term has multiple common meanings, the RegimeX-specific meaning is made explicit.

---

## A

**Adjusted Close**
The closing price of an instrument after applying adjustments for corporate actions such as stock splits and dividend distributions. RegimeX records the adjustment type explicitly to avoid ambiguity.

**Algorithm (Regime Detection)**
A specific method for detecting market regimes from feature data. All algorithms in RegimeX implement the `RegimeDetector` interface. Each algorithm is versioned and documented independently.

**Asset Class**
A category of financial instruments with similar characteristics and behaviors. RegimeX supports: `EQUITY`, `CRYPTO`, `COMMODITY`, `FOREX`, `FIXED_INCOME`.

**ATR (Average True Range)**
A technical indicator measuring market volatility by calculating the average of true ranges over a specified period. Used as a feature input for regime detection.

---

## B

**Backtest**
A simulation of how a trading strategy would have performed on historical data. In RegimeX, backtests are event-driven, use realistic transaction cost models, and support regime attribution.

**Bar**
A single OHLCV data record for a specific instrument and time period. In RegimeX, the default bar frequency is daily.

**BOCPD (Bayesian Online Changepoint Detection)**
A probabilistic algorithm for detecting points in time where a data-generating process changes its statistical properties. Used as one regime detection algorithm option in RegimeX.

---

## C

**CAGR (Compound Annual Growth Rate)**
The annualized rate of return that accounts for compounding. A standard backtest performance metric in RegimeX.

**Calmar Ratio**
A risk-adjusted return metric computed as CAGR divided by Maximum Drawdown. Included in RegimeX backtest performance summaries.

**Changepoint Detection**
The problem of identifying points in a time series where the underlying statistical distribution changes. Used as one approach to market regime detection.

**Confidence Score**
A value in [0.0, 1.0] representing the model's estimated certainty about a regime assignment. RegimeX requires all regime outputs to include a confidence score.

**Corporate Action**
An event initiated by a company that affects its stock: stock split, dividend, merger, rights issue. RegimeX explicitly documents how corporate actions are handled in price data.

**CVaR (Conditional Value at Risk)**
Also known as Expected Shortfall. The expected loss given that a loss exceeds the VaR threshold. Computed at a specified confidence level. A tail risk metric in RegimeX.

---

## D

**Data Contract**
A formal schema definition for a RegimeX data entity (OHLCV, Feature, Regime, Risk, Backtest). All system components that produce or consume that entity must conform to the contract.

**Dataset Version**
A fingerprint (SHA-256 hash) that uniquely identifies a specific snapshot of a dataset. RegimeX uses dataset versions to ensure reproducibility.

**Drawdown**
The decline from a peak to a subsequent trough in portfolio value or instrument price. RegimeX computes drawdown magnitude, duration, and recovery time.

---

## E

**Equity Curve**
A time series of portfolio value over the course of a backtest. A primary output of RegimeX backtest runs.

**Event-Driven Backtest**
A backtesting approach where the simulation processes market events (new bars) one at a time, mimicking how a strategy would execute in real time. RegimeX uses event-driven simulation.

**EWMA (Exponentially Weighted Moving Average)**
A moving average that gives exponentially decreasing weight to older observations. Used in RegimeX for volatility estimation.

---

## F

**Feature**
A quantitative signal computed from market data used as input to regime detection algorithms. All features in RegimeX are point-in-time, versioned, and registered in the Feature Registry.

**Feature Engineering**
The process of computing quantitative features from raw market data. RegimeX enforces no look-ahead bias in all feature engineering.

**Feature Registry**
A catalogue of all available quantitative features in RegimeX, including documentation, version, computation method, and look-ahead bias status.

**Feature Set**
A specific named collection of features used as input to a regime detection run. Feature sets are versioned to enable reproducibility.

---

## G

**GMM (Gaussian Mixture Model)**
A probabilistic model that represents the presence of sub-populations (regimes) within an overall population using Gaussian distributions. One regime detection algorithm in RegimeX.

---

## H

**HMM (Hidden Markov Model)**
A statistical model where the system being modeled is assumed to be a Markov process with hidden (unobserved) states. The primary initial regime detection algorithm in RegimeX.

---

## I

**Idempotent**
An operation that produces the same result when executed multiple times. RegimeX data ingestion pipelines are idempotent — re-ingesting the same data does not produce duplicates.

**Instrument**
A tradeable financial security or asset: a stock, an index, a cryptocurrency, a currency pair, a commodity contract.

---

## L

**Lookback Window**
The number of historical bars used in a computation (feature or risk metric). RegimeX records the lookback window for all computed values to make computation transparent.

**Look-Ahead Bias**
The use of future data when computing a historical value, producing unrealistically optimistic backtest results. RegimeX treats any look-ahead bias as a critical bug.

---

## M

**Market Regime**
A distinct, identifiable state of market behavior characterized by specific statistical properties — such as trend, volatility level, correlation structure, or liquidity profile. RegimeX detects, classifies, and analyzes market regimes.

**Maximum Drawdown**
The largest peak-to-trough decline in portfolio value over a specified period. A key risk and performance metric in RegimeX.

**Monorepo**
A single source code repository containing multiple related packages or applications. RegimeX uses a monorepo structure from V04 onward.

---

## N

**NFR (Non-Functional Requirement)**
A requirement that specifies how a system behaves rather than what it does — covering performance, reliability, security, scalability, and other quality attributes.

---

## O

**OHLCV**
Open, High, Low, Close, Volume. The canonical representation of a financial bar. The primary data entity in RegimeX.

---

## P

**PELT (Pruned Exact Linear Time)**
An efficient changepoint detection algorithm that finds the optimal segmentation of a time series with minimal computational cost.

**pLDDT**
Not applicable in RegimeX context (this is an AlphaFold confidence metric). Listed here to prevent confusion with `pLI` and other quantitative metrics.

**Point-in-Time**
A computation discipline where only data available at or before a given timestamp is used. RegimeX enforces point-in-time correctness for all features and regime assignments.

**Profit Factor**
The ratio of gross profit to gross loss in a backtest. Values > 1.0 indicate a profitable strategy.

**Provider**
A market data source (API, database, file) from which RegimeX ingests OHLCV data. All providers are accessed through the abstract `MarketDataProvider` interface.

**Provider Abstraction**
The RegimeX design pattern where all data provider logic is isolated in adapter modules, enabling providers to be swapped without changing business logic.

---

## R

**Regime**
See *Market Regime*.

**Regime Attribution**
Analysis of strategy performance broken down by which market regime was active during each period. A RegimeX backtest feature.

**Regime Confidence**
See *Confidence Score*.

**Regime Label**
An integer identifier (0-indexed) assigned to a detected market regime. Label semantics (e.g., "high volatility", "trending") are determined by post-detection analysis and are algorithm-specific.

**Regime Persistence**
A measure of how long a regime tends to remain active once entered. Quantified by RegimeX as mean duration, standard deviation of duration, and median duration.

**Regime Transition**
The event when the detected market regime changes from one label to another. RegimeX records transitions in the regime timeline and computes transition probability matrices.

**Regime Transition Matrix**
A K×K matrix where entry (i,j) represents the historical probability of transitioning from regime i to regime j. Computed by RegimeX from the regime timeline.

**Reproducibility**
The ability to re-run an analysis and obtain identical results. RegimeX enforces reproducibility through dataset versioning, algorithm versioning, and configuration persistence.

**RSI (Relative Strength Index)**
A momentum oscillator measuring the speed and magnitude of recent price changes to evaluate overbought or oversold conditions. Available as a RegimeX feature.

**Run ID**
A UUID assigned to a single execution of a regime detection pipeline. All regime outputs from that execution share the same `run_id`, enabling full traceability.

---

## S

**Sharpe Ratio**
A risk-adjusted return measure: excess return per unit of standard deviation. A primary performance metric in RegimeX backtests.

**Slippage**
The difference between the expected price of a trade and the actual execution price. RegimeX backtest cost models include configurable slippage assumptions.

**Sortino Ratio**
A risk-adjusted return measure that penalizes only downside volatility, unlike the Sharpe Ratio which penalizes all volatility.

**Survivorship Bias**
The tendency for data to include only instruments that survived until the present, excluding those that failed or were delisted. RegimeX explicitly documents its survivorship bias handling strategy.

---

## T

**Transaction Cost Model**
A configurable model in the RegimeX backtesting engine that simulates the costs of executing trades: commissions, bid-ask spread, and market impact.

**Transition Matrix**
See *Regime Transition Matrix*.

---

## V

**VaR (Value at Risk)**
An estimate of the maximum loss expected over a given time horizon at a specified confidence level. Computed by RegimeX using historical simulation.

**Volume**
The total number of shares, contracts, or units traded during a bar period. Part of the canonical OHLCV schema.

---

## W

**Walk-Forward Validation**
A backtesting methodology where the strategy is repeatedly trained on a historical window and tested on the subsequent out-of-sample period, advancing forward through time. RegimeX backtesting supports walk-forward validation to prevent overfitting.

**Warm-Up Period**
The minimum number of bars required before a feature or model produces valid output. RegimeX marks feature values as `is_valid = false` during the warm-up period and records the `invalid_reason`.

---

## Y

**Yang-Zhang Volatility**
An OHLCV-based volatility estimator that handles overnight gaps and is more efficient than close-to-close volatility. Available as a RegimeX risk metric.
