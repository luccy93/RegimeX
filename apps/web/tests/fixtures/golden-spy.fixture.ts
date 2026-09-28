/**
 * RegimeX Web — Canonical SPY Golden Test Fixture
 * =================================================
 * Volume 22 — Commit 02: End-to-End Critical Workflows
 *
 * Deterministic test fixtures strictly mirroring FastAPI v1 DTO responses
 * for SPY and benchmark instruments.
 * Zero live market feeds, zero external API keys.
 */

import type {
  MarketItemResponse,
  MarketListResponse,
  OHLCVBarResponse,
  MarketDataResponse,
  MarketRegimeResponse,
  MarketTransitionResponse,
  MarketRiskResponse,
  MarketBacktestResponse,
  ResearchResponseDTO,
  EvidencePacketDTO,
} from "../../lib/api/types";

// =============================================================================
// 1. Benchmark Catalog
// =============================================================================

export const GOLDEN_SPY_INSTRUMENT: MarketItemResponse = {
  symbol: "SPY",
  asset_class: "equity_us",
  exchange: "NYSE",
  currency: "USD",
  description: "SPDR S&P 500 ETF Trust",
};

export const GOLDEN_CATALOG: MarketItemResponse[] = [
  GOLDEN_SPY_INSTRUMENT,
  {
    symbol: "QQQ",
    asset_class: "equity_us",
    exchange: "NASDAQ",
    currency: "USD",
    description: "Invesco QQQ Trust Series 1",
  },
  {
    symbol: "AAPL",
    asset_class: "equity_us",
    exchange: "NASDAQ",
    currency: "USD",
    description: "Apple Inc. Common Stock",
  },
  {
    symbol: "EMPTY",
    asset_class: "equity_us",
    exchange: "NYSE",
    currency: "USD",
    description: "Valid Instrument With Empty Data Store",
  },
];

export const MOCK_GOLDEN_MARKET_LIST: MarketListResponse = {
  items: GOLDEN_CATALOG,
  total: 4,
  limit: 100,
  offset: 0,
};

// =============================================================================
// 2. Deterministic OHLCV Bars (60 Bars)
// =============================================================================

function generateBars(): OHLCVBarResponse[] {
  const bars: OHLCVBarResponse[] = [];
  const baseTime = new Date("2026-01-05T00:00:00Z").getTime();
  const basePrice = 500.0;

  for (let i = 0; i < 60; i++) {
    const d = new Date(baseTime + i * 86400000).toISOString();
    const trend = i * 0.4;
    const cycle = 3.5 * Math.sin(i * 0.35);
    const p = Math.round((basePrice + trend + cycle) * 100) / 100;

    bars.push({
      timestamp: d,
      open: Math.round((p - 0.75) * 100) / 100,
      high: Math.round((p + 1.8) * 100) / 100,
      low: Math.round((p - 1.5) * 100) / 100,
      close: p,
      volume: 45000000 + (i % 7) * 2000000,
    });
  }
  return bars;
}

export const GOLDEN_SPY_BARS: OHLCVBarResponse[] = generateBars();

export const MOCK_GOLDEN_MARKET_DATA: MarketDataResponse = {
  symbol: "SPY",
  interval: "1d",
  start: "2026-01-05T00:00:00Z",
  end: "2026-03-05T00:00:00Z",
  count: GOLDEN_SPY_BARS.length,
  total: GOLDEN_SPY_BARS.length,
  items: GOLDEN_SPY_BARS,
};

// =============================================================================
// 3. Regime Analytics Responses
// =============================================================================

