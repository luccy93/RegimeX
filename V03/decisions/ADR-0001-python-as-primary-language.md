# ADR-0001: Python as Primary Language

**Status:** Accepted
**Date:** 2026-09-02
**Volume:** V03 — System Architecture

---

## Context

RegimeX requires a primary programming language for all backend services, the intelligence layer, and the Python SDK. The language choice has major downstream implications for:
- availability of quantitative/ML libraries
- developer community and contributor accessibility
- typing and code quality tooling
- deployment complexity

The platform needs strong support for numerical computation, statistical modeling, and time-series data manipulation.

## Decision

> We will use **Python 3.10+** as the primary language for all RegimeX backend services, intelligence components, and the Python SDK.

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Julia | Smaller ecosystem, fewer contributors, less mature web framework options |
| R | Strong statistical ecosystem but limited for building production APIs and web services |
| Go | Excellent for APIs but poor quantitative/ML library support; regime detection requires Python-native libraries |
| Rust | High performance but steep learning curve; quantitative library ecosystem immature vs Python |

## Consequences

### Positive
- Access to numpy, pandas, scikit-learn, hmmlearn, statsmodels — all required for quantitative features
- Largest open-source contributor pool for quantitative software
- FastAPI, SQLAlchemy, Pydantic, Celery are all Python-native
- Type annotations supported from Python 3.10+
- Jupyter integration is native

### Negative / Trade-offs
- Python's GIL limits true CPU-parallelism (mitigated by Celery task queues and multiprocessing)
- Slower than compiled languages for compute-intensive loops (mitigated by numpy vectorization)

### Risks
- Python version deprecation cycles must be tracked; minimum supported version is 3.10

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-09-02 | Accepted | Unanimous — no viable alternative for quantitative platform |
