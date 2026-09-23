# Volume 16: Versioned FastAPI Platform

## 1. Executive Summary

Volume 16 establishes the production-grade, versioned **FastAPI HTTP Orchestration Platform** for the RegimeX quantitative intelligence engine.

Operating as the transport and presentation boundary over the existing RegimeX domain capabilities (market discovery, data quality, feature engineering, regime detection, risk analytics, event-driven backtesting, and performance comparison), Volume 16 provides an extensible, typed, and framework-isolated API foundation.

```text
HTTP Client (Web / CLI / Researcher)
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Application                  │
│                                                        │
│  • Request Correlation ID Middleware (X-Request-ID)     │
│  • CORS & Exception Mapping Handlers                   │
│  • OpenAPI Specification (/docs, /openapi.json)        │
│                                                        │
│  Root & Probes:                                        │
│    GET /          GET /health          GET /ready      │
│                                                        │
│  Versioned Boundary (/api/v1):                         │
│    GET /api/v1/markets                                 │
│    GET /api/v1/markets/{symbol}/data                   │
└──────────────────────────┬─────────────────────────────┘
                           │
       FastAPI Dependency Injection Boundary
         (MarketServiceDep, ReadinessCheckerDep)
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Application Service Layer                │
│                                                        │
│  • MarketDataService (Facade & Catalog)                │
│  • Pure Domain Interfaces (MarketDataProvider, etc.)   │
│  • Standard Domain Exceptions (ProviderError, etc.)    │
└────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Clean Architecture Boundary**:
> Domain layers (`app.modules.*.domain`) remain pure Python and completely framework-independent. Domain logic contains **zero imports** of `fastapi`, `starlette`, `HTTPException`, `Request`, or `Response`. The API layer acts solely as a translation boundary converting domain outputs and domain exceptions into typed HTTP contracts.

---

## 2. Commit Roadmap

| Commit | Type | Description | Status |
| :---: | :---: | :--- | :---: |
| **01** | `feat` | `feat(api): establish versioned FastAPI platform` | **DONE** |

---

## 3. Platform Architecture & Standards

### 3.1 Versioning Strategy
- All business and analytical endpoints are strictly scoped under the `/api/v1` URL prefix.
- Operational infrastructure probes (`/health`, `/ready`) and root metadata (`/`) are mounted at the top-level application root for standard Kubernetes/container orchestration integration, while backward-compatible aliases exist under `/api/v1/health`.
- OpenAPI schema is served at `/openapi.json` (with an alias at `/api/openapi.json`) and interactive documentation is available at `/docs`.

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
| `400` | `BAD_REQUEST` | Malformed parameters or syntax errors. |
| `401` | `AUTHENTICATION_REQUIRED` | Missing or invalid authentication credentials (deferred to V17). |
| `403` | `PERMISSION_DENIED` | Authenticated user lacks permission (deferred to V17). |
| `404` | `NOT_FOUND` / `PROVIDER_SYMBOL_NOT_FOUND` | Endpoint or financial instrument not found. |
| `409` | `CONFLICT` | Resource conflict or database constraint violation. |
| `422` | `VALIDATION_ERROR` / Domain Codes | Request schema failure or business invariant violation. |
| `429` | `RATE_LIMIT_EXCEEDED` / `PROVIDER_RATE_LIMIT` | Quota exceeded. |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server failure. Never leaks credentials, queries, or tracebacks. |
| `503` | `SERVICE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` | Degradation or failed readiness probe. |

### 3.4 Dependency Injection & Service Layer
- Route handlers never instantiate concrete infrastructure adapters directly.
- Standard FastAPI `Annotated` dependencies (e.g., `MarketServiceDep`, `ReadinessCheckerDep`) provide clean inversion of control, enabling seamless dependency overrides during integration and unit testing.

---

## 4. Endpoints Catalog

### 4.1 System & Observability
- `GET /`: Application identification, version, environment, and documentation links.
- `GET /health`: Liveness probe returning `200 OK` (`{"status": "ok"}`).
- `GET /ready`: Readiness probe returning `200 OK` when dependencies are healthy, or `503 Service Unavailable` with diagnostic check results when unhealthy.

### 4.2 Market Intelligence
- `GET /api/v1/markets`:
  - Discovers supported instruments across US equities, Indian equities, indices, and crypto.
  - Supports query parameter filtering: `?asset_class=crypto` (case-insensitive).
  - Deterministic pagination: `?limit=100&offset=0`.
- `GET /api/v1/markets/{symbol}/data`:
  - Retrieves chronological OHLCV time-series observations.
  - Enforces timezone-aware UTC datetime bounds (`start`, `end`).
  - Rejects naive timestamps, negative spans (`start >= end`), and unsupported intervals with `422 VALIDATION_ERROR`.
  - Rejects unknown tickers with `404 PROVIDER_SYMBOL_NOT_FOUND`.

---

## 5. Explicit Deferrals (Out of Scope for V16)

To maintain disciplined focus on platform foundation and quantitative analytics delivery:
- **Authentication & Authorization**: Deferred to **Volume 17** (JWT, OAuth2, API key management). No placeholder or insecure mock auth is implemented in V16.
- **WebSocket Streaming**: Real-time tick feeds remain deferred to subsequent streaming commits.
- **Frontend Integration**: Web application UI integration is deferred to Volume 17.

---

## 6. Verification & Quality Gates

The test suite in `apps/api/tests/api/` exercises the HTTP platform:
1. `test_app.py`: Application factory, OpenAPI metadata, root response.
2. `test_health.py`: Liveness probe contract.
3. `test_readiness.py`: Readiness probe contract, 200/503 states, dependency override verification.
4. `test_request_id.py`: Correlation ID generation, header echoing, and error propagation.
5. `test_errors.py`: Platform exception handling, domain translation, validation sanitization, and 500 safety.
6. `test_market_routes.py`: Market discovery, asset class filtering, OHLCV retrieval, datetime validation, pagination, and unknown symbol 404 translation.
7. `test_architecture.py`: Static AST scanning ensuring domain layers have zero web framework imports.
