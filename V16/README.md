# Volume 16: Versioned FastAPI Platform

## 1. Executive Summary

Volume 16 establishes the production-grade, versioned **FastAPI HTTP Orchestration Platform** for the RegimeX quantitative intelligence engine.

Operating as the transport and presentation boundary over the existing RegimeX domain capabilities (market discovery, data quality, feature engineering, regime detection, risk analytics, event-driven backtesting, and performance comparison), Volume 16 provides an extensible, typed, and framework-isolated API foundation.

```text
HTTP Request
     │
     ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Application                  │
│                                                        │
│  • Request Correlation ID Middleware (X-Request-ID)     │
│  • CORS & Domain Exception Mapping Handlers            │
│  • OpenAPI Specification (/docs, /openapi.json)        │
│                                                        │
│  Root & Probes:                                        │
│    GET /          GET /health          GET /ready      │
│                                                        │
│  Versioned Market & Intelligence Endpoints (/api/v1):  │
│    GET /api/v1/markets                                 │
│    GET /api/v1/markets/{symbol}/data                   │
│    GET /api/v1/markets/{symbol}/regime                 │
│    GET /api/v1/markets/{symbol}/regime/transitions     │
└──────────────────────────┬─────────────────────────────┘
                           │
       FastAPI Dependency Injection Boundary
       (MarketServiceDep, MarketIntelligenceDep, etc.)
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Application Facade Layer                 │
│                                                        │
│  • MarketDataService (Catalog & Historical OHLCV)      │
│  • MarketIntelligenceFacade (Regime & Transitions)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Existing Domain Protocols                │
│                                                        │
│  • FeaturePipeline & FeatureMatrixBuilder (V07)        │
│  • RegimeDetector & DetectionService (V08/V10/V11)     │
│  • RegimeIntelligenceService (V09)                     │
│  • RegimeTransitionAnalytics (V12)                     │
└────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Clean Architecture Boundary & Zero New Domain Algorithms**:
> V16 Commit 02 exposes existing RegimeX intelligence capabilities. It does not introduce new domain algorithms.
> Domain layers (`app.modules.*.domain`) remain pure Python and completely framework-independent. Domain logic contains **zero imports** of `fastapi`, `starlette`, `HTTPException`, `Request`, or `Response`. Routes contain **zero business or mathematical logic**; they perform only request parameter validation, service orchestration via dependency injection, and domain-to-DTO translation.

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(api): establish versioned FastAPI platform` | **DONE** |
| **02** | `feat` | `feat(api): expose market intelligence endpoints` | **DONE** |

---

## 3. Platform Architecture & Standards

### 3.1 Versioning Strategy
- All business, market data, and analytical endpoints are strictly scoped under the `/api/v1` URL prefix.
- Operational infrastructure probes (`/health`, `/ready`) and root metadata (`/`) are mounted at the top-level application root for standard Kubernetes/container orchestration integration, while backward-compatible aliases exist under `/api/v1/health`.
- OpenAPI schema is served dynamically at `/openapi.json` (with an alias at `/api/openapi.json`) and interactive documentation is available at `/docs`.

### 3.2 Request Correlation & Tracing
- Every HTTP interaction is tagged with a unique `X-Request-ID` header.
- If a client supplies an `X-Request-ID`, it is validated and propagated across the request context.
- If absent, a cryptographically secure UUID4 is generated.
- The correlation ID is attached to:
  - Outgoing HTTP response headers (`X-Request-ID`).
  - Structured application log records (`request.state.request_id`).
  - All API error response envelopes.

### 3.3 Uniform Error Schema: `ApiError`
All non-2xx responses adhere to an immutable, machine-readable envelope:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description of what failed.",
    "request_id": "00000000-0000-0000-0000-000000000000",
    "details": null
  }
}
```

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400` | `BAD_REQUEST` | Malformed parameters, syntax errors, or unfitted models. |
| `401` | `AUTHENTICATION_REQUIRED` | Missing or invalid authentication credentials (deferred to V17). |
| `403` | `PERMISSION_DENIED` | Authenticated user lacks permission (deferred to V17). |
| `404` | `NOT_FOUND` / `PROVIDER_SYMBOL_NOT_FOUND` | Endpoint or financial instrument not found. |
| `409` | `CONFLICT` | Resource conflict or database constraint violation. |
| `422` | `VALIDATION_ERROR` / Domain Invariant Codes | Query parameter failure, naive timestamps, date inversion, or insufficient observations. |
| `429` | `RATE_LIMIT_EXCEEDED` / `PROVIDER_RATE_LIMIT` | Quota exceeded. |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server failure. Never leaks credentials, queries, or tracebacks. |
| `503` | `SERVICE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` | External provider degradation or failed readiness probe. |

