# ADR-0002: FastAPI as API Framework

**Status:** Accepted
**Date:** 2026-09-02
**Volume:** V03 — System Architecture

---

## Context

RegimeX requires a Python web framework for building the REST API. Requirements:
- Auto-generated OpenAPI/Swagger documentation (FR-API-007)
- Async support for handling concurrent requests efficiently
- Pydantic v2 integration for request/response validation
- Developer-friendly and well-maintained
- Actively maintained open-source project

## Decision

> We will use **FastAPI** as the REST API framework, with **Pydantic v2** for request/response schema validation.

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Django REST Framework | Heavier framework, synchronous-first, more opinionated — overhead not justified for an API-only service |
| Flask | No native async support, no built-in OpenAPI generation, requires more manual wiring |
| Starlette (raw) | FastAPI is built on Starlette; using FastAPI gives us Pydantic integration and OpenAPI for free |
| Litestar | Viable alternative but smaller community; FastAPI has significantly more adoption and third-party support |

## Consequences

### Positive
- Auto-generated OpenAPI schema satisfies FR-API-007 with zero additional code
- Pydantic v2 provides fast, declarative request/response validation at all API boundaries
- Async request handling supports NFR-PERF-008 (100 concurrent users)
- FastAPI's dependency injection system cleanly separates auth, rate limiting, and business logic
- Well-documented; large contributor-accessible ecosystem

### Negative / Trade-offs
- FastAPI does not include a built-in ORM, task queue, or admin interface (all provided by other library choices)
- Pydantic v2 is a breaking change from v1; care needed if third-party libraries require v1

### Risks
- Dependency on Starlette (FastAPI's base); Starlette updates must be monitored

## Status History

| Date | Status | Note |
|------|--------|------|
| 2026-09-02 | Accepted | Best option for async, typed, self-documenting Python API |
