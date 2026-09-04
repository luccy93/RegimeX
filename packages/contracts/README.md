# RegimeX Shared Contracts

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Structure established. Types populated in their respective volumes.

---

## Purpose

This package contains **shared type contracts** between the RegimeX backend API and the Next.js web frontend.

Contracts are types and schemas that both sides of the API boundary must agree on.

---

## What Belongs Here

| Category | Examples | Notes |
|----------|----------|-------|
| **API envelope types** | `ApiEnvelope<T>`, `ApiError` | Standard response shape |
| **Shared enumerations** | `AssetClass`, `RegimeLabel` | Values used on both sides |
| **Shared identifier types** | `InstrumentId`, `RunId` | String-branded types |
| **Versioned request/response shapes** | Health response schemas | Only genuinely shared ones |

---

## What Does NOT Belong Here

| Category | Correct Location | Reason |
|----------|-----------------|--------|
| Database models | `apps/api/app/modules/*/infrastructure/` | Backend-only persistence |
| SQLAlchemy schemas | `apps/api/app/modules/*/infrastructure/` | Backend-only ORM |
| Pydantic domain entities | `apps/api/app/modules/*/domain/` | Backend business rules |
| UI component props | `apps/web/components/` | Frontend-only |
| Next.js page state | `apps/web/app/` | Frontend-only |
| Raw market data arrays | `apps/api/app/modules/market_data/` | Backend-only domain |

---

## Ownership Rules

1. **Backend owns the authoritative definition.** Python Pydantic schemas are the source of truth.
2. **Frontend types are derived.** TypeScript types in `src/` mirror the Python schemas.
3. **Changes require both sides updated.** Never update one without updating the other.
4. **Versioning follows the API version.** Breaking changes increment the API version.
5. **This package must never import from apps/.** It has no runtime dependencies on application code.

---

## Versioning Expectations

- V04: Structure established, minimal types (API envelope only).
- V05+: Instrument types, OHLCV response shapes added as market data API is built.
- V08+: Regime label types, regime response shapes added.
- V10+: Risk metric response shapes added.
- V15+: User identity types, authentication response shapes added.

---

## Structure

```text
packages/contracts/
├── README.md              ← This file
└── src/
    └── index.ts           ← Exported contract types (start here)
```