export const MOCK_GOLDEN_REGIME: MarketRegimeResponse = {
  symbol: "SPY",
  current_regime: 1,
  current_regime_label: "REGIME_1",
  confidence: 0.884,
  current_context: {
    current_regime_id: 1,
    current_regime_label: "REGIME_1",
    current_timestamp: "2026-03-05T00:00:00Z",
    observations_in_current_run: 8,
    historical_frequency: 0.5,
    historical_average_duration: 12.5,
    historical_max_duration: 25,
    historical_min_duration: 3,
    historical_run_count: 4,
    current_features: {
      return_1d: 0.0048,
      volatility_20d: 0.125,
      momentum_20d: 0.032,
    },
  },
  profile: {
    regime_id: 1,
    regime_label: "REGIME_1",
    observation_count: 30,
    frequency: 0.5,
    percentage: 50.0,
    first_seen: "2026-01-05T00:00:00Z",
    last_seen: "2026-03-05T00:00:00Z",
    run_count: 4,
    average_duration: 12.5,
    median_duration: 11.0,
    min_duration: 3,
    max_duration: 25,
    feature_statistics: {
      return_1d: {
        feature_name: "return_1d",
        observation_count: 30,
        mean: 0.0048,
        median: 0.0045,
        std: 0.0062,
        min: -0.0085,
        max: 0.0195,
      },
      volatility_20d: {
        feature_name: "volatility_20d",
        observation_count: 30,
        mean: 0.125,
        median: 0.121,
        std: 0.018,
        min: 0.095,
        max: 0.165,
      },
      momentum_20d: {
        feature_name: "momentum_20d",
        observation_count: 30,
        mean: 0.032,
        median: 0.029,
        std: 0.014,
        min: -0.005,
        max: 0.058,
      },
    },
  },
  profiles: {
    0: {
      regime_id: 0,
      regime_label: "REGIME_0",
      observation_count: 30,
      frequency: 0.5,
      percentage: 50.0,
      first_seen: "2026-01-05T00:00:00Z",
      last_seen: "2026-03-05T00:00:00Z",
      run_count: 4,
      average_duration: 7.5,
      median_duration: 7.0,
      min_duration: 2,
      max_duration: 15,
      feature_statistics: {
        return_1d: {
          feature_name: "return_1d",
          observation_count: 30,
          mean: -0.0032,
          median: -0.0028,
          std: 0.0094,
          min: -0.025,
          max: 0.012,
        },
      },
    },
    1: {
      regime_id: 1,
      regime_label: "REGIME_1",
      observation_count: 30,
      frequency: 0.5,
      percentage: 50.0,
      first_seen: "2026-01-05T00:00:00Z",
      last_seen: "2026-03-05T00:00:00Z",
      run_count: 4,
      average_duration: 12.5,
      median_duration: 11.0,
      min_duration: 3,
      max_duration: 25,
      feature_statistics: {
        return_1d: {
          feature_name: "return_1d",
          observation_count: 30,
          mean: 0.0048,
          median: 0.0045,
          std: 0.0062,
          min: -0.0085,
          max: 0.0195,
        },
      },
    },
  },
  statistics: {},
  regimes_observed: [0, 1],
  total_observations: 60,
  model_name: "ensemble-gmm-kmeans",
  model_version: "1.0.0",
  algorithm: "Ensemble Voting Classifier",
  analysis_start: "2026-01-05T00:00:00Z",
  analysis_end: "2026-03-05T00:00:00Z",
};

export const MOCK_GOLDEN_TRANSITIONS: MarketTransitionResponse = {
  symbol: "SPY",
  regimes: [0, 1],
  probability_matrix: [
    [0.85, 0.15],
    [0.12, 0.88],
  ],
  count_matrix: [
    [25, 4],
    [4, 26],
  ],
  regime_change_counts: [
    [0, 4],
    [4, 0],
  ],
  regime_change_probabilities: [
    [0.0, 1.0],
    [1.0, 0.0],
  ],
  regime_analytics: {
    0: {
      regime_id: 0,
      regime_label: "REGIME_0",
      outgoing_transition_count: 29,
      incoming_transition_count: 29,
      self_transition_count: 25,
      regime_change_count: 4,
      persistence_probability: 0.862,
      change_rate: 0.138,
      most_likely_destination: 1,
      most_likely_destination_probability: 0.138,
      destination_count: 1,
      source_count: 1,
      transition_entropy: 0.578,
      rankings: [
        {
          target_regime: 1,
          target_label: "REGIME_1",
          probability: 0.138,
          count: 4,
          rank: 1,
        },
      ],
    },
    1: {
      regime_id: 1,
      regime_label: "REGIME_1",
      outgoing_transition_count: 30,
      incoming_transition_count: 30,
      self_transition_count: 26,
      regime_change_count: 4,
      persistence_probability: 0.867,
      change_rate: 0.133,
      most_likely_destination: 0,
      most_likely_destination_probability: 0.133,
      destination_count: 1,
      source_count: 1,
      transition_entropy: 0.565,
      rankings: [
        {
          target_regime: 0,
          target_label: "REGIME_0",
          probability: 0.133,
          count: 4,
          rank: 1,
        },
      ],
    },
  },
  global_analytics: {
    total_observations: 60,
    total_consecutive_transitions: 59,
    total_regime_changes: 8,
    total_self_transitions: 51,
    global_change_rate: 0.136,
    global_persistence_rate: 0.864,
    number_of_regimes: 2,
    number_of_observed_transition_edges: 4,
  },
  probabilities: [
    { source_regime: 0, target_regime: 0, count: 25, total_transitions_from_source: 29, probability: 0.862 },
    { source_regime: 0, target_regime: 1, count: 4, total_transitions_from_source: 29, probability: 0.138 },
    { source_regime: 1, target_regime: 0, count: 4, total_transitions_from_source: 30, probability: 0.133 },
    { source_regime: 1, target_regime: 1, count: 26, total_transitions_from_source: 30, probability: 0.867 },
  ],
};

