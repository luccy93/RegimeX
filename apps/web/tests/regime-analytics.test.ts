/**
 * RegimeX Web — Regime Analytics Workspace Tests
 * ===============================================
 * Volume 20 — Commit 01
 * Comprehensive tests for regime profiles, frequency, persistence, duration,
 * feature statistics, empirical transition matrix, transition entropy,
 * missing-data integrity, and accessibility.
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { CurrentRegimeSummary } from "../components/regimes/CurrentRegimeSummary";
import { RegimeDistributionSection } from "../components/regimes/RegimeDistributionSection";
import { RegimeFrequencyPersistence } from "../components/regimes/RegimeFrequencyPersistence";
import { RegimeDurationSection } from "../components/regimes/RegimeDurationSection";
import { RegimeProfileComparison } from "../components/regimes/RegimeProfileComparison";
import { TransitionAnalyticsSection } from "../components/regimes/TransitionAnalyticsSection";
import { MethodologyProvenanceSection } from "../components/regimes/MethodologyProvenanceSection";
import { RegimeWorkspaceHeader } from "../components/regimes/RegimeWorkspaceHeader";

import {
  computeRegimeDistributionPercentages,
  isValidFiniteNumber,
  isValidProbability,
  isValidTransitionMatrix,
} from "../lib/api/regimes";

import {
  formatProbability,
  formatEntropy,
} from "../lib/utils/formatters";

import {
  formatRegimeLabel,
} from "../lib/utils/regime";

import {
  MOCK_MULTI_REGIME_RESPONSE,
  MOCK_SINGLE_REGIME_RESPONSE,
  MOCK_NULL_STATS_REGIME_RESPONSE,
  MOCK_EMPTY_REGIMES_RESPONSE,
  MOCK_TRANSITION_RESPONSE,
  MOCK_ZERO_TRANSITIONS_RESPONSE,
  MOCK_ALL_SELF_TRANSITIONS_RESPONSE,
} from "./fixtures/regime-analytics.fixture";

import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";

// =============================================================================
// 1. Data Integrity & Validation Helpers
// =============================================================================

test("isValidFiniteNumber — correctly identifies valid and invalid numbers", () => {
  assert.strictEqual(isValidFiniteNumber(0), true);
  assert.strictEqual(isValidFiniteNumber(123.45), true);
  assert.strictEqual(isValidFiniteNumber(-0.05), true);
  assert.strictEqual(isValidFiniteNumber(NaN), false);
  assert.strictEqual(isValidFiniteNumber(Infinity), false);
  assert.strictEqual(isValidFiniteNumber(-Infinity), false);
  assert.strictEqual(isValidFiniteNumber(null), false);
  assert.strictEqual(isValidFiniteNumber(undefined), false);
  assert.strictEqual(isValidFiniteNumber("123"), false);
});

test("isValidProbability — accepts valid probabilities in [0, 1] and rejects outside", () => {
  assert.strictEqual(isValidProbability(0.0), true);
  assert.strictEqual(isValidProbability(0.724), true);
  assert.strictEqual(isValidProbability(1.0), true);
  assert.strictEqual(isValidProbability(-0.1), false);
  assert.strictEqual(isValidProbability(1.05), false);
  assert.strictEqual(isValidProbability(NaN), false);
});

test("isValidTransitionMatrix — validates N x N matrix dimensions and values", () => {
  assert.strictEqual(isValidTransitionMatrix([[0.7, 0.3], [0.2, 0.8]], 2), true);
  assert.strictEqual(isValidTransitionMatrix([[1.0]], 1), true);
  // Mismatched size
  assert.strictEqual(isValidTransitionMatrix([[0.7, 0.3]], 2), false);
  assert.strictEqual(isValidTransitionMatrix([[0.7], [0.2]], 2), false);
  // Non-number in cell
  assert.strictEqual(isValidTransitionMatrix([[0.7, NaN], [0.2, 0.8]], 2), false);
  assert.strictEqual(isValidTransitionMatrix(null, 2), false);
});

test("computeRegimeDistributionPercentages — computes exact percentages strictly from counts", () => {
  const profiles = {
    0: { observation_count: 30 },
    1: { observation_count: 50 },
    2: { observation_count: 20 },
  };
  const percentages = computeRegimeDistributionPercentages(profiles, 100);
  assert.strictEqual(percentages["0"], 30);
  assert.strictEqual(percentages["1"], 50);
  assert.strictEqual(percentages["2"], 20);

  // Zero total observations returns empty without NaN / Infinity
  const emptyPercentages = computeRegimeDistributionPercentages(profiles, 0);
  assert.deepStrictEqual(emptyPercentages, {});
});

// =============================================================================
// 2. Formatters: Probabilities & Entropy
// =============================================================================

test("formatProbability — formats probabilities predictably", () => {
  assert.strictEqual(formatProbability(0.724), "0.724");
  assert.strictEqual(formatProbability(0.72412, 2), "0.72");
  assert.strictEqual(formatProbability(1.0), "1.000");
  assert.strictEqual(formatProbability(null), "—");
  assert.strictEqual(formatProbability(undefined), "—");
  assert.strictEqual(formatProbability(NaN), "—");
});

test("formatEntropy — formats transition entropy with nats unit", () => {
  assert.strictEqual(formatEntropy(1.241), "1.24 nats");
  assert.strictEqual(formatEntropy(0.0), "0.00 nats");
  assert.strictEqual(formatEntropy(null), "—");
  assert.strictEqual(formatEntropy(undefined), "—");
  assert.strictEqual(formatEntropy(NaN), "—");
});

// =============================================================================
// 3. CurrentRegimeSummary Component
// =============================================================================

test("CurrentRegimeSummary — renders known regime with full context", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeSummary, { regimeData: MOCK_MULTI_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Regime 1"), "Should display formatted regime label");
  assert.ok(html.includes("ID: 1"), "Should display regime ID badge");
  assert.ok(html.includes("88.4%"), "Should display confidence percentage");
  assert.ok(html.includes("8 bars"), "Should display current run duration");
  assert.ok(html.includes("12.5 bars"), "Should display historical average duration");
  assert.ok(html.includes("25 bars"), "Should display historical max duration");
  assert.ok(html.includes("50.0%"), "Should display historical frequency");
  assert.ok(html.includes("gmm-regime-detector"), "Should mention model provenance");
  assert.ok(html.includes("return_1d"), "Should display active feature return_1d");
  assert.ok(html.includes("volatility_20d"), "Should display active feature volatility_20d");
});

test("CurrentRegimeSummary — handles unavailable confidence and null features gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeSummary, { regimeData: MOCK_NULL_STATS_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Unavailable"), "Should display Unavailable for null confidence");
  assert.ok(html.includes("Unknown"), "Should format UNKNOWN regime label cleanly");
});

test("CurrentRegimeSummary — renders loading skeleton", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeSummary, { isLoading: true })
  );

  assert.ok(html.includes('aria-busy="true"'), "Should render with aria-busy");
  assert.ok(html.includes("ui-skeleton"), "Should render skeletons");
});

// =============================================================================
// 4. RegimeDistributionSection Component
// =============================================================================

test("RegimeDistributionSection — renders proportional horizontal segments and chips", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeDistributionSection, { regimeData: MOCK_MULTI_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Regime Distribution"), "Should render section header");
  assert.ok(html.includes("regime-distribution-bar-track"), "Should render composite bar track");
  assert.ok(html.includes("width:50%"), "Should scale segment according to count / total");
  assert.ok(html.includes("width:30%"), "Should scale segment according to count / total");
  assert.ok(html.includes("width:20%"), "Should scale segment according to count / total");
  assert.ok(html.includes("50.0%"), "Should display 50.0% share");
  assert.ok(html.includes("50 / 100 bars"), "Should display counts");
  assert.ok(html.includes("Current"), "Should mark active regime with Current badge");
});

test("RegimeDistributionSection — handles single regime scenario", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeDistributionSection, { regimeData: MOCK_SINGLE_REGIME_RESPONSE })
  );

  assert.ok(html.includes("100.0%"), "Single regime should display 100.0%");
  assert.ok(html.includes("width:100%"), "Single regime segment should fill track");
});

test("RegimeDistributionSection — handles empty regimes gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeDistributionSection, { regimeData: MOCK_EMPTY_REGIMES_RESPONSE })
  );

  assert.ok(html.includes("No regime distribution observations recorded"), "Should display empty message");
});

// =============================================================================
// 5. RegimeFrequencyPersistence Component
// =============================================================================

test("RegimeFrequencyPersistence — renders frequency table with persistence metrics", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeFrequencyPersistence, {
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
      transitionData: MOCK_TRANSITION_RESPONSE,
    })
  );

  assert.ok(html.includes("Regime Frequency &amp; Persistence"), "Should render title");
  assert.ok(html.includes("70.0%"), "Should display persistence rate for Regime 0");
  assert.ok(html.includes("75.5%"), "Should display persistence rate for Regime 1");
  assert.ok(html.includes("50.0%"), "Should display persistence rate for Regime 2");
  assert.ok(html.includes("First Seen"), "Should render First Seen column");
  assert.ok(html.includes("Last Seen"), "Should render Last Seen column");
  assert.ok(html.includes("Statistical distinction"), "Should include methodological explanation");
});

test("RegimeFrequencyPersistence — handles missing transition data gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeFrequencyPersistence, {
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
      transitionData: null,
    })
  );

  assert.ok(html.includes("—"), "Should display dash when persistence data is unavailable");
});

// =============================================================================
// 6. RegimeDurationSection Component
// =============================================================================

test("RegimeDurationSection — renders comparative duration metrics and distribution notice", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeDurationSection, { regimeData: MOCK_MULTI_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Duration Analysis"), "Should render title");
  assert.ok(html.includes("12.5 bars"), "Should display average duration with units bars");
  assert.ok(html.includes("25 bars"), "Should display max duration with units bars");
  assert.ok(html.includes("Detailed duration distribution unavailable"), "Section 13 explicit fallback");
});

// =============================================================================
// 7. RegimeProfileComparison & Nullable Statistics
// =============================================================================

test("RegimeProfileComparison — renders feature statistics across regimes", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeProfileComparison, { regimeData: MOCK_MULTI_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Regime Profile Comparison"), "Should render title");
  assert.ok(html.includes("return_1d"), "Should display return_1d feature row");
  assert.ok(html.includes("volatility_20d"), "Should display volatility_20d feature row");
  assert.ok(html.includes("Std Dev"), "Should include standard deviation filter button");
});

test("RegimeProfileComparison — respects nullable statistics without zero-imputation", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeProfileComparison, { regimeData: MOCK_NULL_STATS_REGIME_RESPONSE })
  );

  // Crucial test for Section 15: null must NEVER become 0!
  assert.ok(html.includes("—"), "Null feature statistics must display as '—'");
  assert.ok(!html.includes("0.00%"), "Missing feature return must NOT be zero-imputed to 0.00%");
});

// =============================================================================
// 8. TransitionAnalyticsSection Component
// =============================================================================

test("TransitionAnalyticsSection — renders global metrics, transition matrix, and destinations", () => {
  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: MOCK_TRANSITION_RESPONSE,
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("Regime Change &amp; Transition Analytics"), "Should render title");
  assert.ok(html.includes("Total Changes"), "Should display Total Changes metric");
  assert.ok(html.includes("Self-Transitions"), "Should display Self-Transitions metric");
  assert.ok(html.includes("31.3%"), "Should display Global Change Rate");
  assert.ok(html.includes("68.7%"), "Should display Global Persistence Rate");
  assert.ok(html.includes("99"), "Should display consecutive transitions count");
  assert.ok(html.includes("Diagonal: Self-Transition"), "Should distinguish self-transitions from changes");
  assert.ok(html.includes("persist"), "Should label diagonal cells with persist");
  assert.ok(html.includes("0.700"), "Should format probability in matrix");
  assert.ok(html.includes("Entropy: 1.15 nats"), "Should render transition entropy in nats");
  assert.ok(!html.includes("dangerous"), "Must NOT label entropy as dangerous");
  assert.ok(!html.includes("risk"), "Must NOT label transition entropy as risk");
});

test("TransitionAnalyticsSection — isolates API error with retry button", () => {
  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: null,
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
      error: "Insufficient history for transition matrix computation.",
      onRetry: () => {},
    })
  );

  assert.ok(html.includes("transition-error-card"), "Should render isolated error card");
  assert.ok(html.includes("Insufficient history"), "Should render contextual error message");
  assert.ok(html.includes("Retry Transitions"), "Should provide isolated retry button");
});

test("TransitionAnalyticsSection — handles zero transition events gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: MOCK_ZERO_TRANSITIONS_RESPONSE,
      regimeData: MOCK_SINGLE_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes(">0</span>") && html.includes("events"), "Should display 0 events without errors");
  assert.ok(html.includes("0.00 nats"), "Entropy should be 0.00 nats");
});

test("TransitionAnalyticsSection — handles all self-transitions (100% persistence)", () => {
  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: MOCK_ALL_SELF_TRANSITIONS_RESPONSE,
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("100.0%"), "Persistence rate should be 100.0%");
  assert.ok(html.includes("0.0%"), "Change rate should be 0.0%");
});

// =============================================================================
// 9. MethodologyProvenanceSection Component
// =============================================================================

test("MethodologyProvenanceSection — renders model parameters and diagnostic scope", () => {
  const html = renderToStaticMarkup(
    React.createElement(MethodologyProvenanceSection, { regimeData: MOCK_MULTI_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Analytical Methodology &amp; Provenance"), "Should render title");
  assert.ok(html.includes("gmm-regime-detector"), "Should display model name");
  assert.ok(html.includes("2.1.0"), "Should display model version");
  assert.ok(html.includes("gaussian_mixture"), "Should display algorithm");
  assert.ok(html.includes("100 bars"), "Should display sample size");
  assert.ok(html.includes("Descriptive &amp; Diagnostic"), "Must clearly state non-predictive scope");
  assert.ok(!html.includes("AI analysis"), "Must NOT use generic 'AI analysis' label");
});

// =============================================================================
// 10. RegimeWorkspaceHeader Component
// =============================================================================

test("RegimeWorkspaceHeader — renders page titles, market info, and analysis window", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeWorkspaceHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("Regime Analytics"), "Should render page title");
  assert.ok(html.includes("SPDR S&amp;P 500 ETF Trust"), "Should display market description");
  assert.ok(html.includes("2025-09-24 → 2026-09-24"), "Should display verified analysis window");
  assert.ok(html.includes("100 bars"), "Should display sample count");
});

// =============================================================================
// 11. Edge Cases & Boundary Conditions (Section 37)
// =============================================================================

test("TransitionAnalyticsSection — handles high transition entropy vs low transition entropy", () => {
  const highEntropyResponse: typeof MOCK_TRANSITION_RESPONSE = {
    ...MOCK_TRANSITION_RESPONSE,
    regime_analytics: {
      0: {
        ...MOCK_TRANSITION_RESPONSE.regime_analytics[0],
        transition_entropy: 1.386,
      },
      1: {
        ...MOCK_TRANSITION_RESPONSE.regime_analytics[1],
        transition_entropy: 0.05,
      },
    },
  };

  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: highEntropyResponse,
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("1.39 nats"), "Should format high entropy properly");
  assert.ok(html.includes("0.05 nats"), "Should format low entropy properly");
});

test("formatRegimeLabel — handles unknown and non-canonical regime identifiers", () => {
  assert.strictEqual(formatRegimeLabel("UNKNOWN"), "Unknown");
  assert.strictEqual(formatRegimeLabel(null), "Unknown");
  assert.strictEqual(formatRegimeLabel(""), "Unknown");
  assert.strictEqual(formatRegimeLabel("REGIME_99"), "Regime 99");
  assert.strictEqual(formatRegimeLabel("R12"), "Regime 12");
  assert.strictEqual(formatRegimeLabel("CUSTOM_VOLATILITY_STATE"), "Custom Volatility State");
});

test("RegimeWorkspaceHeader — handles large market catalog gracefully", () => {
  const largeCatalog = Array.from({ length: 50 }, (_, i) => ({
    symbol: `SYM${i}`,
    asset_class: "equity_us",
    exchange: "NYSE",
    currency: "USD",
    description: `Security ${i}`,
  }));

  const html = renderToStaticMarkup(
    React.createElement(RegimeWorkspaceHeader, {
      markets: largeCatalog,
      selectedSymbol: "SYM10",
      onSelectMarket: () => {},
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("SYM10 (Security 10)"), "Should find and display active market from large catalog");
});

test("TransitionAnalyticsSection — handles empty transition matrix and zero observed edges", () => {
  const emptyMatrixResponse: typeof MOCK_TRANSITION_RESPONSE = {
    ...MOCK_TRANSITION_RESPONSE,
    probability_matrix: [],
    regimes: [],
    global_analytics: {
      ...MOCK_TRANSITION_RESPONSE.global_analytics,
      number_of_observed_transition_edges: 0,
      total_consecutive_transitions: 0,
      total_regime_changes: 0,
    },
  };

  const html = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: emptyMatrixResponse,
      regimeData: MOCK_MULTI_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("Total Changes"), "Should render empty metrics without throwing");
});
