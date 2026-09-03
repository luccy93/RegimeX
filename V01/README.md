# V01 — Product Foundation

**RegimeX — Open-Source Market Intelligence Platform**

---

## Purpose of V01

V01 is the first volume of the RegimeX project. Its sole purpose is to establish a rigorous, consistent product and engineering foundation **before any implementation work begins**.

This volume answers:

- What is RegimeX?
- Who is it for?
- What problem does it solve?
- What are the product's principles?
- What is in scope and out of scope?
- How will architectural decisions be recorded and reasoned about?

V01 contains no application code, no APIs, no ML models, no databases, no frontend, and no production infrastructure of any kind.

---

## What Is Being Established in V01

| Document | Purpose |
|----------|---------|
| [PRODUCT_FOUNDATION.md](./PRODUCT_FOUNDATION.md) | Product vision, positioning, target users, and core product areas |
| [PROJECT_SCOPE.md](./PROJECT_SCOPE.md) | Explicit in-scope and out-of-scope boundaries for the platform |
| [PRINCIPLES.md](./PRINCIPLES.md) | Engineering, product, and quantitative research principles |
| [PRODUCT_ROADMAP.md](./PRODUCT_ROADMAP.md) | Full 30-volume development roadmap (V01–V30) |
| [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) | Git strategy, commit conventions, volume workflow, quality gates |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contributor guide for open-source participation |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Current implementation status and next volume |
| [decisions/README.md](./decisions/README.md) | Architecture and product decision record (ADR) index and process |

---

## What Is Intentionally NOT Implemented in V01

The following are explicitly deferred to future volumes:

- ❌ Application source code of any kind
- ❌ APIs (REST, GraphQL, WebSocket, etc.)
- ❌ Frontend / web interface
- ❌ Database schemas or migrations
- ❌ ML models, training pipelines, or inference code
- ❌ Market data providers or data ingestion
- ❌ Feature engineering implementations
- ❌ Regime detection algorithms
- ❌ Risk analytics computation
- ❌ Backtesting engine
- ❌ Authentication or authorization
- ❌ Cloud deployment or production infrastructure
- ❌ CI/CD pipelines (beyond minimal scaffolding)
- ❌ Python/Node/other package dependencies

---

## Relationship Between V01 and Future Volumes

V01 is the **north star document set** for all future volumes. Every engineering decision in subsequent volumes should be traceable back to the product principles and scope defined here.

Future volumes will follow a progressive implementation approach across six phases and 30 volumes. See [`PRODUCT_ROADMAP.md`](./PRODUCT_ROADMAP.md) for the complete sequence.

| Phase | Volumes | Focus |
|-------|---------|-------|
| Foundation | V01–V04 | Product identity, requirements, architecture, monorepo |
| Data & Intelligence | V05–V12 | Market data, features, regime detection, transition analysis |
| Quantitative Analytics | V13–V15 | Risk engine, backtesting, strategy analytics |
| Platform | V16–V21 | API, authentication, web interface, AI assistant |
| Production | V22–V26 | Testing, observability, Docker, CI/CD, deployment |
| Open Source | V27–V30 | Developer experience, community, hardening, 1.0 release |

Volumes are not strictly sequential — some work may begin in parallel — but V01 principles govern all of them.

---

## V01 Commit History

| Commit | Message | Description |
|--------|---------|-------------|
| 01 | `chore(project): initialize RegimeX open-source platform` | Project identity, principles, scope, ADR system |
| 02 | `docs(product): establish RegimeX product vision and roadmap` | Roadmap, development guide, contributing, project status |

---

## Status

> **V01 is active.** Product foundation documents are being established.
> Engineering implementation has not begun.
