# RegimeX Shared Configuration

**Volume:** V04 — Monorepo Engineering Foundation  
**Status:** Structure established. Configuration schemas added in V05+.

---

## Purpose

This package contains **shared configuration schemas and defaults** used across multiple applications in the monorepo.

---

## What Belongs Here

- Shared ESLint configuration (`eslint.config.js`)
- Shared TypeScript base configuration (`tsconfig.base.json`)
- Shared Prettier/formatting configuration (if adopted)
- Environment variable schema documentation shared between apps

---

## What Does NOT Belong Here

- Application-specific runtime configuration → each app's own config module
- Secrets or credentials → injected by deployment environment only
- Business logic → domain modules
- Infrastructure scripts → `scripts/` directory

---

## Current Contents

V04 establishes the package structure. Configuration artifacts will be
added as the monorepo grows and shared configuration needs emerge organically.

Premature configuration abstraction is avoided per V04 scope constraints.