// =============================================================================
// 4. Portfolio Risk Response
// =============================================================================

export const MOCK_GOLDEN_RISK: MarketRiskResponse = {
  symbol: "SPY",
  series_id: "SPY",
  observation_count: 60,
  start_timestamp: "2026-01-05T00:00:00Z",
  end_timestamp: "2026-03-05T00:00:00Z",
  computed_at: "2026-03-05T00:00:00Z",
  return_statistics: {
    mean_return: 0.0008,
    median_return: 0.0007,
    standard_deviation: 0.0113,
    minimum_return: -0.024,
    maximum_return: 0.028,
    observation_count: 60,
  },
  volatility: {
    period_volatility: 0.0113,
    annualized_volatility: 0.18,
    periods_per_year: 252.0,
  },
  downside_risk: {
    downside_deviation: 0.115,
    semi_variance: 0.000082,
    target_return: 0.0,
    observation_count: 60,
    downside_observation_count: 28,
  },
  drawdown: {
    max_drawdown: -0.082,
    drawdown_magnitude: 0.082,
    peak_value: 518.5,
    trough_value: 476.0,
    peak_timestamp: "2026-02-10T00:00:00Z",
    trough_timestamp: "2026-02-22T00:00:00Z",
    recovery_timestamp: "2026-03-05T00:00:00Z",
    is_recovered: true,
  },
  var_metrics: {
    "0.9": { confidence_level: 0.9, var_loss: -0.012, return_quantile: -0.012, method: "historical", tail_observations: 6, total_observations: 60 },
    "0.95": { confidence_level: 0.95, var_loss: -0.016, return_quantile: -0.016, method: "historical", tail_observations: 3, total_observations: 60 },
    "0.99": { confidence_level: 0.99, var_loss: -0.022, return_quantile: -0.022, method: "historical", tail_observations: 1, total_observations: 60 },
  },
  expected_shortfall_metrics: {
    "0.9": { confidence_level: 0.9, expected_shortfall: -0.018, tail_mean_return: -0.018, var_loss: -0.012, tail_observations: 6, total_observations: 60 },
    "0.95": { confidence_level: 0.95, expected_shortfall: -0.024, tail_mean_return: -0.024, var_loss: -0.016, tail_observations: 3, total_observations: 60 },
    "0.99": { confidence_level: 0.99, expected_shortfall: -0.029, tail_mean_return: -0.029, var_loss: -0.022, tail_observations: 1, total_observations: 60 },
  },
  price_points: [
    { timestamp: "2026-01-05T00:00:00Z", price: 500.0, period_return: 0.0, running_peak: 500.0, drawdown: 0.0 },
    { timestamp: "2026-02-10T00:00:00Z", price: 518.5, period_return: 0.008, running_peak: 518.5, drawdown: 0.0 },
    { timestamp: "2026-02-22T00:00:00Z", price: 476.0, period_return: -0.015, running_peak: 518.5, drawdown: -0.082 },
    { timestamp: "2026-03-05T00:00:00Z", price: 524.0, period_return: 0.012, running_peak: 524.0, drawdown: 0.0 },
  ],
};

// =============================================================================
// 5. Backtest Response
// =============================================================================

