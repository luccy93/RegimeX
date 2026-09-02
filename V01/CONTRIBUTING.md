# Contributing to RegimeX

**RegimeX — Open-Source Market Intelligence Platform**

---

Thank you for your interest in contributing to RegimeX. RegimeX is an open-source project and contributions from the community are what make it better.

This guide explains how to contribute effectively — whether you are fixing a bug, contributing a new regime detection algorithm, improving documentation, or proposing a new feature.

> **Note:** RegimeX is in its early foundation phase (V01). Contribution workflows involving source code will be fully operational from V04 onward, once the monorepo engineering foundation is established. This guide is written to reflect the intended state for open contributions.

---

## Project Introduction

RegimeX is an open-source platform for market data intelligence, quantitative feature engineering, market regime detection, regime transition analysis, risk analytics, historical backtesting, and grounded AI-assisted quantitative research.

The platform is designed for quantitative researchers, market analysts, developers, and public users who want to understand market regimes — what they are, how they evolve, and what risks they carry.

RegimeX is **not** a trading bot, financial advisor, or stock prediction service.

For full project context, read:
- [`V01/PRODUCT_FOUNDATION.md`](./PRODUCT_FOUNDATION.md) — product vision and positioning
- [`V01/PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) — scope boundaries
- [`V01/PRINCIPLES.md`](./PRINCIPLES.md) — product and engineering principles

---

## Who Can Contribute

Anyone may contribute to RegimeX. There are no prerequisites beyond a willingness to engage with the project's principles and follow the contribution workflow described in this guide.

Valuable contributions include:

- Bug reports and bug fixes
- New regime detection algorithm implementations
- New market data provider adapters
- New quantitative feature implementations
- Documentation improvements
- Test coverage improvements
- Performance optimizations
- Accessibility improvements
- Translation and internationalization
- Community support (answering issues, reviewing PRs)

---

## Before You Start

1. **Read the principles.** RegimeX has explicit product and engineering principles in [`PRINCIPLES.md`](./PRINCIPLES.md). All contributions must align with these principles — especially no look-ahead bias, no data leakage, and explainability over black-box claims.

2. **Check existing issues.** Before starting work, search GitHub Issues to see if the bug or feature has already been reported or is being worked on.

3. **Open an issue first for significant changes.** If you are planning a non-trivial contribution (new algorithm, new provider, new module), open a GitHub Issue describing what you intend to build before starting work. This avoids duplicate effort and ensures alignment with the project roadmap.

4. **Review the roadmap.** Understand where your contribution fits in the 30-volume development plan: [`V01/PRODUCT_ROADMAP.md`](./PRODUCT_ROADMAP.md).

---

## Development Workflow

RegimeX uses a structured development workflow. Follow these steps for all code contributions.

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/<your-username>/RegimeX.git
cd RegimeX
```

### 2. Set Up Your Environment

```bash
# Full setup instructions will be available from V04 onward
make setup
```

### 3. Create a Branch

Branch from `develop`:

```bash
git checkout develop
git pull upstream develop
git checkout -b <branch-type>/<description>
```

See [Branch Naming](#branch-naming) below for naming conventions.

### 4. Make Your Changes

Follow the coding standards and quality requirements described in [`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md).

### 5. Run Quality Gates

Before committing, run all applicable quality checks:

```bash
make format-check   # Formatting
make lint           # Linting
make typecheck      # Type checking
make test           # Unit tests
```

All checks must pass. Do not submit a PR with failing checks.

### 6. Commit Your Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```text
<type>(<scope>): <short description>
```

Examples:
```text
feat(regime): add BOCPD changepoint regime detector
fix(data): handle missing bars in OHLCV gap detection
docs(api): document /v1/regime/history endpoint
test(features): add look-ahead bias tests for ATR feature
```

### 7. Push and Open a Pull Request

```bash
git push origin <your-branch>
```

Open a pull request from your branch to `develop` (not `main`).

Fill in the pull request template completely.

---

## Branch Naming

| Branch Type | Pattern | Example |
|-------------|---------|---------|
| Feature | `feature/<description>` | `feature/bocpd-regime-detector` |
| Bug fix | `fix/<description>` | `fix/ohlcv-gap-detection` |
| Refactor | `refactor/<description>` | `refactor/feature-registry-split` |
| Documentation | `docs/<description>` | `docs/api-endpoint-examples` |

Rules:
- Use lowercase only
- Use hyphens, not underscores or spaces
- Keep names concise but descriptive

---

## Commit Conventions

RegimeX uses **Conventional Commits**. Every commit must follow the format:

```text
<type>(<scope>): <description>
```

### Types

| Type | Purpose |
|------|---------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `test` | Test additions or fixes |
| `refactor` | Code restructure, no behavior change |
| `chore` | Build, CI, tooling, dependencies |
| `style` | Formatting, no logic change |
| `perf` | Performance improvement |
| `revert` | Reverts a prior commit |

### Scopes

Use the module or area being changed: `data`, `features`, `regime`, `risk`, `backtest`, `api`, `auth`, `web`, `ai`, `ci`, `docs`, `sdk`, `config`.

### Rules

- Imperative mood: "add", "fix", "update" — not "added", "fixed", "updating"
- No capital letter at start of description
- No period at end
- Maximum 72 characters in subject line

---

## Pull Requests

### Requirements

Every pull request must:

- Target the `develop` branch (never `main` directly)
- Pass all CI checks (lint, type check, tests, formatting)
- Include a clear description of what was changed and why
- Reference related GitHub issues (`Closes #123`, `Related to #456`)
- Include tests for any new functionality or bug fixes
- Include documentation updates for any new capabilities

### Review Process

- At least one maintainer review is required before merge
- All CI checks must be green
- Reviewers may request changes — address feedback completely before re-requesting review
- Once approved and CI is green, a maintainer will merge the PR

### PR Template

When opening a PR, fill in:
- **Summary:** What does this PR do?
- **Motivation:** Why is this change needed?
- **Type of change:** Feature / Bug fix / Documentation / Refactor / Other
- **Related issues:** Links to related GitHub Issues
- **Testing:** How was this tested?
- **Checklist:** Confirm quality gates passed, documentation updated, etc.

---

## Issues

### Reporting Bugs

When reporting a bug, include:

1. **Description:** Clear description of the unexpected behavior
2. **Steps to reproduce:** Exact sequence of steps to trigger the bug
3. **Expected behavior:** What should have happened
4. **Actual behavior:** What actually happened
5. **Environment:** OS, Python version, RegimeX version
6. **Logs / error output:** Relevant stack traces or error messages

### Requesting Features

When requesting a feature:

1. **Problem statement:** What problem does this solve?
2. **Proposed solution:** What capability would you like to see?
3. **Alternatives considered:** What else did you consider?
4. **Scope check:** Does this fit within RegimeX's stated scope? (See [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md))

### Proposing New Algorithms

When proposing a new regime detection algorithm or quantitative feature:

1. **Algorithm description:** What is the algorithm and how does it work?
2. **Academic reference:** Cite the paper or standard reference where applicable
3. **Assumptions:** What assumptions does the algorithm make about market data?
4. **Limitations:** What does the algorithm not handle well?
5. **Interface compliance:** How will the implementation conform to the `RegimeDetector` or `Feature` interface?

---

## Documentation Contributions

Documentation contributions are as valuable as code contributions.

### Types of Documentation Contributions

- Fixing typos, broken links, or outdated information
- Improving clarity of existing explanations
- Adding examples to API documentation
- Writing tutorials or guides
- Adding or correcting docstrings in source code
- Translating documentation

### Documentation Standards

- All documentation uses standard Markdown
- Code examples must be tested and working
- Internal links must resolve
- File naming: lowercase with hyphens (`development-guide.md`, not `DevelopmentGuide.md`)
- Every new module introduced in a PR must have module-level documentation

---

## Testing Expectations

### Unit Tests

All new functionality must include unit tests. Tests should:

- Test the happy path and edge cases
- Not require network access, databases, or external credentials
- Be deterministic (no random behavior without seeded randomness)
- Be fast (unit tests should complete in seconds, not minutes)

### Quantitative Tests

All quantitative features and regime detection implementations must include:

- **Look-ahead bias tests:** verify that feature/regime computation does not use future data
- **Known-result tests:** verify computation against known analytical results where available
- **Synthetic data tests:** verify behavior on synthetic datasets with known structure

### Test Coverage

RegimeX targets ≥85% line coverage on core modules. New code should maintain or improve this target.

---

## Code Quality Expectations

- **Formatting:** code must pass the formatter without changes
- **Linting:** no lint errors permitted
- **Type annotations:** all public interfaces must be fully type-annotated
- **Docstrings:** all public functions, classes, and modules must have docstrings
- **No look-ahead bias:** quantitative code is held to strict point-in-time constraints
- **No hardcoded credentials:** use environment variables for all secrets
- **No unnecessary dependencies:** new dependencies require justification

---

## Security Reporting

If you discover a security vulnerability in RegimeX, do **not** open a public GitHub Issue.

Report security vulnerabilities by emailing the maintainers directly (contact information will be published in a future volume). Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigation

We will acknowledge receipt within 72 hours and provide an estimated remediation timeline.

---

## Code of Conduct

RegimeX is committed to a welcoming, inclusive, and respectful community. A full Code of Conduct will be published as part of V28 — Contribution System / Open-Source Community.

Until then, all contributors are expected to:

- Treat others with respect and professionalism
- Engage constructively with criticism and feedback
- Avoid personal attacks, harassment, or discriminatory language
- Focus feedback on code and ideas, not individuals

Violations of these expectations will be addressed by project maintainers.

---

## License

RegimeX is open-source software. The full license will be declared in V02. All contributions will be licensed under the project's chosen open-source license.

By submitting a pull request, you agree that your contribution will be licensed under the same terms as the project.

---

## Questions

If you have questions about contributing that are not answered here, open a GitHub Discussion or a GitHub Issue labeled `question`. Questions about whether a contribution fits the project scope are always welcome before starting significant work.

---

*Thank you for contributing to RegimeX — Open-Source Market Intelligence Platform.*
