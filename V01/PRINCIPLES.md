# Principles

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

This document establishes the foundational principles that govern all product, engineering, and quantitative research decisions in RegimeX.

Principles are not aspirational bullet points — they are binding constraints. When a design decision conflicts with a principle, the principle governs unless a documented exception is created via an Architecture Decision Record (ADR).

All contributors, maintainers, and adopters are expected to understand and uphold these principles.

---

## Product Principles

### 1. Evidence Over Speculation

Every regime label, risk metric, and analytical output produced by RegimeX must be grounded in observable data and documented methodology. RegimeX does not generate signals based on speculation, narrative, or unvalidated heuristics.

*Implication:* All models, features, and analytics must document their data sources, computation methods, and known limitations.

---

### 2. Explainability Over Black-Box Claims

RegimeX will not present outputs from models that cannot be explained or audited. When a regime is detected, the algorithm, parameters, and contributing features must be accessible to the user.

*Implication:* Black-box models may be supported if they are accompanied by interpretability tooling. No model output will be surfaced without attribution to its source algorithm.

---

### 3. Reproducibility

Given the same data, configuration, and algorithm version, RegimeX must produce the same result. Every experiment, backtest, and analysis must be reproducible by anyone with access to the platform.

*Implication:* Datasets, model configurations, and feature definitions are versioned. Randomness is seeded and documented. Timestamps are explicit.

---

### 4. Data Integrity

Market data is inherently imperfect. RegimeX treats data quality as a first-class concern — not an afterthought. Missing data, corporate actions, survivorship bias, and provider inconsistencies are explicitly handled, documented, and surfaced to users.

*Implication:* Data ingestion pipelines must include quality validation. Gaps and anomalies are logged, not silently ignored.

---

### 5. Model Transparency

Every model or algorithm deployed in RegimeX has documentation that covers:
- What it does
- What assumptions it makes
- What data it requires
- What it does not do
- Known failure modes

*Implication:* No algorithm is merged without its documentation. Algorithm documentation is treated as a first-class artifact alongside code.

---

### 6. Explicit Uncertainty

RegimeX will not overstate the certainty of its outputs. Confidence intervals, uncertainty estimates, and reliability caveats are surfaced wherever possible. The platform makes clear what is known, what is estimated, and what is unknown.

*Implication:* Regime labels are accompanied by confidence scores. Risk metrics are accompanied by their assumptions. AI outputs include uncertainty disclosures.

---

### 7. User Control

Users retain control over analytical parameters. RegimeX provides intelligent defaults but does not hide configuration from users who want to understand or modify how the platform produces its outputs.

*Implication:* Default parameters are documented. Advanced configuration is always accessible. Users are not locked into opaque defaults.

---

### 8. Open-Source First

RegimeX is built for the open-source community. Every design decision prioritizes openness, forkability, self-hosting capability, and community contribution. Proprietary lock-in — in data, tooling, or infrastructure — is avoided.

*Implication:* Dependencies are evaluated for open-source license compatibility. The platform must be fully self-hostable without proprietary cloud services.

---

## Engineering Principles

### 1. Modular Architecture

RegimeX is built as a collection of well-defined, independently testable modules. No module has unnecessary knowledge of other modules' internals. Interfaces between modules are explicit and documented.

*Implication:* Module boundaries are defined before implementation. Cross-module dependencies go through public interfaces, not internal state.

---

### 2. Provider Abstraction

All external dependencies — market data providers, storage backends, ML frameworks — are accessed through abstract interfaces. RegimeX never hard-codes a specific provider into core logic.

*Implication:* Adding a new data provider or swapping a storage backend does not require changes to business logic. Provider-specific code lives in isolated adapter modules.

---

### 3. Model Abstraction

Regime detection algorithms and ML models are accessed through a common interface. New algorithms can be added without modifying regime detection consumers.

*Implication:* A standard `RegimeDetector` interface is defined before any algorithm is implemented. All algorithms implement this interface.

---

### 4. Testability

Every module in RegimeX is designed to be testable in isolation. Pure functions are preferred over stateful classes where appropriate. Side effects (I/O, external calls) are isolated at the boundary.

