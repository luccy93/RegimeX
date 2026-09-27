import type {
  CitationDTO,
  CurrentRegimeContextDTO,
  EvidencePacketDTO,
  ResearchMessage,
  ResearchResponseDTO,
} from "../../lib/api/types";

export const MOCK_CITATION_REGIME: CitationDTO = {
  id: 1,
  source_id: "regime:SPY:current",
  source_type: "regime",
  title: "Regime Intelligence — SPY",
  symbol: "SPY",
  timestamp: "2026-09-26T20:00:00Z",
  model: "HMM / GMM Ensemble",
  facts_summary: "current_regime_label: BULLISH, confidence: 0.884, observations_in_current_run: 42",
  details: {
    current_regime_label: "BULLISH",
    confidence: 0.884,
    observations_in_current_run: 42,
  },
};

export const MOCK_CITATION_RISK: CitationDTO = {
  id: 2,
  source_id: "risk:SPY",
  source_type: "risk",
  title: "Portfolio Risk Profile — SPY",
  symbol: "SPY",
  timestamp: "2026-09-26T20:00:00Z",
  model: "Parametric & Historical VaR",
  facts_summary: "annualized_volatility: 0.1425, max_drawdown: 0.0821, var_95: 0.0152",
  details: {
    annualized_volatility: 0.1425,
    max_drawdown: 0.0821,
  },
};

export const MOCK_EVIDENCE_PACKETS: EvidencePacketDTO[] = [
  {
    source_id: "regime:SPY:current",
    source_type: "regime",
    title: "Regime Intelligence — SPY",
    facts: {
      symbol: "SPY",
      current_regime_label: "BULLISH",
      confidence: 0.884,
      observations_in_current_run: 42,
      historical_average_duration: 35.2,
      historical_run_count: 12,
    },
    timestamp: "2026-09-26T20:00:00Z",
    metadata: { algorithm: "Ensemble", model_name: "v1.2" },
  },
  {
    source_id: "market:SPY",
    source_type: "market",
    title: "Market Instrument — SPY",
    facts: {
      symbol: "SPY",
      exchange: "NYSE",
      currency: "USD",
      latest_close: 570.25,
      observation_count: 252,
    },
    timestamp: "2026-09-26T20:00:00Z",
    metadata: { exchange: "NYSE", currency: "USD" },
  },
];

export const MOCK_RESEARCH_RESPONSE_BULLISH: ResearchResponseDTO = {
  answer:
    "Based on RegimeX model analytics, SPY is currently classified in the **BULLISH** regime with **88.4%** model confidence [1]. The current regime run has persisted for **42** consecutive observations, compared to a historical average duration of **35.2** periods for this state [1].",
  citations: [MOCK_CITATION_REGIME],
  evidence: MOCK_EVIDENCE_PACKETS,
  model: "deterministic-grounded-v1",
  generated_at: "2026-09-26T20:00:05Z",
  request_id: "req-test-123",
  intent: "CURRENT_REGIME",
  symbol: "SPY",
};

export const MOCK_RESEARCH_REFUSAL_RESPONSE: ResearchResponseDTO = {
  answer:
    "RegimeX can describe historical and model-derived regime information and risk analytics, but it does not provide future price predictions or speculative forecasts.",
  citations: [],
  evidence: [],
  model: "deterministic-grounded-v1",
  generated_at: "2026-09-26T20:00:05Z",
  request_id: "req-test-refusal",
  intent: "PREDICTION_REFUSAL",
  symbol: "SPY",
};

export const MOCK_CURRENT_REGIME_CONTEXT: CurrentRegimeContextDTO = {
  current_regime_id: 0,
  current_regime_label: "BULLISH",
  current_timestamp: "2026-09-26T20:00:00Z",
  observations_in_current_run: 42,
  historical_frequency: 0.45,
  historical_average_duration: 35.2,
  historical_max_duration: 85,
  historical_min_duration: 5,
  historical_run_count: 12,
  current_features: null,
};

export const MOCK_RESEARCH_MESSAGES: ResearchMessage[] = [
  {
    id: "user-1",
    role: "user",
    content: "What regime is SPY currently in?",
    timestamp: "2026-09-26T20:00:01Z",
    symbol: "SPY",
  },
  {
    id: "asst-1",
    role: "assistant",
    content: MOCK_RESEARCH_RESPONSE_BULLISH.answer,
    citations: MOCK_RESEARCH_RESPONSE_BULLISH.citations,
    evidence: MOCK_RESEARCH_RESPONSE_BULLISH.evidence,
    model: MOCK_RESEARCH_RESPONSE_BULLISH.model,
    intent: MOCK_RESEARCH_RESPONSE_BULLISH.intent,
    symbol: "SPY",
    timestamp: "2026-09-26T20:00:05Z",
    status: "complete",
  },
];
