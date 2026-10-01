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

// =============================================================================
// Portfolio Risk Analytics Models (V13 / V20)
// =============================================================================

export interface ReturnStatisticsDTO {
  mean_return: number;
  median_return: number;
  standard_deviation: number;
  minimum_return: number;
  maximum_return: number;
  observation_count: number;
}

export interface VolatilityMetricsDTO {
  period_volatility: number;
  annualized_volatility: number;
  periods_per_year: number;
}

export interface DownsideRiskMetricsDTO {
  downside_deviation: number;
  semi_variance: number;
  target_return: number;
  observation_count: number;
  downside_observation_count: number;
}

export interface DrawdownMetricsDTO {
  max_drawdown: number;
  drawdown_magnitude: number;
  peak_value: number;
  trough_value: number;
  peak_timestamp: string;
  trough_timestamp: string;
  recovery_timestamp: string | null;
  is_recovered: boolean;
}

export interface VaRMetricsDTO {
  confidence_level: number;
  var_loss: number;
  return_quantile: number;
  method: string;
  tail_observations: number;
  total_observations: number;
}

export interface ExpectedShortfallMetricsDTO {
  confidence_level: number;
  expected_shortfall: number;
  tail_mean_return: number;
  var_loss: number;
  tail_observations: number;
  total_observations: number;
}

export interface RiskPricePointDTO {
  timestamp: string;
  price: number;
  period_return: number | null;
  running_peak: number;
  drawdown: number;
}

export interface MarketRiskResponse {
  symbol: string;
  series_id: string;
  observation_count: number;
  start_timestamp: string;
  end_timestamp: string;
  computed_at: string;
  return_statistics: ReturnStatisticsDTO;
  volatility: VolatilityMetricsDTO;
  downside_risk: DownsideRiskMetricsDTO;
  drawdown: DrawdownMetricsDTO;
  var_metrics: Record<string, VaRMetricsDTO>;
  expected_shortfall_metrics: Record<string, ExpectedShortfallMetricsDTO>;
  price_points: RiskPricePointDTO[];
}

// =============================================================================
// Systematic Backtesting Models (V14 / V15 / V20)
// =============================================================================

export interface EquitySnapshotDTO {
  timestamp: string;
  cash: number;
  market_value: number;
  equity: number;
  fees: number;
  realized_pnl: number;
  unrealized_pnl: number;
  drawdown: number;
}

export interface TradeStatisticsDTO {
  order_count: number;
  fill_count: number;
  completed_trade_count: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_realized_pnl: number;
  average_trade_pnl: number;
  largest_winning_trade: number;
  largest_losing_trade: number;
}

export interface BacktestTradeDTO {
  timestamp: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  commission: number;
  slippage: number;
}

export interface BacktestRiskMetricsDTO {
  volatility: number;
  annualized_volatility: number;
  maximum_drawdown: number;
  drawdown_magnitude: number;
  var_95: number;
  expected_shortfall_95: number;
}

export interface MethodologyDTO {
  common_period_policy: string;
  trade_definition: string;
  risk_engine_source: string;
  return_type: string;
  execution_engine_source: string;
}

export interface MetricDefinitionDTO {
  metric_name: string;
  description: string;
  unit: string;
  direction_semantics: string;
  source: string;
}

export interface PerformanceReportDTO {
  report_id: string;
  report_version: string;
  generated_at: string;
  methodology: MethodologyDTO;
  limitations: string[];
  metric_definitions: MetricDefinitionDTO[];
}

export interface MarketBacktestResponse {
  symbol: string;
  strategy_id: string;
  strategy_name: string;
  execution_convention: "CURRENT_CLOSE" | "NEXT_OPEN" | string;
  initial_cash: number;
  final_cash: number;
  final_equity: number;
  total_return: number;
  annualized_return: number;
  absolute_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_fees: number;
  slippage_rate: number;
  commission_rate: number;
  trades: TradeStatisticsDTO;
  risk_metrics: BacktestRiskMetricsDTO;
  equity_curve: EquitySnapshotDTO[];
  executed_trades: BacktestTradeDTO[];
  report: PerformanceReportDTO;
}

// =============================================================================
// AI Quantitative Research Assistant Models (V21 Commit 01)
// =============================================================================

export interface CitationDTO {
  id: number;
  source_id: string;
  source_type: string;
  title: string;
  symbol?: string | null;
  timestamp?: string | null;
  model?: string | null;
  facts_summary?: string | null;
  details: Record<string, unknown>;
}

export interface EvidencePacketDTO {
  source_id: string;
  source_type: string;
  title: string;
  facts: Record<string, unknown>;
  timestamp?: string | null;
  metadata: Record<string, unknown>;
}

export interface ResearchQueryRequest {
  question: string;
  symbol?: string | null;
  conversation_id?: string | null;
  context?: Record<string, unknown>;
  stream?: boolean;
}

export interface ResearchResponseDTO {
  answer: string;
  citations: CitationDTO[];
  evidence: EvidencePacketDTO[];
  model: string;
  generated_at: string;
  request_id: string;
  intent: string;
  symbol?: string | null;
}