*Implication:* Unit tests can run without network access, database connections, or external API credentials. Integration tests are clearly separated from unit tests.

---

### 5. Type Safety Where Appropriate

RegimeX uses type annotations, schema validation, and typed interfaces wherever they meaningfully reduce bugs and improve developer experience. Type safety is not dogmatic — pragmatic trade-offs are acceptable with documentation.

*Implication:* Public APIs, configuration schemas, and data models are typed. Internal implementation details are typed where the benefit outweighs the cost.

---

### 6. Security by Design

Security considerations are evaluated at design time, not patched in afterward. Authentication, authorization, secrets management, and input validation are addressed before features are shipped.

*Implication:* No credentials in source code. No unauthenticated endpoints in production. Security review is part of the definition of done for any API or data-access feature.

---

### 7. Observability

RegimeX is designed to be observable — structured logging, metrics emission, and tracing are built into the platform from the start, not added as an afterthought.

*Implication:* Logging uses structured formats (JSON). Key operations emit metrics. Errors include context sufficient for diagnosis without access to production systems.

---

### 8. Backward Compatibility

Public APIs, data schemas, and configuration formats are changed only with deliberate versioning and a migration path. Breaking changes are never silent.

*Implication:* All public interfaces are versioned. Deprecation warnings are issued before removal. Breaking changes require a major version bump and migration documentation.

---

### 9. Documentation as a First-Class Artifact

Documentation is not an afterthought — it is a deliverable. Every module, algorithm, API endpoint, and configuration option has documentation written at the same time as the code, not months later.

*Implication:* Pull requests that add or change functionality without corresponding documentation are not merged. Documentation is included in CI validation.

---

## Quantitative Research Principles

### 1. No Look-Ahead Bias

RegimeX strictly prohibits the use of future data when computing features or running regime detection for a given historical timestamp. All feature computation is point-in-time.

*Implication:* Feature computation pipelines are evaluated with strict point-in-time constraints. Any violation of this rule is treated as a critical bug.

---

### 2. No Data Leakage

Training data and validation/test data are never allowed to cross-contaminate. Model training uses only data that would have been available at the time of training in a realistic deployment.

*Implication:* Data splits are defined and frozen before any model training begins. Leakage checks are automated as part of the validation pipeline.

---

### 3. Reproducible Experiments

Every experiment in RegimeX — whether a backtesting run, a regime detection analysis, or a research notebook — is reproducible from its configuration, data version, and algorithm version alone.

*Implication:* All experiments record their full configuration, data version fingerprints, and software versions. Results are deterministic given these inputs.

---

### 4. Walk-Forward Validation Where Appropriate

Historical performance evaluation uses walk-forward (out-of-sample) validation wherever the analysis involves a model that could be overfit to in-sample data.

*Implication:* Backtest results that use in-sample-only validation are explicitly labeled as such and treated as preliminary. Walk-forward results are the standard for publication-quality analysis.

---

### 5. Realistic Transaction Costs

Backtests use realistic transaction cost assumptions — commissions, bid-ask spreads, market impact, and slippage — rather than assuming costless execution.

*Implication:* Transaction cost models are configurable, documented, and defaulted to conservative assumptions. Zero-cost backtests are not surfaced as production results.

---

### 6. Explicit Assumptions

Every quantitative analysis explicitly documents its assumptions. Users are never required to infer assumptions from outputs.

*Implication:* Analysis outputs include an assumptions section. Configuration files include comments explaining the purpose and impact of each parameter.

---

### 7. Versioned Datasets, Models, and Configurations

Quantitative research is only reproducible if datasets, models, and configurations are versioned and archived. RegimeX enforces this at the platform level.

*Implication:* Dataset snapshots used in experiments are fingerprinted and archived. Model weights and configurations are versioned alongside code. Research outputs reference their exact inputs.

---

### 8. Uncertainty Is Never Hidden

When RegimeX does not know something with confidence — the current regime, the reliability of a signal, the validity of a model in unusual market conditions — it says so explicitly.

*Implication:* "Unknown," "uncertain," and "low-confidence" are valid and important outputs. Displaying false precision is prohibited.
