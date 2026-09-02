# API Contracts

**RegimeX — Open-Source Market Intelligence Platform**

> API contracts define the structural conventions for the RegimeX REST API. Implementation begins in V16. These contracts govern all API design decisions from V03 onward.

---

## Versioning Strategy

All RegimeX API endpoints are versioned using a URL path prefix.

```text
/api/v1/<resource>/<action>
```

**Rules:**
- The API version is always explicit in the URL — never implicit
- `v1` is the initial stable version
- Breaking changes to request or response schemas require a new version prefix (`v2`, `v3`)
- Non-breaking additions (new optional fields, new endpoints) do not require version bumps
- Deprecated versions will receive a minimum 6-month deprecation notice before removal
- `v1` and `v2` may coexist during transition periods

---

## Response Envelope

All successful API responses use a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO 8601 UTC",
    "api_version": "v1"
  }
}
```

List responses include pagination metadata:

```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO 8601 UTC",
    "api_version": "v1",
    "pagination": {
      "page": 1,
      "page_size": 100,
      "total_items": 2450,
      "total_pages": 25,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

---

## Error Model

All API errors use a consistent error response schema:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error description",
    "details": [ ... ],
    "request_id": "uuid",
    "timestamp": "ISO 8601 UTC",
    "documentation_url": "/api/v1/docs#errors"
  }
}
```

### Error Codes

| HTTP Status | Error Code | When Used |
|-------------|-----------|-----------|
| 400 | `VALIDATION_ERROR` | Request body or query parameter fails validation |
| 400 | `INVALID_SYMBOL` | Symbol not found in instrument catalogue |
| 400 | `INVALID_DATE_RANGE` | Start date is after end date, or range exceeds limits |
| 401 | `AUTHENTICATION_REQUIRED` | No credentials provided |
| 401 | `INVALID_CREDENTIALS` | API key or token is invalid or expired |
| 403 | `PERMISSION_DENIED` | Authenticated user lacks required role |
| 404 | `NOT_FOUND` | Requested resource does not exist |
| 409 | `CONFLICT` | Resource already exists (e.g., duplicate ingestion job) |
| 422 | `UNPROCESSABLE_REQUEST` | Request is well-formed but semantically invalid |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests from this client |
| 500 | `INTERNAL_ERROR` | Unexpected server error (always logged with `request_id`) |
| 503 | `SERVICE_UNAVAILABLE` | Upstream dependency (data provider, DB) is unavailable |

---

## Authentication Model

### API Key Authentication

```text
Authorization: ApiKey <api-key>
```

- API keys are issued per user account
- Keys have no expiry by default but can be revoked
- Keys are associated with a role: `public`, `researcher`, `admin`
- Keys are never returned in plaintext after creation (only the hash is stored)

### JWT Bearer Authentication (Web Platform)

```text
Authorization: Bearer <jwt-token>
```

- Used by the web platform for session-based access
- Tokens expire after a configurable duration (default: 1 hour)
- Refresh tokens are issued alongside access tokens
- Tokens are invalidated on logout

### Public Endpoints

The following endpoint categories are accessible without authentication:
- `GET /api/v1/instruments` — instrument catalogue
- `GET /api/v1/regime/current` — current regime for any instrument
- `GET /api/v1/regime/history` — regime history (last 90 days)
- `GET /api/v1/health` — service health check

---

## Rate Limiting Model

Rate limits are applied per authenticated user (by API key or JWT).

| Tier | Rate Limit | Burst |
|------|-----------|-------|
| Public (unauthenticated) | 30 requests/minute | 10 |
| Researcher | 300 requests/minute | 50 |
| Admin | 1000 requests/minute | 200 |

Rate limit headers are returned on every response:

```text
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 247
X-RateLimit-Reset: 1735689600
```

When a rate limit is exceeded, the API returns HTTP 429 with a `Retry-After` header.

---

## Endpoint Categories

> Endpoints are defined structurally here. Exact request/response schemas will be specified in V16.

### Market Discovery
```text
GET  /api/v1/instruments                    — List all supported instruments
GET  /api/v1/instruments/{symbol}           — Get instrument metadata
GET  /api/v1/instruments/search?q={query}   — Fuzzy search instruments
```

### Market Data
```text
GET  /api/v1/data/{symbol}/ohlcv            — Historical OHLCV data
GET  /api/v1/data/{symbol}/quality          — Data quality report
```

### Feature Engineering
```text
GET  /api/v1/features                       — List all registered features
GET  /api/v1/features/{feature_id}          — Feature documentation
GET  /api/v1/features/{feature_id}/values   — Computed feature values for a symbol
```

### Regime Detection
```text
GET  /api/v1/regime/algorithms              — List available detection algorithms
GET  /api/v1/regime/current/{symbol}        — Current regime for a symbol
GET  /api/v1/regime/history/{symbol}        — Regime history for a symbol
POST /api/v1/regime/detect                  — Run regime detection (async job)
GET  /api/v1/regime/runs/{run_id}           — Get detection run results
```

### Regime Intelligence
```text
GET  /api/v1/regime/transitions/{symbol}    — Regime transition matrix
GET  /api/v1/regime/stats/{symbol}          — Regime-conditional asset statistics
```

### Risk Analytics
```text
GET  /api/v1/risk/{symbol}/metrics          — Risk metrics for a symbol
GET  /api/v1/risk/{symbol}/regime-metrics   — Risk metrics by regime
```

### Backtesting
```text
POST /api/v1/backtest/run                   — Submit backtest job (async)
GET  /api/v1/backtest/runs/{backtest_id}    — Get backtest results
GET  /api/v1/backtest/runs                  — List user's backtest runs
```

### Platform
```text
GET  /api/v1/health                         — Service health
GET  /api/v1/ready                          — Service readiness
GET  /api/v1/docs                           — OpenAPI documentation (Swagger UI)
GET  /api/v1/openapi.json                   — OpenAPI schema
```

---

## Pagination

All list endpoints support pagination via query parameters:

```text
?page=1&page_size=100
```

- Default `page_size` is 100
- Maximum `page_size` is 1000
- Page is 1-indexed
- Total item counts are always returned

---

## Async Jobs

Long-running operations (regime detection, backtest execution) are submitted as async jobs:

1. Client submits `POST` request → receives `202 Accepted` with `job_id`
2. Client polls `GET /api/v1/jobs/{job_id}` for status
3. When `status = "completed"`, the result URL is included in the response
4. Jobs have a configurable TTL — results are retained for 24 hours by default

```json
{
  "job_id": "uuid",
  "status": "pending | running | completed | failed",
  "created_at": "ISO 8601 UTC",
  "completed_at": "ISO 8601 UTC | null",
  "result_url": "/api/v1/regime/runs/uuid | null",
  "error": "null | error message"
}
```
