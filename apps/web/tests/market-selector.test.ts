import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarketSelector } from "../components/markets/MarketSelector";
import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";

test("MarketSelector — renders available markets and active selection", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSelector, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
    })
  );

  assert.ok(html.includes("SPY"), "Selector trigger displays selected symbol SPY");
  assert.ok(
    html.includes("SPDR S&amp;P 500 ETF Trust") || html.includes("SPDR S&P 500 ETF Trust"),
    "Selector trigger displays market description"
  );
  assert.ok(html.includes("EQUITY US"), "Selector trigger displays asset class badge");
  assert.ok(html.includes('aria-haspopup="listbox"'), "Trigger has proper accessibility aria-haspopup");
});

test("MarketSelector — loading state", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSelector, {
      markets: [],
      selectedSymbol: "",
      onSelectMarket: () => {},
      isLoading: true,
    })
  );

  assert.ok(html.includes("disabled"), "Trigger is disabled during initial load");
  assert.ok(html.includes("ui-spinner"), "Trigger shows loading spinner");
});

test("MarketSelector — empty catalog fallback", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSelector, {
      markets: [],
      selectedSymbol: "",
      onSelectMarket: () => {},
      isLoading: false,
    })
  );

  assert.ok(html.includes("Select Market"), "Trigger renders placeholder when no market selected");
});

test("MarketSelector — error display", () => {
  const html = renderToStaticMarkup(
    React.createElement(MarketSelector, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
      error: "Failed to connect to market gateway",
    })
  );

  // Even with an error, the trigger renders the selected market if available
  assert.ok(html.includes("SPY"));
});