export const MOCK_GOLDEN_BACKTEST: MarketBacktestResponse = {
  symbol: "SPY",
  strategy_id: "BUY_AND_HOLD",
  strategy_name: "Benchmark Buy and Hold",
  execution_convention: "CURRENT_CLOSE",
  initial_cash: 100000.0,
  final_cash: 14500.5,
  final_equity: 114500.5,
  total_return: 0.145,
  annualized_return: 0.145,
  absolute_pnl: 14500.5,
  realized_pnl: 10000.5,
  unrealized_pnl: 4500.0,
  total_fees: 45.2,
  slippage_rate: 0.0005,
  commission_rate: 0.0005,
  trades: {
    order_count: 12,
    fill_count: 12,
    completed_trade_count: 6,
    winning_trades: 4,
    losing_trades: 2,
    win_rate: 0.667,
    total_realized_pnl: 10000.5,
    average_trade_pnl: 1666.75,
    largest_winning_trade: 3500.0,
    largest_losing_trade: -1200.0,
  },
  risk_metrics: {
    volatility: 0.142,
    annualized_volatility: 0.142,
    maximum_drawdown: -0.065,
    drawdown_magnitude: 0.065,
    var_95: -0.014,
    expected_shortfall_95: -0.019,
  },
  equity_curve: [
    { timestamp: "2026-01-05T00:00:00Z", cash: 100000.0, market_value: 0.0, equity: 100000.0, fees: 0.0, realized_pnl: 0.0, unrealized_pnl: 0.0, drawdown: 0.0 },
    { timestamp: "2026-02-10T00:00:00Z", cash: 5200.0, market_value: 103000.0, equity: 108200.0, fees: 22.5, realized_pnl: 0.0, unrealized_pnl: 8200.0, drawdown: 0.0 },
    { timestamp: "2026-02-22T00:00:00Z", cash: 5200.0, market_value: 96000.0, equity: 101200.0, fees: 22.5, realized_pnl: 0.0, unrealized_pnl: 1200.0, drawdown: -0.065 },
    { timestamp: "2026-03-05T00:00:00Z", cash: 14500.5, market_value: 100000.0, equity: 114500.5, fees: 45.2, realized_pnl: 10000.5, unrealized_pnl: 4500.0, drawdown: 0.0 },
  ],
  executed_trades: [],
  report: {
    report_id: "rpt-golden-spy-001",
    report_version: "1.0",
    generated_at: "2026-03-05T00:00:00Z",
    methodology: {
      common_period_policy: "strict_overlap",
      trade_definition: "round_trip",
      risk_engine_source: "v13_portfolio_risk",
      return_type: "log_returns",
      execution_engine_source: "v14_event_driven",
    },
    limitations: [
      "Past performance is not indicative of future returns",
      "Execution slippage modeled as fixed percentage",
    ],
    metric_definitions: [
      {
        metric_name: "total_return",
        description: "Cumulative percentage return over initial equity",
        unit: "percentage",
        direction_semantics: "higher_is_better",
        source: "backtesting_engine",
      },
      {
        metric_name: "maximum_drawdown",
        description: "Peak-to-trough decline in equity over backtest duration",
        unit: "percentage",
        direction_semantics: "lower_is_better",
        source: "backtesting_engine",
      },
    ],
  },
};

// =============================================================================
// 6. Grounded AI Research Responses
// =============================================================================

export const GOLDEN_RESEARCH_EVIDENCE: EvidencePacketDTO[] = [
  {
    source_id: "regime:SPY:current",
    source_type: "regime",
    title: "SPY Current Regime Classification",
    facts: {
      symbol: "SPY",
      current_regime_id: 1,
      current_regime_label: "REGIME_1",
      confidence: 0.884,
      observations_in_current_run: 8,
      historical_average_duration: 12.5,
      historical_frequency: 0.5,
      return_1d: 0.0048,
      volatility_20d: 0.125,
      momentum_20d: 0.032,
    },
    timestamp: "2026-03-05T00:00:00Z",
    metadata: {
      model_name: "ensemble-gmm-kmeans",
      model_version: "1.0.0",
      algorithm: "Ensemble Voting Classifier",
    },
  },
  {
    source_id: "risk:SPY:metrics",
    source_type: "risk",
    title: "SPY Historical Portfolio Risk Profile",
    facts: {
      symbol: "SPY",
      annualized_volatility: 0.18,
      maximum_drawdown: -0.082,
      downside_deviation: 0.115,
      var_95: -0.016,
      expected_shortfall_95: -0.024,
      mean_daily_return: 0.0008,
    },
    timestamp: "2026-03-05T00:00:00Z",
    metadata: {
      methodology: "Historical simulation across 60 daily trading periods",
    },
  },
];

