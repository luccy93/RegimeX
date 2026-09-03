# V03 — System Architecture

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  

---

## 1. Purpose of V03

V03 defines the comprehensive technical architecture blueprint of RegimeX — the modular boundaries, data flows, service boundaries, technology policies, and architecture decisions that govern all implementation beginning in V04.

This volume does **not** implement application code. It establishes the enterprise architectural blueprint that implementation volumes must follow.

---

## 2. Core Architecture Blueprint Documents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Primary enterprise architecture blueprint: goals, layers, domains, security, storage, AI, traceability, and risks |
| [DIAGRAMS.md](./DIAGRAMS.md) | Formal Mermaid architecture diagrams: System Context, Container Runtime, Data Pipeline, Grounded AI, and Security |
| [ARCHITECTURE_PRINCIPLES.md](./ARCHITECTURE_PRINCIPLES.md) | Foundational engineering and architectural principles governing system design |
| [MODULE_BOUNDARIES.md](./MODULE_BOUNDARIES.md) | Strict boundaries, responsibilities, data ownership, and prohibited actions for all 14 modules |
| [SERVICE_BOUNDARIES.md](./SERVICE_BOUNDARIES.md) | Logical service boundaries, communication mechanisms, failure modes, and scaling characteristics |
| [DATA_FLOW.md](./DATA_FLOW.md) | End-to-end data pipeline from raw market ingestion through validation gates to delivery |
| [INTERFACE_SPECIFICATIONS.md](./INTERFACE_SPECIFICATIONS.md) | Abstract Python interface specifications for core extension points |
| [DEPLOYMENT_TOPOLOGY.md](./DEPLOYMENT_TOPOLOGY.md) | Containerized deployment topologies for local development and production |
| [decisions/](./decisions/) | Architecture Decision Records (ADR) system and register |

---

## 3. Architecture Decision Records

| ADR | Title | Status |
|:---:|:------|:------:|
| [ADR-0001](./decisions/ADR-0001-architecture-style.md) | Modular Monolith with Asynchronous Workers | Accepted |
| [ADR-0002](./decisions/ADR-0002-data-provider-abstraction.md) | Market Data Provider Abstraction | Accepted |
| [ADR-0003](./decisions/ADR-0003-regime-model-abstraction.md) | Regime Detection Model Abstraction | Accepted |
| [ADR-0004](./decisions/ADR-0004-provider-abstraction-pattern.md) | Provider Abstraction Pattern (Detailed Spec) | Accepted |
| [ADR-0005](./decisions/ADR-0005-regime-detector-interface-design.md) | Regime Detector Interface Design (Detailed Spec) | Accepted |
