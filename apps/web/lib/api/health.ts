/**
 * RegimeX Web — Health & Observability API Client
 * ===============================================
 * Typed methods for querying system liveness, readiness, data health,
 * model health, upstream providers, and pipeline stages.
 */

import { apiFetch, type RequestOptions } from "./client";
import type {
  DataHealthListResponseDTO,
  DataHealthResponseDTO,
  HealthResponse,
  ModelHealthListResponseDTO,
  ModelHealthResponseDTO,
  PipelineHealthDTO,
  ProviderHealthListResponseDTO,
  ReadinessResponse,
  RootResponse,
  SystemHealthSummaryResponseDTO,
} from "./types";

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

  /** Get high-level system operational health summary. */
  getSummary: (options?: RequestOptions) =>
    apiFetch<SystemHealthSummaryResponseDTO>("/api/v1/health/summary", options),

  /** List data health snapshots for all monitored instruments. */
  listDataHealth: (options?: RequestOptions) =>
    apiFetch<DataHealthListResponseDTO>("/api/v1/health/data", options),

  /** Get data health snapshot for a specific symbol. */
  getDataHealth: (symbol: string, options?: RequestOptions) =>
    apiFetch<DataHealthResponseDTO>(`/api/v1/health/data/${encodeURIComponent(symbol)}`, options),

  /** List health snapshots for all regime detection models. */
  listModelHealth: (options?: RequestOptions) =>
    apiFetch<ModelHealthListResponseDTO>("/api/v1/health/models", options),

  /** Get health snapshot for a specific regime model. */
  getModelHealth: (modelId: string, options?: RequestOptions) =>
    apiFetch<ModelHealthResponseDTO>(`/api/v1/health/models/${encodeURIComponent(modelId)}`, options),

  /** List upstream market data provider health snapshots. */
  listProviders: (options?: RequestOptions) =>
    apiFetch<ProviderHealthListResponseDTO>("/api/v1/health/providers", options),

  /** Get data pipeline health across all stages. */
  getPipeline: (options?: RequestOptions) =>
    apiFetch<PipelineHealthDTO>("/api/v1/health/pipeline", options),
};
