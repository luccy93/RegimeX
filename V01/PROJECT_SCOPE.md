# Project Scope

**RegimeX — Open-Source Market Intelligence Platform**

---

## Overview

This document defines the long-term scope of the RegimeX platform and the explicit boundaries for what is and is not in scope — both overall and specifically for V01.

Scope boundaries exist to protect the product's focus, prevent scope creep, and ensure that engineering effort is directed at problems RegimeX is genuinely designed to solve.

---

## Long-Term Platform Scope (In Scope)

The following capabilities are in scope for the RegimeX platform across its full development lifecycle. They are not all implemented now — they represent the intended eventual scope.

### Market and Asset Coverage

- **Multiple asset classes:** equities, crypto, commodities, foreign exchange, fixed income (prioritized progressively)
- **Multiple geographies:** US markets, Indian markets, and international markets over time
- **Multiple instrument types:** spot, index, ETFs, and relevant derivatives where data is publicly accessible

### Market Data Infrastructure

- **Provider-independent data ingestion:** architecture that abstracts over specific data vendors
- **Normalized historical market data:** consistent schema across providers and asset classes
- **Data quality validation:** explicit checks for gaps, outliers, corporate actions, survivorship bias
- **Versioned datasets:** datasets identified by version to enable reproducible experiments

### Quantitative Feature Engineering

- **Technical feature library:** price-derived indicators, volume features, volatility measures
- **Statistical feature library:** rolling statistics, correlation features, cross-asset spreads
- **Macro overlay features:** regime-relevant macroeconomic signals (where publicly available)
- **Feature registry:** discoverable, documented, and version-controlled feature definitions
- **Bias prevention:** strict enforcement of no look-ahead bias in all feature computation

### Regime Detection

- **Multiple algorithm support:** Hidden Markov Models, Gaussian Mixture Models, clustering approaches, and others
- **Configurable regime detection:** users can configure algorithm parameters and compare outputs
- **Regime classification:** discrete regime labels with associated properties
- **Confidence estimation:** explicit uncertainty quantification on regime assignments
- **Algorithm transparency:** every detection algorithm documented with assumptions and limitations

### Regime Analysis

- **Regime transition analysis:** transition matrices, persistence metrics, leading indicators
- **Historical regime timeline:** a navigable record of detected regimes over time
- **Regime-conditional statistics:** asset behavior statistics conditional on regime

### Risk Analytics

- **Volatility metrics:** realized volatility, GARCH-family estimates, implied volatility where available
- **Drawdown analytics:** maximum drawdown, drawdown duration, recovery time
- **Tail risk metrics:** Value at Risk (VaR), Conditional VaR (CVaR), stress scenarios
- **Correlation dynamics:** rolling and regime-conditional correlation matrices
- **Regime-aware risk:** risk metrics computed separately per regime

### Backtesting

- **Event-driven backtesting engine:** accurate simulation of strategy execution
- **Realistic transaction costs:** configurable commission, slippage, and market impact models
- **Walk-forward validation:** out-of-sample testing to prevent overfitting
- **Performance attribution by regime:** understanding strategy performance across market conditions
- **Strategy analytics:** Sharpe, Sortino, Calmar ratios; drawdown analysis; regime performance breakdown

### Research and Reproducibility

- **Reproducible experiments:** version-controlled configurations, data snapshots, and model states
- **Research workspace:** parameterized, auditable analytical pipelines
- **Jupyter and notebook integration:** for quantitative research workflows
- **Explicit assumption logging:** all experiments record their assumptions

### AI Research Assistant

- **Grounded market research:** AI assistant that cites sources and quantitative evidence
- **Uncertainty acknowledgment:** AI outputs include confidence levels and caveats
- **No fabrication policy:** AI assistant will not generate unsupported market signals

### Platform Access

- **API access:** RESTful API for programmatic access to platform data and analytics
- **Web-based analytics:** browser-based dashboards and research interface
- **SDK support:** Python SDK (primary); additional SDKs in future volumes
- **Self-hosting:** full support for organizations running their own RegimeX instance

### Developer and Community

- **Plugin/extension system:** allow developers to contribute new providers, features, and algorithms
- **Contributor infrastructure:** contribution guides, code of conduct, PR templates, CI
- **Open-source community tools:** forums, plugin registry, community documentation

---

## Initial Market Scope

The RegimeX data architecture will be designed to be **provider-independent** and **asset-class-agnostic** from the start. The following asset classes represent the intended initial and near-term coverage.

| Asset Class | Markets | Priority |
|-------------|---------|----------|
| Equities | US (S&P 500, NASDAQ, NYSE) | High |
| Equities | India (NSE, BSE, NIFTY) | High |
| Cryptocurrency | BTC, ETH, major pairs | Medium |
| Commodities | Gold, Oil, major commodities | Medium |
| Foreign Exchange | Major currency pairs (USD, EUR, GBP, JPY, INR) | Medium |
| Fixed Income | US Treasuries, bond indices | Lower |

> ⚠️ **No market data providers are implemented in V01.** The above represents architectural intention, not current capability.

---

## Explicitly Out of Scope — V01

The following are **explicitly not in scope for V01**. These will be addressed in future volumes.

| Category | Out of Scope Item |
|----------|-------------------|
| APIs | Production REST/GraphQL/WebSocket APIs |
| Frontend | Web interface, dashboards, charts |
| Authentication | User accounts, OAuth, API keys, sessions |
| Databases | Schema design, migrations, production databases |
| ML Implementation | Model training, inference code, pipelines |
| Data Ingestion | Market data providers, connectors, normalization |
| Feature Engineering | Feature computation, feature registry |
| Backtesting | Backtesting engine, transaction models |
| AI | LLM integration, AI assistant, grounding pipelines |
| Cloud | AWS/GCP/Azure deployment, containerization |
| Infrastructure | Docker, Kubernetes, Terraform, CI/CD pipelines |
| Real-Time | Streaming data, real-time analytics |
| Trading | Order management, broker integration |
| Financial Advice | Any advisory or personalized recommendation capability |
| Licensing | License file (deferred to V02) |
| Package Registry | PyPI, npm, or other registry publication |
| Dependencies | No packages installed in V01 |

---

## Explicitly Permanent Out of Scope

The following will **never** be in scope for RegimeX, regardless of version:

- ❌ **Automated or algorithmic trading execution** (RegimeX does not trade)
- ❌ **Personalized financial advice** (RegimeX does not advise individuals)
- ❌ **Guaranteed return claims** (RegimeX makes no financial promises)
- ❌ **Proprietary data vendor lock-in** (the platform remains provider-independent)
- ❌ **Closed-source commercial forks that remove attribution** (governed by license)

---

## Scope Management Process

As RegimeX grows, scope decisions — both expansions and exclusions — will be documented as Architecture Decision Records (ADRs) in `V01/decisions/`.

Scope changes require:
1. A documented rationale
2. An assessment of impact on existing architecture
3. An ADR entry
4. Review before implementation begins
