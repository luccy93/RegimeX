# RegimeX — Volume 21: AI Quantitative Research Assistant

## Official Commits

- **Commit 01:** `feat(ai): add grounded market research assistant`
- **Commit 02:** *(Scheduled)* Model-aware explanation capabilities

> **Scope Declaration:**
> Volume 21 Commit 01 builds the production-grade **AI Quantitative Research Assistant** for RegimeX.
> The assistant answers market research questions using **actual RegimeX platform data and documented analytics**, with explicit grounding and citations.
> The assistant is a **research interface**, not an investment advisor or trading execution engine.

---

## 1. Architectural Distinction

```text
V21 Commit 01 (This Commit):
Grounded Research Assistant
- Deterministic intent classification
- Verified platform evidence retrieval (Regimes, Risk, Transitions, Backtests)
- Provider abstraction (Mock & OpenAI-compatible)
- Grounding validator & 1-to-1 citation tracking
- Professional analytical UI (/app/research)
- Full SSE token streaming & synchronous evaluation

V21 Commit 02 (Next Commit):
Model-Aware Explanation Pipeline
- Deep-dive feature attribution explanations
- Transition entropy interpretations
- Cross-model diagnostic reasoning
```

---

## 2. Research Flow Architecture

The LLM is **not the source of truth**. RegimeX backend engines are the source of truth.

```text
User Question
      ↓
Question Analysis (Deterministic Intent Routing & Symbol Resolution)
      ↓
Platform Retrieval (MarketData, RegimeIntelligence, PortfolioRisk, Backtesting)
      ↓
Bounded Evidence Packets (Immutable Facts, Timestamps, Provenance)
      ↓
Controlled Prompt Construction (10 Core Grounding Invariants)
      ↓
Model Provider (Mock Deterministic or External LLM)
      ↓
Grounding Validator (Citation Verification & Numerical Integrity Defense)
      ↓
Traceable Output ([1] Citations + Auditable Evidence Panel)
```

---

## 3. Dedicated Backend Research Module

Located at: `apps/api/app/modules/ai_research/`

```text
ai_research/
├── domain/
│   ├── models.py            # ResearchIntent, EvidencePacket, Citation, Query/Response DTOs
│   ├── errors.py             # Domain errors (RefusalError, GroundingError, ProviderError)
│   └── interfaces.py         # ResearchModelProvider abstract protocol
│
├── application/
│   ├── routing.py            # Zero-latency deterministic regex & rule-based intent router
│   ├── symbol_resolver.py    # Catalog-driven symbol extraction and validation
│   ├── retrieval.py          # Deterministic evidence packet assembler
│   ├── grounding.py          # Prompt builder enforcing the 10 grounding invariants
│   ├── validator.py          # Post-generation citation & numerical integrity validator
│   └── service.py            # AIResearchService application facade (synchronous & SSE stream)
│
└── infrastructure/
    └── providers/
        ├── factory.py        # Settings-driven provider factory
        ├── mock_provider.py  # High-fidelity offline deterministic provider
        └── openai_provider.py# External OpenAI-compatible streaming client
```

---

## 4. Grounded Evidence Retrieval Strategy

The assistant does not rely on opaque vector embeddings or ungrounded web search. It retrieves structured evidence directly from platform engines:

| Analytical Intent | Retrieved Evidence Packets | Source Domain Engine |
| :--- | :--- | :--- |
| `CURRENT_REGIME` | Current regime, confidence, duration run, historical averages | `MarketIntelligenceFacade` |
| `REGIME_ANALYTICS` | Empirical profile distributions, feature statistics, extrema | `MarketIntelligenceFacade` |
| `TRANSITIONS` | 1-step Markov transition matrix, persistence, change rates | `MarketIntelligenceFacade` |
| `RISK` | Realized volatility, max drawdown, 95% VaR, 95% CVaR | `PortfolioRiskService` |
| `BACKTEST` | Total return, win rate, trade counts, simulated drawdown | `BacktestingService` |
| `METHODOLOGY` | Assumptions, execution conventions, metric definitions | `BacktestingService` / Platform |
| `MARKET_OVERVIEW` | Instrument metadata, exchange, currency, latest close | `MarketDataService` |

