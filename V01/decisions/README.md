# Decision Records

**RegimeX — Open-Source Market Intelligence Platform**

---

## Purpose

This directory contains **Architecture and Product Decision Records (ADRs)** for RegimeX.

Every significant architectural choice, product scope decision, technology selection, or design trade-off made in the development of RegimeX is documented here. Decision records are not bureaucracy — they are the memory of the project.

Without recorded decisions, teams repeat debates already resolved, new contributors can't understand *why* something was built a specific way, and the project accumulates silent assumptions that eventually become problems.

RegimeX uses decision records to:

- **Preserve context** — document the problem, options considered, and reasoning behind choices
- **Enable informed challenge** — allow future contributors to understand a decision well enough to revisit it with new evidence
- **Prevent repeated debates** — when a decision is made, it is documented; the debate is resolved until new information changes it
- **Create accountability** — decisions are attributed to a point in time and a state of knowledge

---

## When to Create a Decision Record

Create a decision record when:

- Choosing a language, framework, or major dependency
- Defining a module boundary or architectural pattern
- Making a data schema or storage decision with long-term consequences
- Choosing between materially different algorithmic approaches
- Expanding or contracting product scope in a significant way
- Resolving a disagreement that has architectural implications
- Choosing an API contract that will be publicly committed to

You do **not** need a decision record for:

- Routine implementation choices (variable naming, minor refactors)
- Decisions trivially reversible without downstream impact
- Documentation-only changes

---

## ADR Naming Convention

ADRs are named using the following format:

```text
ADR-NNNN-short-descriptive-title.md
```

Where:
- `NNNN` is a zero-padded sequential number (e.g., `0001`, `0002`)
- `short-descriptive-title` is a brief, lowercase, hyphenated description of the decision

### Examples

```text
ADR-0001-python-as-primary-language.md
ADR-0002-provider-abstraction-pattern.md
ADR-0003-regime-detector-interface-design.md
ADR-0004-database-selection.md
ADR-0005-api-versioning-strategy.md
```

Numbers are assigned in the order decisions are made, not by topic or importance.

---

## ADR Template

Each ADR should use the following structure:

```markdown
# ADR-NNNN: [Short Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]
**Date:** YYYY-MM-DD
**Author(s):** [Name(s) or GitHub handle(s)]

---

## Context

Describe the problem or situation that requires a decision. Include:
- What is driving this decision?
- What constraints exist?
- What does the team need to be true after this decision is made?

## Decision

State the decision clearly and unambiguously.

> We will [specific choice] because [primary reason].

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Option A    | ...               |
| Option B    | ...               |

## Consequences

### Positive
- ...

### Negative / Trade-offs
- ...

### Risks
- ...

## Status History

| Date | Status | Note |
|------|--------|------|
| YYYY-MM-DD | Proposed | Initial draft |
| YYYY-MM-DD | Accepted | After team review |
```

---

## Decision Record Index

As ADRs are created, they will be indexed here.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | *(no decisions recorded yet)* | — | — |

---

## Notes on Status

| Status | Meaning |
|--------|---------|
| **Proposed** | Decision has been written and is under review |
| **Accepted** | Decision has been agreed upon and governs current implementation |
| **Deprecated** | Decision was once accepted but is no longer applicable (context changed) |
| **Superseded** | Decision was replaced by a newer ADR (link to successor) |

---

> Decision records are not permanent — they reflect the best available knowledge at the time they were made. New evidence, new constraints, or new team understanding can and should lead to revised decisions. When a decision is revised, the original ADR is marked **Deprecated** or **Superseded**, not deleted.
