# Development Guide

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

This document defines the engineering workflow for RegimeX. All contributors — core maintainers and community contributors alike — are expected to follow these conventions.

Consistent workflow practices enable RegimeX to remain a high-quality, well-understood codebase as it grows across 30 development volumes and an open-source community.

---

## Git Strategy

RegimeX uses a structured branching model designed for a project that progresses through defined development volumes with clear validation gates.

### Branches

```text
main
develop
feature/*
fix/*
refactor/*
docs/*
```

---

#### `main`

The **production branch**. Contains only code that has been:

- Fully implemented across a complete volume
- Validated against the volume's quality gates
- Reviewed and merged from `develop`

**Rules:**
- Direct commits to `main` are never permitted
- All merges into `main` come from `develop` via pull request
- Every merge to `main` is tagged with a version or volume identifier
- `main` is always deployable

---

#### `develop`

The **integration branch**. Contains completed, validated work from individual volume feature branches.

**Rules:**
- Direct commits to `develop` are never permitted (except emergency fixes reviewed by a maintainer)
- Work is integrated from `feature/*`, `fix/*`, `refactor/*`, and `docs/*` branches via pull request
- `develop` should always be in a passing state (CI green)
- At the end of each volume, `develop` is merged into `main`

---

#### `feature/*`

Used for all new capability implementation work within a volume.

**Naming pattern:**
```text
feature/v05-market-data-provider-abstraction
feature/v08-hmm-regime-detector
feature/v14-backtesting-event-loop
```

**Rules:**
- Branched from `develop`
- Merged back into `develop` via pull request
- One feature branch per discrete capability or module
- Should not contain unrelated changes

---

#### `fix/*`

Used for bug fixes discovered during development or after release.

**Naming pattern:**
```text
fix/v06-data-gap-detection-edge-case
fix/v16-api-symbol-validation-error
fix/v17-jwt-expiry-not-enforced
```

**Rules:**
- Critical fixes on `develop`: branched from `develop`, merged back into `develop`
- Hotfixes on `main` (production): branched from `main`, merged into both `main` and `develop`

---

#### `refactor/*`

Used for restructuring existing code without changing external behavior.

**Naming pattern:**
```text
refactor/v07-feature-registry-cleanup
refactor/v13-risk-engine-module-split
```

**Rules:**
- Must have test coverage proving no behavior change
- Must not expand scope to new features

---

#### `docs/*`

Used for documentation-only changes: README updates, guide revisions, ADRs, docstring improvements.

**Naming pattern:**
```text
docs/v01-product-roadmap
docs/v03-architecture-decision-adr-0001
docs/contributing-guide-update
```

**Rules:**
- Does not require the same quality gates as implementation branches
- Still requires CI to pass (Markdown lint, link checks)

---

## Commit Convention

