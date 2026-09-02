# User Stories

**RegimeX — Open-Source Market Intelligence Platform**

> User stories describe desired platform behaviors from each target user's perspective. These inform acceptance criteria and feature prioritization. Stories are written in the form: *As a [user type], I want to [action], so that [benefit].*

---

## US-PUB — Public User Stories

| ID | Story | Priority |
|----|-------|---------|
| US-PUB-001 | As a public user, I want to see the current market regime for a major index (e.g., S&P 500), so that I can quickly understand the current market environment. | Critical |
| US-PUB-002 | As a public user, I want to see how long the current regime has been active, so that I understand whether it is a new or established market state. | High |
| US-PUB-003 | As a public user, I want to see the historical regime timeline for an index, so that I can see how market conditions have changed over time. | High |
| US-PUB-004 | As a public user, I want to see the current volatility level for an instrument, so that I have a sense of current risk levels. | High |
| US-PUB-005 | As a public user, I want to access this information without creating an account, so that there is no barrier to basic market intelligence. | High |
| US-PUB-006 | As a public user, I want the dashboard to be usable on a desktop browser without needing technical knowledge, so that market intelligence is accessible to non-technical users. | High |

---

## US-MR — Market Researcher Stories

| ID | Story | Priority |
|----|-------|---------|
| US-MR-001 | As a market researcher, I want to view the full historical regime timeline for any supported instrument, so that I can identify patterns in market structure over time. | Critical |
| US-MR-002 | As a market researcher, I want to see regime-conditional statistics (average returns, volatility, drawdown by regime), so that I can characterize how assets behave in different market states. | Critical |
| US-MR-003 | As a market researcher, I want to export regime history data to CSV, so that I can analyze it with my own tools. | High |
| US-MR-004 | As a market researcher, I want to compare regime timelines across multiple instruments simultaneously, so that I can identify cross-asset regime correlations. | Medium |
| US-MR-005 | As a market researcher, I want to see the regime transition matrix (probability of moving from regime A to regime B), so that I can analyze market state persistence. | High |
| US-MR-006 | As a market researcher, I want to search the instrument catalogue by asset class and geography, so that I can quickly find the instruments relevant to my research. | High |

---

## US-QR — Quantitative Researcher Stories

| ID | Story | Priority |
|----|-------|---------|
| US-QR-001 | As a quantitative researcher, I want to select a regime detection algorithm and configure its parameters, so that I can experiment with different regime definitions. | Critical |
| US-QR-002 | As a quantitative researcher, I want to run regime detection on custom date ranges and instruments, so that I can scope my analysis precisely. | Critical |
| US-QR-003 | As a quantitative researcher, I want to compare regime detection outputs across multiple algorithms on the same dataset, so that I can assess algorithmic consistency. | High |
| US-QR-004 | As a quantitative researcher, I want to backtest a quantitative strategy with regime attribution, so that I can understand how my strategy performs across different market regimes. | Critical |
| US-QR-005 | As a quantitative researcher, I want walk-forward backtest validation to be built in, so that I avoid overfitting to in-sample data. | Critical |
| US-QR-006 | As a quantitative researcher, I want every analysis run to be reproducible from a configuration file, so that I can share and verify my results. | Critical |
| US-QR-007 | As a quantitative researcher, I want to see the full feature set used as inputs to regime detection, so that I understand what signals are driving regime assignments. | High |
| US-QR-008 | As a quantitative researcher, I want to define and register custom quantitative features, so that I can extend the platform with my own signal engineering. | Medium |
| US-QR-009 | As a quantitative researcher, I want risk metrics computed separately per regime, so that I can see how risk characteristics differ across market states. | High |
| US-QR-010 | As a quantitative researcher, I want to integrate RegimeX with Jupyter notebooks, so that I can use familiar research tools. | High |

---

## US-DEV — Developer Stories

| ID | Story | Priority |
|----|-------|---------|
| US-DEV-001 | As a developer, I want to query the RegimeX REST API for current regime data, so that I can integrate market intelligence into my own applications. | Critical |
| US-DEV-002 | As a developer, I want a Python SDK with type annotations, so that I can consume RegimeX data programmatically with IDE support. | High |
| US-DEV-003 | As a developer, I want the API to provide auto-generated OpenAPI documentation, so that I can quickly understand available endpoints without reading source code. | High |
| US-DEV-004 | As a developer, I want to implement a custom regime detection algorithm using the `RegimeDetector` interface, so that I can extend the platform with proprietary algorithms. | High |
| US-DEV-005 | As a developer, I want to implement a custom market data provider adapter, so that I can connect RegimeX to a proprietary data source. | High |
| US-DEV-006 | As a developer, I want API errors to have consistent, machine-readable error codes, so that I can handle failure cases reliably in my integration. | Critical |
| US-DEV-007 | As a developer, I want API rate limits to be communicated in response headers, so that my client can implement respectful rate limiting without trial and error. | High |
| US-DEV-008 | As a developer, I want the platform to be self-hostable via Docker Compose, so that I can run a private RegimeX instance for internal use. | High |

---

## US-CONT — Open-Source Contributor Stories

| ID | Story | Priority |
|----|-------|---------|
| US-CONT-001 | As a contributor, I want a clear setup guide that gets my local development environment running in under 15 minutes, so that I can start contributing quickly. | Critical |
| US-CONT-002 | As a contributor, I want contribution guidelines that explain the branching model, commit conventions, and PR process, so that my contributions are consistent with the project's standards. | Critical |
| US-CONT-003 | As a contributor, I want to know how to add a new regime detection algorithm, so that I can contribute new quantitative methods to the platform. | High |
| US-CONT-004 | As a contributor, I want automated CI to run on my PR, so that I get immediate feedback on lint errors, type errors, and test failures. | Critical |
| US-CONT-005 | As a contributor, I want an issue template for proposing new algorithms, so that my proposal is structured and reviewable. | Medium |
| US-CONT-006 | As a contributor, I want the codebase to have high test coverage with clear test organization, so that I can understand what is tested and write tests for my contributions. | High |

---

## US-ADMIN — Platform Administrator Stories

| ID | Story | Priority |
|----|-------|---------|
| US-ADMIN-001 | As an administrator, I want to deploy the full RegimeX platform using Docker Compose, so that I can self-host for my organization. | Critical |
| US-ADMIN-002 | As an administrator, I want to configure environment variables for all secrets and service connections, so that I can customize the deployment without modifying source code. | Critical |
| US-ADMIN-003 | As an administrator, I want to manage API keys (create, list, revoke), so that I can control access to my deployment. | High |
| US-ADMIN-004 | As an administrator, I want to monitor platform health through structured logs and metrics, so that I can detect and diagnose operational issues. | High |
| US-ADMIN-005 | As an administrator, I want to schedule market data ingestion jobs, so that the platform automatically stays up-to-date. | High |
| US-ADMIN-006 | As an administrator, I want automated database backups configured out of the box, so that I do not lose data due to infrastructure failures. | High |