export interface ResearchStreamEvent {
  event: "metadata" | "evidence" | "token" | "citation" | "complete" | "error" | string;
  data: Record<string, unknown>;
}

export interface ResearchMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationDTO[];
  evidence?: EvidencePacketDTO[];
  model?: string;
  timestamp: string;
  intent?: string;
  symbol?: string | null;
  status?: "idle" | "loading" | "streaming" | "complete" | "error";
  error?: string;
}

// =============================================================================
// Health & Observability Models (V23 Commit 02)
// =============================================================================

export type OperationalHealthStatus = "HEALTHY" | "DEGRADED" | "UNHEALTHY" | "STALE" | "UNKNOWN";
export type OperationalProviderStatus = "AVAILABLE" | "DEGRADED" | "UNAVAILABLE" | "UNKNOWN";

export interface DataFreshnessDTO {
  latest_observation_time: string | null;
  freshness_seconds: number | null;
  market_open: boolean;
  calendar_id: string;
  status: OperationalHealthStatus | string;
  reason: string | null;
}

export interface DataCompletenessDTO {
  expected_rows: number;
  received_rows: number;
  missing_rows: number;
  duplicate_rows: number;
  completeness_ratio: number;
  status: OperationalHealthStatus | string;
}

export interface DataValidityDTO {
  is_valid: boolean;
  critical_issues_count: number;
  warning_issues_count: number;
  failed_rule_ids: string[];
  violations_by_category: Record<string, number>;
  status: OperationalHealthStatus | string;
}

export interface ProviderHealthDTO {
  provider_id: string;
  status: OperationalProviderStatus | string;
  request_count: number;
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
  failure_rate: number;
  avg_latency_ms: number;
  last_successful_request: string | null;
  last_failure: string | null;
  last_error_category: string | null;
}

export interface PipelineStageHealthDTO {
  stage: string;
  status: OperationalHealthStatus | string;
  last_run: string | null;
  details: Record<string, unknown>;
}

export interface PipelineHealthDTO {
  overall_status: OperationalHealthStatus | string;
  stages: Record<string, PipelineStageHealthDTO>;
}

export interface DataHealthResponseDTO {
  symbol: string;
  timestamp: string;
  status: OperationalHealthStatus | string;
  freshness: DataFreshnessDTO;
  completeness: DataCompletenessDTO;
  validity: DataValidityDTO;
  provider?: ProviderHealthDTO | null;
  pipeline?: PipelineHealthDTO | null;
  summary: string;
}

export interface DataHealthListResponseDTO {
  items: DataHealthResponseDTO[];
  total: number;
}

export interface PredictionValidityDTO {
  total_predictions: number;
  valid_predictions: number;
  invalid_predictions: number;
  invalid_regime_ids: number;
  non_finite_values: number;
  invalid_probability_vectors: number;
  status: OperationalHealthStatus | string;
  violations: string[];
}

export interface ModelExecutionDTO {
  prediction_count: number;
  failure_count: number;
  failure_rate: number;
  avg_latency_ms: number;
  status: OperationalHealthStatus | string;
}

export interface ModelConfidenceDTO {
  mean_confidence: number | null;
  min_confidence: number | null;
  max_confidence: number | null;
  std_confidence: number | null;
  low_confidence_count: number;
  low_confidence_ratio: number;
  missing_confidence_count: number;
  status: OperationalHealthStatus | string;
}

export interface ModelStabilityDTO {
  regime_switching_frequency: number;
  consecutive_stable_bars: number;
  confidence_variability: number;
  status: OperationalHealthStatus | string;
}

export interface RegimeDistributionDTO {
  sample_count: number;
  regime_counts: Record<string, number>;
  regime_percentages: Record<string, number>;
  entropy: number;
}

export interface DistributionDriftDTO {
  metric_name: string;
  method: string;
  drift_score: number;
  threshold: number;
  is_drift_detected: boolean;
  reference_distribution: Record<string, number>;
  comparison_distribution: Record<string, number>;
  status: OperationalHealthStatus | string;
}

export interface ModelHealthResponseDTO {
  model_id: string;
  timestamp: string;
  status: OperationalHealthStatus | string;
  validity: PredictionValidityDTO;
  execution: ModelExecutionDTO;
  confidence: ModelConfidenceDTO;
  stability: ModelStabilityDTO;
  regime_distribution: RegimeDistributionDTO;
  drift?: DistributionDriftDTO | null;
  summary: string;
}

export interface ModelHealthListResponseDTO {
  items: ModelHealthResponseDTO[];
  total: number;
}

export interface ProviderHealthListResponseDTO {
  items: ProviderHealthDTO[];
  total: number;
}

export interface SystemHealthSummaryResponseDTO {
  status: OperationalHealthStatus | string;
  timestamp: string;
  components: Record<string, { status: string }>;
  active_models: string[];
  active_providers: string[];
  details: Record<string, unknown>;
}


