/**
 * RegimeX Web — Market Intelligence API Client
 * =============================================
 * Typed methods for querying market discovery, OHLCV time-series,
 * market regime detection, and empirical transition analytics.
 */

import { apiFetch, type RequestOptions } from "./client";
import type {
  MarketDataResponse,
  MarketListResponse,
  MarketRegimeResponse,
  MarketTransitionResponse,
} from "./types";

export interface ListMarketsParams {
  asset_class?: string;
  limit?: number;
  offset?: number;
}

export interface GetMarketDataParams {
  start: string; // ISO 8601 UTC
  end: string;   // ISO 8601 UTC
  interval?: string;
  limit?: number;
  offset?: number;
}

export interface GetRegimeParams {
  start?: string; // ISO 8601 UTC
  end?: string;   // ISO 8601 UTC
  interval?: string;
  limit?: number;
}

/**
 * List discoverable market instruments.
 */
export async function listMarkets(
  params: ListMarketsParams = {},
  options?: RequestOptions
): Promise<MarketListResponse> {
  const query = new URLSearchParams();
  if (params.asset_class) query.set("asset_class", params.asset_class);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  const path = qs ? `/markets?${qs}` : "/markets";
  return apiFetch<MarketListResponse>(path, options);
}

/**
 * Retrieve historical OHLCV data bars.
 */
export async function getMarketData(
  symbol: string,
  params: GetMarketDataParams,
  options?: RequestOptions
): Promise<MarketDataResponse> {
  const cleanSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  const query = new URLSearchParams();
  query.set("start", params.start);
  query.set("end", params.end);
  if (params.interval) query.set("interval", params.interval);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  return apiFetch<MarketDataResponse>(
    `/markets/${cleanSymbol}/data?${query.toString()}`,
    options
  );
}

/**
 * Retrieve current market regime context and historical regime profiles.
 */
export async function getMarketRegime(
  symbol: string,
  params: GetRegimeParams = {},
  options?: RequestOptions
): Promise<MarketRegimeResponse> {
  const cleanSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  const query = new URLSearchParams();
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  if (params.interval) query.set("interval", params.interval);
  if (params.limit !== undefined) query.set("limit", String(params.limit));

  const qs = query.toString();
  const path = qs
    ? `/markets/${cleanSymbol}/regime?${qs}`
    : `/markets/${cleanSymbol}/regime`;

  return apiFetch<MarketRegimeResponse>(path, options);
}

/**
 * Retrieve regime transition analytics and persistence metrics.
 */
export async function getRegimeTransitions(
  symbol: string,
  params: GetRegimeParams = {},
  options?: RequestOptions
): Promise<MarketTransitionResponse> {
  const cleanSymbol = encodeURIComponent(symbol.trim().toUpperCase());
  const query = new URLSearchParams();
  if (params.start) query.set("start", params.start);
  if (params.end) query.set("end", params.end);
  if (params.interval) query.set("interval", params.interval);
  if (params.limit !== undefined) query.set("limit", String(params.limit));

  const qs = query.toString();
  const path = qs
    ? `/markets/${cleanSymbol}/regime/transitions?${qs}`
    : `/markets/${cleanSymbol}/regime/transitions`;

  return apiFetch<MarketTransitionResponse>(path, options);
}
