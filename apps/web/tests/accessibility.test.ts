import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { Button, Input, Select, Alert, EmptyState, ErrorState } from "../components/ui";
import { AppShell } from "../components/layout/AppShell";
import { ResearchCitationChip } from "../components/research/ResearchCitationChip";
import { ResearchEvidencePanel } from "../components/research/ResearchEvidencePanel";
import { ResearchComposer } from "../components/research/ResearchComposer";
import { TradeStatisticsSection } from "../components/backtesting/TradeStatisticsSection";
import { MOCK_MARKET_BACKTEST_RESPONSE } from "./fixtures/risk-and-backtesting.fixture";
import { MOCK_CITATION_REGIME, MOCK_EVIDENCE_PACKETS } from "./fixtures/ai-research.fixture";

test("Accessibility — AppShell structural landmarks and skip link", () => {
  const html = renderToStaticMarkup(
    React.createElement(AppShell, null, React.createElement("div", { id: "main-content" }, "Page Content"))
  );

  assert.ok(html.includes('href="#main-content"'), "Skip link targets main content");
  assert.ok(html.includes('id="main-content"'), "Main landmark has matching ID");
  assert.ok(html.includes("<header") || html.includes('role="banner"'), "Header landmark present");
  assert.ok(html.includes("<nav") || html.includes('role="navigation"') || html.includes("<aside"), "Navigation or sidebar landmark present");
  assert.ok(html.includes("<main"), "Main landmark element present");
});

test("Accessibility — Button states and busy attributes", () => {
  // Loading button should declare busy or disabled
  const loadingHtml = renderToStaticMarkup(
    React.createElement(Button, { isLoading: true }, "Executing")
  );
  assert.ok(loadingHtml.includes("disabled"), "Loading button is disabled to prevent re-submission");
  assert.ok(loadingHtml.includes('type="button"') || loadingHtml.includes("<button"), "Renders button element");

  // Disabled button
  const disabledHtml = renderToStaticMarkup(
    React.createElement(Button, { disabled: true }, "Disabled Action")
  );
  assert.ok(disabledHtml.includes("disabled"), "Disabled button has native disabled attribute");
});

test("Accessibility — Form inputs declare error descriptions and IDs", () => {
  const errorInputHtml = renderToStaticMarkup(
    React.createElement(Input, {
      id: "search-input",
      label: "Search Ticker",
      error: "Symbol not found in catalog",
    })
  );

  assert.ok(errorInputHtml.includes('for="search-input"') || errorInputHtml.includes('htmlFor="search-input"'), "Label references input ID");
  assert.ok(errorInputHtml.includes('aria-invalid="true"'), "Input declares aria-invalid when in error");
  assert.ok(errorInputHtml.includes("Symbol not found in catalog"), "Error message text is rendered");
});

test("Accessibility — Alert announces status via ARIA live region", () => {
  const alertHtml = renderToStaticMarkup(
    React.createElement(Alert, {
      variant: "danger",
      title: "Connection Lost",
    }, "Unable to reach market data service.")
  );

  assert.ok(alertHtml.includes('role="alert"') || alertHtml.includes('role="status"'), "Declares alert or status role");
  assert.ok(alertHtml.includes("Connection Lost"), "Alert title is rendered");
});

test("Accessibility — ResearchCitationChip provides descriptive button accessibility", () => {
  const chipHtml = renderToStaticMarkup(
    React.createElement(ResearchCitationChip, {
      id: 1,
      citation: MOCK_CITATION_REGIME,
      isSelected: false,
      onClick: () => {},
    })
  );

  assert.ok(chipHtml.includes("<button"), "Citation chip is a keyboard accessible button");
  assert.ok(chipHtml.includes("aria-label"), "Declares descriptive aria-label");
  assert.ok(chipHtml.includes("[1]"), "Contains bracketed citation identifier");
});

test("Accessibility — ResearchEvidencePanel declares complementary audit panel semantics", () => {
  const drawerHtml = renderToStaticMarkup(
    React.createElement(ResearchEvidencePanel, {
      evidence: MOCK_EVIDENCE_PACKETS,
      citations: [MOCK_CITATION_REGIME],
      isOpen: true,
      onClose: () => {},
      selectedCitationId: null,
      onSelectCitation: () => {},
    })
  );

  assert.ok(drawerHtml.includes('role="complementary"'), "Declares complementary role");
  assert.ok(drawerHtml.includes("aria-label"), "Declares accessible dialog labeling");
  assert.ok(drawerHtml.includes("Close") || drawerHtml.includes("Close audit trail"), "Includes accessible close button");
});

test("Accessibility — TradeStatisticsSection renders accessible definition cards", () => {
  const tradeStatsHtml = renderToStaticMarkup(
    React.createElement(TradeStatisticsSection, {
      trades: MOCK_MARKET_BACKTEST_RESPONSE.trades,
      executedTrades: MOCK_MARKET_BACKTEST_RESPONSE.executed_trades,
    })
  );

  assert.ok(tradeStatsHtml.includes("Trade Execution &amp; Win/Loss Statistics") || tradeStatsHtml.includes("Trade Statistics"), "Renders section title");
  assert.ok(tradeStatsHtml.includes("Win Rate") || tradeStatsHtml.includes("win rate"), "Renders Win Rate stat");
});
