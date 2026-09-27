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

## 5. Continuous Integration (CI) Expectations

Every commit on `main` and Pull Requests must satisfy all quality gates:
1. Backend test suite: 100% passing tests with zero regressions.
2. Backend static analysis: Ruff linter, Ruff formatting, and Mypy strict type checks passing.
3. Frontend test suite: 100% passing tests.
4. Frontend static analysis: ESLint, TypeScript compiler (`tsc --noEmit`), and Next.js production build (`next build`) passing.
