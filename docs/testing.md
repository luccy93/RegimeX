# RegimeX Testing Guide

This document outlines the testing architecture, standards, fixture strategies, and execution commands for the RegimeX automated test suite.

---

## 1. Test Architecture & Pyramid

RegimeX follows a rigorous automated testing pyramid:

```text
              [E2E Workflows]          (Critical End-to-End paths)
           [API & Service Invariants]  (HTTP contracts, error models, DB repos)
      [Domain Invariants & Unit Tests] (Pure math, models, deterministic engines)
```

1. **Domain & Unit Layer**:
   - Tests pure domain invariants, data quality calendars, regime detection algorithms (KMeans, GMM, HMM, Ensemble), Markov transition calculations, risk engine mathematics, backtesting event processing, and AI grounding validators.
   - Zero I/O dependencies; deterministic execution with fixed random seeds.

2. **Service & Infrastructure Layer**:
   - Validates repository error translation (e.g. SQLAlchemy `OperationalError` to `StorageConnectionError`), persistence idempotency, calendar gap detection, and caching behaviors.
   - Uses in-memory or transactional SQLite fixtures for fast local test cycles.

3. **API & Contract Integration Layer**:
   - Exercises FastAPI routes, Pydantic request/response serialization contracts, error envelopes (`{"error": {"code", "message", "request_id"}}`), and security headers.
   - Ensures internal stack traces and server internals are sanitized and never leaked to API callers.

4. **Frontend Component & Accessibility Layer**:
   - Tests critical UI component states (loading, error with retry, empty, active data) across dashboards, risk metrics, trade statistics, and the AI research workspace.
   - Validates WCAG accessibility semantics (ARIA live regions, semantic landmarks, keyboard interactive chips, and dialogs).

---

## 2. External Service Policy

> **Zero Live External Services in Default Test Suite**

All standard unit and integration tests execute completely offline without live internet access or external credentials:
- **Market Data**: All provider interactions (Yahoo Finance, Alpaca, etc.) use synthetic fixtures and mock providers.
- **AI Research**: LLM calls are mocked using `MockModelProvider` or mock HTTP transports (`httpx.MockTransport`) for `OpenAICompatibleProvider`. Live OpenAI/LLM endpoints are never called.
- **Databases**: SQLite in-memory or isolated file databases are used for repository unit and integration testing.

---

## 3. Fixture Strategy

Deterministic fixtures reside in dedicated test modules:

- **Backend Fixtures**:
  - `tests/fixtures/`: Synthetic OHLCV bars, feature matrices, regime assignments, risk metrics, and audit context packets.
  - Controlled time stamps (UTC) and deterministic pseudo-random seeds (`np.random.RandomState(42)`).

- **Frontend Fixtures (`apps/web/tests/fixtures/`)**:
  - `ai-research.fixture.ts`: Grounded answers, citations, and verified evidence packets.
  - `market-data.fixture.ts`: Catalogs, OHLCV time series, and status responses.
  - `risk-and-backtesting.fixture.ts`: Full risk profiles, drawdown curves, equity curves, and executed trade statistics.

---

## 4. Running Tests Locally

### Backend (apps/api)

Run the full backend test suite:
```bash
python -m pytest tests/ -q
```

Run specific test modules:
```bash
python -m pytest tests/unit/ai_research/ -v
python -m pytest tests/unit/regime_detection/ -v
python -m pytest tests/unit/portfolio_risk/ -v
python -m pytest tests/api/test_api_contracts_and_errors.py -v
```

Check code quality gates:
```bash
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app tests
```

