# RegimeX — Volume 21: AI Quantitative Research Assistant

## Official Commits

- **Commit 01:** `feat(ai): add grounded market research assistant`
- **Commit 02:** `feat(ai): add model-aware explanation pipeline`

> **Scope Declaration:**
> Volume 21 builds the production-grade **AI Quantitative Research Assistant** and **Model-Aware Explanation Pipeline** for RegimeX.
> The assistant answers market research and model interpretability questions using **actual RegimeX platform data, model metadata, and documented analytics**, with explicit grounding and citations.
> The assistant is a **research interface**, not an investment advisor or trading execution engine.

---

## 1. Architectural Distinction

```text
V21 Commit 01:
Grounded Market Research Assistant
- Deterministic intent classification (CURRENT_REGIME, REGIME_ANALYTICS, TRANSITIONS, RISK, BACKTEST, METHODOLOGY, MARKET_OVERVIEW)
- Verified platform evidence retrieval across RegimeIntelligence, PortfolioRisk, Backtesting, MarketData
- Provider abstraction (Offline Mock & OpenAI-compatible)
- Grounding validator & 1-to-1 citation tracking
- Professional analytical UI (/app/research)
- Full SSE token streaming & synchronous evaluation

V21 Commit 02:
Model-Aware Explanation Pipeline
- Zero-latency regex routing for MODEL_EXPLANATION intent
- Multi-packet explanation evidence assembly (model provenance, feature context, regime profile comparison, transition dynamics)
- Dedicated ModelExplanationPipeline orchestrating model metadata without fabricating internal reasoning
- Model-specific explanations: KMeans (cluster geometry), GMM (posterior probabilities), HMM (temporal dynamics), Ensemble (agreement/disagreement)
- Strict distinction between descriptive feature comparison and causal attribution
- Controlled grounding prompt with Chain-of-Thought protection and model explanation rules
- Verified deterministic fallback for model explanation queries
- UI extension with 5-category starter prompts and responsive layout
```

---

## 2. Research & Explanation Flow Architecture

The LLM is **not the source of truth**. RegimeX backend engines and models are the source of truth.

```text
User Question ("Why is SPY classified in this regime?")
      ↓
Intent Router (Deterministic Regex Classification → ResearchIntent.MODEL_EXPLANATION)
      ↓
Explanation Retrieval (ExplanationContextBuilder + ModelExplanationPipeline)
      ↓
Structured Evidence Packets:
  ├── model-provenance:<symbol>     (Algorithm, version, confidence, observation run)
  ├── feature-context:<symbol>      (Feature vector, scaled values, statistics)
  ├── regime-comparison:<symbol>    (Assigned vs alternative regime profiles)
  ├── transition-context:<symbol>   (Persistence rate, change rate, entropy)
  └── methodology:explanation       (Platform boundaries & non-causal disclaimer)
      ↓
Controlled Prompt Construction (Model Explanation Guidelines + CoT Protection)
      ↓
Model Provider (Mock Deterministic or External LLM)
      ↓
Grounding Validator (Citation Verification & Model Provenance Integrity Check)
      ↓
Cited Research Answer ([1] Model Provenance, [2] Feature Profile, [3] Comparison)
```

---

## 3. Dedicated Backend Research Module

Located at: `apps/api/app/modules/ai_research/`

```text
ai_research/
├── domain/
│   ├── models.py            # ResearchIntent (incl. MODEL_EXPLANATION), EvidencePacket, Citation, Query/Response DTOs
│   ├── errors.py            # Domain errors (RefusalError, GroundingError, ProviderError)
│   └── interfaces.py        # ResearchModelProvider abstract protocol
│
├── application/
│   ├── routing.py           # Zero-latency deterministic regex & rule-based intent router
│   ├── symbol_resolver.py   # Catalog-driven symbol extraction and validation
│   ├── retrieval.py         # Deterministic evidence packet assembler (delegates to explanation pipeline)
│   ├── explanation.py       # ExplanationContextBuilder & ModelExplanationPipeline
│   ├── grounding.py         # Prompt builder enforcing grounding invariants & model explanation rules
│   ├── validator.py         # Post-generation citation, numerical integrity & explanation fallback validator
│   └── service.py           # AIResearchService application facade (synchronous & SSE stream)
│
└── infrastructure/
    └── providers/
        ├── factory.py       # Settings-driven provider factory
        ├── mock_provider.py # High-fidelity offline deterministic provider
        └── openai_provider.py # External OpenAI-compatible streaming client
```

