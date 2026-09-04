# RegimeX End-to-End Tests

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Structure established. E2E tests added in V16+ (Platform Volume).

---

## Purpose

End-to-end tests verify complete user flows against a fully running RegimeX stack (API + frontend + database + Redis).

---

## Planned Tool Stack

- **Playwright** — browser automation for web UI flows
- **pytest** + **httpx** — API end-to-end flows

---

## Running E2E Tests

```bash
# Requires full stack running (use docker-compose)
docker compose up -d
cd tests/e2e
pytest -m e2e -v
```

---

## E2E Test Scope

E2E tests cover complete user workflows:
- User authentication flow (V15+)
- Market regime dashboard load (V16+)
- Strategy backtest submission and result retrieval (V11+)
- AI research query flow (V21+)

---

## Important Constraints

- E2E tests run against a dedicated test environment.
- They must NEVER run against production.
- E2E tests are run in CI on merge to `main` only (not on every PR).
