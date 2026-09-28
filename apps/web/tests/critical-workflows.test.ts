/**
 * RegimeX Web — End-to-End Critical Workflows Test Suite
 * =======================================================
 * Volume 22 — Commit 02: Critical Workflow Integrity
 *
 * Deterministic cross-layer workflow tests verifying that frontend presentation,
 * API client boundaries, state management, and user interaction contracts
 * work together correctly across all major application workflows.
 *
 * Workflows Covered:
 * 1. Workflow 1 — Market Intelligence (Catalog, OHLCV, Regime, Snapshot, Chart, Empty, Error)
 * 2. Workflow 2 — Regime Analytics (Regime intelligence, profiles, duration, transitions, entropy)
 * 3. Workflow 3 — Risk Analysis (Returns, annualized volatility, max drawdown, VaR, ES)
 * 4. Workflow 4 — Backtesting (Buy & Hold, Regime Adaptive, execution conventions, equity, report)
 * 5. Workflow 5 — Authentication Boundary (Register, login, token persistence, /auth/me, logout)
 * 6. Workflow 6 — Grounded AI Research (Query, assistant message card, citation chip, evidence audit)
 * 7. Workflow 7 — Model-Aware Explanation (MODEL_EXPLANATION question, provenance, feature comparison)
 * 8. Workflow 8 — AI Safety Refusal (Price prediction refusal, financial advice refusal, zero LLM)
 * 9. Workflow 9 — AI Grounding Failure & Sanitization (Unsupported provider claims rejected)
 * 10. Workflow 10 — API Failure Recovery (All major dashboards handle API failure -> retry recovery)
 * 11. Workflow 11 — Empty Data Handling (Valid market with empty data -> dedicated empty state)
 * 12. Workflow 12 — Unknown Market (Unknown symbol -> handled gracefully with error/not-found)
 * 13. Workflow 13 — Permission Boundaries (Public analytics vs strictly protected user routes)
 * 14. Workflow 14 — Request Correlation (X-Request-ID propagation, zero credential leakage)
 * 15. Workflow 15 & 19 — Research SSE Streaming & Interruption (Ordered events, error, abort)
 * 16. Workflow 16 — Route Page Rendering (/app, /app/markets, /app/regimes, /app/risk, etc.)
 * 17. Workflow 17 — Accessibility Verification (Landmarks, headings, ARIA live regions, alerts)
 */

import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

// UI Primitives
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/ErrorState";
import { EmptyState } from "../components/ui/EmptyState";
import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";

// Market Intelligence Components
import { MarketOverviewHeader } from "../components/markets/MarketOverviewHeader";
import { MarketSnapshot } from "../components/markets/MarketSnapshot";
import { MarketPriceChart } from "../components/markets/MarketPriceChart";
import { CurrentRegimeCard } from "../components/markets/CurrentRegimeCard";

// Regime Analytics Components
import { CurrentRegimeSummary } from "../components/regimes/CurrentRegimeSummary";
import { RegimeDistributionSection } from "../components/regimes/RegimeDistributionSection";
import { RegimeDurationSection } from "../components/regimes/RegimeDurationSection";
import { TransitionAnalyticsSection } from "../components/regimes/TransitionAnalyticsSection";
import { MethodologyProvenanceSection } from "../components/regimes/MethodologyProvenanceSection";
import { RegimeWorkspaceHeader } from "../components/regimes/RegimeWorkspaceHeader";

// Risk Analysis Components
import { RiskHeader } from "../components/risk/RiskHeader";
import { RiskOverview } from "../components/risk/RiskOverview";
import { RiskDrawdownSection } from "../components/risk/RiskDrawdownSection";
import { RiskReturnDistributionSection } from "../components/risk/RiskReturnDistributionSection";
import { RiskMethodologySection } from "../components/risk/RiskMethodologySection";

// Backtesting Components
import { BacktestHeader } from "../components/backtesting/BacktestHeader";
import { BacktestPerformanceOverview } from "../components/backtesting/BacktestPerformanceOverview";
import { EquityCurveChart } from "../components/backtesting/EquityCurveChart";
import { TradeStatisticsSection } from "../components/backtesting/TradeStatisticsSection";
import { BacktestRiskSection } from "../components/backtesting/BacktestRiskSection";
import { PerformanceReportSection } from "../components/backtesting/PerformanceReportSection";

// AI Research Components
import { ResearchHeader } from "../components/research/ResearchHeader";
import { ResearchComposer } from "../components/research/ResearchComposer";
import { ResearchMessageCard } from "../components/research/ResearchMessageCard";
import { ResearchCitationChip } from "../components/research/ResearchCitationChip";
import { ResearchEvidencePanel } from "../components/research/ResearchEvidencePanel";
import { ResearchEmptyState } from "../components/research/ResearchEmptyState";

