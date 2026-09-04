# RegimeX Scripts

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Structure established. Scripts added as needs emerge.

---

## Purpose

The `scripts/` directory contains operational scripts for:

- Local development setup helpers
- Database migration helpers (V05+)
- Seed data generation (V05+)
- CI/CD utility scripts
- Release automation

---

## Naming Conventions

Scripts follow a `verb-noun` kebab-case naming pattern:
- `setup-dev.sh` — Set up the local development environment
- `run-migrations.sh` — Apply database migrations
- `seed-test-data.sh` — Seed test database with fixture data
- `check-secrets.sh` — Verify no secrets are committed (CI gate)

---

## Rules

- Scripts must be executable and self-documented (include a usage comment block).
- Scripts must never hardcode credentials.
- Scripts must fail loudly and early if required environment variables are missing.
- Destructive scripts (data deletion, database resets) must prompt for confirmation.