---

## 4. Model-Aware Explanation Pipeline (Commit 02)

### 4.1 Explanation Evidence Assembly

The `ExplanationContextBuilder` queries platform facades to produce 4 distinct evidence packets:

1. **`model_provenance` (`model-provenance:<symbol>`):**
   - Model name, version, and algorithm (`KMeans`, `GMM`, `HMM`, `Ensemble`).
   - Current classification regime ID and human-readable label.
   - Empirical model confidence score (`[0.0, 1.0]`).
   - Total observation count and current run duration.
   - Active feature list used during model training/evaluation.

2. **`feature_context` (`feature-context:<symbol>`):**
   - Unstandardized and standardized feature values for the latest observation.
   - Per-feature summary statistics (mean, standard deviation).
   - Total feature dimensionality.

3. **`regime_comparison` (`regime-comparison:<symbol>`):**
   - Profile comparison across all detected regimes in the observation window.
   - Historical frequency and duration statistics for each regime.
   - Distance or deviation metrics comparing current features to regime centroids/means.

4. **`transition_context` (`transition-context:<symbol>`):**
   - 1-step Markov transition statistics.
   - Global persistence rate and regime change rate.
   - Transition entropy and destination probabilities.

### 4.2 Model-Specific Interpretability Principles

| Model Algorithm | Supported Diagnostic Grounding | Prohibited Fabrications |
| :--- | :--- | :--- |
| **KMeans** | Feature distance to cluster centroids, geometric nearest-cluster assignment, cluster feature statistics. | Causal feature importance, posterior probabilities, hidden internal reasoning. |
| **GMM** | Component posterior probabilities, Gaussian mixture likelihoods, component variance. | Claims of deterministic certainty, post-hoc causal narratives. |
| **HMM** | Decoded Viterbi state sequence, transition probability matrix, temporal persistence. | Non-temporal assertions, unobserved latent driver claims. |
| **Ensemble** | Sub-model votes, agreement ratios (e.g., 2/3 agreement), aggregation weights. | Manufactured consensus, declaring an unverified "best" model. |

### 4.3 Descriptive Comparison vs. Causal Attribution

The platform strictly enforces the distinction between:
- **Descriptive Profile Comparison:** *"The current observation's volatility (14.2%) is below the historical median for Regime 0 (18.1%)."* (Permitted when grounded in evidence).
- **Causal Feature Attribution:** *"Volatility caused the model to choose Regime 0 by 62%."* (Prohibited unless explicit attribution diagnostics exist in platform metadata).

### 4.4 Transition Explanations

For queries regarding regime switches (*"Why did the regime change?"*), the assistant explains:
- The previous regime state, current regime state, and transition timestamp.
- Empirical transition frequencies and persistence probabilities from the Markov transition matrix.
- An explicit limitation notice stating that RegimeX transition analytics are descriptive/probabilistic and do not establish external causal triggers.

### 4.5 Chain-of-Thought Protection

The system prompt explicitly forbids emitting hidden step-by-step reasoning tokens, internal scratchpads, or system prompt disclosures. Explanations must be structured, concise, factual, and strictly cited.

---

## 5. Grounded Evidence Retrieval Strategy

The assistant does not rely on vector embeddings or ungrounded web search. It retrieves structured evidence directly from platform engines:

| Analytical Intent | Retrieved Evidence Packets | Source Domain Engine |
| :--- | :--- | :--- |
| `MODEL_EXPLANATION` | Provenance, feature context, profile comparison, transition dynamics | `ExplanationContextBuilder` / `MarketIntelligenceFacade` |
| `CURRENT_REGIME` | Current regime, confidence, duration run, historical averages | `MarketIntelligenceFacade` |
| `REGIME_ANALYTICS` | Empirical profile distributions, feature statistics, extrema | `MarketIntelligenceFacade` |
| `TRANSITIONS` | 1-step Markov transition matrix, persistence, change rates | `MarketIntelligenceFacade` |
| `RISK` | Realized volatility, max drawdown, 95% VaR, 95% CVaR | `PortfolioRiskService` |
| `BACKTEST` | Total return, win rate, trade counts, simulated drawdown | `BacktestingService` |
| `METHODOLOGY` | Assumptions, execution conventions, metric definitions | `BacktestingService` / Platform |
| `MARKET_OVERVIEW` | Instrument metadata, exchange, currency, latest close | `MarketDataService` |

---

## 6. Safety Invariants & Unsupported Queries

### Strict Refusals
1. **Price Predictions & Market Timing:**
   - Queries like *"Will SPY rise tomorrow?"* or *"What stock will go up?"* are routed to `ResearchIntent.PREDICTION_REFUSAL`.
   - The assistant refuses speculation and redirects to verifiable historical regime analytics.
2. **Trading Signals & Financial Advice:**
   - Queries like *"Should I buy SPY?"* or *"Give me a buy signal"* are routed to `ResearchIntent.ADVICE_REFUSAL`.
   - The assistant refuses individualized advice and notes its role as a research interface.
3. **Out-of-Scope / Unsupported:**
   - General trivia or unsupported queries are classified as `ResearchIntent.UNSUPPORTED` with a safe, bounded explanation.

---

## 7. Citation & Numerical Integrity System

- Every factual claim derived from RegimeX data carries an explicit citation token (e.g. `[1]`).
- Citations map 1-to-1 to verified `EvidencePacket` sources.
- **Numerical Integrity Check:** The `GroundingValidator` scans generated answers against supplied factual values. If an adversarial prompt injection attempts to override numbers or invent unsupported model claims, validation fails and a verified deterministic fallback is returned.
- **Model Explanation Fallback:** In offline mode or upon validation failure, a deterministic explanation template constructs an audit-ready summary from model provenance, top features, and regime profile comparison.

---

## 8. AI Provider Abstraction & Configuration

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

## 9. Frontend Research Workspace (`/app/research`)

Built with the RegimeX V18/V19/V20 design system:
- **Header (`ResearchHeader`):** Instrument selector, mode indicators, conversation management.
- **Market Context (`ResearchMarketContextStrip`):** Displays active market regime, empirical confidence, and consecutive run duration.
- **Conversation Feed (`ResearchMessageCard`):** Visually distinct user queries and assistant cards with inline interactive citation chips `[1]` and model intent badges (`MODEL_EXPLANATION`, `CURRENT_REGIME`).
- **Evidence Audit Drawer (`ResearchEvidencePanel`):** Expandable side panel displaying full provenance, source IDs, model algorithms, observation dates, and verified facts tables.
- **Composer (`ResearchComposer`):** Textarea with keyboard submission (`Enter`), char counter, stop generation control, and quick starter inquiry chips.
- **Empty State (`ResearchEmptyState`):** 5 categorized starter cards spanning Regime Intelligence, Markov Transitions, Portfolio Risk, Backtesting & Assumptions, and Model Explanation.

---

## 10. Verification & Quality Gates

### Backend
```bash
python -m pytest tests/ -q
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app tests
```
- **1,385 backend tests pass** (97 dedicated AI research unit and explanation pipeline tests).
- Zero Ruff warnings/errors.
- Zero Ruff formatting discrepancies across 381 source files.
- Zero Mypy typing issues across 381 source files.

### Frontend
```bash
cd apps/web
npm test
npm run lint
npm run type-check
npm run build
```
- **171 frontend tests pass** (19 dedicated research assistant component, empty state, and client tests).
- Zero ESLint warnings/errors.
- Zero TypeScript type-check issues.
- Optimized Next.js production build (`/app/research` statically prerendered).