### Evidence Packet Structure
```json
{
  "source_id": "regime:SPY:current",
  "source_type": "regime",
  "title": "Regime Intelligence — SPY",
  "facts": {
    "symbol": "SPY",
    "current_regime_label": "BULLISH",
    "confidence": 0.884,
    "observations_in_current_run": 42,
    "historical_average_duration": 35.2
  },
  "timestamp": "2026-09-26T20:00:00Z",
  "metadata": {
    "algorithm": "Ensemble",
    "model_name": "v1.2"
  }
}
```

---

## 5. Safety Invariants & Unsupported Queries

### Strict Refusals
1. **Price Predictions & Market Timing:**
   - Queries like *"Will SPY rise tomorrow?"* or *"What stock will go up?"* are immediately routed to `ResearchIntent.PREDICTION_REFUSAL`.
   - The assistant refuses speculation and redirects to verifiable historical regime analytics.
2. **Trading Signals & Financial Advice:**
   - Queries like *"Should I buy SPY?"* or *"Give me a buy signal"* are immediately routed to `ResearchIntent.ADVICE_REFUSAL`.
   - The assistant refuses individualized advice and notes its role as a research interface.
3. **Out-of-Scope / Unsupported:**
   - General trivia or unsupported queries are classified as `ResearchIntent.UNSUPPORTED` with a safe, bounded explanation.

---

## 6. Citation & Numerical Integrity System

- Every factual claim derived from RegimeX data carries an explicit citation token (e.g. `[1]`).
- Citations map 1-to-1 to verified `EvidencePacket` sources.
- **Numerical Integrity Check:** The `GroundingValidator` scans generated answers against supplied factual values. If an adversarial prompt injection attempts to override numbers (e.g., claiming volatility is 42% when evidence says 14%), validation fails and a verified deterministic fallback is returned.

---

## 7. AI Provider Abstraction & Configuration

The assistant is decoupled from proprietary vendors via the `ResearchModelProvider` abstraction:

```python
class ResearchModelProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    @property
    def model_name(self) -> str: ...

    async def generate(self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]) -> str: ...
    async def stream(self, prompt: str, system_prompt: str, evidence: list[EvidencePacket]) -> AsyncGenerator[str, None]: ...
```

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `REGIMEX_AI_PROVIDER` | `mock` | Model provider: `mock` (offline deterministic) or `openai` |
| `REGIMEX_AI_MODEL` | `gpt-4o-mini` | AI model identifier |
| `REGIMEX_AI_API_KEY` | *(None)* | Optional external API key (never committed) |
| `REGIMEX_AI_BASE_URL` | *(None)* | Optional custom OpenAI-compatible endpoint (Ollama, LiteLLM) |
| `REGIMEX_AI_TIMEOUT` | `30.0` | Request timeout in seconds |
| `REGIMEX_AI_MAX_TOKENS` | `2000` | Maximum token generation limit |

---

## 8. Frontend Research Workspace (`/app/research`)

Built with the RegimeX V18/V19/V20 design system:
- **Header (`ResearchHeader`):** Instrument selector, mode indicators, conversation management.
- **Market Context (`ResearchMarketContextStrip`):** Displays active market regime, empirical confidence, and consecutive run duration.
- **Conversation Feed (`ResearchMessageCard`):** Visually distinct user queries and assistant cards with inline interactive citation chips `[1]`.
- **Evidence Audit Drawer (`ResearchEvidencePanel`):** Expandable side panel displaying full provenance, source IDs, observation dates, and verified facts tables.
- **Composer (`ResearchComposer`):** Textarea with keyboard submission (`Enter`), char counter, stop generation control, and quick starter inquiry chips.
- **Empty State (`ResearchEmptyState`):** Categorized starter questions spanning regimes, transitions, risk, and backtesting.

---

## 9. Verification & Quality Gates

### Backend
```bash
python -m pytest tests/ -q
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app tests
```
- **1,351 backend tests pass** (63 dedicated AI research unit and API route tests).
- Zero Ruff warnings/errors.
- Zero Mypy typing issues across 379 source files.

### Frontend
```bash
cd apps/web
npm test
npm run lint
npm run type-check
npm run build
```
- **170 frontend tests pass** (18 dedicated research assistant component and client tests).
- Zero ESLint warnings/errors.
- Zero TypeScript type-check issues.
- Optimized Next.js production build (`/app/research` statically prerendered).
