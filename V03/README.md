# V03 — System Architecture

**RegimeX — Open-Source Market Intelligence Platform**

---

## Purpose of V03

V03 defines the technical architecture of RegimeX — the module boundaries, data flows, technology choices, and interface specifications that constrain all implementation work beginning in V04.

This volume does **not** implement any application code. It defines the blueprint that implementation volumes follow.

---

## Documents in V03

| Document | Purpose |
|----------|---------|
| [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) | High-level system design and component overview |
| [MODULE_DESIGN.md](./MODULE_DESIGN.md) | Module decomposition, boundaries, and responsibilities |
| [DATA_FLOWS.md](./DATA_FLOWS.md) | End-to-end data flow from ingestion to API |
| [INTERFACE_SPECIFICATIONS.md](./INTERFACE_SPECIFICATIONS.md) | Abstract interface definitions for core extension points |
| [DEPLOYMENT_TOPOLOGY.md](./DEPLOYMENT_TOPOLOGY.md) | Self-hosted deployment topology and service map |
| [decisions/](./decisions/) | Architecture Decision Records for all major technology choices |

---

## Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](./decisions/ADR-0001-python-as-primary-language.md) | Python as Primary Language | Accepted |
| [ADR-0002](./decisions/ADR-0002-fastapi-as-api-framework.md) | FastAPI as API Framework | Accepted |
| [ADR-0003](./decisions/ADR-0003-postgresql-timescaledb-for-storage.md) | PostgreSQL + TimescaleDB for Storage | Accepted |
| [ADR-0004](./decisions/ADR-0004-provider-abstraction-pattern.md) | Provider Abstraction Pattern | Accepted |
| [ADR-0005](./decisions/ADR-0005-regime-detector-interface-design.md) | Regime Detector Interface Design | Accepted |

---

## V03 Commit History

| Commit | Message | Description |
|--------|---------|-------------|
| 01 | `feat(architecture): define system architecture and module design` | Architecture, modules, data flows, ADR-0001–0003 |
| 02 | `feat(architecture): add interface specs, ADRs, and deployment topology` | Interfaces, deployment, ADR-0004–0005 |
