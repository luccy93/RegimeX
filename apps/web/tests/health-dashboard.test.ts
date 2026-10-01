import test from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  HealthHeader,
  SystemHealthOverview,
  DataHealthSection,
  ProviderHealthSection,
  PipelineHealthSection,
  ModelHealthSection,
} from "../components/health";
import type {
  SystemHealthSummaryResponseDTO,
  DataHealthResponseDTO,
  ModelHealthResponseDTO,
  ProviderHealthDTO,
  PipelineHealthDTO,
} from "../lib/api/types";

const MOCK_SUMMARY: SystemHealthSummaryResponseDTO = {
  status: "HEALTHY",
  timestamp: "2026-10-01T22:00:00Z",
  components: {
    market_data: { status: "HEALTHY" },
    models: { status: "HEALTHY" },
    providers: { status: "HEALTHY" },
    pipeline: { status: "HEALTHY" },
  },
  active_models: ["kmeans", "gmm", "hmm", "ensemble"],
  active_providers: ["yahoo_finance", "alpha_vantage"],
  details: {},
};

const MOCK_DATA_FEED: DataHealthResponseDTO = {
  symbol: "SPY",
  status: "HEALTHY",
  timestamp: "2026-10-01T22:00:00Z",
  summary: "Market data feed SPY is healthy.",
  freshness: {
    latest_observation_time: "2026-10-01T20:00:00Z",
    freshness_seconds: 7200,
    market_open: false,
    calendar_id: "nyse",
    status: "HEALTHY",
    reason: "Observation matches latest market session close.",
  },
  completeness: {
    expected_rows: 100,
    received_rows: 100,
    missing_rows: 0,
    duplicate_rows: 0,
    completeness_ratio: 1.0,
    status: "HEALTHY",
  },
  validity: {
    is_valid: true,
    critical_issues_count: 0,
    warning_issues_count: 0,
    failed_rule_ids: [],
    violations_by_category: {},
    status: "HEALTHY",
  },
  provider: {
    provider_id: "yahoo_finance",
    status: "AVAILABLE",
    request_count: 50,
    success_count: 50,
    failure_count: 0,
    consecutive_failures: 0,
    failure_rate: 0.0,
    avg_latency_ms: 120.5,
    last_successful_request: "2026-10-01T20:00:00Z",
    last_failure: null,
    last_error_category: null,
  },
  pipeline: null,
};

const MOCK_MODEL_FEED: ModelHealthResponseDTO = {
  model_id: "kmeans",
  status: "HEALTHY",
  timestamp: "2026-10-01T22:00:00Z",
  summary: "Model operating within expected performance bounds.",
  validity: {
    total_predictions: 100,
    valid_predictions: 100,
    invalid_predictions: 0,
    invalid_regime_ids: 0,
    non_finite_values: 0,
    invalid_probability_vectors: 0,
    status: "HEALTHY",
    violations: [],
  },
  execution: {
    prediction_count: 100,
    failure_count: 0,
    failure_rate: 0.0,
    avg_latency_ms: 15.2,
    status: "HEALTHY",
  },
  confidence: {
    mean_confidence: 0.88,
    min_confidence: 0.65,
    max_confidence: 0.99,
    std_confidence: 0.05,
    low_confidence_count: 2,
    low_confidence_ratio: 0.02,
    missing_confidence_count: 0,
    status: "HEALTHY",
  },
  stability: {
    regime_switching_frequency: 0.051,
    consecutive_stable_bars: 25,
    confidence_variability: 0.04,
    status: "HEALTHY",
  },
  regime_distribution: {
    sample_count: 100,
    regime_counts: { "0": 60, "1": 40 },
    regime_percentages: { "0": 60.0, "1": 40.0 },
    entropy: 0.673,
  },
  drift: {
    metric_name: "regime_predictions",
    method: "jsd",
    drift_score: 0.02,
    threshold: 0.20,
    is_drift_detected: false,
    reference_distribution: { "0": 0.5, "1": 0.5 },
    comparison_distribution: { "0": 0.6, "1": 0.4 },
    status: "HEALTHY",
  },
};

const MOCK_PROVIDER: ProviderHealthDTO = {
  provider_id: "alpha_vantage",
  status: "AVAILABLE",
  request_count: 200,
  success_count: 198,
  failure_count: 2,
  consecutive_failures: 0,
  failure_rate: 0.01,
  avg_latency_ms: 210.0,
  last_successful_request: "2026-10-01T21:55:00Z",
  last_failure: "2026-10-01T18:00:00Z",
  last_error_category: null,
};

