/**
 * V19 Commit 02 — Interactive Regime Visualization Tests
 * ======================================================
 * Tests regime timeline computation, regime overlay chart rendering,
 * regime legend, and regime confidence bar components.
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { RegimeLegend } from "../components/markets/RegimeLegend";
import { RegimeTimeline } from "../components/markets/RegimeTimeline";
import { RegimeOverlayChart } from "../components/markets/RegimeOverlayChart";
import { RegimeConfidenceBar } from "../components/markets/RegimeConfidenceBar";

import {
  computeRegimeTimeline,
  computeRegimeDistribution,
} from "../lib/utils/regime-timeline";
import {
  getRegimeColor,
  getRegimeColorIndex,
  formatRegimeLabel,
} from "../lib/utils/regime";

import {
  MOCK_BARS_SERIES,
  MOCK_KNOWN_REGIME_RESPONSE,
  MOCK_UNKNOWN_REGIME_RESPONSE,
} from "./fixtures/market-data.fixture";

// =============================================================================
// Unit: regime-timeline.ts — computeRegimeTimeline
// =============================================================================

test("computeRegimeTimeline — returns empty for null regime data", () => {
  const result = computeRegimeTimeline(null, MOCK_BARS_SERIES);
  assert.strictEqual(result.segments.length, 0);
  assert.strictEqual(result.transitions.length, 0);
  assert.strictEqual(result.totalBars, 0);
});

test("computeRegimeTimeline — returns empty for empty bars", () => {
  const result = computeRegimeTimeline(MOCK_KNOWN_REGIME_RESPONSE, []);
  assert.strictEqual(result.segments.length, 0);
  assert.strictEqual(result.totalBars, 0);
});

test("computeRegimeTimeline — produces segments from known regime data", () => {
  const result = computeRegimeTimeline(MOCK_KNOWN_REGIME_RESPONSE, MOCK_BARS_SERIES);

  assert.ok(result.segments.length > 0, "Should produce at least one segment");
  assert.strictEqual(result.totalBars, MOCK_BARS_SERIES.length);

  // Each segment should have valid indices
  for (const seg of result.segments) {
    assert.ok(seg.startIndex >= 0, "startIndex should be >= 0");
    assert.ok(seg.endIndex < MOCK_BARS_SERIES.length, "endIndex should be within bounds");
    assert.ok(seg.endIndex >= seg.startIndex, "endIndex should be >= startIndex");
    assert.ok(seg.barCount > 0, "barCount should be > 0");
    assert.ok(seg.regimeLabel.length > 0, "regimeLabel should be non-empty");
  }
});

test("computeRegimeTimeline — transitions match segment boundaries", () => {
  const result = computeRegimeTimeline(MOCK_KNOWN_REGIME_RESPONSE, MOCK_BARS_SERIES);

  // Transitions = segments.length - 1 (at most)
  assert.ok(
    result.transitions.length <= result.segments.length - 1 || result.segments.length <= 1,
    "Transitions should be at most segments - 1"
  );

  // Each transition should reference valid regime IDs
  for (const tr of result.transitions) {
    assert.ok(tr.barIndex >= 0, "barIndex should be >= 0");
    assert.ok(tr.barIndex < MOCK_BARS_SERIES.length, "barIndex should be within bounds");
    assert.ok(tr.fromRegimeLabel.length > 0, "fromRegimeLabel should be non-empty");
    assert.ok(tr.toRegimeLabel.length > 0, "toRegimeLabel should be non-empty");
  }
});

test("computeRegimeTimeline — last segment is marked as current", () => {
  const result = computeRegimeTimeline(MOCK_KNOWN_REGIME_RESPONSE, MOCK_BARS_SERIES);

  if (result.segments.length > 0) {
    const lastSeg = result.segments[result.segments.length - 1];
    assert.strictEqual(lastSeg.isCurrent, true, "Last segment should be marked as current");
    assert.strictEqual(
      lastSeg.regimeId,
      MOCK_KNOWN_REGIME_RESPONSE.current_regime,
      "Last segment regime should match current_regime"
    );
  }
});

test("computeRegimeTimeline — handles unknown regime gracefully", () => {
  const result = computeRegimeTimeline(MOCK_UNKNOWN_REGIME_RESPONSE, MOCK_BARS_SERIES);
  // Unknown regime has no profiles, so should fall back to single segment
  assert.ok(result.segments.length >= 0, "Should not throw on unknown regime");
});

// =============================================================================
// Unit: computeRegimeDistribution
// =============================================================================

test("computeRegimeDistribution — returns 0 for empty", () => {
  const dist = computeRegimeDistribution([], 0);
  assert.strictEqual(dist.size, 0);
});

test("computeRegimeDistribution — sums percentages correctly", () => {
  const result = computeRegimeTimeline(MOCK_KNOWN_REGIME_RESPONSE, MOCK_BARS_SERIES);
  const dist = computeRegimeDistribution(result.segments, result.totalBars);

  let totalPct = 0;
  for (const pct of dist.values()) {
    totalPct += pct;
  }

  assert.ok(
    Math.abs(totalPct - 100) < 0.01,
    `Total distribution should sum to ~100%, got ${totalPct}`
  );
});

// =============================================================================
// Unit: regime.ts — getRegimeColor
// =============================================================================

test("getRegimeColor — returns semantic color for BULLISH label", () => {
  const color = getRegimeColor("BULLISH", 0);
  assert.strictEqual(color.hex, "#10b981", "BULLISH should map to emerald");
  assert.ok(color.hexSubtle.includes("rgba"), "Should have RGBA subtle variant");
});

test("getRegimeColor — returns semantic color for BEARISH label", () => {
  const color = getRegimeColor("BEARISH", 1);
  assert.strictEqual(color.hex, "#ef4444", "BEARISH should map to red");
});

test("getRegimeColor — returns palette color for canonical REGIME_N labels", () => {
  const color0 = getRegimeColor("REGIME_0", 0);
  const color1 = getRegimeColor("REGIME_1", 1);
  // Canonical labels should fall back to palette
  assert.ok(color0.hex.startsWith("#"), "Should return a hex color");
  assert.ok(color1.hex.startsWith("#"), "Should return a hex color");
  assert.notStrictEqual(color0.hex, color1.hex, "Different regime IDs should map to different colors");
});

test("getRegimeColor — handles null label gracefully", () => {
  const color = getRegimeColor(null, 3);
  assert.ok(color.hex.startsWith("#"), "Should return a hex color even with null label");
});

test("getRegimeColorIndex — wraps around the 8-color palette", () => {
  assert.strictEqual(getRegimeColorIndex(0), 0);
  assert.strictEqual(getRegimeColorIndex(8), 0);
  assert.strictEqual(getRegimeColorIndex(3), 3);
  assert.strictEqual(getRegimeColorIndex(15), 7);
});

// =============================================================================
// Component: RegimeLegend
// =============================================================================

test("RegimeLegend — renders nothing when no regime data", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeLegend, { regimeData: null })
  );
  assert.strictEqual(html, "", "Should render empty string for null regime data");
});

test("RegimeLegend — renders legend items for each regime profile", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeLegend, { regimeData: MOCK_KNOWN_REGIME_RESPONSE })
  );

  assert.ok(html.includes("regime-legend"), "Should render legend container");
  assert.ok(html.includes("Regime 0"), "Should render formatted label for Regime 0");
  assert.ok(html.includes("Regime 1"), "Should render formatted label for Regime 1");
  assert.ok(html.includes("regime-legend-swatch"), "Should render color swatches");
});

test("RegimeLegend — highlights the active regime", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeLegend, { regimeData: MOCK_KNOWN_REGIME_RESPONSE })
  );

  assert.ok(html.includes("regime-legend-item-active"), "Should mark the current regime as active");
  assert.ok(html.includes("regime-legend-active-badge"), "Should show Active badge");
});

// =============================================================================
// Component: RegimeTimeline
// =============================================================================

test("RegimeTimeline — renders nothing when no regime data", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeTimeline, {
      symbol: "SPY",
      bars: MOCK_BARS_SERIES,
      regimeData: null,
    })
  );
  assert.strictEqual(html, "", "Should render empty for null regime data");
});

test("RegimeTimeline — renders timeline with segments and legend", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeTimeline, {
      symbol: "SPY",
      bars: MOCK_BARS_SERIES,
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
    })
  );

  assert.ok(html.includes("regime-timeline-container"), "Should render timeline container");
  assert.ok(html.includes("Regime Timeline"), "Should render timeline title");
  assert.ok(html.includes("regime-legend"), "Should include regime legend");
  assert.ok(html.includes("regime-timeline-svg"), "Should render SVG timeline");
  assert.ok(html.includes("regime-timeline-segment"), "Should render segment rectangles");
});

// =============================================================================
// Component: RegimeOverlayChart
// =============================================================================

test("RegimeOverlayChart — renders error state", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeOverlayChart, {
      symbol: "SPY",
      bars: [],
      error: "API timeout",
      requestId: "req-overlay-err",
      onRetry: () => {},
    })
  );

  assert.ok(html.includes("Market Data Unavailable"), "Should render error title");
  assert.ok(html.includes("API timeout"), "Should render error message");
  assert.ok(html.includes("req-overlay-err"), "Should render request ID");
});

test("RegimeOverlayChart — renders regime-colored chart with regime data", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeOverlayChart, {
      symbol: "SPY",
      bars: MOCK_BARS_SERIES,
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      currency: "USD",
      interval: "1d",
    })
  );

  assert.ok(html.includes("Regime-Colored Price History"), "Should render enhanced title");
  assert.ok(html.includes("regime overlay segments"), "Should mention regime overlay in description");
  assert.ok(html.includes("regime-overlay-svg"), "Should render SVG canvas");
  assert.ok(html.includes("regime-overlay-band"), "Should render regime background bands");
});

test("RegimeOverlayChart — renders without regime data gracefully", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeOverlayChart, {
      symbol: "SPY",
      bars: MOCK_BARS_SERIES,
      regimeData: null,
      currency: "USD",
    })
  );

  assert.ok(html.includes("regime-overlay-svg"), "Should still render SVG chart without regime data");
  // Should not include regime bands when no regime data
  assert.ok(!html.includes("regime-overlay-band"), "Should not render regime bands without data");
});

// =============================================================================
// Component: RegimeConfidenceBar
// =============================================================================

test("RegimeConfidenceBar — renders nothing for null regime data", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeConfidenceBar, { regimeData: null })
  );
  assert.strictEqual(html, "", "Should not render when regime data is null");
});

test("RegimeConfidenceBar — renders nothing when confidence is null", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeConfidenceBar, { regimeData: MOCK_UNKNOWN_REGIME_RESPONSE })
  );
  assert.strictEqual(html, "", "Should not render when confidence is null");
});

test("RegimeConfidenceBar — renders confidence gauge for known regime", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeConfidenceBar, { regimeData: MOCK_KNOWN_REGIME_RESPONSE })
  );

  assert.ok(html.includes("Regime Confidence"), "Should render title");
  assert.ok(html.includes("regime-confidence-gauge-track"), "Should render gauge track");
  assert.ok(html.includes("regime-confidence-gauge-fill"), "Should render gauge fill");
  assert.ok(html.includes("88.4%"), "Should display confidence percentage");
  assert.ok(html.includes("regime-confidence-gauge-dot"), "Should render regime color dot");
});

test("RegimeConfidenceBar — classifies confidence zone correctly", () => {
  // 88.4% should be "high" confidence zone
  const html = renderToStaticMarkup(
    React.createElement(RegimeConfidenceBar, { regimeData: MOCK_KNOWN_REGIME_RESPONSE })
  );
  assert.ok(html.includes("High Confidence"), "88.4% should be classified as High Confidence");
});

test("RegimeConfidenceBar — displays model provenance metadata", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeConfidenceBar, { regimeData: MOCK_KNOWN_REGIME_RESPONSE })
  );
  assert.ok(html.includes("kmeans-regime-detector"), "Should display model name");
  assert.ok(html.includes("kmeans"), "Should display algorithm");
});
