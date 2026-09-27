/**
 * RegimeX Web — API Client Module Entrypoint
 * ===========================================
 * Re-exports typed API contracts, error handlers, and client methods.
 */

export * from "./types";
export * from "./errors";
export * from "./client";
export * from "./markets";
export * from "./auth";
export * from "./health";
export * from "./regimes";
export {
  getMarketRisk,
  formatDecimal as formatRiskDecimal,
  type GetRiskParams,
} from "./risk";
export {
  getMarketBacktest,
  formatCurrency as formatBacktestCurrency,
  type GetBacktestParams,
} from "./backtesting";
export {
  queryResearchAssistant,
  getInstrumentEvidenceContext,
  streamResearchQuery,
  type StreamEventCallbacks,
} from "./research";

