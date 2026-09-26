/**
 * RegimeX Web — Systematic Backtesting API Client & Validation Layer
 * ==================================================================
 * Typed API methods and defensive validation helpers for V14 event-driven
 * backtesting simulations and V15 strategy performance reports.
 */

import { apiFetch, type RequestOptions } from "./client";
import type { MarketBacktestResponse } from "./types";

export interface GetBacktestParams {
  strategy?: "BUY_AND_HOLD" | "REGIME_ADAPTIVE" | string;
  start?: string;
  end?: string;
  interval?: string;
  limit?: number;
  initial_cash?: number;
  commission_rate?: number;
  slippage_rate?: number;
  execution_convention?: "CURRENT_CLOSE" | "NEXT_OPEN" | string;
  periods_per_year?: number;
}

/**
 * Execute systematic event-driven backtest simulation.
 */
export async function getMarketBacktest(
  symbol: string,
  params: GetBacktestParams = {},
  options?: RequestOptions
): Promise<MarketBacktestResponse> {
  const cleanSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  const query = new URLSearchParams();
  if (params.strategy) query.set("strategy", params.strategy);
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  if (params.interval) query.set("interval", params.interval);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.initial_cash !== undefined) query.set("initial_cash", String(params.initial_cash));
  if (params.commission_rate !== undefined) query.set("commission_rate", String(params.commission_rate));
  if (params.slippage_rate !== undefined) query.set("slippage_rate", String(params.slippage_rate));
  if (params.execution_convention) query.set("execution_convention", params.execution_convention);
  if (params.periods_per_year !== undefined) query.set("periods_per_year", String(params.periods_per_year));

  const qs = query.toString();
  const path = qs ? `/markets/${cleanSymbol}/backtest?${qs}` : `/markets/${cleanSymbol}/backtest`;

  return apiFetch<MarketBacktestResponse>(path, options);
}

/**
 * Checks if a value is a valid, finite number.
 */
export function isValidFiniteNumber(val: unknown): val is number {
  return typeof val === "number" && Number.isFinite(val) && !Number.isNaN(val);
}

/**
 * Safely format currency amounts in USD.
 */
export function formatCurrency(val: unknown, decimals: number = 2): string {
  if (!isValidFiniteNumber(val)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
}

/**
 * Safely format return or percentage values.
 */
export function formatPercentage(val: unknown, decimals: number = 2): string {
  if (!isValidFiniteNumber(val)) return "—";
  return `${(val * 100).toFixed(decimals)}%`;
}
