import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CurrentRegimeCard } from "../components/markets/CurrentRegimeCard";
import {
  MOCK_KNOWN_REGIME_RESPONSE,
  MOCK_UNKNOWN_REGIME_RESPONSE,
} from "./fixtures/market-data.fixture";

test("CurrentRegimeCard — renders known regime with full statistical context", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeCard, {
      symbol: "SPY",
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      isLoading: false,
    })
  );

  // Regime label and tag
  assert.ok(html.includes("Regime 1"), "Displays formatted regime name");
  assert.ok(html.includes("REGIME_1"), "Displays raw canonical code badge");

  // Confidence
  assert.ok(html.includes("88.4%"), "Displays confidence percentage");
  assert.ok(html.includes("kmeans"), "Displays algorithm name");

  // Persistence & Duration
  assert.ok(html.includes("8 bars"), "Displays current run persistence");
  assert.ok(html.includes("12.4 bars"), "Displays historical average duration");
  assert.ok(html.includes("24 bars"), "Displays historical max duration");
  assert.ok(html.includes("62.50%"), "Displays historical occurrence frequency");

  // Feature distributions table
  assert.ok(html.includes("return_1d"), "Displays feature table with return_1d");
  assert.ok(html.includes("volatility_20d"), "Displays feature table with volatility_20d");
});

test("CurrentRegimeCard — handles unknown regime and unavailable confidence", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeCard, {
      symbol: "XYZ",
      regimeData: MOCK_UNKNOWN_REGIME_RESPONSE,
      isLoading: false,
    })
  );

  assert.ok(html.includes("Unknown"), "Displays Unknown for unclassified market");
  assert.ok(html.includes("Unavailable"), "Confidence shows Unavailable when null");
  assert.ok(html.includes("regime-neutral"), "Unknown regime uses neutral semantic styling");
  assert.ok(
    html.includes("No continuous feature distributions provided"),
    "Renders friendly message when features are absent"
  );
});

test("CurrentRegimeCard — renders error state with retry", () => {
  const html = renderToStaticMarkup(
    React.createElement(CurrentRegimeCard, {
      symbol: "SPY",
      error: "FastAPI regime detector timeout",
      requestId: "req-err-456",
      onRetry: () => {},
    })
  );

  assert.ok(html.includes("Regime Classification Unavailable"), "Displays error state title");
  assert.ok(html.includes("FastAPI regime detector timeout"), "Displays error message");
  assert.ok(html.includes("req-err-456"), "Renders correlation request ID");
  assert.ok(html.includes("Retry Regime Detection"), "Renders retry button");
});
