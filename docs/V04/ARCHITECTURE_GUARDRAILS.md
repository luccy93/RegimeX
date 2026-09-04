# RegimeX — Architectural Guardrails

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Authoritative. All contributors must follow these rules.

---

## Purpose

These guardrails prevent architectural drift as RegimeX grows and the contributor base expands. They are lightweight, maintainable conventions — not an overly complex dependency enforcement framework.

> For the full architecture rationale behind these rules, see [`V03/ARCHITECTURE.md`](../../V03/ARCHITECTURE.md) and [`V03/MODULE_BOUNDARIES.md`](../../V03/MODULE_BOUNDARIES.md).

---

## Rule 1 — Domain modules must not depend on UI code

**Prohibited:**
```python
# apps/api/app/modules/regime_detection/domain/detector.py
from apps.web import ...  # NEVER
import nextjs_stuff        # NEVER
```

**Why:** Domain logic is pure Python, independent of web frameworks, HTTP, or frontend code. This preserves testability and allows domain logic to be used by API endpoints, Celery workers, and CLIs alike.

---

## Rule 2 — Frontend must not access the database directly

**Prohibited:**
```typescript
// apps/web/app/page.tsx
import { db } from "../../../apps/api/app/core/database"  // NEVER
import postgres from "postgres"  // NEVER — no database client in web
```

**Required:**
```typescript
// apps/web/app/page.tsx
import { healthApi } from "@/lib/api-client"  // ✅ All backend access via API client
```

**Why:** The web frontend is a pure HTTP client. All data comes through the FastAPI layer, which enforces authentication, authorization, and rate limiting.

---

## Rule 3 — Backend modules must respect module boundaries

**Prohibited:**
```python
# regime_detection domain importing from backtesting infrastructure
from app.modules.backtesting.infrastructure.repository import BacktestRepository  # NEVER
```

**Required:**
```python
# regime_detection domain using only its defined interface
from app.modules.regime_detection.domain.detector import RegimeDetector  # ✅
```

**Dependency direction is strictly inward:**
```
api → application → domain
infrastructure → domain (via interfaces)
```

Circular imports between modules are strictly forbidden.

---

## Rule 4 — Secrets must never be committed

**Prohibited files to commit:**
- `.env`
- `.env.local`
- `.env.production`
- Any file containing: database passwords, API keys, JWT secrets, private keys

**Required:**
- Use `.env.example` files as configuration contracts (these ARE committed).
- Inject real credentials via CI/CD secrets, Docker secrets, or environment injection.
- If you accidentally commit a secret: rotate it immediately, then remove it from history.

**Verification command:**
```bash
# Scan for common secret patterns before committing:
git diff --cached | grep -E "(password|secret|api_key|token)" --color
```

---

## Rule 5 — Contracts must remain intentional

**Prohibited:**
```typescript
// packages/contracts/src/index.ts
export interface SQLAlchemyORM { ... }  // NEVER — backend-only
export interface ReactComponentProps { ... }  // NEVER — frontend-only
export interface DatabaseRow { ... }  // NEVER — infrastructure concern
```

`packages/contracts/` is for types that **genuinely must cross the API boundary**. See [`packages/contracts/README.md`](../../packages/contracts/README.md).

**Decision rule:** If the frontend doesn't need to parse it, it does not belong in contracts.

---

## Rule 6 — Infrastructure concerns must not leak into domain logic

**Prohibited:**
```python
# apps/api/app/modules/regime_detection/domain/detector.py
from sqlalchemy import select  # NEVER — SQL in domain logic
import redis  # NEVER — cache client in domain logic
import httpx  # NEVER — HTTP client in domain logic
```

**Required pattern:**
```python
# Domain defines the interface:
class RegimeDetectionRepository(Protocol):
    async def save_model(self, model: TrainedModel) -> None: ...

# Infrastructure implements it:
class PostgresRegimeDetectionRepository:
    async def save_model(self, model: TrainedModel) -> None:
        # SQLAlchemy code lives here, not in domain
        ...
```

---

## Rule 7 — Future providers and models must use abstraction boundaries

**Prohibited:**
```python
# Hardcoding a specific data provider in domain logic
from yfinance import download  # NEVER in domain
from openai import OpenAI  # NEVER in domain
```

**Required:**
```python
# Domain uses provider-agnostic interfaces (V03/ADR-0002, ADR-0004)
class MarketDataProvider(Protocol):
    async def fetch(self, symbol: str, start: date, end: date) -> list[OHLCVRecord]: ...
```

Provider-specific implementations (Yahoo Finance, Alpha Vantage, OpenAI, Anthropic) live exclusively in `infrastructure/` sub-packages and are injected via dependency injection.

---

## Rule 8 — API layer contains no business logic

**Prohibited:**
```python
# apps/api/app/api/v1/endpoints/regime.py
@router.get("/regime/{symbol}")
async def get_regime(symbol: str):
    # Computing regime math directly in the endpoint — NEVER
    features = compute_rsi(symbol)
    regime = kmeans_model.predict(features)
    return regime
```

**Required:**
```python
@router.get("/regime/{symbol}")
async def get_regime(symbol: str, service: RegimeDetectionService = Depends(...)):
    # Delegate ALL computation to domain/application layer
    return await service.get_current_regime(symbol)
```

---

## Enforcement

In V04, these rules are enforced by convention and code review.

V04 Commit 02 will introduce automated quality gates:
- Ruff linting (import order, style)
- mypy type checking
- Import boundary validation (planned for CI in a future volume)

---

## Quick Reference Card

| ❌ Never | ✅ Instead |
|---------|----------|
| SQL/ORM in domain modules | Use repository interfaces |
| Database client in frontend | Use `api-client.ts` |
| Hardcoded credentials | Environment variables |
| Provider SDK in domain | Use provider interface |
| Business logic in API routes | Delegate to application services |
| Types crossing boundaries without a contract | Add to `packages/contracts/` with rationale |
| Circular module imports | Restructure using interfaces |