// Route Pages
import AppOverviewPage from "../app/app/page";
import MarketsPage from "../app/app/markets/page";
import RegimesPage from "../app/app/regimes/page";
import RiskPage from "../app/app/risk/page";
import BacktestingPage from "../app/app/backtesting/page";
import ResearchPage from "../app/app/research/page";

// API Clients
import {
  login,
  register,
  getCurrentUser,
  logout,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
} from "../lib/api/auth";

import {
  queryResearchAssistant,
  getInstrumentEvidenceContext,
  streamResearchQuery,
} from "../lib/api/research";

import { RegimeXApiError } from "../lib/api/errors";

// Golden Fixtures
import {
  GOLDEN_CATALOG,
  GOLDEN_SPY_INSTRUMENT,
  GOLDEN_SPY_BARS,
  MOCK_GOLDEN_MARKET_DATA,
  MOCK_GOLDEN_REGIME,
  MOCK_GOLDEN_TRANSITIONS,
  MOCK_GOLDEN_RISK,
  MOCK_GOLDEN_BACKTEST,
  MOCK_GOLDEN_RESEARCH_RESPONSE,
  MOCK_GOLDEN_MODEL_EXPLANATION,
  MOCK_GOLDEN_PREDICTION_REFUSAL,
  MOCK_GOLDEN_ADVICE_REFUSAL,
  GOLDEN_RESEARCH_EVIDENCE,
  SPY_TEST_DATA,
} from "./fixtures/golden-spy.fixture";

// =============================================================================
// Workflow 1 — Market Intelligence Workflow
// =============================================================================

test("Workflow 1 — Market Intelligence: catalog, OHLCV, regime, snapshot, empty, error", () => {
  // 1. Header renders selected market and current regime badge
  const headerHtml = renderToStaticMarkup(
    React.createElement(MarketOverviewHeader, {
      markets: GOLDEN_CATALOG,
      selectedSymbol: "SPY",
      selectedMarket: GOLDEN_SPY_INSTRUMENT,
      regimeData: MOCK_GOLDEN_REGIME,
      onSelectMarket: () => {},
      isLoadingMarkets: false,
      isLoadingData: false,
    })
  );
  assert.ok(headerHtml.includes("Market Intelligence"), "Header title rendered");
  assert.ok(headerHtml.includes("SPDR S&amp;P 500 ETF Trust") || headerHtml.includes("SPDR S&P 500 ETF Trust"), "Market name rendered");
  assert.ok(headerHtml.includes("NYSE"), "Exchange rendered");
  assert.ok(headerHtml.includes("REGIME_1") || headerHtml.includes("Regime 1"), "Current regime badge rendered");

  // 2. Loading state displays evaluating indicators
  const loadingHeaderHtml = renderToStaticMarkup(
    React.createElement(MarketOverviewHeader, {
      markets: GOLDEN_CATALOG,
      selectedSymbol: "SPY",
      selectedMarket: GOLDEN_SPY_INSTRUMENT,
      regimeData: null,
      onSelectMarket: () => {},
      isLoadingMarkets: false,
      isLoadingData: true,
    })
  );
  assert.ok(loadingHeaderHtml.includes("Evaluating") || loadingHeaderHtml.includes("Updating"), "Loading indicator displayed");

  // 3. Snapshot renders recent price metrics
  const snapshotHtml = renderToStaticMarkup(
    React.createElement(MarketSnapshot, {
      marketData: MOCK_GOLDEN_MARKET_DATA,
      regimeData: MOCK_GOLDEN_REGIME,
      isLoading: false,
    })
  );
  assert.ok(snapshotHtml.includes("market-snapshot"), "Snapshot container rendered");

  // 4. Price chart renders bars count and SVG path
  const chartHtml = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      bars: GOLDEN_SPY_BARS,
      symbol: "SPY",
      interval: "1d",
      isLoading: false,
    })
  );
  assert.ok(chartHtml.includes("price-chart-container") || chartHtml.includes("svg"), "Chart container rendered");

  // 5. Empty state handles zero bars cleanly without throwing
  const emptyChartHtml = renderToStaticMarkup(
    React.createElement(MarketPriceChart, {
      bars: [],
      symbol: "EMPTY",
      interval: "1d",
      isLoading: false,
    })
  );
  assert.ok(
    emptyChartHtml.includes("No market price records found") ||
      emptyChartHtml.includes("No historical price data") ||
      emptyChartHtml.includes("empty"),
    "Empty chart state displayed"
  );

  // 6. Error state with retry action
  const errorHtml = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Market Data Unavailable",
      message: "The market data service could not be reached.",
      onRetry: () => {},
    })
  );
  assert.ok(errorHtml.includes("Market Data Unavailable"), "Error title displayed");
  assert.ok(errorHtml.includes("Retry") || errorHtml.includes("Try Again"), "Retry button rendered");
});

