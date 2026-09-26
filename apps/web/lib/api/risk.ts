/**
 * RegimeX Web — Portfolio Risk API Client & Validation Layer
 * ==========================================================
 * Typed API methods and defensive validation helpers for V13 portfolio risk
 * analytics (return statistics, volatility, downside risk, drawdowns, VaR,
 * and Expected Shortfall).
 */

import { apiFetch, type RequestOptions } from "./client";
import type { MarketRiskResponse } from "./types";

export interface GetRiskParams {
  start?: string;
  end?: string;
  interval?: string;
  limit?: number;
  periods_per_year?: number;
  target_return?: number;
}

/**
 * Retrieve portfolio risk intelligence for an instrument.
 */
export async function getMarketRisk(
  symbol: string,
  params: GetRiskParams = {},
  options?: RequestOptions
): Promise<MarketRiskResponse> {
  const cleanSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  const query = new URLSearchParams();
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  if (params.interval) query.set("interval", params.interval);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.periods_per_year !== undefined) query.set("periods_per_year", String(params.periods_per_year));
  if (params.target_return !== undefined) query.set("target_return", String(params.target_return));

  const qs = query.toString();
  const path = qs ? `/markets/${cleanSymbol}/risk?${qs}` : `/markets/${cleanSymbol}/risk`;

  return apiFetch<MarketRiskResponse>(path, options);
}

/**
 * Checks if a value is a valid, finite number.
 */
export function isValidFiniteNumber(val: unknown): val is number {
  return typeof val === "number" && Number.isFinite(val) && !Number.isNaN(val);
}

/**
 * Safely format a percentage value.
 */
export function formatPercentage(val: unknown, decimals: number = 2): string {
  if (!isValidFiniteNumber(val)) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}

/**
 * Safely format a basis points or decimal value.
 */
export function formatDecimal(val: unknown, decimals: number = 4): string {
  if (!isValidFiniteNumber(val)) return "—";
  return val.toFixed(decimals);
}
