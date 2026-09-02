# Product Roadmap

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

This document defines the full 30-volume development roadmap for RegimeX. Each volume is a focused, independently deliverable increment of the platform. Volumes are grouped into phases that reflect how capabilities build on each other.

> ⚠️ **This roadmap describes planned future work.** Nothing beyond V01 has been implemented. Volumes are not time-boxed to calendar dates — they are sequenced by dependency and engineering readiness.

Every volume produces exactly **two commits** before being pushed. See [`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md) for commit and branching conventions.

---

## Phase 1 — Foundation

> Establishes the product identity, enterprise requirements, system architecture, and monorepo engineering infrastructure before any application development begins.

---

### V01 — Product Foundation

**Status:** ✅ In Progress (Current)

**Objective:**
Establish the product identity, principles, scope, decision record infrastructure, development methodology, and contributor foundation for RegimeX before any implementation begins.

**Major Capabilities:**
- Product vision, positioning, and target user definitions
- Engineering, product, and quantitative research principles
- Project scope boundaries (in-scope, out-of-scope, permanent exclusions)
- Architecture Decision Record (ADR) system and index
- 30-volume development roadmap
- Development guide (Git strategy, commit conventions, volume workflow)
- Contributor guide
- Project status tracking

**Engineering Outcome:**
A well-documented, internally consistent product foundation that all future volumes can reference as the authoritative source of product intent.

**Dependencies:** None — this is the root volume.

**Validation Expectations:**
- All documents are internally consistent
- All internal links resolve
- No application code introduced
- No dependencies installed
- Exactly two commits in V01

---

### V02 — Enterprise Requirements

**Status:** 🔜 Planned

**Objective:**
Capture detailed functional and non-functional requirements for RegimeX at an enterprise-grade level of rigor. Define user stories, acceptance criteria, data contracts, and system quality attributes.

**Major Capabilities:**
- Functional requirements per product area (Market Data, Feature Engineering, Regime Detection, Risk, Backtesting, Research, API, Web, AI Assistant)
- Non-functional requirements: performance, reliability, scalability, security, observability
- Data contract definitions (market data schema, feature schema, regime output schema)
- API contract outlines (versioning strategy, error model, authentication model)
- User story catalogue per target user type
- Acceptance criteria templates
- Glossary of domain terms

**Engineering Outcome:**
A requirements baseline that implementation volumes can verify against. Acceptance criteria serve as the foundation for future automated tests.

**Dependencies:** V01

**Validation Expectations:**
- Requirements are unambiguous and testable
- No contradictions with V01 scope
- Data contracts are schema-ready (defined structurally, not yet implemented)

---

### V03 — System Architecture

**Status:** 🔜 Planned

**Objective:**
Design the technical architecture for the RegimeX platform — module boundaries, data flows, integration points, and technology selections. Produce Architecture Decision Records for all major choices.

**Major Capabilities:**
- High-level system architecture diagram
- Module decomposition (data layer, feature layer, regime layer, risk layer, backtest layer, API layer, web layer, AI layer)
- Data flow diagrams for core platform pipelines
- Technology selection ADRs (language, framework, database, message queue, ML tooling)
- Provider abstraction pattern definition
- Regime detector interface specification
- Feature registry design
- Deployment topology overview (self-hosted, containerized)
- Security architecture outline

**Engineering Outcome:**
An architecture baseline that constrains implementation choices and enables parallel work across modules without integration surprises.

**Dependencies:** V01, V02

**Validation Expectations:**
- All major technology choices documented as ADRs
- Module interfaces defined before implementation
- Architecture supports V02 non-functional requirements

---

### V04 — Monorepo Engineering Foundation

**Status:** 🔜 Planned

**Objective:**
Initialize the RegimeX monorepo with consistent tooling, project structure, dependency management, code quality configuration, and minimal CI scaffolding.

**Major Capabilities:**
- Monorepo directory structure (packages, apps, tools, docs)
- Python project scaffolding (pyproject.toml, uv/pip-tools, virtual environment)
- Code formatting configuration (Ruff/Black)
- Linting configuration
- Type checking configuration (mypy/pyright)
- Pre-commit hooks
- Basic GitHub Actions CI (lint, type check, test on push)
- Makefile / task runner for common developer workflows
- Environment variable management (.env.example, never .env in git)
- Initial test infrastructure (pytest, coverage)
- Documentation tooling (MkDocs or Sphinx scaffold)

**Engineering Outcome:**
A working monorepo where any developer can clone, set up, and run quality checks within minutes. The scaffolding enforces quality standards automatically.

**Dependencies:** V01, V02, V03

**Validation Expectations:**
- `make lint`, `make typecheck`, `make test` all pass on the empty scaffold
- No secrets in source control
- CI pipeline runs successfully on PR

---

## Phase 2 — Data & Intelligence

> Builds the data ingestion, normalization, feature engineering, and regime detection capabilities that form the analytical core of RegimeX.

---

### V05 — Market Data Engine

**Status:** 🔜 Planned

**Objective:**
Implement the provider-independent market data ingestion layer. Define the canonical market data schema and build the first concrete provider adapter.

**Major Capabilities:**
- Abstract `MarketDataProvider` interface
- Canonical OHLCV market data schema (with metadata: symbol, exchange, currency, adjustment type, data source version)
- First concrete provider adapter (e.g., Yahoo Finance or equivalent open data source)
- Historical OHLCV ingestion for US equities and major indices
- Data quality checks (gap detection, outlier flagging, schema validation)
- Ingestion logging and audit trail
- Basic CLI command for data ingestion

**Engineering Outcome:**
A working, testable market data ingestion pipeline that can ingest and validate historical OHLCV data for at least one asset class and one provider.

**Dependencies:** V04

**Validation Expectations:**
- Unit tests for provider interface and schema validation
- Integration test against live provider (rate-limited, skippable in CI)
- Data quality checks catch known anomalies in test datasets

---

### V06 — Data Validation & Storage

**Status:** 🔜 Planned

**Objective:**
Implement persistent storage for ingested market data with full data validation, versioning, and retrieval capability.

**Major Capabilities:**
- Database schema for market data (time-series optimized)
- Data versioning and dataset fingerprinting
- Idempotent ingestion (re-running ingestion does not duplicate data)
- Data validation pipeline (completeness, consistency, corporate action handling)
- Survivorship bias documentation and handling strategy
- Data retrieval API (internal, not yet public-facing)
- Dataset export utilities (CSV, Parquet)

**Engineering Outcome:**
A persistent, versioned market data store that other modules can reliably query.

**Dependencies:** V05

**Validation Expectations:**
- Round-trip ingestion and retrieval tests
- Idempotency tests
- Data validation catches injected anomalies in test data

---

### V07 — Feature Engineering

**Status:** 🔜 Planned

**Objective:**
Build the quantitative feature engineering layer — a library of point-in-time, reproducible features computed from market data.

**Major Capabilities:**
- Abstract `Feature` interface and `FeatureRegistry`
- Technical features: returns, volatility (realized, EWMA), volume ratios, momentum indicators, moving averages, RSI, Bollinger Bands, ATR
- Statistical features: rolling correlation, rolling autocorrelation, skewness, kurtosis
- Cross-asset spread features (where data permits)
- Feature computation pipeline with strict point-in-time enforcement
- Look-ahead bias detection tooling
- Feature versioning (features identified by name and version)
- Feature documentation standard

**Engineering Outcome:**
A tested, documented, extensible feature library with zero tolerance for look-ahead bias.

**Dependencies:** V06

**Validation Expectations:**
- Unit tests for every feature implementation
- Look-ahead bias tests using synthetic data with known future contamination
- Feature output schema validation

---

### V08 — Baseline Regime Engine

**Status:** 🔜 Planned

**Objective:**
Implement the first production-ready regime detection algorithm and the standard `RegimeDetector` interface.

**Major Capabilities:**
- Abstract `RegimeDetector` interface (fit, predict, predict_proba, metadata)
- Hidden Markov Model (HMM) regime detector (first implementation)
- Regime label schema (label, confidence, algorithm, parameters, timestamp)
- Regime detection pipeline (feature input → regime output)
- Configurable regime count
- Regime output persistence
- Basic CLI command for regime detection

**Engineering Outcome:**
A working, tested regime detection system with one algorithm, exercising the full detection interface.

**Dependencies:** V07

**Validation Expectations:**
- Unit tests for HMM detector (synthetic data with known regime structure)
- Interface compliance tests (all implementations must pass common test suite)
- Regime output schema validation

---

### V09 — Regime Intelligence

**Status:** 🔜 Planned

**Objective:**
Build regime analysis capabilities — regime history, transition analysis, and regime-conditional statistics.

**Major Capabilities:**
- Regime timeline construction from detection outputs
- Regime persistence metrics (average duration, standard deviation of duration)
- Regime transition matrix computation
- Regime-conditional asset statistics (returns, volatility, Sharpe, drawdown by regime)
- Regime history export (JSON, CSV)
- Regime visualization data outputs (structured for downstream chart rendering)

**Engineering Outcome:**
A regime intelligence module capable of characterizing historical regime behavior and transition probabilities.

**Dependencies:** V08

**Validation Expectations:**
- Unit tests for transition matrix computation
- Regime statistics validated against known synthetic datasets
- Output schemas validated

---

### V10 — Advanced Models

**Status:** 🔜 Planned

**Objective:**
Extend the regime detection model library with additional algorithms, increasing coverage across statistical paradigms.

**Major Capabilities:**
- Gaussian Mixture Model (GMM) regime detector
- Changepoint detection regime detector (e.g., PELT/BOCPD-based)
- K-Means / clustering-based regime detector
- Model comparison utilities (same data, multiple detectors)
- Hyperparameter configuration system
- Model persistence and versioning

**Engineering Outcome:**
Multiple independently configurable regime detectors, all conforming to the standard `RegimeDetector` interface, enabling comparative analysis.

**Dependencies:** V08

**Validation Expectations:**
- Interface compliance tests pass for all new detectors
- Comparative output tests on shared synthetic datasets
- Configuration schema validation

---

### V11 — Ensemble Regime Engine

**Status:** 🔜 Planned

**Objective:**
Build an ensemble regime detection layer that combines signals from multiple detectors into a unified, confidence-weighted regime output.

**Major Capabilities:**
- Ensemble `RegimeDetector` implementation (voting, weighted average, stacking)
- Confidence aggregation across detectors
- Disagreement detection and uncertainty quantification
- Ensemble configuration system
- Ensemble output schema (includes individual detector contributions)

**Engineering Outcome:**
A production-quality ensemble regime detector that is more robust than any single algorithm.

**Dependencies:** V10

**Validation Expectations:**
- Tests verify ensemble is more stable than individual detectors on noisy synthetic data
- Uncertainty outputs are well-calibrated
- Interface compliance tests pass

---

### V12 — Regime Transition Engine

**Status:** 🔜 Planned

**Objective:**
Build a dedicated engine for detecting, characterizing, and forecasting regime transitions.

**Major Capabilities:**
- Transition probability forecasting (short-horizon)
- Leading indicator identification for regime transitions
- Transition event log (timestamped regime changes with contributing features)
- Transition visualization data outputs
- Early-warning signal framework

**Engineering Outcome:**
A regime transition engine capable of characterizing how and why markets move between regimes.

**Dependencies:** V11, V09

**Validation Expectations:**
- Transition detection accuracy validated on synthetic data
- False-positive rate quantified and documented
- Uncertainty is explicitly reported in all forecasts

---

## Phase 3 — Quantitative Analytics

> Implements risk computation, strategy backtesting, and performance analytics with full regime awareness.

---

### V13 — Risk Engine

**Status:** 🔜 Planned

**Objective:**
Implement a comprehensive, regime-aware risk analytics module.

**Major Capabilities:**
- Realized volatility computation (multiple estimators: close-to-close, Parkinson, Yang-Zhang)
- Rolling drawdown analytics (drawdown, duration, recovery time)
- Value at Risk (VaR): historical simulation, parametric
- Conditional VaR (CVaR / Expected Shortfall)
- Rolling correlation matrices
- Regime-conditional risk metrics (risk computed separately per regime)
- Risk output schema and persistence
- Risk report data outputs

**Engineering Outcome:**
A tested, regime-aware risk engine that characterizes risk across market conditions.

**Dependencies:** V09

**Validation Expectations:**
- Unit tests for every risk metric against known analytical results
- Regime-conditional outputs validated on synthetic regime datasets
- Risk schema validation

---

### V14 — Backtesting Engine

**Status:** 🔜 Planned

**Objective:**
Build an event-driven backtesting engine capable of realistic strategy simulation across historical data.

**Major Capabilities:**
- Event-driven simulation loop (bar-by-bar execution)
- Strategy interface (`Strategy.on_bar()`, `Strategy.on_signal()`)
- Portfolio and position management
- Transaction cost model (commission, bid-ask spread, slippage)
- Order management (market, limit orders at minimum)
- Walk-forward validation framework
- Equity curve computation
- Benchmark comparison
- Backtest result schema and persistence

**Engineering Outcome:**
A working, realistic backtesting engine with configurable transaction costs and walk-forward validation support.

**Dependencies:** V07, V13

**Validation Expectations:**
- Backtest results on simple known strategies validated analytically
- Transaction cost impact verified on test cases
- Walk-forward results differ from in-sample results (overfitting not hidden)

---

### V15 — Strategy Analytics

**Status:** 🔜 Planned

**Objective:**
Build a comprehensive strategy performance analytics layer with regime attribution.

**Major Capabilities:**
- Performance metrics: CAGR, Sharpe, Sortino, Calmar, Maximum Drawdown, Win Rate, Profit Factor
- Regime attribution: performance breakdown by detected regime
- Strategy comparison utilities
- Tear sheet data outputs (structured for rendering)
- Monte Carlo simulation for performance uncertainty
- Strategy analytics export (JSON, CSV, HTML report)

**Engineering Outcome:**
A complete performance analytics module that gives researchers a rigorous, regime-aware view of strategy behavior.

**Dependencies:** V14, V09

**Validation Expectations:**
- Metric calculations validated against known analytical results
- Regime attribution consistent with regime timeline
- Monte Carlo output uncertainty is well-characterized

---

## Phase 4 — Platform

> Builds the API, authentication, and web interface layers that expose RegimeX capabilities to developers and end users.

---

### V16 — FastAPI Platform

**Status:** 🔜 Planned

**Objective:**
Build the RegimeX REST API using FastAPI, exposing data, features, regime outputs, and risk metrics programmatically.

**Major Capabilities:**
- FastAPI application scaffold
- API versioning strategy (v1/ prefix)
- Market data endpoints (symbol lookup, OHLCV retrieval)
- Feature endpoints (feature definitions, feature retrieval)
- Regime endpoints (current regime, regime history, transition matrix)
- Risk endpoints (risk metrics by symbol and regime)
- Error model (consistent error response schema)
- API documentation (auto-generated OpenAPI/Swagger)
- Rate limiting framework
- Health and readiness endpoints

**Engineering Outcome:**
A documented, versioned REST API that developers can consume programmatically.

**Dependencies:** V13, V15 (for full coverage); V09 (for regime endpoints)

**Validation Expectations:**
- All endpoints have automated integration tests
- OpenAPI schema is valid and accurate
- Error handling is consistent and documented

---

### V17 — Authentication & Security

**Status:** 🔜 Planned

**Objective:**
Implement authentication, authorization, and API security for the RegimeX platform.

**Major Capabilities:**
- API key authentication
- JWT-based session authentication
- Role-based access control (public, researcher, admin roles)
- Rate limiting per authenticated user
- Input validation and sanitization
- Security headers (CORS, CSP, HSTS)
- Secrets management (environment-based, never in source)
- Security audit logging

**Engineering Outcome:**
A secure API platform suitable for public deployment with proper authentication and authorization boundaries.

**Dependencies:** V16

**Validation Expectations:**
- Authentication tests (valid/invalid credentials)
- Authorization tests (role boundary enforcement)
- Security header validation
- Rate limiting tests

---

### V18 — Web Platform Foundation

**Status:** 🔜 Planned

**Objective:**
Build the RegimeX web frontend foundation — design system, routing, API integration, and authentication.

**Major Capabilities:**
- Frontend framework selection and scaffold (ADR required)
- Design system (typography, colors, spacing, components)
- Application routing
- API client layer (typed, versioned)
- Authentication flow (login, logout, session management)
- Responsive layout foundation
- Accessibility baseline (WCAG 2.1 AA target)

**Engineering Outcome:**
A functional frontend scaffold that implements the design system and authenticates against the API.

**Dependencies:** V17

**Validation Expectations:**
- Design system components render correctly across major browsers
- Authentication flow works end-to-end
- API client connects to V17 API

---

### V19 — Market Dashboard

**Status:** 🔜 Planned

**Objective:**
Build the primary RegimeX market intelligence dashboard for public and authenticated users.

**Major Capabilities:**
- Current regime panel (regime label, confidence, duration)
- Market overview charts (price, volume, volatility)
- Regime history timeline visualization
- Regime transition probability display
- Risk metrics panel
- Symbol/market selector
- Date range selector
- Dashboard data refreshes from live API

**Engineering Outcome:**
A production-quality market intelligence dashboard that clearly communicates current and historical regime state.

**Dependencies:** V18, V16

**Validation Expectations:**
- Dashboard renders correctly with real API data
- All data sourced from API (no hardcoded values)
- Loading and error states handled

---

### V20 — Advanced Analytics UI

**Status:** 🔜 Planned

**Objective:**
Build the advanced analytics interface for quantitative researchers and power users.

**Major Capabilities:**
- Feature explorer (browse, search, visualize features)
- Regime comparison view (side-by-side regime periods)
- Risk analytics deep-dive (regime-conditional risk visualization)
- Backtest result viewer (equity curve, drawdown, regime attribution)
- Custom date range analysis
- Export utilities (chart images, data CSVs)
- Research workspace UI (parameterized analysis runs)

**Engineering Outcome:**
A researcher-grade analytics interface that exposes RegimeX's full analytical depth.

**Dependencies:** V19

**Validation Expectations:**
- All analytics sourced from API
- Complex visualizations render accurately
- Export functions produce correct outputs

---

### V21 — AI Research Assistant

**Status:** 🔜 Planned

**Objective:**
Implement the grounded AI research assistant that helps users understand market regimes with cited evidence and explicit uncertainty.

**Major Capabilities:**
- AI assistant integration (LLM with grounding against RegimeX data)
- Grounding pipeline: AI responses cite specific regime data, risk metrics, and historical observations from the platform
- Uncertainty disclosure: AI explicitly states confidence levels and limitations
- Anti-hallucination safeguards: AI cannot claim regime signals not present in data
- Research question interface (natural language queries about market regimes)
- Conversation history
- Response provenance display (which data sources support each claim)

**Engineering Outcome:**
An AI research assistant that augments quantitative research without fabricating market signals or providing personalized advice.

**Dependencies:** V20, V16

**Validation Expectations:**
- Grounding tests: AI responses reference actual platform data
- Hallucination tests: AI refuses to claim signals not in data
- Uncertainty disclosure present in all probabilistic statements
- Performance acceptable for interactive research use

---

## Phase 5 — Production

> Implements the reliability, observability, infrastructure, CI/CD, and deployment capabilities required for production operation.

---

### V22 — Testing & Reliability

**Status:** 🔜 Planned

**Objective:**
Achieve high test coverage and reliability standards across all RegimeX modules.

**Major Capabilities:**
- Comprehensive unit test suite for all modules
- Integration test suite for API and data pipelines
- End-to-end test suite for critical user journeys
- Property-based testing for quantitative computations
- Mutation testing to validate test quality
- Test coverage reporting (target: ≥85% line coverage on core modules)
- Regression test suite for known edge cases

**Engineering Outcome:**
A high-reliability test baseline that supports confident refactoring and safe feature development.

**Dependencies:** All prior implementation volumes

**Validation Expectations:**
- Coverage target met
- All tests pass in CI
- No known regressions from prior volumes

---

### V23 — Observability

**Status:** 🔜 Planned

**Objective:**
Implement structured logging, metrics, and distributed tracing across the RegimeX platform.

**Major Capabilities:**
- Structured JSON logging (all services)
- Metrics emission (API latency, error rates, ingestion throughput, regime detection latency)
- Distributed tracing (cross-service request traces)
- Alerting rules (error rate thresholds, latency SLOs)
- Logging and metrics integration with open-source observability stack (Prometheus, Grafana, or equivalent)
- Operational runbook for common alerts

**Engineering Outcome:**
A fully observable platform where operational issues can be diagnosed from logs, metrics, and traces without access to production source code.

**Dependencies:** V22

**Validation Expectations:**
- Logs are structured and queryable
- Metrics appear in dashboards
- Traces link API requests to downstream operations

---

### V24 — Docker & Infrastructure

**Status:** 🔜 Planned

**Objective:**
Containerize all RegimeX services and define infrastructure-as-code for reproducible deployments.

**Major Capabilities:**
- Dockerfiles for all services (API, web, workers)
- Docker Compose configuration for local development
- Docker Compose configuration for single-host self-hosting
- Infrastructure-as-code scaffold (Terraform or Pulumi, for cloud)
- Environment configuration management
- Volume and network definitions
- Build optimization (multi-stage builds, layer caching)
- Container security baseline (non-root user, read-only filesystem where possible)

**Engineering Outcome:**
A fully containerized platform that anyone can self-host with a single `docker compose up`.

**Dependencies:** V23

**Validation Expectations:**
- `docker compose up` starts all services successfully
- API health check passes in containerized environment
- Self-hosting documentation verified by end-to-end test

---

### V25 — CI/CD

**Status:** 🔜 Planned

**Objective:**
Build a complete, automated CI/CD pipeline for RegimeX.

**Major Capabilities:**
- Full CI pipeline: format check, lint, type check, unit tests, integration tests, security scan on every PR
- Build pipeline: Docker image build and push on merge
- Deployment pipeline: automated deployment to staging on merge to develop
- Release pipeline: tagged release to production on version tag
- Dependency vulnerability scanning
- SBOM (Software Bill of Materials) generation
- Automated changelog generation from conventional commits
- PR checks enforced (CI must pass before merge)

**Engineering Outcome:**
A fully automated pipeline that enforces quality gates and enables continuous delivery with confidence.

**Dependencies:** V24

**Validation Expectations:**
- CI runs on every PR and fails appropriately on injected errors
- Images build and push on merge
- Release pipeline produces correctly versioned artifacts

---

### V26 — Production Deployment

**Status:** 🔜 Planned

**Objective:**
Deploy RegimeX to a production environment with appropriate reliability, security, and operational readiness.

**Major Capabilities:**
- Production environment configuration (cloud or bare-metal)
- TLS/HTTPS configuration
- DNS configuration
- Database production configuration (backups, point-in-time recovery)
- Secrets management (production-grade, not .env files)
- Load balancing
- Auto-scaling configuration
- Production monitoring integration
- Incident response runbook
- Disaster recovery plan

**Engineering Outcome:**
A production-ready RegimeX deployment that is reliable, secure, and operationally manageable.

**Dependencies:** V25

**Validation Expectations:**
- Production health checks pass
- TLS configured correctly
- Backup and recovery procedures tested
- Runbook reviewed and validated

---

## Phase 6 — Open Source

> Establishes the developer experience, community infrastructure, production hardening, and the RegimeX 1.0 public release.

---

### V27 — Developer Experience

**Status:** 🔜 Planned

**Objective:**
Build a world-class developer experience for RegimeX contributors and API consumers.

**Major Capabilities:**
- Python SDK (typed, documented, installable via pip)
- SDK documentation and quickstart guide
- API client examples (Python, curl)
- Developer portal (API reference, SDK docs, tutorials)
- Quickstart guide: local development setup in under 10 minutes
- Plugin/extension API (documented interface for third-party extensions)
- Interactive API explorer (Swagger UI / ReDoc)
- Changelog and migration guide infrastructure

**Engineering Outcome:**
A developer experience that makes it easy for contributors to onboard and for API consumers to build on RegimeX.

**Dependencies:** V26

**Validation Expectations:**
- Quickstart guide tested on a clean machine
- SDK passes all documented examples
- Plugin API documented with working example plugin

---

### V28 — Contribution System / Open-Source Community

**Status:** 🔜 Planned

**Objective:**
Build the open-source community infrastructure that enables external contributors to participate in RegimeX development.

**Major Capabilities:**
- Comprehensive CONTRIBUTING.md (beyond V01 initial draft)
- Code of conduct
- Issue templates (bug report, feature request, algorithm proposal, data provider proposal)
- Pull request template
- Good first issues labelling system
- Community discussion forum (GitHub Discussions or equivalent)
- Plugin registry design and initial implementation
- Algorithm contribution guide (how to add a regime detection algorithm)
- Data provider contribution guide
- Recognition and attribution system for contributors

**Engineering Outcome:**
A welcoming, structured open-source community that lowers the barrier for contributors to participate meaningfully.

**Dependencies:** V27

**Validation Expectations:**
- Issue templates work on GitHub
- Contribution process tested by a first-time contributor
- Plugin registry accepts and serves a test plugin

---

### V29 — Production Hardening

**Status:** 🔜 Planned

**Objective:**
Harden the RegimeX platform for broad public use — performance, security, data integrity, and operational reliability.

**Major Capabilities:**
- Performance profiling and optimization (API latency, computation throughput)
- Database query optimization and indexing review
- Security penetration testing (automated + manual review)
- Data integrity audit (end-to-end validation of ingestion → detection pipeline)
- Load testing (sustained concurrent user simulation)
- Chaos engineering (service failure recovery testing)
- Accessibility audit (WCAG 2.1 AA compliance verification)
- Dependency audit and update sweep
- Third-party security disclosure response process

**Engineering Outcome:**
A production-hardened platform ready for public launch, with known performance characteristics and validated security posture.

**Dependencies:** V28

**Validation Expectations:**
- Load test results meet defined SLOs
- Security scan results reviewed and remediated
- Data integrity audit passes end-to-end
- Accessibility issues at critical severity resolved

---

### V30 — RegimeX 1.0 Release

**Status:** 🔜 Planned

**Objective:**
Execute the official RegimeX 1.0 open-source release — the first stable, production-ready public release of the platform.

**Major Capabilities:**
- 1.0 release tag and changelog
- Release announcement and blog post
- Documentation site launch (versioned, searchable)
- SDK 1.0.0 published to PyPI
- Docker Hub / GitHub Container Registry images published
- Verified self-hosting guide (tested end-to-end)
- Community launch (GitHub Discussions, announcement)
- Press kit and open-source community outreach
- Post-launch issue triage and rapid response plan
- V31+ roadmap teaser

**Engineering Outcome:**
RegimeX 1.0 is publicly available, documented, installable, and ready for community adoption.

**Dependencies:** V29

**Validation Expectations:**
- `pip install regimex` installs and works
- `docker compose up` starts a working RegimeX instance
- Documentation site is live and searchable
- All V01–V29 validation criteria remain passing
- Release announcement published

---

## Roadmap Summary

| Volume | Title | Phase | Status |
|--------|-------|-------|--------|
| V01 | Product Foundation | Foundation | ✅ In Progress |
| V02 | Enterprise Requirements | Foundation | 🔜 Planned |
| V03 | System Architecture | Foundation | 🔜 Planned |
| V04 | Monorepo Engineering Foundation | Foundation | 🔜 Planned |
| V05 | Market Data Engine | Data & Intelligence | 🔜 Planned |
| V06 | Data Validation & Storage | Data & Intelligence | 🔜 Planned |
| V07 | Feature Engineering | Data & Intelligence | 🔜 Planned |
| V08 | Baseline Regime Engine | Data & Intelligence | 🔜 Planned |
| V09 | Regime Intelligence | Data & Intelligence | 🔜 Planned |
| V10 | Advanced Models | Data & Intelligence | 🔜 Planned |
| V11 | Ensemble Regime Engine | Data & Intelligence | 🔜 Planned |
| V12 | Regime Transition Engine | Data & Intelligence | 🔜 Planned |
| V13 | Risk Engine | Quantitative Analytics | 🔜 Planned |
| V14 | Backtesting Engine | Quantitative Analytics | 🔜 Planned |
| V15 | Strategy Analytics | Quantitative Analytics | 🔜 Planned |
| V16 | FastAPI Platform | Platform | 🔜 Planned |
| V17 | Authentication & Security | Platform | 🔜 Planned |
| V18 | Web Platform Foundation | Platform | 🔜 Planned |
| V19 | Market Dashboard | Platform | 🔜 Planned |
| V20 | Advanced Analytics UI | Platform | 🔜 Planned |
| V21 | AI Research Assistant | Platform | 🔜 Planned |
| V22 | Testing & Reliability | Production | 🔜 Planned |
| V23 | Observability | Production | 🔜 Planned |
| V24 | Docker & Infrastructure | Production | 🔜 Planned |
| V25 | CI/CD | Production | 🔜 Planned |
| V26 | Production Deployment | Production | 🔜 Planned |
| V27 | Developer Experience | Open Source | 🔜 Planned |
| V28 | Contribution System / Open-Source Community | Open Source | 🔜 Planned |
| V29 | Production Hardening | Open Source | 🔜 Planned |
| V30 | RegimeX 1.0 Release | Open Source | 🔜 Planned |

---

> This roadmap is a living document. As the project evolves, volumes may be reordered, split, or merged — all such decisions will be captured as ADRs in [`V01/decisions/`](./decisions/README.md).