const MOCK_PIPELINE: PipelineHealthDTO = {
  overall_status: "HEALTHY",
  stages: {
    provider: { stage: "provider", status: "HEALTHY", last_run: null, details: {} },
    ingestion: { stage: "ingestion", status: "HEALTHY", last_run: null, details: {} },
    validation: { stage: "validation", status: "HEALTHY", last_run: null, details: {} },
    normalization: { stage: "normalization", status: "HEALTHY", last_run: null, details: {} },
    storage: { stage: "storage", status: "HEALTHY", last_run: null, details: {} },
    features: { stage: "features", status: "HEALTHY", last_run: null, details: {} },
  },
};

test("HealthHeader — renders title, status badge, and refresh action", () => {
  const html = renderToStaticMarkup(
    React.createElement(HealthHeader, {
      systemStatus: "HEALTHY",
      lastUpdated: "2026-10-01T22:00:00Z",
      onRefresh: () => {},
      isLoading: false,
    })
  );

  assert.ok(html.includes("System Health &amp; Telemetry"), "Renders dashboard title");
  assert.ok(html.includes("HEALTHY"), "Renders status badge");
  assert.ok(html.includes("not investment advice"), "Renders disclaimer text");
  assert.ok(html.includes("Refresh"), "Renders refresh action button");
});

test("SystemHealthOverview — renders component counts and cards", () => {
  const html = renderToStaticMarkup(
    React.createElement(SystemHealthOverview, {
      summary: MOCK_SUMMARY,
    })
  );

  assert.ok(html.includes("System Status"), "Renders system status card");
  assert.ok(html.includes("Market Data"), "Renders market data card");
  assert.ok(html.includes("Regime Models"), "Renders regime models card");
  assert.ok(html.includes("Upstream Providers"), "Renders providers card");
  assert.ok(html.includes("Data Pipeline"), "Renders data pipeline card");
});

test("DataHealthSection — renders observation metrics and completeness", () => {
  const html = renderToStaticMarkup(
    React.createElement(DataHealthSection, {
      dataFeeds: [MOCK_DATA_FEED],
    })
  );

  assert.ok(html.includes("Market Data Health"), "Renders section title");
  assert.ok(html.includes("SPY"), "Renders feed symbol");
  assert.ok(html.includes("NYSE"), "Renders calendar id");
  assert.ok(html.includes("100.0%"), "Renders completeness ratio");
  assert.ok(html.includes("Validation Status"), "Renders validation section");
});

test("DataHealthSection — handles empty feed list", () => {
  const html = renderToStaticMarkup(
    React.createElement(DataHealthSection, {
      dataFeeds: [],
    })
  );

  assert.ok(
    html.includes("No data health feeds currently registered"),
    "Renders empty feed message"
  );
});

test("ModelHealthSection — renders validity, stability, and distribution", () => {
  const html = renderToStaticMarkup(
    React.createElement(ModelHealthSection, {
      models: [MOCK_MODEL_FEED],
    })
  );

  assert.ok(html.includes("Regime Models Operational Health"), "Renders section title");
  assert.ok(html.includes("kmeans"), "Renders model name");
  assert.ok(html.includes("100/100 valid"), "Renders valid predictions ratio");
  assert.ok(html.includes("5.1%"), "Renders switching frequency");
  assert.ok(html.includes("88.0%"), "Renders mean confidence");
  assert.ok(html.includes("Regime 0:"), "Renders regime 0 distribution");
  assert.ok(html.includes("Regime 1:"), "Renders regime 1 distribution");
  assert.ok(html.includes("Distribution Drift (jsd)"), "Renders drift metric");
});

test("ProviderHealthSection — renders provider latency and failure stats", () => {
  const html = renderToStaticMarkup(
    React.createElement(ProviderHealthSection, {
      providers: [MOCK_PROVIDER],
    })
  );

  assert.ok(html.includes("Upstream Data Providers"), "Renders section title");
  assert.ok(html.includes("alpha_vantage"), "Renders provider identifier");
  assert.ok(html.includes("198 / 2"), "Renders success/failure count");
  assert.ok(html.includes("210 ms"), "Renders average latency");
});

test("PipelineHealthSection — renders all 6 pipeline stages", () => {
  const html = renderToStaticMarkup(
    React.createElement(PipelineHealthSection, {
      pipeline: MOCK_PIPELINE,
    })
  );

  assert.ok(html.includes("Data Pipeline Stages"), "Renders section title");
  assert.ok(html.includes("provider"), "Renders provider stage");
  assert.ok(html.includes("ingestion"), "Renders ingestion stage");
  assert.ok(html.includes("validation"), "Renders validation stage");
  assert.ok(html.includes("normalization"), "Renders normalization stage");
  assert.ok(html.includes("storage"), "Renders storage stage");
  assert.ok(html.includes("features"), "Renders features stage");
});
