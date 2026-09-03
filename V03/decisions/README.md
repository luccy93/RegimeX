# Architecture Decision Records (ADRs)

**RegimeX — Open-Source Market Intelligence Platform**  
**Volume:** V03 — System Architecture  

---

## 1. Overview

Architecture Decision Records (ADRs) capture significant architectural, design, structural, and technology decisions made across the lifecycle of RegimeX.

Every non-trivial technical decision that constrains implementation, introduces dependencies, defines interfaces, or alters module boundaries must be documented as an ADR before implementation begins.

---

## 2. ADR Standard Structure

Each ADR in this directory must adhere to the following standard template:

```markdown
# ADR-XXXX: Title of Decision

**Status:** [Proposed | Accepted | Superseded | Deprecated]  
**Date:** YYYY-MM-DD  
**Volume:** VXX — Volume Name  
**Deciders:** List of contributors/architects involved  

---

## 1. Context
What is the business, architectural, or technical problem being solved?
What are the constraints, requirements, and forces at play?

## 2. Decision
What is the chosen approach, pattern, or technology?
State clearly in the active voice: "We will..." or "RegimeX mandates..."

## 3. Alternatives Considered
Table or list of alternatives evaluated and specific reasons why they were rejected.

## 4. Consequences
What becomes easier or possible (positive)?
What becomes harder or restricted (negative / trade-offs)?
What risks are accepted?

## 5. Requirements Addressed
Explicit mapping to V01 product goals and V02 Functional (FR-XXX) and Non-Functional (NFR-XXX) requirements.
```

---

## 3. Register of Architecture Decision Records

| ADR | Title | Status | Date | Addressed Requirements |
|:---:|:------|:------:|:----:|:-----------------------|
| [ADR-0001](./ADR-0001-architecture-style.md) | Modular Monolith with Asynchronous Workers | Accepted | 2026-09-03 | NFR-001, NFR-008, NFR-026, NFR-064, NFR-075 |
| [ADR-0002](./ADR-0002-data-provider-abstraction.md) | Market Data Provider Abstraction | Accepted | 2026-09-03 | FR-005–FR-013, NFR-023, NFR-034, NFR-078 |
| [ADR-0003](./ADR-0003-regime-model-abstraction.md) | Regime Detection Model Abstraction | Accepted | 2026-09-03 | FR-022–FR-031, NFR-030, NFR-032, NFR-101 |
| [ADR-0004](./ADR-0004-provider-abstraction-pattern.md) | Provider Abstraction Pattern (Detailed Spec) | Accepted | 2026-09-02 | FR-005, NFR-078 |
| [ADR-0005](./ADR-0005-regime-detector-interface-design.md) | Regime Detector Interface Design (Detailed Spec) | Accepted | 2026-09-02 | FR-022, NFR-030, NFR-032 |

---

## 4. Decision Lifecycle & Immutability

1. **Draft / Proposed:** The decision is under active design review and RFC discussion.
2. **Accepted:** The decision is approved and forms the authoritative architectural constraint for subsequent volumes.
3. **Superseded:** A later decision replaces this ADR. The superseded ADR must link to its replacement (e.g., "Superseded by ADR-XXXX").
4. **Immutability:** Accepted ADRs are historical records. Once accepted and committed, the text of the context and decision should not be retroactively rewritten; revisions must be recorded via status updates or new ADRs.
