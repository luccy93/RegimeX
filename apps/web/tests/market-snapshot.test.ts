import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarketSnapshot } from "../components/markets/MarketSnapshot";
import {
  MOCK_MARKET_DATA_RESPONSE,
  MOCK_KNOWN_REGIME_RESPONSE,
  MOCK_UNKNOWN_REGIME_RESPONSE,
} from "./fixtures/market-data.fixture";

test("MarketSnapshot — renders metrics derived from real API-shaped responses", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSnapshot, {
      marketData: MOCK_MARKET_DATA_RESPONSE,
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      currency: "USD",
      isLoading: false,
    })
  );

  // Current Price: close of last bar is 513.5
  assert.ok(html.includes("$513.50"), "Snapshot renders formatted current close price");

  // Latest Return: (513.5 - 511.0) / 511.0 = +0.49%
  assert.ok(html.includes("+0.49%"), "Snapshot renders calculated 1-bar return with positive sign");

  // Regime Volatility: from statistics.volatility_20d.mean = 0.125 = 12.50%
  assert.ok(html.includes("12.50%"), "Snapshot renders regime volatility metric");

  // Current Regime: REGIME_1 -> Regime 1
  assert.ok(html.includes("Regime 1"), "Snapshot renders formatted regime label");

  // Confidence: 0.884 -> 88.4%
  assert.ok(html.includes("88.4%"), "Snapshot renders model confidence percentage");
});

test("MarketSnapshot — handles missing / unavailable metrics gracefully without NaNs", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSnapshot, {
      marketData: null,
      regimeData: MOCK_UNKNOWN_REGIME_RESPONSE,
      currency: "USD",
      isLoading: false,
    })
  );

  assert.ok(!html.includes("NaN"), "Snapshot must never leak NaN");
  assert.ok(!html.includes("undefined"), "Snapshot must never leak undefined");
  assert.ok(html.includes("Unavailable"), "Confidence shows Unavailable when null");
  assert.ok(html.includes("—"), "Missing price renders em-dash placeholder");
});

test("MarketSnapshot — renders skeleton loading state", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSnapshot, {
      marketData: null,
      regimeData: null,
      isLoading: true,
    })
  );

  assert.ok(html.includes("ui-skeleton"), "Snapshot renders skeletons when isLoading=true");
});