### 3.4 Dependency Injection & Service Layer
- Route handlers never instantiate concrete infrastructure adapters, providers, or ML engines directly.
- Standard FastAPI `Annotated` dependencies (e.g., `MarketServiceDep`, `MarketIntelligenceDep`, `ReadinessCheckerDep`) provide clean inversion of control, enabling seamless dependency overrides during integration and unit testing.

---

## 4. Endpoints Catalog

### 4.1 System & Observability
- `GET /`: Application identification, version, environment, and documentation links.
- `GET /health`: Liveness probe returning `200 OK` (`{"status": "ok"}`).
- `GET /ready`: Readiness probe returning `200 OK` when dependencies are healthy, or `503 Service Unavailable` with diagnostic check results when unhealthy.

### 4.2 Market Catalog & Data
- `GET /api/v1/markets`:
  - Discovers supported instruments across US equities, Indian equities, indices, and crypto from the registered provider catalog.
  - Supports query parameter filtering: `?asset_class=crypto` (case-insensitive).
  - Deterministic pagination: `?limit=100&offset=0` (bounded: `1 <= limit <= 1000`, `offset >= 0`).
  - Deterministic ordering by symbol ascending.
- `GET /api/v1/markets/{symbol}/data`:
  - Retrieves chronological OHLCV time-series observations.
  - Query parameters:
    - `start` (ISO 8601 UTC datetime, optional, default: 30 days ago)
    - `end` (ISO 8601 UTC datetime, optional, default: now UTC)
    - `interval` (Enum: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`, `1mo`, default: `1d`)
    - `limit` (int, default: 500, range: 1 to 5000)
    - `offset` (int, default: 0, range: >= 0)
  - Enforces timezone-aware UTC datetime bounds (`start < end`).
  - Rejects naive timestamps, negative spans (`start >= end`), and unsupported intervals with `422 VALIDATION_ERROR`.
  - Rejects unknown tickers with `404 PROVIDER_SYMBOL_NOT_FOUND`.
  - Preserves exact numeric precision and timezone offsets; returns empty list if no bars fall within range.

### 4.3 Regime Intelligence
- `GET /api/v1/markets/{symbol}/regime`:
  - Exposes read-oriented regime intelligence using existing V08 detection and V09 intelligence contracts.
  - Query parameters:
    - `start` (ISO 8601 UTC datetime, optional, default: 180 days ago)
    - `end` (ISO 8601 UTC datetime, optional, default: now UTC)
    - `interval` (Enum: `1d`, `1h`, etc., default: `1d`)
    - `n_regimes` (int, default: 3, range: 2 to 10)
    - `limit` (int, default: 500, range: 1 to 5000)
  - Orchestration:
    - Fetches market data via `MarketDataService`.
    - Generates standardized feature matrix via `FeaturePipeline` & `FeatureMatrixBuilder` (V07).
    - Detects regimes via `RegimeDetectionService` (V08).
    - Computes regime context, duration, profiles, and feature statistics via `RegimeIntelligenceService` (V09).
  - Response DTO (`MarketRegimeResponse`):
    - `symbol`, `interval`, `start_date`, `end_date`, `total_observations`
    - `current_regime`: `regime_id`, `regime_name`, `confidence`, `duration`, `start_timestamp`, `end_timestamp`
    - `profiles`: Map of `regime_id` -> `RegimeProfileDTO` (frequency, mean duration, max duration, total occurrences, percentage share)
    - `feature_statistics`: Map of `regime_id` -> list of `FeatureStatisticDTO` (mean, std, median, min, max, iqr, skewness)
  - Error Handling:
    - Unknown symbol: `404 PROVIDER_SYMBOL_NOT_FOUND`
    - Insufficient data (< minimum feature window): `422 INSUFFICIENT_REGIME_DATA`
    - Unfitted detector: `400 MODEL_NOT_FITTED`
    - Upstream failure: `503 SERVICE_UNAVAILABLE`

### 4.4 Regime Transition Analytics
- `GET /api/v1/markets/{symbol}/regime/transitions`:
  - Exposes read-only regime transition analytics using existing V12 transition engine and analytics contracts.
  - Query parameters:
    - `start` (ISO 8601 UTC datetime, optional, default: 180 days ago)
    - `end` (ISO 8601 UTC datetime, optional, default: now UTC)
    - `interval` (Enum: `1d`, `1h`, etc., default: `1d`)
    - `n_regimes` (int, default: 3, range: 2 to 10)
    - `limit` (int, default: 500, range: 1 to 5000)
  - Orchestration:
    - Fetches market data and generates regime classifications.
    - Analyzes transitions via `RegimeTransitionAnalytics` (V12).
  - Response DTO (`MarketTransitionResponse`):
    - `symbol`, `total_transitions`, `total_observations`
    - `transition_matrix`: Full NxN transition probability matrix with self-transitions (`P(j | i)`).
    - `transition_shift_matrix`: Zero-diagonal transition shift distribution matrix (`P(j | i, j != i)`).
    - `regime_analytics`: Map of `regime_id` -> `TransitionRegimeAnalyticsDTO` (persistence, exit probability, half-life, entropy, top destinations).
    - `global_analytics`: `GlobalTransitionAnalyticsDTO` (transition frequency, change rate, overall entropy, diversity index).
    - `probabilities`: Deterministically ordered list of all pairwise transition probabilities (`from_regime`, `to_regime`, `probability`, `sample_count`).

---

## 5. Scope & Status Breakdown

### 5.1 Implemented Capabilities
- Market catalog discovery (`GET /api/v1/markets`) with asset class filtering and bounded pagination.
- Historical market data retrieval (`GET /api/v1/markets/{symbol}/data`) with strict timezone-aware validation and deterministic ordering.
- Regime intelligence endpoint (`GET /api/v1/markets/{symbol}/regime`) orchestrating V07/V08/V09 contracts.
- Regime transition analytics endpoint (`GET /api/v1/markets/{symbol}/regime/transitions`) orchestrating V12 analytics contracts.
- Complete domain-to-DTO translation layer preserving internal domain purity.
- Application facade (`MarketIntelligenceFacade`) maintaining clean architecture.
- Full OpenAPI / Swagger documentation at `/openapi.json` and `/docs`.
- Comprehensive API and facade regression test suite (62 API tests, 1179 total tests passing).

### 5.2 Deferred Capabilities
- **Risk Endpoint (`GET /api/v1/markets/{symbol}/risk`)**:
  - *Status*: **Deferred**.
  - *Rationale*: Not implemented because the existing application/domain layer does not currently provide a suitable contract. Specifically, V13 `portfolio_risk` provides numerical calculation engines and domain models, but lacks an application service or facade for single-market HTTP data routing. Creating such an abstraction would violate the strict scope rule against inventing new application layers in route handlers.
- **Backtest Endpoint (`GET /api/v1/markets/{symbol}/backtest`)**:
  - *Status*: **Deferred**.
  - *Rationale*: Not implemented because the existing application/domain layer does not currently provide a suitable contract. Specifically, V14/V15 backtesting contracts require full simulation configurations, accounts, data feeds, and execution engines without an existing read-oriented application service.

### 5.3 Out of Scope
- Authentication & authorization (JWT, OAuth2, API keys) — strictly scheduled for **Volume 17**.
- User account management and rate limiting.
- Frontend UI components or modifications (scheduled for Volumes 18 & 19).
- WebSocket streaming and real-time live trading / broker execution.
- Optimization sweeps and new machine learning algorithms.

---

## 6. Verification & Quality Gates

The test suite exercises the HTTP platform and intelligence endpoints:
1. `test_app.py`: Application factory, OpenAPI metadata, root response, schema verification for all versioned endpoints.
2. `test_health.py`: Liveness probe contract.
3. `test_readiness.py`: Readiness probe contract, 200/503 states, dependency override verification.
4. `test_request_id.py`: Correlation ID generation, header echoing, and error propagation.
5. `test_errors.py`: Platform exception handling, domain translation, validation sanitization, and 500 safety.
6. `test_market_routes.py`: Market discovery, asset class filtering, empty catalog, OHLCV retrieval, datetime validation, pagination bounds, unknown symbol 404 translation, and deterministic ordering.
7. `test_regime_routes.py`: Regime intelligence retrieval, default date bounds, domain-to-DTO conversion, model not fitted handling, service unavailable handling, 404 symbol not found, 422 insufficient data, and dependency injection overrides.
8. `test_transition_routes.py`: Transition analytics retrieval, transition matrices, shift matrices, persistence metrics, parameter validation, deterministic ordering, and dependency injection overrides.
9. `test_architecture.py`: Static AST scanning verifying:
   - Domain layers have zero web framework imports (`fastapi`, `starlette`).
   - Route handlers never import ML engines (`sklearn`, `scipy`, `numpy`, `torch`) or detector implementations directly.
10. `test_facade.py`: Unit test suite verifying end-to-end orchestration of V07, V08, V09, and V12 domain contracts by `MarketIntelligenceFacade`.
