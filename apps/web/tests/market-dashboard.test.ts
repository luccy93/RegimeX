import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarketOverviewHeader } from "../components/markets/MarketOverviewHeader";
import MarketsPage from "../app/app/markets/page";
import {
  MOCK_MARKET_ITEMS,
  MOCK_KNOWN_REGIME_RESPONSE,
} from "./fixtures/market-data.fixture";

test("MarketsPage — server component renders breadcrumbs and dashboard container", () => {
  const html = renderToStaticMarkup(React.createElement(MarketsPage));

  assert.ok(html.includes("market-intelligence-page"), "Renders page root container");
  assert.ok(html.includes("Console"), "Renders Console breadcrumb");
  assert.ok(html.includes("Markets"), "Renders Markets breadcrumb");
});

test("MarketOverviewHeader — renders market details, regime badge, and selector", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketOverviewHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      selectedMarket: MOCK_MARKET_ITEMS[0],
      regimeData: MOCK_KNOWN_REGIME_RESPONSE,
      onSelectMarket: () => {},
      isLoadingMarkets: false,
      isLoadingData: false,
    })
  );

  assert.ok(html.includes("Market Intelligence"), "Renders header title");
  assert.ok(
    html.includes("SPDR S&amp;P 500 ETF Trust") || html.includes("SPDR S&P 500 ETF Trust"),
    "Renders market name"
  );
  assert.ok(html.includes("NYSE"), "Renders exchange badge");
  assert.ok(html.includes("EQUITY_US"), "Renders asset class badge");
  assert.ok(html.includes("Regime 1"), "Renders current regime status badge");
  assert.ok(html.includes("Data Available"), "Renders data available indicator");
});

test("MarketOverviewHeader — loading state displays evaluating indicator", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketOverviewHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      selectedMarket: MOCK_MARKET_ITEMS[0],
      regimeData: null,
      onSelectMarket: () => {},
      isLoadingMarkets: false,
      isLoadingData: true,
    })
  );

  assert.ok(html.includes("Evaluating…"), "Displays Evaluating regime text");
  assert.ok(html.includes("Updating"), "Displays Updating feed text");
});
