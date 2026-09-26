/**
 * RegimeX Web — Systematic Backtesting Workspace Tests
 * ====================================================
 * Volume 20 — Commit 02
 * Comprehensive test suite verifying BacktestHeader, BacktestPerformanceOverview,
 * EquityCurveChart, TradeStatisticsSection, BacktestRiskSection,
 * PerformanceReportSection, defensive currency formatters, and edge cases.
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { BacktestHeader } from "../components/backtesting/BacktestHeader";
import { BacktestPerformanceOverview } from "../components/backtesting/BacktestPerformanceOverview";
import { EquityCurveChart } from "../components/backtesting/EquityCurveChart";
import { TradeStatisticsSection } from "../components/backtesting/TradeStatisticsSection";
import { BacktestRiskSection } from "../components/backtesting/BacktestRiskSection";
import { PerformanceReportSection } from "../components/backtesting/PerformanceReportSection";

import {
  isValidFiniteNumber,
  formatCurrency,
  formatPercentage,
} from "../lib/api/backtesting";

import {
  MOCK_MARKET_BACKTEST_RESPONSE,
  MOCK_REGIME_ADAPTIVE_BACKTEST_RESPONSE,
  MOCK_NEGATIVE_RETURN_BACKTEST_RESPONSE,
} from "./fixtures/risk-and-backtesting.fixture";

import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";

// =============================================================================
// 1. Validation & Formatting Helpers
// =============================================================================

test("Backtest Helpers — formatCurrency formats USD and handles edge cases", () => {
  assert.strictEqual(formatCurrency(100000), "$100,000.00");
  assert.strictEqual(formatCurrency(114500.5), "$114,500.50");
  assert.strictEqual(formatCurrency(0), "$0.00");
  assert.strictEqual(formatCurrency(NaN), "—");
  assert.strictEqual(formatCurrency(null), "—");
});

test("Backtest Helpers — formatPercentage formats percentages accurately", () => {
  assert.strictEqual(formatPercentage(0.145), "14.50%");
  assert.strictEqual(formatPercentage(-0.12), "-12.00%");
  assert.strictEqual(formatPercentage(NaN), "—");
});

// =============================================================================
// 2. Component Rendering Tests
// =============================================================================

test("BacktestHeader — renders title, strategy toggles, and convention selector", () => {
  const html = renderToStaticMarkup(
    React.createElement(BacktestHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
      selectedStrategy: "BUY_AND_HOLD",
      onSelectStrategy: () => {},
      selectedConvention: "CURRENT_CLOSE",
      onSelectConvention: () => {},
      backtestData: MOCK_MARKET_BACKTEST_RESPONSE,
    })
  );

  assert.ok(html.includes("Systematic Backtesting"), "Header must include title");
  assert.ok(html.includes("V20 Event-Driven Engine"), "Header must include badge");
  assert.ok(html.includes("Benchmark Buy &amp; Hold"), "Must render Buy & Hold toggle");
  assert.ok(html.includes("Regime Adaptive"), "Must render Regime Adaptive toggle");
  assert.ok(html.includes("CURRENT_CLOSE"), "Must render convention selector");
  assert.ok(html.includes("$100,000.00"), "Must display starting capital");
  assert.ok(html.includes("5 bps Fee / 5 bps Slip"), "Must display transaction friction");
});

test("BacktestPerformanceOverview — renders final equity, CAGR, and fee decomposition", () => {
  const html = renderToStaticMarkup(
    React.createElement(BacktestPerformanceOverview, {
      backtestData: MOCK_MARKET_BACKTEST_RESPONSE,
    })
  );

  assert.ok(html.includes("Performance Summary"), "Must render section title");
  assert.ok(html.includes("$114,500.00"), "Must display final equity");
  assert.ok(html.includes("+$14,500.00"), "Must display absolute net PnL");
  assert.ok(html.includes("14.50%"), "Must display total return percentage");
  assert.ok(html.includes("PnL Decomposition"), "Must display PnL card");
  assert.ok(html.includes("Execution Friction"), "Must display friction card");
  assert.ok(html.includes("$110.00"), "Must display total fees");
});

test("BacktestPerformanceOverview — handles negative returns gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(BacktestPerformanceOverview, {
      backtestData: MOCK_NEGATIVE_RETURN_BACKTEST_RESPONSE,
    })
  );

  assert.ok(html.includes("Capital Loss"), "Must display capital loss badge");
  assert.ok(html.includes("$88,000.00"), "Must display negative final equity");
  assert.ok(html.includes("-12.00%"), "Must display negative return percentage");
});

test("EquityCurveChart — renders SVG curve with initial capital baseline and drawdown track", () => {
  const html = renderToStaticMarkup(
    React.createElement(EquityCurveChart, {
      equityCurve: MOCK_MARKET_BACKTEST_RESPONSE.equity_curve,
      initialCash: 100_000.0,
    })
  );

  assert.ok(html.includes("Portfolio Equity Trajectory &amp; Drawdown"), "Must render section heading");
  assert.ok(html.includes("<svg"), "Must render SVG chart element");
  assert.ok(html.includes("Capital Basis: $100k"), "Must render capital baseline label");
  assert.ok(html.includes("Equity Curve ($) &amp; Drawdown Subplot (%)"), "Must render chart slot title");
});

test("TradeStatisticsSection — renders trade stats and executed fills log", () => {
  const html = renderToStaticMarkup(
    React.createElement(TradeStatisticsSection, {
      trades: MOCK_REGIME_ADAPTIVE_BACKTEST_RESPONSE.trades,
      executedTrades: MOCK_REGIME_ADAPTIVE_BACKTEST_RESPONSE.executed_trades,
    })
  );

  assert.ok(html.includes("Trade Execution &amp; Win/Loss Statistics"), "Must render section title");
  assert.ok(html.includes("6 / 6"), "Must display order and fill counts");
  assert.ok(html.includes("66.67%"), "Must display win rate");
  assert.ok(html.includes("+$6,200.00"), "Must display largest winning trade");
  assert.ok(html.includes("-$1,200.00"), "Must display largest losing trade");
  assert.ok(html.includes("Executed Fills &amp; Transaction Detail"), "Must render fills table");
  assert.ok(html.includes("BUY"), "Must render buy fill side");
  assert.ok(html.includes("$470.00"), "Must render fill price");
});

test("TradeStatisticsSection — handles empty executed trades gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(TradeStatisticsSection, {
      trades: {
        order_count: 0,
        fill_count: 0,
        completed_trade_count: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0.0,
        total_realized_pnl: 0.0,
        average_trade_pnl: 0.0,
        largest_winning_trade: 0.0,
        largest_losing_trade: 0.0,
      },
      executedTrades: [],
    })
  );

  assert.ok(html.includes("No trade fills were executed"), "Must display empty trades notice");
});

test("BacktestRiskSection — renders risk diagnostics evaluated on equity curve", () => {
  const html = renderToStaticMarkup(
    React.createElement(BacktestRiskSection, {
      riskMetrics: MOCK_MARKET_BACKTEST_RESPONSE.risk_metrics,
    })
  );

  assert.ok(html.includes("Strategy Risk Diagnostics"), "Must render section heading");
  assert.ok(html.includes("17.78%"), "Must render annualized volatility");
  assert.ok(html.includes("-9.85%"), "Must render max equity drawdown");
  assert.ok(html.includes("1.82%"), "Must render 95% VaR loss");
  assert.ok(html.includes("2.48%"), "Must render 95% Expected Shortfall");
});

test("PerformanceReportSection — renders deterministic metadata, methodology, and limitations", () => {
  const html = renderToStaticMarkup(
    React.createElement(PerformanceReportSection, {
      report: MOCK_MARKET_BACKTEST_RESPONSE.report,
    })
  );

  assert.ok(html.includes("Deterministic Performance Report"), "Must render report section heading");
  assert.ok(html.includes("rep-f82b"), "Must render report ID snippet");
  assert.ok(html.includes("Ver: 1.0"), "Must render report version");
  assert.ok(html.includes("Execution Methodology &amp; Policies"), "Must render methodology title");
  assert.ok(html.includes("EventDrivenBacktestEngine (V14)"), "Must render execution engine name");
  assert.ok(html.includes("PortfolioRiskEngine (V13)"), "Must render risk engine name");
  assert.ok(html.includes("Simulation Limitations &amp; Disclaimers"), "Must render limitations title");
  assert.ok(html.includes("Metric Definitions &amp; Directional Semantics"), "Must render definitions table");
  assert.ok(html.includes("HIGHER_IS_BETTER"), "Must render higher-is-better badge");
});
