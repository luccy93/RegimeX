# RegimeX Integration Tests

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Structure established. Tests added as infrastructure is wired in V05+.

---

## Purpose

Integration tests verify that multiple system components work correctly together — the API with the database, the worker with Redis, etc.

---

## When Tests Live Here vs `apps/api/tests/`

| Test Type | Location | Scope |
|-----------|----------|-------|
| Unit tests | `apps/api/tests/` | Single module, no external deps |
| API endpoint tests (mock deps) | `apps/api/tests/` | FastAPI TestClient |
| **Integration tests** | `tests/integration/` | Real database + Redis required |
| E2E tests | `tests/e2e/` | Running full stack required |

---

## Running Integration Tests

```bash
# Requires a running database and Redis (use docker-compose)
cd tests/integration
pytest -m integration -v
```

Integration tests require the `REGIMEX_ENV=test` environment and a test
database populated by migrations (V05+).

---

## Test Isolation Requirements

- Each test must create its own data fixtures.
- Tests must not depend on order of execution.
- Tests must clean up after themselves (or use transactions rolled back on teardown).
- Tests must NEVER run against the production database.
