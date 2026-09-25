/**
 * RegimeX Web — Health & Diagnostic Probes API Client
 * ====================================================
 * Typed methods for querying system liveness and readiness.
 */

import { apiFetch, type RequestOptions } from "./client";
import type { HealthResponse, ReadinessResponse, RootResponse } from "./types";

export const healthApi = {
  /** Check API root metadata. */
  getRoot: (options?: RequestOptions) =>
    apiFetch<RootResponse>("/", options),

  /** Check API liveness probe. */
  liveness: (options?: RequestOptions) =>
    apiFetch<HealthResponse>("/health", options),

  /** Check API operational readiness probe. */
  readiness: (options?: RequestOptions) =>
    apiFetch<ReadinessResponse>("/ready", options),
};
