/**
 * RegimeX Web — Regime Analytics API Client & Validation Layer
 * ==============================================================
 * Dedicated, typed API methods and defensive validation helpers for
 * regime profiles, duration analytics, empirical transition matrices,
 * and transition entropy.
 */

import { getMarketRegime, getRegimeTransitions, type GetRegimeParams } from "./markets";
import type {
  MarketRegimeResponse,
  MarketTransitionResponse,
} from "./types";
import type { RequestOptions } from "./client";

export type { GetRegimeParams };

/**
 * Retrieve market regime context, observation counts, and feature profiles.
 */
export async function getRegimeAnalytics(
  symbol: string,
  params: GetRegimeParams = {},
  options?: RequestOptions
): Promise<MarketRegimeResponse> {
  return getMarketRegime(symbol, params, options);
}

/**
 * Retrieve empirical regime transition matrix and persistence metrics.
 */
export async function fetchRegimeTransitions(
  symbol: string,
  params: GetRegimeParams = {},
  options?: RequestOptions
): Promise<MarketTransitionResponse> {
  return getRegimeTransitions(symbol, params, options);
}

// =============================================================================
// Defensive Data Validation Helpers (Section 38: Frontend Data Integrity)
// =============================================================================

/**
 * Checks if a value is a valid, finite number.
 */
export function isValidFiniteNumber(val: unknown): val is number {
  return typeof val === "number" && Number.isFinite(val) && !Number.isNaN(val);
}

/**
 * Checks if a numeric value is a valid probability in [0, 1].
 */
export function isValidProbability(val: unknown): val is number {
  return isValidFiniteNumber(val) && val >= -1e-6 && val <= 1.000001;
}

/**
 * Validates the dimensions and contents of a transition probability matrix.
 * Returns true if the matrix is an N x N array where N equals regimes.length.
 */
export function isValidTransitionMatrix(
  matrix: unknown,
  expectedSize: number
): matrix is number[][] {
  if (!Array.isArray(matrix)) return false;
  if (matrix.length !== expectedSize) return false;

  for (let i = 0; i < matrix.length; i++) {
    const row = matrix[i];
    if (!Array.isArray(row) || row.length !== expectedSize) return false;
    for (let j = 0; j < row.length; j++) {
      if (!isValidFiniteNumber(row[j])) return false;
    }
  }

  return true;
}

/**
 * Computes observed regime distribution percentages strictly from counts.
 * Prevents division by zero and preserves mathematical integrity without assumptions.
 */
export function computeRegimeDistributionPercentages(
  profiles: Record<number | string, { observation_count: number }>,
  totalObservations: number
): Record<string, number> {
  const result: Record<string, number> = {};
  if (totalObservations <= 0) return result;

  for (const [key, p] of Object.entries(profiles)) {
    if (isValidFiniteNumber(p.observation_count) && p.observation_count >= 0) {
      result[key] = (p.observation_count / totalObservations) * 100;
    } else {
      result[key] = 0;
    }
  }

  return result;
}