export const MOCK_GOLDEN_RESEARCH_RESPONSE: ResearchResponseDTO = {
  answer:
    "Based on RegimeX model analytics, SPY is currently classified in the **REGIME_1** regime with **88.4%** model confidence [1]. The current regime run has persisted for **8** consecutive observations, compared to a historical average duration of **12.5** periods. Annualized realized volatility is **18.0%** [2].",
  citations: [
    {
      id: 1,
      source_id: "regime:SPY:current",
      source_type: "regime",
      title: "SPY Current Regime Classification",
      symbol: "SPY",
      timestamp: "2026-03-05T00:00:00Z",
      model: "ensemble-gmm-kmeans (1.0.0)",
      facts_summary: "Regime 1 (confidence 88.4%, 8 observations in run)",
      details: {
        current_regime_label: "REGIME_1",
        confidence: 0.884,
        observations_in_current_run: 8,
      },
    },
    {
      id: 2,
      source_id: "risk:SPY:metrics",
      source_type: "risk",
      title: "SPY Historical Portfolio Risk Profile",
      symbol: "SPY",
      timestamp: "2026-03-05T00:00:00Z",
      facts_summary: "Annualized volatility 18.0%, max drawdown -8.2%",
      details: {
        annualized_volatility: 0.18,
        maximum_drawdown: -0.082,
      },
    },
  ],
  evidence: GOLDEN_RESEARCH_EVIDENCE,
  model: "mock (deterministic-grounded-v1)",
  generated_at: "2026-03-05T00:00:00Z",
  request_id: "req-golden-spy-001",
  intent: "CURRENT_REGIME",
  symbol: "SPY",
};

export const MOCK_GOLDEN_MODEL_EXPLANATION: ResearchResponseDTO = {
  answer:
    "The classification of SPY as **REGIME_1** by the **ensemble-gmm-kmeans** model is based on feature vector values (1-day return: 0.48%, 20-day volatility: 12.5%, 20-day momentum: 3.2%) [1]. The ensemble classifier assigned 88.4% confidence based on high proximity to the REGIME_1 centroid. Limitations: Model outputs represent statistical associations and do not guarantee future regime stability.",
  citations: [
    {
      id: 1,
      source_id: "regime:SPY:current",
      source_type: "regime",
      title: "SPY Current Regime Classification",
      symbol: "SPY",
      timestamp: "2026-03-05T00:00:00Z",
      model: "ensemble-gmm-kmeans (1.0.0)",
      facts_summary: "Return 0.48%, Volatility 12.5%, Momentum 3.2%",
      details: {
        model_name: "ensemble-gmm-kmeans",
        algorithm: "Ensemble Voting Classifier",
      },
    },
  ],
  evidence: GOLDEN_RESEARCH_EVIDENCE,
  model: "mock (deterministic-grounded-v1)",
  generated_at: "2026-03-05T00:00:00Z",
  request_id: "req-golden-expl-001",
  intent: "MODEL_EXPLANATION",
  symbol: "SPY",
};

export const MOCK_GOLDEN_PREDICTION_REFUSAL: ResearchResponseDTO = {
  answer:
    "RegimeX can describe historical and model-derived regime information and risk analytics, but it does not provide future price predictions or speculative forecasts.",
  citations: [],
  evidence: [],
  model: "mock (deterministic-grounded-v1)",
  generated_at: "2026-03-05T00:00:00Z",
  request_id: "req-golden-refusal-001",
  intent: "PREDICTION_REFUSAL",
  symbol: "SPY",
};

export const MOCK_GOLDEN_ADVICE_REFUSAL: ResearchResponseDTO = {
  answer:
    "RegimeX is a quantitative research platform and does not provide personalized financial advice, trade signals, or buy/sell recommendations.",
  citations: [],
  evidence: [],
  model: "mock (deterministic-grounded-v1)",
  generated_at: "2026-03-05T00:00:00Z",
  request_id: "req-golden-advice-001",
  intent: "ADVICE_REFUSAL",
  symbol: "SPY",
};

// =============================================================================
// 7. Canonical SPY Test Data Object
// =============================================================================

export const SPY_TEST_DATA = {
  symbol: "SPY",
  assetClass: "equity_us",
  exchange: "NYSE",
  currency: "USD",
  barCount: GOLDEN_SPY_BARS.length,
  firstDate: GOLDEN_SPY_BARS[0].timestamp,
  lastDate: GOLDEN_SPY_BARS[GOLDEN_SPY_BARS.length - 1].timestamp,
  firstPrice: GOLDEN_SPY_BARS[0].close,
  lastPrice: GOLDEN_SPY_BARS[GOLDEN_SPY_BARS.length - 1].close,
  currentRegimeId: 1,
  currentRegimeLabel: "REGIME_1",
  confidence: 0.884,
  annualizedVolatility: 0.18,
  maximumDrawdown: -0.082,
  var95: -0.016,
  expectedShortfall95: -0.024,
  backtestTotalReturn: 0.145,
  backtestInitialCash: 100000.0,
  backtestFinalEquity: 114500.5,
  modelName: "ensemble-gmm-kmeans",
};
