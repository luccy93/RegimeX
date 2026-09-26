/**
 * Test-Only Realistic API-Shaped Fixtures
 * =======================================
 * Strictly test-only data structures mirroring FastAPI v1 responses
 * for SPY and benchmark instruments.
 *
 * DO NOT import in production code.
 */

import type {
  MarketItemResponse,
  MarketListResponse,
  MarketDataResponse,
  MarketRegimeResponse,
  OHLCVBarResponse,
} from "../../lib/api/types";

export const MOCK_MARKET_ITEMS: MarketItemResponse[] = [
  {
    symbol: "SPY",
    asset_class: "equity_us",
    exchange: "NYSE",
    currency: "USD",
    description: "SPDR S&P 500 ETF Trust",
  },
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
    symbol: "BTC-USD",
    asset_class: "crypto",
    exchange: "COINBASE",
    currency: "USD",
    description: "Bitcoin / US Dollar",
  },
];

export const MOCK_MARKET_LIST_RESPONSE: MarketListResponse = {
  items: MOCK_MARKET_ITEMS,
  total: 4,
  limit: 100,
  offset: 0,
};

export const MOCK_BARS_SERIES: OHLCVBarResponse[] = [
  {
    timestamp: "2026-09-20T00:00:00Z",
    open: 500.0,
    high: 505.0,
    low: 498.5,
    close: 503.2,
    volume: 45000000,
  },
  {
    timestamp: "2026-09-21T00:00:00Z",
    open: 503.5,
    high: 508.0,
    low: 502.0,
    close: 506.8,
    volume: 52000000,
  },
  {
    timestamp: "2026-09-22T00:00:00Z",
    open: 507.0,
    high: 510.5,
    low: 505.2,
    close: 509.4,
    volume: 48000000,
  },
  {
    timestamp: "2026-09-23T00:00:00Z",
    open: 509.0,
    high: 512.0,
    low: 508.0,
    close: 511.0,
    volume: 43000000,
  },
  {
    timestamp: "2026-09-24T00:00:00Z",
    open: 510.5,
    high: 514.2,
    low: 509.8,
    close: 513.5,
    volume: 58000000,
  },
];

export const MOCK_MARKET_DATA_RESPONSE: MarketDataResponse = {
  symbol: "SPY",
  interval: "1d",
  start: "2026-09-20T00:00:00Z",
  end: "2026-09-24T00:00:00Z",
  count: 5,
  total: 5,
  items: MOCK_BARS_SERIES,
};

export const MOCK_KNOWN_REGIME_RESPONSE: MarketRegimeResponse = {
  symbol: "SPY",
  current_regime: 1,
  current_regime_label: "REGIME_1",
  confidence: 0.884,
  current_context: {
    current_regime_id: 1,
    current_regime_label: "REGIME_1",
    current_timestamp: "2026-09-24T00:00:00Z",
    observations_in_current_run: 8,
    historical_frequency: 0.625,
    historical_average_duration: 12.4,
    historical_max_duration: 24,
    historical_min_duration: 3,
    historical_run_count: 5,
    current_features: {
      return_1d: 0.0048,
      volatility_20d: 0.125,
    },
  },
  profile: {
    regime_id: 1,
    regime_label: "REGIME_1",
    observation_count: 50,
    frequency: 0.625,
    percentage: 62.5,
    first_seen: "2025-09-24T00:00:00Z",
    last_seen: "2026-09-24T00:00:00Z",
    run_count: 5,
    average_duration: 12.4,
    median_duration: 11.0,
    min_duration: 3,
    max_duration: 24,
    feature_statistics: {
      return_1d: {
        feature_name: "return_1d",
        observation_count: 50,
        mean: 0.0008,
        median: 0.0006,
        std: 0.0078,
        min: -0.021,
        max: 0.028,
      },
      volatility_20d: {
        feature_name: "volatility_20d",
        observation_count: 50,
        mean: 0.125,
        median: 0.121,
        std: 0.018,
        min: 0.095,
        max: 0.165,
      },
    },
  },
  profiles: {
    0: {
      regime_id: 0,
      regime_label: "REGIME_0",
      observation_count: 30,
      frequency: 0.375,
      percentage: 37.5,
      first_seen: "2025-10-15T00:00:00Z",
      last_seen: "2026-08-30T00:00:00Z",
      run_count: 4,
      average_duration: 7.5,
      median_duration: 7.0,
      min_duration: 2,
      max_duration: 15,
      feature_statistics: {
        return_1d: {
          feature_name: "return_1d",
          observation_count: 30,
          mean: -0.0012,
          median: -0.0009,
          std: 0.0165,
          min: -0.045,
          max: 0.035,
        },
      },
    },
    1: {
      regime_id: 1,
      regime_label: "REGIME_1",
      observation_count: 50,
      frequency: 0.625,
      percentage: 62.5,
      first_seen: "2025-09-24T00:00:00Z",
      last_seen: "2026-09-24T00:00:00Z",
      run_count: 5,
      average_duration: 12.4,
      median_duration: 11.0,
      min_duration: 3,
      max_duration: 24,
      feature_statistics: {},
    },
  },
  statistics: {
    return_1d: {
      feature_name: "return_1d",
      observation_count: 50,
      mean: 0.0008,
      median: 0.0006,
      std: 0.0078,
      min: -0.021,
      max: 0.028,
    },
    volatility_20d: {
      feature_name: "volatility_20d",
      observation_count: 50,
      mean: 0.125,
      median: 0.121,
      std: 0.018,
      min: 0.095,
      max: 0.165,
    },
  },
  regimes_observed: [0, 1],
  total_observations: 80,
  model_name: "kmeans-regime-detector",
  model_version: "1.2.0",
  algorithm: "kmeans",
  analysis_start: "2025-09-24T00:00:00Z",
  analysis_end: "2026-09-24T00:00:00Z",
};

export const MOCK_UNKNOWN_REGIME_RESPONSE: MarketRegimeResponse = {
  symbol: "XYZ",
  current_regime: 0,
  current_regime_label: "UNKNOWN",
  confidence: null,
  current_context: {
    current_regime_id: 0,
    current_regime_label: "UNKNOWN",
    current_timestamp: "2026-09-24T00:00:00Z",
    observations_in_current_run: 1,
    historical_frequency: 0.0,
    historical_average_duration: 0.0,
    historical_max_duration: 0,
    historical_min_duration: 0,
    historical_run_count: 0,
    current_features: null,
  },
  profile: null,
  profiles: {},
  statistics: {},
  regimes_observed: [],
  total_observations: 0,
  model_name: null,
  model_version: null,
  algorithm: null,
  analysis_start: null,
  analysis_end: null,
};
