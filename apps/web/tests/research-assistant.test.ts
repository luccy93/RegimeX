/**
 * RegimeX Web — AI Quantitative Research Assistant Tests
 * =======================================================
 * Volume 21 — Commit 01
 * Verifies ResearchHeader, ResearchMarketContextStrip, ResearchCitationChip,
 * ResearchEvidencePanel, ResearchEmptyState, ResearchMessageCard,
 * ResearchComposer, API client methods, and accessibility semantics.
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ResearchHeader } from "../components/research/ResearchHeader";
import { ResearchMarketContextStrip } from "../components/research/ResearchMarketContextStrip";
import { ResearchCitationChip } from "../components/research/ResearchCitationChip";
import { ResearchEvidencePanel } from "../components/research/ResearchEvidencePanel";
import { ResearchEmptyState } from "../components/research/ResearchEmptyState";
import { ResearchMessageCard } from "../components/research/ResearchMessageCard";
import { ResearchComposer } from "../components/research/ResearchComposer";

import {
  queryResearchAssistant,
  getInstrumentEvidenceContext,
} from "../lib/api/research";

import {
  MOCK_CITATION_REGIME,
  MOCK_CITATION_RISK,
  MOCK_EVIDENCE_PACKETS,
  MOCK_RESEARCH_RESPONSE_BULLISH,
  MOCK_RESEARCH_RESPONSE_EXPLANATION,
  MOCK_CURRENT_REGIME_CONTEXT,
} from "./fixtures/ai-research.fixture";

import { MOCK_MARKET_ITEMS } from "./fixtures/market-data.fixture";

// =============================================================================
// 1. ResearchHeader Tests
// =============================================================================

test("ResearchHeader — renders title, mode badges, market selector, and clear button", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectSymbol: () => {},
      onClearConversation: () => {},
      messageCount: 3,
      isLoading: false,
    })
  );

  assert.ok(html.includes("AI Research Assistant"), "Title rendered");
  assert.ok(html.includes("Grounded Analytics"), "Grounded badge rendered");
  assert.ok(html.includes("Deterministic Evidence"), "Evidence badge rendered");
  assert.ok(html.includes("SPY"), "Selected symbol in dropdown");
  assert.ok(html.includes("Clear Chat"), "Clear button rendered when messages > 0");
});

test("ResearchHeader — hides clear button when conversation is empty", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchHeader, {
      markets: MOCK_MARKET_ITEMS,
      selectedSymbol: "SPY",
      onSelectSymbol: () => {},
      onClearConversation: () => {},
      messageCount: 0,
      isLoading: false,
    })
  );

  assert.ok(!html.includes("Clear Chat"), "Clear button hidden when messageCount is 0");
});

// =============================================================================
// 2. ResearchMarketContextStrip Tests
// =============================================================================

test("ResearchMarketContextStrip — renders active market, regime badge, confidence, and duration", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMarketContextStrip, {
      selectedSymbol: "SPY",
      marketItem: MOCK_MARKET_ITEMS[0],
      regimeContext: MOCK_CURRENT_REGIME_CONTEXT,
      confidence: 0.884,
      isLoadingRegime: false,
    })
  );

  assert.ok(html.includes("SPY"), "Market symbol rendered");
  assert.ok(html.includes("BULLISH"), "Regime label rendered");
  assert.ok(html.includes("88.4%"), "Confidence formatted");
  assert.ok(html.includes("42 obs"), "Run duration rendered");
  assert.ok(html.includes("Grounding Context Attached"), "Attached context badge");
});

test("ResearchMarketContextStrip — renders global scope fallback when symbol is empty", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMarketContextStrip, {
      selectedSymbol: "",
      isLoadingRegime: false,
    })
  );

  assert.ok(html.includes("Active Scope:"), "Active scope label rendered");
  assert.ok(html.includes("Global Platform Intelligence"), "Global scope fallback");
});

test("ResearchMarketContextStrip — handles evaluating regime loading state", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMarketContextStrip, {
      selectedSymbol: "SPY",
      isLoadingRegime: true,
    })
  );

  assert.ok(html.includes("Evaluating..."), "Evaluating status indicator rendered");
});

// =============================================================================
// 3. ResearchCitationChip Tests
// =============================================================================

test("ResearchCitationChip — renders interactive badge with bracket formatting and accessibility", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchCitationChip, {
      id: 1,
      citation: MOCK_CITATION_REGIME,
      onClick: () => {},
      isSelected: false,
    })
  );

  assert.ok(html.includes("["), "Opening bracket rendered");
  assert.ok(html.includes("1"), "Citation ID rendered");
  assert.ok(html.includes("]"), "Closing bracket rendered");
  assert.ok(html.includes("Regime Intelligence — SPY"), "Accessible title in tooltip");
  assert.ok(!html.includes("selected"), "Not marked selected");
});

test("ResearchCitationChip — applies selected class when highlighted", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchCitationChip, {
      id: 1,
      citation: MOCK_CITATION_REGIME,
      onClick: () => {},
      isSelected: true,
    })
  );

  assert.ok(html.includes("selected"), "Selected class applied");
  assert.ok(html.includes('aria-pressed="true"'), "Aria-pressed true");
});

// =============================================================================
// 4. ResearchEvidencePanel Tests
// =============================================================================

test("ResearchEvidencePanel — returns null when closed", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchEvidencePanel, {
      isOpen: false,
      onClose: () => {},
      citations: [MOCK_CITATION_REGIME],
      evidence: MOCK_EVIDENCE_PACKETS,
      selectedCitationId: null,
      onSelectCitation: () => {},
    })
  );

  assert.strictEqual(html, "", "Renders nothing when isOpen is false");
});

test("ResearchEvidencePanel — renders audit cards with source_id, model, and verified facts when open", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchEvidencePanel, {
      isOpen: true,
      onClose: () => {},
      citations: [MOCK_CITATION_REGIME, MOCK_CITATION_RISK],
      evidence: MOCK_EVIDENCE_PACKETS,
      selectedCitationId: 1,
      onSelectCitation: () => {},
    })
  );

  assert.ok(html.includes("Audit Evidence &amp; Provenance"), "Header title rendered");
  assert.ok(html.includes("2 Packets"), "Packet count badge rendered");
  assert.ok(html.includes("Regime Intelligence — SPY"), "Citation title rendered");
  assert.ok(html.includes("source_id: regime:SPY:current"), "Canonical source_id rendered");
  assert.ok(html.includes("HMM / GMM Ensemble"), "Model engine provenance rendered");
  assert.ok(html.includes("current regime label:"), "Facts table key rendered");
  assert.ok(html.includes("highlighted"), "Selected citation card highlighted");
});

// =============================================================================
// 5. ResearchEmptyState Tests
// =============================================================================

test("ResearchEmptyState — renders introductory hero, disclaimer, and 5 question categories", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchEmptyState, {
      onSelectPrompt: () => {},
      selectedSymbol: "SPY",
    })
  );

  assert.ok(html.includes("Quantitative Research Assistant"), "Hero heading rendered");
  assert.ok(html.includes("Institutional Scope:"), "Disclaimer badge rendered");
  assert.ok(
    html.includes("does not provide future price predictions"),
    "Non-predictive disclaimer rendered"
  );
  assert.ok(html.includes("Regime Intelligence"), "Category 1 rendered");
  assert.ok(html.includes("Markov Transitions"), "Category 2 rendered");
  assert.ok(html.includes("Portfolio Risk"), "Category 3 rendered");
  assert.ok(html.includes("Backtesting &amp; Assumptions"), "Category 4 rendered");
  assert.ok(html.includes("Model Explanation"), "Category 5 rendered");
  assert.ok(html.includes("What regime is SPY currently in?"), "Question formatted with symbol");
  assert.ok(html.includes("Why is SPY classified in this regime?"), "Explanation prompt formatted with symbol");
});

// =============================================================================
// 6. ResearchMessageCard Tests
// =============================================================================

test("ResearchMessageCard — renders user question with distinct bubble and time", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "u-1",
        role: "user",
        content: "What is the drawdown of SPY?",
        timestamp: "2026-09-26T20:00:00Z",
        symbol: "SPY",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  assert.ok(html.includes("user-row"), "User row class rendered");
  assert.ok(html.includes("Research Query"), "User label rendered");
  assert.ok(html.includes("What is the drawdown of SPY?"), "Content rendered");
});

test("ResearchMessageCard — renders assistant grounded answer with inline citations and sources footer", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "a-1",
        role: "assistant",
        content: MOCK_RESEARCH_RESPONSE_BULLISH.answer,
        citations: MOCK_RESEARCH_RESPONSE_BULLISH.citations,
        evidence: MOCK_RESEARCH_RESPONSE_BULLISH.evidence,
        model: MOCK_RESEARCH_RESPONSE_BULLISH.model,
        intent: MOCK_RESEARCH_RESPONSE_BULLISH.intent,
        timestamp: "2026-09-26T20:00:05Z",
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  assert.ok(html.includes("RegimeX Assistant"), "Assistant title rendered");
  assert.ok(html.includes("deterministic-grounded-v1"), "Model name badge rendered");
  assert.ok(html.includes("CURRENT_REGIME"), "Intent badge rendered");
  assert.ok(html.includes("BULLISH"), "Markdown bold formatted text");
  assert.ok(html.includes("research-citation-chip"), "Interactive citation chip rendered");
  assert.ok(html.includes("Grounded Citations"), "Citations footer rendered");
  assert.ok(html.includes("Inspect Audit Evidence →"), "Evidence button rendered");
  assert.ok(html.includes("Non-predictive"), "Financial disclaimer note rendered");
});

test("ResearchMessageCard — renders assistant grounded answer for MODEL_EXPLANATION intent", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "a-explain-1",
        role: "assistant",
        content: MOCK_RESEARCH_RESPONSE_EXPLANATION.answer,
        citations: MOCK_RESEARCH_RESPONSE_EXPLANATION.citations,
        evidence: MOCK_RESEARCH_RESPONSE_EXPLANATION.evidence,
        model: MOCK_RESEARCH_RESPONSE_EXPLANATION.model,
        intent: MOCK_RESEARCH_RESPONSE_EXPLANATION.intent,
        timestamp: "2026-09-26T20:00:05Z",
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  assert.ok(html.includes("RegimeX Assistant"), "Assistant title rendered");
  assert.ok(html.includes("MODEL_EXPLANATION"), "Intent badge rendered");
  assert.ok(html.includes("HMM / GMM Ensemble"), "Model engine provenance rendered in text");
  assert.ok(html.includes("research-citation-chip"), "Interactive citation chip rendered");
  assert.ok(html.includes("Inspect Audit Evidence →"), "Evidence button rendered");
});

test("ResearchMessageCard — renders loading state with spinner", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "a-loading",
        role: "assistant",
        content: "",
        timestamp: "2026-09-26T20:00:00Z",
        status: "loading",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  assert.ok(html.includes("research-loading-state"), "Loading container rendered");
  assert.ok(html.includes("Retrieving verified platform intelligence"), "Loading message rendered");
});

test("ResearchMessageCard — renders error state with retry button", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "a-error",
        role: "assistant",
        content: "",
        error: "AI provider timeout.",
        timestamp: "2026-09-26T20:00:00Z",
        status: "error",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
      onRetry: () => {},
    })
  );

  assert.ok(html.includes("AI provider timeout."), "Error message displayed");
  assert.ok(html.includes("Retry Query"), "Retry button rendered");
});

// =============================================================================
// 7. ResearchComposer Tests
// =============================================================================

test("ResearchComposer — renders textarea, char counter, suggestion chips, and submit button", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchComposer, {
      onSendMessage: () => {},
      isLoading: false,
      selectedSymbol: "SPY",
    })
  );

  assert.ok(html.includes("research-textarea"), "Textarea rendered");
  assert.ok(html.includes("0/1000"), "Char counter rendered");
  assert.ok(html.includes("What regime is SPY in?"), "Suggestion chip formatted with SPY");
  assert.ok(html.includes("Inquire →"), "Submit button label rendered");
});

test("ResearchComposer — renders Stop button when loading", () => {
  const html = renderToStaticMarkup(
    React.createElement(ResearchComposer, {
      onSendMessage: () => {},
      onCancelGeneration: () => {},
      isLoading: true,
      selectedSymbol: "SPY",
    })
  );

  assert.ok(html.includes("■ Stop"), "Stop button rendered when isLoading is true");
});

// =============================================================================
// 8. API Client Method Tests
// =============================================================================

test("API Client — queryResearchAssistant executes POST /api/v1/research/query", async () => {
  let capturedUrl = "";
  let capturedOptions: RequestInit | undefined;

  const mockFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    capturedUrl = String(input);
    capturedOptions = init;
    return new Response(JSON.stringify(MOCK_RESEARCH_RESPONSE_BULLISH), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Request-ID": "req-123" },
    });
  };

  const response = await queryResearchAssistant(
    { question: "What regime is SPY in?", symbol: "SPY" },
    null,
    mockFetch as unknown as typeof fetch
  );

  assert.ok(capturedUrl.includes("/api/v1/research/query"), "Correct endpoint called");
  assert.strictEqual(capturedOptions?.method, "POST", "Used POST method");
  assert.strictEqual(response.symbol, "SPY");
  assert.strictEqual(response.citations.length, 1);
  assert.strictEqual(response.citations[0].source_id, "regime:SPY:current");
});

test("API Client — getInstrumentEvidenceContext executes GET /api/v1/research/context/SPY", async () => {
  let capturedUrl = "";

  const mockFetch = async (input: RequestInfo | URL): Promise<Response> => {
    capturedUrl = String(input);
    return new Response(JSON.stringify(MOCK_EVIDENCE_PACKETS), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const packets = await getInstrumentEvidenceContext(
    "SPY",
    null,
    mockFetch as unknown as typeof fetch
  );

  assert.ok(capturedUrl.includes("/api/v1/research/context/SPY"), "Correct context path called");
  assert.strictEqual(packets.length, 2);
  assert.strictEqual(packets[0].source_type, "regime");
});
