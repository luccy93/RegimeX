import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RegimeHistory } from "../components/markets/RegimeHistory";
import { DataHealth } from "../components/markets/DataHealth";
import {
  MOCK_MARKET_DATA_RESPONSE,
  MOCK_KNOWN_REGIME_RESPONSE,
  MOCK_UNKNOWN_REGIME_RESPONSE,
} from "./fixtures/market-data.fixture";

test("RegimeHistory — renders distribution bar and profiles table", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeHistory, {
      symbol: "SPY",
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      isLoading: false,
    })
  );

  assert.ok(html.includes("Observed Regime Profiles &amp; Distribution"), "Renders title");
  assert.ok(html.includes("2 distinct regime states observed"), "Renders observation summary");
  assert.ok(html.includes("regime-dist-bar-track"), "Renders distribution progress bar");
  assert.ok(html.includes("62.50%"), "Displays regime 1 frequency");
  assert.ok(html.includes("37.50%"), "Displays regime 0 frequency");
  assert.ok(html.includes("Active"), "Marks current regime 1 as active");
});

test("RegimeHistory — handles empty historical profiles", () => {
  const html = renderToStaticMarkup(
    React.createElement(RegimeHistory, {
      symbol: "XYZ",
      regimeData: MOCK_UNKNOWN_REGIME_RESPONSE,
      isLoading: false,
    })
  );

  assert.ok(
    html.includes("No historical regime profiles available for XYZ"),
    "Displays empty state message"
  );
});

test("DataHealth — renders verified data feed and model provenance metrics", () => {
  const html = renderToStaticMarkup(
    React.createElement(DataHealth, {
      symbol: "SPY",
      marketData: MOCK_MARKET_DATA_RESPONSE,
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      isLoading: false,
    })
  );

  assert.ok(html.includes("Data Health &amp; Model Provenance"), "Renders card title");
  assert.ok(html.includes("Data available"), "Renders positive data available status");
  assert.ok(html.includes("5 bars"), "Renders verified bar count");
  assert.ok(html.includes("kmeans-regime-detector"), "Renders model provenance name");
  assert.ok(html.includes("1.2.0"), "Renders model version");
  assert.ok(html.includes("UTC (ISO 8601 aware)"), "States timezone-aware UTC");
  assert.ok(html.includes("Explore Transition Matrix"), "Renders future transition analytics link");
});