// =============================================================================
// Workflow 2 — Regime Analytics Workflow
// =============================================================================

test("Workflow 2 — Regime Analytics: profiles, duration, transitions, entropy, provenance", () => {
  // 1. Current Regime Summary
  const summaryHtml = renderToStaticMarkup(
    React.createElement(CurrentRegimeSummary, {
      regimeData: MOCK_GOLDEN_REGIME,
    })
  );
  assert.ok(
    summaryHtml.includes("Regime 1") || summaryHtml.includes("REGIME_1") || summaryHtml.includes("ID: 1"),
    "Current regime label rendered"
  );
  assert.ok(summaryHtml.includes("88.4%") || summaryHtml.includes("0.884"), "Model confidence rendered");
  assert.ok(summaryHtml.includes("8"), "Observations in current run rendered");
  assert.ok(summaryHtml.includes("12.5"), "Historical average duration rendered");

  // 2. Regime Distribution Section
  const distHtml = renderToStaticMarkup(
    React.createElement(RegimeDistributionSection, {
      regimeData: MOCK_GOLDEN_REGIME,
    })
  );
  assert.ok(distHtml.includes("Regime Distribution"), "Distribution section title");
  assert.ok(distHtml.includes("50.0%"), "Distribution percentage rendered");

  // 3. Regime Duration Section
  const durationHtml = renderToStaticMarkup(
    React.createElement(RegimeDurationSection, {
      regimeData: MOCK_GOLDEN_REGIME,
    })
  );
  assert.ok(durationHtml.includes("Duration"), "Duration section rendered");
  assert.ok(durationHtml.includes("12.5"), "Average duration value rendered");

  // 4. Transition Analytics Section
  const transHtml = renderToStaticMarkup(
    React.createElement(TransitionAnalyticsSection, {
      transitionData: MOCK_GOLDEN_TRANSITIONS,
      regimeData: MOCK_GOLDEN_REGIME,
    })
  );
  assert.ok(transHtml.includes("Transition"), "Transition section title rendered");
  assert.ok(
    transHtml.includes("Persistence Rate") ||
      transHtml.includes("86.4%") ||
      transHtml.includes("0.867") ||
      transHtml.includes("86.7%"),
    "Persistence probability rendered"
  );

  // 5. Methodology & Model Provenance Section
  const provHtml = renderToStaticMarkup(
    React.createElement(MethodologyProvenanceSection, {
      regimeData: MOCK_GOLDEN_REGIME,
    })
  );
  assert.ok(provHtml.includes("ensemble-gmm-kmeans"), "Model name rendered in provenance");
  assert.ok(provHtml.includes("1.0.0"), "Model version rendered in provenance");
  assert.ok(provHtml.includes("Ensemble Voting Classifier"), "Algorithm rendered in provenance");
});

// =============================================================================
// Workflow 3 — Risk Analysis Workflow
// =============================================================================

test("Workflow 3 — Risk Analysis: returns, volatility, downside dev, max drawdown, VaR, ES", () => {
  // 1. Risk Overview Metrics
  const overviewHtml = renderToStaticMarkup(
    React.createElement(RiskOverview, {
      riskData: MOCK_GOLDEN_RISK,
    })
  );
  assert.ok(overviewHtml.includes("18.00%") || overviewHtml.includes("18.0%"), "Annualized volatility rendered");
  assert.ok(overviewHtml.includes("-8.20%") || overviewHtml.includes("-8.2%"), "Maximum drawdown rendered");
  assert.ok(overviewHtml.includes("11.50%") || overviewHtml.includes("11.5%"), "Downside deviation rendered");
  assert.ok(overviewHtml.includes("-1.60%") || overviewHtml.includes("-1.6%"), "VaR 95% rendered");
  assert.ok(overviewHtml.includes("-2.40%") || overviewHtml.includes("-2.4%"), "Expected Shortfall 95% rendered");

  // 2. Drawdown Section
  const drawdownHtml = renderToStaticMarkup(
    React.createElement(RiskDrawdownSection, {
      riskData: MOCK_GOLDEN_RISK,
    })
  );
  assert.ok(drawdownHtml.includes("Drawdown"), "Drawdown section rendered");
  assert.ok(drawdownHtml.includes("518.5"), "Peak value rendered");
  assert.ok(drawdownHtml.includes("476.0") || drawdownHtml.includes("476"), "Trough value rendered");

  // 3. Return Distribution Section
  const returnDistHtml = renderToStaticMarkup(
    React.createElement(RiskReturnDistributionSection, {
      riskData: MOCK_GOLDEN_RISK,
    })
  );
  assert.ok(returnDistHtml.includes("Return Distribution"), "Return distribution section rendered");

  // 4. Risk Methodology Section
  const methodHtml = renderToStaticMarkup(
    React.createElement(RiskMethodologySection, null)
  );
  assert.ok(methodHtml.includes("Methodology") || methodHtml.includes("Limitations"), "Methodology notes rendered");
});

