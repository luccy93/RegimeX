/**
 * RegimeX Shared Contracts — Public API
 * ========================================
 * This module exports all shared type contracts between the backend API
 * and the frontend web application.
 *
 * V04: Minimal foundation types only.
 * Domain-specific types will be added in their respective volumes.
 *
 * Import in Next.js:
 *   import type { ApiEnvelope, ApiError } from "@regimex/contracts";
 *
 * Note: The canonical implementation of these types lives in the
 * backend (Pydantic schemas). TypeScript types here must remain in sync.
 */

// =============================================================================
// Standard API Response Envelope
// Mirrors: apps/api/app/core/ response utilities
// =============================================================================

/** Standard RegimeX API success/error envelope. */
export interface ApiEnvelope<T = unknown> {
  /** True if the request succeeded; false if an error occurred. */
  success: boolean;
  /** The response payload (null on error). */
  data: T | null;
  /** Response metadata always present. */
  meta: ApiMeta;
  /** Error details (null on success). */
  error: ApiError | null;
}

/** Metadata present in every RegimeX API response. */
export interface ApiMeta {
  /** Unique identifier for this request (trace correlation). */
  request_id: string;
  /** ISO 8601 UTC timestamp of the response. */
  timestamp: string;
  /** Optional pagination cursor for paginated responses (V05+). */
  next_cursor?: string | null;
  /** Optional total count for paginated responses (V05+). */
  total?: number | null;
}

/** Standard error payload. */
export interface ApiError {
  /** Machine-readable error code (e.g., "NOT_FOUND", "VALIDATION_ERROR"). */
  code: string;
  /** Human-readable error description. */
  message: string;
  /** Additional structured details (validation errors, context). */
  details: Record<string, unknown>;
}

// =============================================================================
// Health Check Types
// Mirrors: apps/api/app/api/v1/endpoints/health.py
// =============================================================================

export interface LivenessData {
  status: "ok";
  timestamp: string;
  service: string;
  version: string;
}

export interface ReadinessData {
  status: "ready" | "degraded" | "unavailable";
  timestamp: string;
  checks: Record<string, "ok" | "degraded" | "unavailable" | string>;
}

// =============================================================================
// Future Shared Types (added in their designated volumes)
// =============================================================================

// V05 — Market Discovery & Data
// export type AssetClass = "equity" | "fixed_income" | "commodity" | "fx" | "crypto";
// export interface InstrumentId extends String { readonly _brand: "InstrumentId" }

// V08 — Regime Detection
// export type RegimeLabel = string; // Regime labels are model-defined, not fixed enums

// V09 — Regime Intelligence
// export interface TransitionMatrix { ... }

// V10 — Risk Analytics
// export type RiskMetricType = "var" | "cvar" | "max_drawdown" | "volatility";

// V15 — Identity
// export interface UserRole { ... }
