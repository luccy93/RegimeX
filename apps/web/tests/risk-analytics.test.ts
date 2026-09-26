/**
 * RegimeX Web — Risk Analytics Workspace Tests
 * ============================================
 * Volume 20 — Commit 02
 * Comprehensive test suite verifying RiskHeader, RiskOverview,
 * RiskDrawdownSection, RiskReturnDistributionSection, RiskMethodologySection,
 * defensive formatting helpers, and edge-case rendering.
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { RiskHeader } from "../components/risk/RiskHeader";
import { RiskOverview } from "../components/risk/RiskOverview";
import { RiskDrawdownSection } from "../components/risk/RiskDrawdownSection";
import { RiskReturnDistributionSection } from "../components/risk/RiskReturnDistributionSection";
import { RiskMethodologySection } from "../components/risk/RiskMethodologySection";

import {
  isValidFiniteNumber,
  formatPercentage,
  formatDecimal,
} from "../lib/api/risk";

import {
  MOCK_MARKET_RISK_RESPONSE,
  MOCK_UNRECOVERED_RISK_RESPONSE,
} from "./fixtures/risk-and-backtesting.fixture";

import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";

// =============================================================================
// 1. Validation & Formatting Helpers
// =============================================================================

test("Risk Helpers — isValidFiniteNumber accurately classifies values", () => {
  assert.strictEqual(isValidFiniteNumber(0), true);
  assert.strictEqual(isValidFiniteNumber(0.0112), true);
  assert.strictEqual(isValidFiniteNumber(-0.0985), true);
  assert.strictEqual(isValidFiniteNumber(NaN), false);
  assert.strictEqual(isValidFiniteNumber(Infinity), false);
  assert.strictEqual(isValidFiniteNumber(-Infinity), false);
  assert.strictEqual(isValidFiniteNumber(null), false);
  assert.strictEqual(isValidFiniteNumber(undefined), false);
  assert.strictEqual(isValidFiniteNumber("0.05"), false);
});

test("Risk Helpers — formatPercentage formats percentages and handles non-numbers", () => {
  assert.strictEqual(formatPercentage(0.1778), "17.78%");
  assert.strictEqual(formatPercentage(-0.0985), "-9.85%");
  assert.strictEqual(formatPercentage(0.0, 1), "0.0%");
  assert.strictEqual(formatPercentage(NaN), "—");
  assert.strictEqual(formatPercentage(null), "—");
});

test("Risk Helpers — formatDecimal formats fixed decimals safely", () => {
  assert.strictEqual(formatDecimal(0.00052, 4), "0.0005");
  assert.strictEqual(formatDecimal(12.34567, 2), "12.35");
  assert.strictEqual(formatDecimal(NaN), "—");
});

// =============================================================================
// 2. Component Rendering Tests
// =============================================================================

test("RiskHeader — renders title, badges, and context strip", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
      riskData: MOCK_MARKET_RISK_RESPONSE,
    })
  );

  assert.ok(html.includes("Portfolio Risk Analytics"), "Header must include title");
  assert.ok(html.includes("V20 Risk Intelligence"), "Header must include V20 badge");
  assert.ok(html.includes("SPY"), "Header must display active instrument");
  assert.ok(html.includes("252 bars"), "Header must display sample bar count");
  assert.ok(html.includes("252 periods/yr"), "Header must display annualization basis");
  assert.ok(html.includes("0.00%"), "Header must display target return");
});

test("RiskOverview — renders key risk cards with correct mathematical values", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskOverview, {
      riskData: MOCK_MARKET_RISK_RESPONSE,
    })
  );

  assert.ok(html.includes("Risk Profile Overview"), "Must render section title");
  assert.ok(html.includes("Annualized Volatility"), "Must render Annualized Volatility");
  assert.ok(html.includes("17.78%"), "Must display annualized volatility value");
  assert.ok(html.includes("Maximum Drawdown"), "Must render Maximum Drawdown");
  assert.ok(html.includes("-9.85%"), "Must display max drawdown value");
  assert.ok(html.includes("Value at Risk (95% 1-Day)"), "Must render VaR 95% card");
  assert.ok(html.includes("1.82%"), "Must render VaR 95% loss value");
  assert.ok(html.includes("Expected Shortfall (95% 1-Day)"), "Must render Expected Shortfall card");
  assert.ok(html.includes("2.48%"), "Must render ES 95% tail mean loss");
  assert.ok(html.includes("Downside Deviation"), "Must render Downside Deviation card");
  assert.ok(html.includes("Mean Daily Return"), "Must render Mean Daily Return");
});

test("RiskDrawdownSection — renders SVG drawdown timeline and peak-to-trough details", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskDrawdownSection, {
      riskData: MOCK_MARKET_RISK_RESPONSE,
    })
  );

  assert.ok(html.includes("Drawdown Track &amp; Peak-to-Trough Profile"), "Must render section heading");
  assert.ok(html.includes("<svg"), "Must render SVG chart");
  assert.ok(html.includes("Pre-Crash Peak"), "Must render pre-crash peak label");
  assert.ok(html.includes("$512.45"), "Must render peak value");
  assert.ok(html.includes("Trough Depth"), "Must render trough depth label");
  assert.ok(html.includes("$462.00"), "Must render trough value");
  assert.ok(html.includes("Fully Recovered"), "Must display fully recovered status for recovered drawdown");
});

test("RiskDrawdownSection — renders Unrecovered badge when drawdown is active", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskDrawdownSection, {
      riskData: MOCK_UNRECOVERED_RISK_RESPONSE,
    })
  );

  assert.ok(html.includes("Active Underwater Phase"), "Must display active underwater phase badge");
  assert.ok(html.includes("Unrecovered"), "Must display unrecovered badge");
});

test("RiskReturnDistributionSection — renders multi-tier VaR and ES quantile table", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskReturnDistributionSection, {
      riskData: MOCK_MARKET_RISK_RESPONSE,
    })
  );

  assert.ok(html.includes("Tail Risk &amp; Return Dispersion"), "Must render section title");
  assert.ok(html.includes("90% Confidence"), "Must display 90% confidence tier");
  assert.ok(html.includes("95% Confidence"), "Must display 95% confidence tier");
  assert.ok(html.includes("99% Confidence"), "Must display 99% confidence tier");
  assert.ok(html.includes("Minimum 1-Day Return"), "Must render minimum return statistic");
  assert.ok(html.includes("-3.85%"), "Must display minimum return value");
  assert.ok(html.includes("Maximum 1-Day Return"), "Must render maximum return statistic");
  assert.ok(html.includes("+3.42%"), "Must display maximum return value");
});

test("RiskMethodologySection — renders mathematical formulas and regulatory disclaimers", () => {
  const html = renderToStaticMarkup(
    React.createElement(RiskMethodologySection, {})
  );

  assert.ok(html.includes("Analytical Methodology &amp; Risk Disclosures"), "Must render title");
  assert.ok(html.includes("R_t = (P_t - P_(t-1)) / P_(t-1)"), "Must disclose discrete return formula");
  assert.ok(html.includes("σ_ann = σ_period × √(252)"), "Must disclose annualization scaling factor");
  assert.ok(html.includes("VaR_α = -Quantile_(1-α)(R)"), "Must disclose loss-oriented VaR formulation");
  assert.ok(html.includes("Model Limitations &amp; Non-Stationarity"), "Must disclose non-stationarity disclaimer");
});