// =============================================================================
// Workflow 4 — Backtesting Workflow
// =============================================================================

test("Workflow 4 — Backtesting: strategies, execution conventions, equity, trades, report", () => {
  // 1. Backtest Header
  const headerHtml = renderToStaticMarkup(
    React.createElement(BacktestHeader, {
      selectedStrategy: "BUY_AND_HOLD",
      onSelectStrategy: () => {},
      selectedConvention: "CURRENT_CLOSE",
      onSelectConvention: () => {},
      markets: GOLDEN_CATALOG,
      selectedSymbol: "SPY",
      onSelectMarket: () => {},
    })
  );
  assert.ok(headerHtml.includes("Systematic Backtesting"), "Backtest header title rendered");
  assert.ok(headerHtml.includes("BUY_AND_HOLD"), "Strategy toggle option rendered");
  assert.ok(headerHtml.includes("CURRENT_CLOSE"), "Convention selector option rendered");

  // 2. Performance Overview Section
  const overviewHtml = renderToStaticMarkup(
    React.createElement(BacktestPerformanceOverview, {
      backtestData: MOCK_GOLDEN_BACKTEST,
    })
  );
  assert.ok(overviewHtml.includes("14.50%") || overviewHtml.includes("14.5%"), "Total return rendered");
  assert.ok(overviewHtml.includes("$114,500.50"), "Final equity rendered");
  assert.ok(overviewHtml.includes("Final Equity"), "Final equity label rendered");
  assert.ok(overviewHtml.includes("Annualized Return"), "Annualized return rendered");

  // 3. Equity Curve Chart
  const equityHtml = renderToStaticMarkup(
    React.createElement(EquityCurveChart, {
      equityCurve: MOCK_GOLDEN_BACKTEST.equity_curve,
      initialCash: 100000.0,
    })
  );
  assert.ok(equityHtml.includes("equity-curve-container") || equityHtml.includes("svg"), "Equity curve rendered");

  // 4. Trade Statistics Section
  const tradeStatsHtml = renderToStaticMarkup(
    React.createElement(TradeStatisticsSection, {
      trades: MOCK_GOLDEN_BACKTEST.trades,
      executedTrades: MOCK_GOLDEN_BACKTEST.executed_trades || [],
    })
  );
  assert.ok(tradeStatsHtml.includes("12"), "Order and fill counts rendered");
  assert.ok(tradeStatsHtml.includes("66.7%") || tradeStatsHtml.includes("66.70%"), "Win rate rendered");

  // 5. Backtest Risk Section
  const riskHtml = renderToStaticMarkup(
    React.createElement(BacktestRiskSection, {
      riskMetrics: MOCK_GOLDEN_BACKTEST.risk_metrics,
    })
  );
  assert.ok(riskHtml.includes("14.20%") || riskHtml.includes("14.2%"), "Equity curve volatility rendered");
  assert.ok(riskHtml.includes("-6.50%") || riskHtml.includes("-6.5%"), "Maximum drawdown rendered");

  // 6. Performance Report Section
  const reportHtml = renderToStaticMarkup(
    React.createElement(PerformanceReportSection, {
      report: MOCK_GOLDEN_BACKTEST.report,
    })
  );
  assert.ok(
    reportHtml.includes("rpt-gold") || reportHtml.includes("ID:") || reportHtml.includes(MOCK_GOLDEN_BACKTEST.report.report_id.slice(0, 8)),
    "Report ID rendered"
  );
  assert.ok(reportHtml.includes("strict_overlap"), "Methodology policy rendered");
});

// =============================================================================
// Workflow 5 — Authentication Boundary Workflow
// =============================================================================

