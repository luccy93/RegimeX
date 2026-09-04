## Description

<!-- Describe what this PR does and why. Be specific. -->

## Related

<!-- Link issues, ADRs, or context this PR relates to. -->
<!-- Example: Implements V05 / Closes #42 -->

## Type of Change

<!-- Mark the appropriate option with [x] -->

- [ ] 🔧 Chore / tooling
- [ ] 📖 Documentation
- [ ] ✨ New feature
- [ ] 🐛 Bug fix
- [ ] ♻️ Refactor
- [ ] 🧪 Test improvement
- [ ] 🚨 Security fix

## Quality Gate Checklist

All items must be complete before requesting review.

**Backend (if applicable)**

- [ ] `ruff check app/ tests/` — lint clean
- [ ] `ruff format --check app/ tests/` — format clean
- [ ] `mypy app/` — type check passes
- [ ] `pytest tests/ -v` — all tests pass

**Frontend (if applicable)**

- [ ] `npm run lint` — ESLint clean
- [ ] `npm run type-check` — TypeScript clean

**General**

- [ ] No secrets, credentials, or API keys committed
- [ ] No `.env` files committed
- [ ] No `node_modules/`, `__pycache__/`, or build artefacts committed
- [ ] V01–V03 architecture documentation is not modified (unless this is a doc PR)
- [ ] Domain module boundaries respected (see `docs/V04/ARCHITECTURE_GUARDRAILS.md`)

## Architectural Guardrails

Confirm none of the following guardrails are violated:

- [ ] No database/ORM code in domain modules
- [ ] No business logic in API routes (delegated to application services)
- [ ] No hardcoded credentials or provider-specific secrets
- [ ] Frontend does not access the database directly
- [ ] Cross-boundary types added to `packages/contracts/` with justification
- [ ] Module imports respect the inward-only dependency direction

## Testing Notes

<!-- Describe how this was tested. What scenarios were covered? -->
<!-- If tests are not added, explain why. -->

---

> **Reminder:** Use `bash scripts/quality-check.sh` or `make quality`
> to run the full local quality gate before requesting review.
