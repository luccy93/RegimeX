import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { EmptyState, ErrorState, Skeleton, Spinner, Card } from "../components/ui";
import { MarketSelector } from "../components/markets/MarketSelector";
import { ResearchEmptyState } from "../components/research/ResearchEmptyState";
import { ResearchMessageCard } from "../components/research/ResearchMessageCard";
import { ResearchHeader } from "../components/research/ResearchHeader";
import { RiskOverview } from "../components/risk/RiskOverview";
import { TradeStatisticsSection } from "../components/backtesting/TradeStatisticsSection";
import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";
import { MOCK_MARKET_BACKTEST_RESPONSE, MOCK_MARKET_RISK_RESPONSE } from "./fixtures/risk-and-backtesting.fixture";
import { MOCK_RESEARCH_RESPONSE_BULLISH } from "./fixtures/ai-research.fixture";

test("Component States — EmptyState rendering and action", () => {
  const html = renderToStaticMarkup(
    React.createElement(EmptyState, {
      title: "No Data Available",
      description: "Historical data could not be found for the queried symbol.",
      action: React.createElement("button", { type: "button" }, "Try Again"),
    })
  );

  assert.ok(html.includes("No Data Available"), "Renders title");
  assert.ok(html.includes("Historical data could not be found"), "Renders description");
  assert.ok(html.includes("Try Again"), "Renders action button");
  assert.ok(html.includes("ui-empty-state"), "Has ui-empty-state CSS class");
});

test("Component States — ErrorState rendering, details, and retry", () => {
  const html = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Failed to load risk analytics",
      message: "The risk calculation service timed out after 5.0 seconds.",
      onRetry: () => {},
      retryLabel: "Retry Calculation",
    })
  );

  assert.ok(html.includes("Failed to load risk analytics"), "Renders title");
  assert.ok(html.includes("timed out"), "Renders error message");
  assert.ok(html.includes("Retry Calculation"), "Renders retry button");
  assert.ok(html.includes("ui-error-state"), "Has ui-error-state CSS class");
});

test("Component States — MarketSelector rendering available markets", () => {
  const populatedHtml = renderToStaticMarkup(
    React.createElement(MarketSelector, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
    })
  );
  assert.ok(populatedHtml.includes("SPY"), "Includes SPY option");
  assert.ok(populatedHtml.includes("SPDR S&amp;P 500 ETF Trust") || populatedHtml.includes("SPDR S&P 500 ETF Trust"), "Includes market description");
});

test("Component States — ResearchMessageCard all states (loading, error, content)", () => {
  // Loading state
  const loadingHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-1",
        role: "assistant",
        content: "",
        status: "loading",
        timestamp: "2026-09-28T00:00:00Z",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(loadingHtml.includes("research-loading-state") || loadingHtml.includes("Spinner") || loadingHtml.includes("Retrieving verified"), "Renders loading state");

  // Error state
  const errorHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-2",
        role: "assistant",
        content: "Original question",
        error: "AI Provider connection refused",
        status: "error",
        timestamp: "2026-09-28T00:00:00Z",
      },
      onRetry: () => {},
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(errorHtml.includes("AI Provider connection refused"), "Displays error text");
  assert.ok(errorHtml.includes("Retry Query"), "Offers retry action");

  // Complete grounded state with citations
  const contentHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-3",
        role: "assistant",
        content: MOCK_RESEARCH_RESPONSE_BULLISH.answer,
        citations: MOCK_RESEARCH_RESPONSE_BULLISH.citations,
        intent: MOCK_RESEARCH_RESPONSE_BULLISH.intent,
        status: "complete",
        timestamp: "2026-09-28T00:00:00Z",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(contentHtml.includes("BULLISH") || contentHtml.includes("regime") || contentHtml.includes("Bullish"), "Contains regime content");
  assert.ok(contentHtml.includes("research-citation-chip") || contentHtml.includes("citation-badge") || contentHtml.includes("Grounded Citations"), "Renders interactive citation chips");
});

test("Component States — RiskOverview handling null and extreme values without throwing", () => {
  const safeHtml = renderToStaticMarkup(
    React.createElement(RiskOverview, {
      riskData: MOCK_MARKET_RISK_RESPONSE,
    })
  );
  assert.ok(safeHtml.includes("risk-overview-section"), "Renders overview component without crashing");
  assert.ok(safeHtml.includes("Risk Profile Overview"), "Renders section title");
});

test("Component States — TradeStatisticsSection rendering stats", () => {
  const tradeStatsHtml = renderToStaticMarkup(
    React.createElement(TradeStatisticsSection, {
      trades: MOCK_MARKET_BACKTEST_RESPONSE.trades,
      executedTrades: MOCK_MARKET_BACKTEST_RESPONSE.executed_trades,
    })
  );

  assert.ok(tradeStatsHtml.includes("Trade Execution") || tradeStatsHtml.includes("Trade Statistics"), "Renders section title");
  assert.ok(tradeStatsHtml.includes("Win Rate"), "Renders Win Rate stat");
});