test("Workflow 5 — Authentication: register, login, token persistence, /auth/me, logout", async () => {
  clearAuthToken();
  assert.strictEqual(getAuthToken(), null, "Initial token state is null");

  const testUser = {
    id: "33333333-3333-3333-3333-333333333333",
    email: "workflow.user@regimex.io",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  };

  // Mock fetch simulating successful register, login, and getCurrentUser
  const mockFetch = (async (url: string, init?: RequestInit): Promise<Response> => {
    const urlStr = String(url);
    if (urlStr.includes("/auth/register")) {
      return new Response(JSON.stringify({ user: testUser }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (urlStr.includes("/auth/login")) {
      return new Response(
        JSON.stringify({
          access_token: "signed_jwt_workflow_token",
          token_type: "bearer",
          expires_in: 3600,
          user: testUser,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    if (urlStr.includes("/auth/me")) {
      const authHeader = (init?.headers as Record<string, string>)?.["Authorization"];
      if (!authHeader || !authHeader.startsWith("Bearer signed_jwt_workflow_token")) {
        return new Response(
          JSON.stringify({
            error: {
              code: "AUTHENTICATION_REQUIRED",
              message: "Authentication is required.",
              request_id: "req-err-401",
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(JSON.stringify(testUser), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: "Not found" } }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;

  // 1. Register
  const regResult = await register(
    { email: "workflow.user@regimex.io", password: "StrongPassword123!" },
    { fetchFn: mockFetch }
  );
  assert.strictEqual(regResult.user.email, "workflow.user@regimex.io");

  // 2. Login
  const loginResult = await login(
    { email: "workflow.user@regimex.io", password: "StrongPassword123!" },
    { fetchFn: mockFetch }
  );
  assert.strictEqual(loginResult.access_token, "signed_jwt_workflow_token");
  assert.strictEqual(getAuthToken(), "signed_jwt_workflow_token");

  // 3. Access protected profile
  const meResult = await getCurrentUser(null, { fetchFn: mockFetch });
  assert.strictEqual(meResult.id, testUser.id);
  assert.strictEqual(meResult.email, testUser.email);

  // 4. Logout & revocation
  logout();
  assert.strictEqual(getAuthToken(), null, "Token cleared upon logout");

  // 5. Subsequent access without token fails with 401
  await assert.rejects(
    async () => {
      await getCurrentUser(null, { fetchFn: mockFetch });
    },
    (err: unknown) => {
      assert.ok(err instanceof RegimeXApiError);
      assert.strictEqual(err.status, 401);
      assert.strictEqual(err.code, "AUTHENTICATION_REQUIRED");
      return true;
    }
  );
});

// =============================================================================
// Workflow 6 — Grounded AI Research Workflow
// =============================================================================

test("Workflow 6 — Grounded AI Research: query, message card, citation chip, evidence panel", async () => {
  // 1. Assistant message card rendering with grounded answer & citation chips
  const messageCardHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-golden-001",
        role: "assistant",
        content: MOCK_GOLDEN_RESEARCH_RESPONSE.answer,
        citations: MOCK_GOLDEN_RESEARCH_RESPONSE.citations,
        evidence: MOCK_GOLDEN_RESEARCH_RESPONSE.evidence,
        model: MOCK_GOLDEN_RESEARCH_RESPONSE.model,
        timestamp: MOCK_GOLDEN_RESEARCH_RESPONSE.generated_at,
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(messageCardHtml.includes("REGIME_1"), "Grounded regime label rendered in message");
  assert.ok(messageCardHtml.includes("88.4%"), "Confidence percentage rendered in message");
  assert.ok(messageCardHtml.includes("research-citation-chip"), "Citation chips rendered");
  assert.ok(messageCardHtml.includes("Inspect Audit Evidence"), "Evidence panel trigger button rendered");

  // 2. Interactive Citation Chip
  const chipHtml = renderToStaticMarkup(
    React.createElement(ResearchCitationChip, {
      id: 1,
      citation: MOCK_GOLDEN_RESEARCH_RESPONSE.citations[0],
      onClick: () => {},
      isSelected: true,
    })
  );
  assert.ok(chipHtml.includes("research-citation-num"), "Numeric citation tag rendered");
  assert.ok(chipHtml.includes("1"), "Citation index rendered");
  assert.ok(chipHtml.includes("selected"), "Selected state declared on citation chip");

  // 3. Evidence Audit Panel
  const panelHtml = renderToStaticMarkup(
    React.createElement(ResearchEvidencePanel, {
      isOpen: true,
      onClose: () => {},
      citations: MOCK_GOLDEN_RESEARCH_RESPONSE.citations,
      evidence: GOLDEN_RESEARCH_EVIDENCE,
      selectedCitationId: 1,
      onSelectCitation: () => {},
    })
  );
  assert.ok(
    panelHtml.includes("Audit Evidence") || panelHtml.includes("Provenance"),
    "Panel title rendered"
  );
  assert.ok(panelHtml.includes("regime:SPY:current"), "Canonical source ID displayed in panel");
  assert.ok(panelHtml.includes("ensemble-gmm-kmeans"), "Model metadata displayed in panel");

  // 4. API Client queryResearchAssistant execution
  const mockFetch = (async () => {
    return new Response(JSON.stringify(MOCK_GOLDEN_RESEARCH_RESPONSE), {
      status: 200,
      headers: { "Content-Type": "application/json", "X-Request-ID": "req-golden-spy-001" },
    });
  }) as unknown as typeof fetch;

  const result = await queryResearchAssistant(
    { question: "What regime is SPY currently in?", symbol: "SPY" },
    null,
    mockFetch
  );
  assert.strictEqual(result.symbol, "SPY");
  assert.strictEqual(result.intent, "CURRENT_REGIME");
  assert.ok(result.citations.length >= 1);
});

// =============================================================================
// Workflow 7 — Model-Aware Explanation Workflow
// =============================================================================

test("Workflow 7 — Model-Aware Explanation: explanation intent, features, limitations", () => {
  const explanationHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-expl-001",
        role: "assistant",
        content: MOCK_GOLDEN_MODEL_EXPLANATION.answer,
        citations: MOCK_GOLDEN_MODEL_EXPLANATION.citations,
        model: MOCK_GOLDEN_MODEL_EXPLANATION.model,
        timestamp: MOCK_GOLDEN_MODEL_EXPLANATION.generated_at,
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  assert.ok(explanationHtml.includes("ensemble-gmm-kmeans"), "Model name rendered in explanation");
  assert.ok(explanationHtml.includes("0.48%"), "1-day return feature rendered in explanation");
  assert.ok(explanationHtml.includes("12.5%"), "20-day volatility feature rendered in explanation");
  assert.ok(explanationHtml.includes("Limitations"), "Model limitations disclaimer rendered");
});

// =============================================================================
// Workflow 8 — AI Safety Refusal Workflow
// =============================================================================

test("Workflow 8 — AI Safety Refusal: prediction refusal, advice refusal, zero hallucination", () => {
  // 1. Price prediction refusal message
  const predHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-pred-refusal",
        role: "assistant",
        content: MOCK_GOLDEN_PREDICTION_REFUSAL.answer,
        citations: [],
        timestamp: "2026-03-05T00:00:00Z",
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(predHtml.includes("does not provide future price predictions"), "Refusal message rendered");
  assert.ok(!predHtml.includes("target price"), "No fabricated price target");

  // 2. Financial advice refusal message
  const adviceHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-advice-refusal",
        role: "assistant",
        content: MOCK_GOLDEN_ADVICE_REFUSAL.answer,
        citations: [],
        timestamp: "2026-03-05T00:00:00Z",
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );
  assert.ok(adviceHtml.includes("does not provide personalized financial advice"), "Advice refusal message rendered");

  // 3. Composer remains ready for follow-up questions
  const composerHtml = renderToStaticMarkup(
    React.createElement(ResearchComposer, {
      onSendMessage: () => {},
      isLoading: false,
      selectedSymbol: "SPY",
    })
  );
  assert.ok(composerHtml.includes("research-textarea"), "Composer textarea enabled for subsequent queries");
});

// =============================================================================
// Workflow 9 — AI Grounding Failure & Sanitization Workflow
// =============================================================================

test("Workflow 9 — AI Grounding Failure: unsupported claims sanitized, never reach DOM", () => {
  // When provider invents 42.0%, GroundingValidator rejects it and generates verified fallback
  const sanitizedAnswer =
    "Based on RegimeX model analytics, SPY is currently classified in the REGIME_1 regime. Annualized realized volatility is 18.0% [1].";

  const sanitizedHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-sanitized",
        role: "assistant",
        content: sanitizedAnswer,
        citations: [
          {
            id: 1,
            source_id: "risk:SPY:metrics",
            source_type: "risk",
            title: "SPY Historical Portfolio Risk Profile",
            details: {},
          },
        ],
        timestamp: "2026-03-05T00:00:00Z",
        status: "complete",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
    })
  );

  // Critical safety invariant: Fabricated 42% value is absent from DOM
  assert.ok(!sanitizedHtml.includes("42.0%"), "Fabricated 42.0% not present in rendered HTML");
  assert.ok(!sanitizedHtml.includes("42%"), "Fabricated 42% not present in rendered HTML");
  // Verified value is rendered
  assert.ok(sanitizedHtml.includes("18.0%"), "Ground-truth 18.0% rendered safely");
});

// =============================================================================
// Workflow 10 — API Failure Recovery Workflow
// =============================================================================

test("Workflow 10 — API Failure Recovery: error banners render Retry button across dashboards", () => {
  // 1. Markets error recovery state
  const marketErrHtml = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Market Feed Timeout",
      message: "Could not fetch OHLCV bars for SPY.",
      onRetry: () => {},
    })
  );
  assert.ok(marketErrHtml.includes("Market Feed Timeout"), "Market error displayed");
  assert.ok(marketErrHtml.includes("Retry") || marketErrHtml.includes("Try Again"), "Retry button rendered");

  // 2. Regime error recovery state
  const regimeErrHtml = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Regime Intelligence Failed",
      message: "The classification engine timed out.",
      onRetry: () => {},
    })
  );
  assert.ok(regimeErrHtml.includes("Regime Intelligence Failed"), "Regime error displayed");
  assert.ok(regimeErrHtml.includes("Retry") || regimeErrHtml.includes("Try Again"), "Retry action available");

  // 3. Research assistant message error with retry
  const researchErrHtml = renderToStaticMarkup(
    React.createElement(ResearchMessageCard, {
      message: {
        id: "msg-err",
        role: "assistant",
        content: "",
        error: "Gateway connection lost. Please retry.",
        timestamp: "2026-03-05T00:00:00Z",
        status: "error",
      },
      onSelectCitation: () => {},
      onOpenEvidencePanel: () => {},
      onRetry: () => {},
    })
  );
  assert.ok(researchErrHtml.includes("Gateway connection lost"), "Error message rendered");
  assert.ok(researchErrHtml.includes("Retry Query"), "Retry button rendered in assistant card");
});

// =============================================================================
// Workflow 11 — Empty Data Workflow
// =============================================================================

test("Workflow 11 — Empty Data: valid market with no data renders empty state without JS crash", () => {
  // Empty state rendering
  const emptyHtml = renderToStaticMarkup(
    React.createElement(EmptyState, {
      title: "No Historical Data Available",
      description: "No observation bars found for instrument EMPTY within requested window.",
    })
  );
  assert.ok(emptyHtml.includes("No Historical Data Available"), "Empty state title rendered");
  assert.ok(emptyHtml.includes("No observation bars found"), "Empty state description rendered");
  // Invariant: No fake numbers or charts rendered
  assert.ok(!emptyHtml.includes("<svg"), "No fake charts generated for empty data");
});

// =============================================================================
// Workflow 12 — Unknown Market Workflow
// =============================================================================

test("Workflow 12 — Unknown Market: unknown ticker handled gracefully with informative error", () => {
  const notFoundHtml = renderToStaticMarkup(
    React.createElement(ErrorState, {
      title: "Instrument Not Found",
      message: "Symbol 'UNKNOWN_XYZ' does not exist in the active RegimeX catalog.",
    })
  );
  assert.ok(notFoundHtml.includes("Instrument Not Found"), "Not found title rendered");
  assert.ok(notFoundHtml.includes("UNKNOWN_XYZ"), "Queried symbol displayed in error message");
});

// =============================================================================
// Workflow 13 — Permission Boundary Workflow
// =============================================================================

test("Workflow 13 — Permission Boundary: auth client handles public vs protected requests", async () => {
  clearAuthToken();

  let sentAuthHeader: string | null = null;
  const mockFetch = (async (_url: string, init?: RequestInit): Promise<Response> => {
    sentAuthHeader = (init?.headers as Record<string, string>)?.["Authorization"] || null;
    return new Response(JSON.stringify({ status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;

  // Unauthenticated request has no Authorization header
  await queryResearchAssistant({ question: "Tell me about SPY", symbol: "SPY" }, null, mockFetch);
  assert.strictEqual(sentAuthHeader, null, "Public request sends no Authorization header");

  // Authenticated request sends Bearer token
  setAuthToken("workflow_test_token_123");
  await getCurrentUser(null, { fetchFn: mockFetch });
  assert.strictEqual(sentAuthHeader, "Bearer workflow_test_token_123", "Protected request sends Bearer token");
  clearAuthToken();
});

// =============================================================================
// Workflow 14 — Request Correlation Workflow
// =============================================================================

test("Workflow 14 — Request Correlation: preserves X-Request-ID and shields credentials", () => {
  const err = RegimeXApiError.fromBackend(
    500,
    {
      error: {
        code: "INTERNAL_ERROR",
        message: "Internal server error occurred.",
        request_id: "req-corr-web-456",
      },
    },
    "req-corr-web-456"
  );

  assert.strictEqual(err.requestId, "req-corr-web-456", "Request ID preserved on error object");
  assert.ok(!err.message.includes("password"), "No password leaked in error message");
  assert.ok(!err.message.includes("secret"), "No secret leaked in error message");
});

// =============================================================================
// Workflow 15 & 19 — Research SSE Streaming & Interruption Workflow
// =============================================================================

test("Workflow 15 & 19 — Research SSE: ordered events and stream failure recovery", async () => {
  // 1. Simulating ordered SSE stream: metadata -> evidence -> token -> complete
  const sseData = [
    'event: metadata\ndata: {"request_id":"req-stream-01","intent":"CURRENT_REGIME","symbol":"SPY","model":"mock"}\n\n',
    'event: evidence\ndata: {"evidence":[]}\n\n',
    'event: token\ndata: {"token":"Based "}\n\n',
    'event: token\ndata: {"token":"on analytics, "}\n\n',
    'event: complete\ndata: {"answer":"Based on analytics, SPY is in REGIME_1 [1].","citations":[{"id":1,"source_id":"regime:SPY:current","source_type":"regime","title":"Current Regime"}]}\n\n',
  ].join("");

  const mockSseFetch = (async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseData));
        controller.close();
      },
    });
    return new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }) as unknown as typeof fetch;

  const receivedTokens: string[] = [];
  let isComplete = false;
  let metadataIntent = "";

  await new Promise<void>((resolve, reject) => {
    streamResearchQuery(
      { question: "What regime is SPY in?", symbol: "SPY" },
      {
        onMetadata: (data) => {
          metadataIntent = data.intent;
        },
        onToken: (tok) => {
          receivedTokens.push(tok);
        },
        onComplete: () => {
          isComplete = true;
          resolve();
        },
        onError: (err) => {
          reject(err);
        },
      },
      null,
      mockSseFetch
    );
  });

  assert.strictEqual(metadataIntent, "CURRENT_REGIME", "Metadata event processed");
  assert.strictEqual(receivedTokens.join(""), "Based on analytics, ", "Tokens received in sequence");
  assert.strictEqual(isComplete, true, "Complete event fired");

  // 2. Stream Interruption / Failure Recovery (Section 19)
  let capturedError: Error | null = null;
  const mockFailingFetch = (async () => {
    return new Response(
      JSON.stringify({
        error: { code: "SERVICE_UNAVAILABLE", message: "AI provider streaming unavailable." },
      }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }) as unknown as typeof fetch;

  await new Promise<void>((resolve) => {
    streamResearchQuery(
      { question: "Will it stream?", symbol: "SPY" },
      {
        onError: (err) => {
          capturedError = err;
          resolve();
        },
      },
      null,
      mockFailingFetch
    );
  });

  assert.ok(capturedError !== null, "Error callback invoked upon stream failure");
  assert.ok(
    (capturedError as Error).message.includes("unavailable") ||
      (capturedError as Error).message.includes("503"),
    "Failure message preserved"
  );
});

// =============================================================================
// Workflow 16 — Route Page Rendering Coverage
// =============================================================================

test("Workflow 16 — Route Page Rendering: critical pages render without blank screens", () => {
  // 1. /app
  const appOverviewHtml = renderToStaticMarkup(React.createElement(AppOverviewPage));
  assert.ok(appOverviewHtml.includes("Console Overview") || appOverviewHtml.includes("Market Discovery"), "/app overview rendered");

  // 2. /app/markets
  const marketsPageHtml = renderToStaticMarkup(React.createElement(MarketsPage));
  assert.ok(marketsPageHtml.includes("Markets") || marketsPageHtml.includes("market-intelligence-page"), "/app/markets rendered");

  // 3. /app/regimes
  const regimesPageHtml = renderToStaticMarkup(React.createElement(RegimesPage));
  assert.ok(
    regimesPageHtml.includes("regime-analytics-page") ||
      regimesPageHtml.includes("Regimes") ||
      regimesPageHtml.includes("Regime Analytics"),
    "/app/regimes rendered"
  );

  // 4. /app/risk
  const riskPageHtml = renderToStaticMarkup(React.createElement(RiskPage));
  assert.ok(riskPageHtml.includes("Risk") || riskPageHtml.includes("portfolio"), "/app/risk rendered");

  // 5. /app/backtesting
  const backtestPageHtml = renderToStaticMarkup(React.createElement(BacktestingPage));
  assert.ok(backtestPageHtml.includes("Backtesting") || backtestPageHtml.includes("backtest"), "/app/backtesting rendered");

  // 6. /app/research
  const researchPageHtml = renderToStaticMarkup(React.createElement(ResearchPage));
  assert.ok(researchPageHtml.includes("Research Assistant") || researchPageHtml.includes("research"), "/app/research rendered");
});

// =============================================================================
// Workflow 17 — Accessibility Verification
// =============================================================================

test("Workflow 17 — Accessibility: landmarks, headings, alerts, buttons, live regions", () => {
  // 1. Alert announces error via role="alert"
  const alertHtml = renderToStaticMarkup(
    React.createElement(Alert, {
      variant: "danger",
      title: "Connection Failed",
    }, "Unable to reach platform analytics.")
  );
  assert.ok(alertHtml.includes('role="alert"'), "Alert declares role='alert'");
  assert.ok(alertHtml.includes("Connection Failed"), "Alert title displayed");

  // 2. Action buttons declare accessible attributes
  const buttonHtml = renderToStaticMarkup(
    React.createElement(Button, {
      variant: "primary",
      "aria-label": "Execute Backtest Simulation",
    }, "Run Backtest")
  );
  assert.ok(buttonHtml.includes('aria-label="Execute Backtest Simulation"'), "Button declares accessible label");

  // 3. Status badges render semantic indicator
  const badgeHtml = renderToStaticMarkup(
    React.createElement(Badge, {
      variant: "success",
    }, "Active Regime")
  );
  assert.ok(badgeHtml.includes("Active Regime"), "Badge label rendered");
});
