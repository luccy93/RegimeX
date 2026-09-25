/**
 * RegimeX Web — Typed API Contracts
 * ===================================
 * Frontend TypeScript interfaces corresponding strictly to existing
 * FastAPI v1 response and request models defined in apps/api/app/api/v1/models.py
 *
 * Strictly adheres to backend presentation DTOs without inventing
 * frontend-only fake representations.
 */

// =============================================================================
// Standard Error Envelope
// =============================================================================

export interface ApiErrorDetail {
  code: string;
  message: string;
  request_id: string;
  details?: unknown;
}

export interface ApiError {
  error: ApiErrorDetail;
}

// =============================================================================
// Platform Root & Diagnostic Models
// =============================================================================

export interface RootResponse {
  name: string;
  version: string;
  api_version: string;
  status: string;
}

export interface HealthResponse {
  status: string;
}

export interface ReadinessResponse {
  status: string;
  checks: Record<string, string>;
  timestamp?: string | null;
}

// =============================================================================
// Market Intelligence Models (V16 Commit 01 & 02)
// =============================================================================

export interface MarketItemResponse {
  symbol: string;
  asset_class: string;
  exchange: string;
  currency: string;
  description: string;
}

export interface MarketListResponse {
  items: MarketItemResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface OHLCVBarResponse {
  timestamp: string; // ISO 8601 UTC
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketDataResponse {
  symbol: string;
  interval: string;
  start: string; // ISO 8601 UTC
  end: string;   // ISO 8601 UTC
  count: number;
  total: number;
  items: OHLCVBarResponse[];
}

export interface FeatureStatisticDTO {
  feature_name: string;
  observation_count: number;
  mean: number | null;
  median: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
}

export interface RegimeProfileDTO {
  regime_id: number;
  regime_label: string;
  observation_count: number;
  frequency: number;
  percentage: number;
  first_seen: string | null;
  last_seen: string | null;
  run_count: number;
  average_duration: number;
  median_duration: number;
  min_duration: number;
  max_duration: number;
  feature_statistics: Record<string, FeatureStatisticDTO>;
}

export interface CurrentRegimeContextDTO {
  current_regime_id: number;
  current_regime_label: string;
  current_timestamp: string;
  observations_in_current_run: number;
  historical_frequency: number;
  historical_average_duration: number;
  historical_max_duration: number;
  historical_min_duration: number;
  historical_run_count: number;
  current_features: Record<string, number | null> | null;
}

export interface MarketRegimeResponse {
  symbol: string;
  current_regime: number;
  current_regime_label: string;
  confidence: number | null;
  current_context: CurrentRegimeContextDTO;
  profile: RegimeProfileDTO | null;
  profiles: Record<number, RegimeProfileDTO>;
  statistics: Record<string, FeatureStatisticDTO>;
  regimes_observed: number[];
  total_observations: number;
  model_name: string | null;
  model_version: string | null;
  algorithm: string | null;
  analysis_start: string | null;
  analysis_end: string | null;
}

// =============================================================================
// Transition Analytics Models (V16 Commit 02)
// =============================================================================

export interface RankedDestinationDTO {
  target_regime: number;
  target_label: string;
  probability: number;
  count: number;
  rank: number;
}

export interface TransitionRegimeAnalyticsDTO {
  regime_id: number;
  regime_label: string;
  outgoing_transition_count: number;
  incoming_transition_count: number;
  self_transition_count: number;
  regime_change_count: number;
  persistence_probability: number;
  change_rate: number;
  most_likely_destination: number | null;
  most_likely_destination_probability: number;
  destination_count: number;
  source_count: number;
  transition_entropy: number;
  rankings: RankedDestinationDTO[];
}

export interface GlobalTransitionAnalyticsDTO {
  total_observations: number;
  total_consecutive_transitions: number;
  total_regime_changes: number;
  total_self_transitions: number;
  global_change_rate: number;
  global_persistence_rate: number;
  number_of_regimes: number;
  number_of_observed_transition_edges: number;
}

export interface TransitionProbabilityDTO {
  source_regime: number;
  target_regime: number;
  count: number;
  total_transitions_from_source: number;
  probability: number;
}

export interface MarketTransitionResponse {
  symbol: string;
  regimes: number[];
  probability_matrix: number[][];
  count_matrix: number[][];
  regime_change_counts: number[][];
  regime_change_probabilities: number[][];
  regime_analytics: Record<number, TransitionRegimeAnalyticsDTO>;
  global_analytics: GlobalTransitionAnalyticsDTO;
  probabilities: TransitionProbabilityDTO[];
}

// =============================================================================
// Authentication Models (V17 Commit 01)
// =============================================================================

export interface UserResponse {
  id: string; // UUID
  email: string;
  is_active: boolean;
  created_at: string;
}

export type UserDTO = UserResponse;

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  user: UserResponse;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}