RegimeX uses **Conventional Commits** (https://www.conventionalcommits.org/).

Every commit message must follow this format:

```text
<type>(<scope>): <short imperative description>
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New capability or feature |
| `fix` | Bug fix |
| `docs` | Documentation only change |
| `test` | Test additions or corrections |
| `refactor` | Code restructure without behavior change |
| `chore` | Build, CI, tooling, dependency management |
| `style` | Formatting, whitespace (no logic change) |
| `perf` | Performance improvement |
| `revert` | Reverts a prior commit |

### Scopes

Scopes identify the RegimeX module or area being changed. Use consistent, lowercase scope names.

**Examples:** `data`, `features`, `regime`, `risk`, `backtest`, `api`, `auth`, `web`, `ai`, `ci`, `docs`, `config`, `sdk`

### Commit Message Examples

```text
feat(data): add MarketDataProvider abstract interface
feat(regime): implement HMM regime detector
feat(risk): add regime-conditional VaR computation
feat(api): add /v1/regime/current endpoint
feat(auth): implement JWT authentication middleware
feat(web): add regime timeline chart component

fix(data): handle missing OHLCV bars in gap detection
fix(api): return 422 for invalid market symbol input
fix(regime): correct off-by-one in HMM state sequence
fix(risk): clamp CVaR computation at confidence bounds

docs(architecture): document data pipeline flow
docs(contributing): add algorithm contribution guide
docs(api): update endpoint examples in OpenAPI spec

test(backtest): add execution integrity tests for limit orders
test(regime): add look-ahead bias detection tests
test(risk): validate VaR against analytical Gaussian result

refactor(features): extract feature registry into separate module
refactor(data): split provider adapter from ingestion pipeline

chore(ci): configure GitHub Actions lint and test pipeline
chore(deps): update FastAPI to 0.115.x
chore(docker): optimize API service multi-stage build
```

### Rules

- Subject line: imperative mood, lowercase, no period at the end
- Maximum 72 characters for the subject line
- Body (optional): explain *why*, not *what* — the diff shows what
- Breaking changes: append `!` after type/scope and include `BREAKING CHANGE:` in the body

```text
feat(api)!: rename /regime/detect to /regime/analyze

BREAKING CHANGE: The /v1/regime/detect endpoint has been renamed
to /v1/regime/analyze for consistency with other analytics endpoints.
Callers must update their integrations.
```

---

## Volume Rule

Every development volume in RegimeX **must** contain exactly **two meaningful commits** before the volume is pushed.

### Why Two Commits Per Volume?

Two commits enforce a discipline of **build, then validate**:

- **Commit 01** — core implementation of the volume's objective
- **Commit 02** — validation, documentation, tests, and polish that make the implementation production-ready

This is not an arbitrary rule. It prevents the common failure mode of shipping implementation without validation, or validating without a clear record of what was implemented.

### Volume Commit Structure

| Commit | Focus |
|--------|-------|
| Commit 01 | Core implementation, scaffolding, primary capabilities |
| Commit 02 | Validation, documentation, tests, quality gate passage, consistency review |

### Examples

```text
# V05 — Market Data Engine
Commit 01: feat(data): implement MarketDataProvider interface and OHLCV schema
Commit 02: test(data): add provider integration tests and data quality validation

# V08 — Baseline Regime Engine
Commit 01: feat(regime): implement HMM regime detector and detection pipeline
Commit 02: test(regime): add regime detector tests and interface compliance suite

# V14 — Backtesting Engine
Commit 01: feat(backtest): implement event-driven simulation loop and strategy interface
Commit 02: test(backtest): add execution integrity tests and walk-forward validation
```

---

## Development Sequence

Every volume follows this exact sequence. No steps are skipped.

```text
┌──────────────────────────────────────┐
│           Start Volume N             │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Branch: feature/vNN-description     │
│  from develop                        │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Commit 01                           │
│  Core implementation                 │
│  (feat / docs / chore)               │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Validation 01                       │
│  - Run quality gates                 │
│  - Fix issues found                  │
│  - Verify scope                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Commit 02                           │
│  Validation, tests, documentation,   │
│  polish, consistency check           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Validation 02                       │
│  - All quality gates pass            │
│  - No regressions                    │
│  - Git status clean                  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Open Pull Request                   │
│  feature/vNN → develop               │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Review & Merge to develop           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  git push (develop)                  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  At volume completion:               │
│  Merge develop → main                │
│  Tag release                         │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Start Volume N+1                    │
└──────────────────────────────────────┘
```

### Rules

- **Never skip validation steps.** A commit that does not pass quality gates is not done.
- **Never start the next volume before the current volume passes all quality gates and is pushed.**
- **Never combine two volumes' work in a single branch.** Volume scope is enforced at the branch level.
- **Git status must be clean** (no untracked or modified files) before pushing.

---

## Quality Gates

Every implementation volume (V04 and later) must pass these quality gates before Commit 02 is created.

Quality gate tooling is configured in V04 — Monorepo Engineering Foundation. The gates below define what must pass; tooling specifics will be documented in V04.

### Formatting

```text
# All files must pass formatter without changes
make format-check
```

Code formatting must be deterministic. Files that require formatting changes have not passed this gate.

### Linting

```text
# No lint errors permitted
make lint
```

Lint warnings may be reviewed case-by-case; lint errors block the commit.

### Type Checking

```text
# No type errors on typed modules
make typecheck
```

Applies to all modules that use type annotations (all core modules in RegimeX).

### Unit Tests

```text
# All unit tests must pass
make test
```

No unit test failures are permitted. Flaky tests must be fixed or removed before the volume is closed.

### Integration Tests (where applicable)

```text
# Integration tests pass (may require test environment)
make test-integration
```

Integration tests that require external services (databases, market data providers) must pass in the CI integration test environment.

### Security Checks (where applicable)

```text
# Dependency vulnerability scan
make security-check
```

High or critical severity vulnerabilities in dependencies must be resolved before the volume is closed.

### Documentation Updates

All new modules, interfaces, and endpoints introduced in a volume must have:
- Module-level docstrings
- Public function/method docstrings
- Updated README or guide if the volume changes developer-facing behavior

Documentation is verified as part of CI.

### Git Status Verification

```text
git status
```

Before pushing, git status must report:
```text
On branch <current-branch>
nothing to commit, working tree clean
```

No untracked files, modified files, or staged changes may remain.

---

## Volume Scope Discipline

Every volume has a defined objective and scope. Scope discipline is enforced at the branch and commit level.

**If work discovered during a volume is clearly out of scope for that volume:**
1. Create a GitHub Issue describing the out-of-scope work
2. Label it with the appropriate future volume
3. Do not implement it in the current volume
4. Continue with the current volume's defined scope

**If a scope decision has architectural implications:**
1. Document it as an ADR before implementing
2. Get maintainer review if it affects module interfaces

---

## Local Development Workflow

Once V04 is complete, the standard local development workflow will be:

```bash
# Clone and set up
git clone https://github.com/luccy93/RegimeX
cd RegimeX
make setup            # Install dependencies, configure environment

# Create a feature branch
git checkout develop
git pull origin develop
git checkout -b feature/vNN-description

# Develop
# ... make changes ...

# Quality gate check (run before every commit)
make lint
make typecheck
make test

# Commit (using conventional commit format)
git add -A
git commit -m "feat(scope): description"

# Push and open PR
git push origin feature/vNN-description
# Open PR: feature/vNN-description → develop
```

> This workflow will be fully functional from V04 onward. V01–V03 are documentation-only volumes with no application code.

---

## Versioning

RegimeX uses **Semantic Versioning** (https://semver.org/):

```text
MAJOR.MINOR.PATCH
```

| Increment | When |
|-----------|------|
| MAJOR | Breaking changes to public API contracts |
| MINOR | New backward-compatible capabilities |
| PATCH | Backward-compatible bug fixes |

Pre-1.0: versions are `0.x.y` — minor versions may include breaking changes with documented migration paths.

RegimeX **1.0.0** is the target of **V30 — RegimeX 1.0 Release**.
