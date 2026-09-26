import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarketPriceChart } from "../components/markets/MarketPriceChart";
import { MOCK_BARS_SERIES } from "./fixtures/market-data.fixture";

test("MarketPriceChart — renders price line, HUD, and SVG coordinates", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      symbol: "SPY",
      bars: MOCK_BARS_SERIES,
      currency: "USD",
      interval: "1d",
      isLoading: false,
    })
  );

  assert.ok(html.includes("SPY — Historical Price Action"), "Chart title renders symbol");
  assert.ok(html.includes("market-chart-svg"), "Renders SVG canvas");
  assert.ok(html.includes("<path"), "Renders SVG price paths");
  assert.ok(html.includes("linearGradient"), "Renders area fill gradient");
  assert.ok(html.includes("$513.50"), "HUD displays latest close price");
  assert.ok(html.includes("Historical OHLCV for SPY"), "Renders accessible fallback table");
});

test("MarketPriceChart — renders empty state when no bars returned", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      symbol: "EMPTY",
      bars: [],
      isLoading: false,
    })
  );

  assert.ok(
    html.includes("No market price records found for EMPTY"),
    "ChartSlot displays empty label when no bars"
  );
});

test("MarketPriceChart — renders loading state", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      symbol: "SPY",
      bars: [],
      isLoading: true,
    })
  );

  assert.ok(html.includes("chart-slot-body-loading"), "ChartSlot applies loading class");
  assert.ok(html.includes("Loading chart data…"), "Displays chart loading text");
});

test("MarketPriceChart — renders error state with correlation ID and retry", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      symbol: "SPY",
      bars: [],
      error: "Gateway connection refused",
      requestId: "req-chart-789",
      onRetry: () => {},
    })
  );

  assert.ok(html.includes("Market Data Unavailable (SPY)"), "Displays error title");
  assert.ok(html.includes("Gateway connection refused"), "Displays error description");
  assert.ok(html.includes("req-chart-789"), "Displays request correlation ID");
  assert.ok(html.includes("Retry Market Data"), "Displays retry button");
});