Measure coverage:
```bash
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Frontend (apps/web)

Run unit and component state tests:
```bash
npm test
```

Run specific test suites:
```bash
node --no-warnings --loader ./tests/loader.mjs --test tests/accessibility.test.ts
node --no-warnings --loader ./tests/loader.mjs --test tests/component-states.test.ts
```

Check frontend quality gates:
```bash
npm run lint
npm run type-check
npm run build
```

---

## 5. End-to-End Critical Workflows (V22 Commit 02)

RegimeX features a deterministic, cross-layer workflow testing suite that exercises real application boundaries from API route to application service, domain engines, persistence fixtures, and frontend presentation contracts.

### 5.1 Architecture & Canonical Golden Fixtures

Critical workflows rely on canonical golden fixtures with fixed UTC timestamps and mathematical invariants:
- **Canonical Asset**: `SPY` (60 deterministic daily OHLCV bars spanning `2026-01-05T00:00:00Z` to `2026-03-05T00:00:00Z`).
- **Backend Provider**: `GoldenMarketDataProvider` (`apps/api/tests/fixtures/spy_golden_fixture.py`) serves deterministic bars, prevents external network access, and provides known mathematical outcomes for return (0.0048 daily / 0.145 cumulative), volatility (0.125 / 0.180), and regime classifications.
- **Frontend Fixtures**: `apps/web/tests/fixtures/golden-spy.fixture.ts` mirrors backend DTO contracts 1:1, guaranteeing contract integrity for headers, price charts, regime profiles, Markov transition matrices, risk tables, and backtesting equity curves.

### 5.2 Workflows Covered

1. **Workflow 1 — Market Intelligence**: Catalog retrieval, OHLCV time-series querying, regime evaluation, snapshot metrics, loading states, empty charts, and API error states.
2. **Workflow 2 — Regime Analytics**: Current regime summary, duration/frequency statistics, Markov transition probability matrices, transition entropy, and model methodology provenance.
3. **Workflow 3 — Risk Analysis**: Return distributions, annualized volatility, downside deviation, maximum drawdown, Parametric VaR, Historical VaR, Expected Shortfall (ES), and risk methodology audit trail.
4. **Workflow 4 — Backtesting**: Strategy execution (`BUY_AND_HOLD`, `REGIME_ADAPTIVE`), execution conventions (`CURRENT_CLOSE`, `NEXT_OPEN`), equity curve generation, fill logs, trade statistics, risk decomposition, and deterministic reporting.
5. **Workflow 5 — Authentication**: Complete security boundary: deterministic registration, credential validation, JWT token persistence, protected `/auth/me` access, token revocation on logout, and 401 unauthenticated enforcement.
6. **Workflow 6 — Grounded AI Research**: Query intake, intent routing, symbol extraction, evidence packet retrieval, grounded synthesis via deterministic mock model provider, citation chip generation, and evidence panel exploration.
7. **Workflow 7 — Model Explanation**: Dedicated `MODEL_EXPLANATION` intent processing, feature comparison, model confidence semantics, provenance display, and limitation disclosure.
8. **Workflow 8 — AI Safety Refusal**: Deterministic rejection of future price predictions and speculative financial advice without invoking LLMs or fabricating citations.
9. **Workflow 9 — AI Grounding Failure & Sanitization**: Detection and rejection of unsupported provider claims by `GroundingValidator`, falling back to safe deterministic responses without leaking hallucinations to the DOM.
10. **Workflow 10 — API Failure Recovery**: Dashboard-wide error states rendering user-safe messages, request IDs, and retry triggers that cleanly recover upon service restoration.
11. **Workflow 11 — Empty Data**: Valid symbols with zero observation bars render dedicated empty states without JavaScript errors or misleading zeroed charts.
12. **Workflow 12 — Unknown Market**: Early catalog verification rejecting unknown tickers with structured 404 responses before executing downstream providers.
13. **Workflow 13 — Permission Boundaries**: Strict distinction between public market analytics and protected user profile routes.
14. **Workflow 14 — Request Correlation**: Preservation of `X-Request-ID` correlation identifiers across requests and responses without leaking authorization tokens or secrets.
15. **Workflow 15 & 19 — Research SSE Streaming & Interruption**: Server-Sent Events delivering ordered metadata, token, and complete events, with graceful abort handling and connection recovery.
16. **Workflow 16 — Route Page Rendering**: Static verification ensuring critical routes (`/app`, `/app/markets`, `/app/regimes`, `/app/risk`, `/app/backtesting`, `/app/research`) render complete layouts without blank screens.
17. **Workflow 17 — Accessibility**: WCAG compliance verifying landmarks, headings, ARIA live regions, alert roles, and accessible button triggers.

### 5.3 Executing Workflow Tests

Run backend critical workflows:
```bash
cd apps/api
python -m pytest tests/workflows/test_critical_workflows.py -v
```

Run frontend critical workflows:
```bash
cd apps/web
node --no-warnings --loader ./tests/loader.mjs --test tests/critical-workflows.test.ts
```

---

## 6. Continuous Integration (CI) Expectations

Every commit on `main` and Pull Requests must satisfy all quality gates:
1. Backend test suite: 100% passing tests with zero regressions.
2. Backend static analysis: Ruff linter, Ruff formatting, and Mypy strict type checks passing.
3. Frontend test suite: 100% passing tests.
4. Frontend static analysis: ESLint, TypeScript compiler (`tsc --noEmit`), and Next.js production build (`next build`) passing.
5. Zero external network calls or live LLM dependencies during test execution.

