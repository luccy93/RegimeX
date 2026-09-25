# RegimeX — Volume 18: Web Platform Foundation

## Official Commit 01
`feat(web): initialize RegimeX web platform`

> **Scope Declaration:**
> **V18 Commit 01 establishes the web platform foundation.**
> **Market dashboards and advanced analytics are intentionally deferred to V19/V20.**

---

## 1. Overview & Primary Objective

Volume 18 establishes the production-grade **Next.js web platform foundation** for RegimeX. The web platform serves as the presentation boundary through which quantitative researchers, portfolio risk analysts, and engineers interact with the platform.

### Target Architecture

```text
Browser
  ↓
Next.js Web Application (apps/web)
  ↓
Typed API Client (apps/web/lib/api)
  ↓
RegimeX FastAPI v1 REST Service (apps/api)
  ↓
Application Services & Orchestration
  ↓
Domain Layer (Pure Python Models & Statistical Engines)
```

The frontend application architecture is constructed with institutional rigor, adhering to analytical, technical, calm design principles rather than decorative or gaming aesthetics.

---

## 2. Directory Structure & App Router Architecture

The web application is located in `apps/web/` and uses Next.js 14 App Router:

```text
apps/web/
├── app/
│   ├── app/                      # Platform console routes
│   │   ├── backtesting/page.tsx  # Backtesting placeholder (V20)
│   │   ├── layout.tsx            # Console layout with AppShell
│   │   ├── loading.tsx           # Console loading boundary
│   │   ├── markets/page.tsx      # Market discovery placeholder (V19)
│   │   ├── page.tsx              # Console overview page
│   │   ├── regimes/page.tsx      # Regime detection placeholder (V19)
│   │   ├── research/page.tsx     # Research assistant placeholder (V21)
│   │   └── risk/page.tsx         # Risk analytics placeholder (V20)
│   ├── error.tsx                 # Root application error boundary
│   ├── globals.css               # Centralized tokens & design system styles
│   ├── layout.tsx                # Root layout with metadata and viewport
│   ├── loading.tsx               # Root loading boundary
│   ├── not-found.tsx             # Accessible 404 handler
│   └── page.tsx                  # Public landing page
├── components/
│   ├── feedback/
│   │   └── ErrorBoundaryView.tsx # Accessible error state presenter
│   ├── layout/
│   │   ├── AppHeader.tsx         # Shell header with platform status
│   │   ├── AppSidebar.tsx        # Shell sidebar with module navigation
│   │   ├── AppShell.tsx          # Master application shell
│   │   ├── LandingFooter.tsx     # Public footer
│   │   └── LandingHeader.tsx     # Public header
│   ├── navigation/
│   │   ├── Breadcrumbs.tsx       # Semantic breadcrumbs
│   │   └── NavItem.tsx           # Accessible navigation link
│   └── ui/                       # Foundational UI primitives
│       ├── Alert.tsx
│       ├── Badge.tsx
│       ├── Button.tsx
│       ├── Card.tsx
│       ├── EmptyState.tsx
│       ├── ErrorState.tsx
│       ├── Input.tsx
│       ├── Select.tsx
│       ├── Skeleton.tsx
│       ├── Spinner.tsx
│       └── index.ts
├── lib/
│   ├── api/                      # Typed API client module
│   │   ├── auth.ts               # Authentication client & token storage
│   │   ├── client.ts             # Fetch wrapper & request builder
│   │   ├── errors.ts             # Classified error models & translators
│   │   ├── health.ts             # Diagnostic and liveness endpoints
│   │   ├── index.ts              # Module exports
│   │   ├── markets.ts            # Market intelligence endpoints
│   │   └── types.ts              # Backend schema contracts (FastAPI v1)
│   ├── api-client.ts             # Backward compatibility adapter
│   ├── config/
│   │   └── env.ts                # Environment configuration & URL sanitizer
│   └── utils/
│       └── cn.ts                 # Classname utility
└── tests/                        # Frontend test suite
    ├── api-client.test.ts        # Fetch, error envelopes, and request ID
    ├── auth-client.test.ts       # In-memory tokens & Bearer headers
    ├── env-config.test.ts        # Base URL normalization & security
    ├── error-boundary.test.ts    # Error boundary rendering & digest
    ├── loader.mjs                # ESM loader for Node test runner
    ├── not-found.test.ts         # 404 page accessibility
    ├── root-page.test.ts         # Landing page landmarks & branding
    ├── shell.test.ts             # AppShell, header, sidebar landmarks
    └── ui-primitives.test.ts     # Primitives behavior & accessibility
```

---

## 3. Design System & Tokens

The platform employs a centralized, variable-driven design token system in `apps/web/app/globals.css`.

### Tokens

| Token Family | CSS Variables | Purpose |
|---|---|---|
| **Surfaces** | `--background`, `--surface`, `--surface-muted`, `--surface-elevated` | Dark analytical palette with depth hierarchy |
| **Borders** | `--border`, `--border-subtle`, `--border-focus` | Crisp structural separation |
| **Typography** | `--foreground`, `--muted-foreground`, `--text-muted` | High-contrast WCAG AA accessible text |
| **Brand** | `--primary`, `--primary-hover`, `--primary-foreground` | Deep blue interactive accents (`#2563eb`) |
| **Semantics** | `--success`, `--warning`, `--danger`, `--info` | State indicators and alert themes |
| **Spacing** | `--spacing-1` (4px) through `--spacing-24` (96px) | Standardized 4px baseline rhythm |
| **Radius** | `--radius-sm` (4px) through `--radius-full` (9999px) | Subdued rounded corners |
| **Typography Scale** | `--font-size-xs` (12px) through `--font-size-4xl` (36px) | Clear visual hierarchy |
| **Numerical Format** | `.tabular-nums` (`font-variant-numeric: tabular-nums`) | Precise tabular alignment for market figures |
| **Z-Index** | `--z-base`, `--z-dropdown`, `--z-sticky`, `--z-header`, `--z-modal`, `--z-tooltip` | Strict stacking order |
| **Motion** | `--transition-fast`, `--transition-base`, `--transition-slow` | Subtle micro-interactions with reduced-motion fallbacks |

---

## 4. Typed API Client & Backend Contracts

The frontend API client communicates directly with the FastAPI backend through the canonical REST endpoints established in Volumes 16 and 17.

### Contract Alignments

* **Error Envelope:**
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Human-readable description",
      "request_id": "uuid",
      "details": []
    }
  }
  ```
* **Supported Endpoints:**
  * `GET /health` & `GET /ready` (Liveness & readiness probes)
  * `GET /api/v1/markets` (Instrument discovery)
  * `GET /api/v1/markets/{symbol}/data` (Historical OHLCV bars)
  * `GET /api/v1/markets/{symbol}/regime` (Current regime & historical profile)
  * `GET /api/v1/markets/{symbol}/regime/transitions` (Transition probability matrix & entropy)
  * `POST /api/v1/auth/register` (Argon2id user registration)
  * `POST /api/v1/auth/login` (Credential authentication & JWT access token)
  * `GET /api/v1/auth/me` (Authenticated identity profile)

---

## 5. Security Boundary & Authentication Client

1. **No Secret Leakage:**
   * Browser bundles ONLY expose `NEXT_PUBLIC_*` variables.
   * Privileged secrets (e.g. `AUTH_JWT_SECRET`, database passwords) never exist in the web application code.
2. **Credential Safety:**
   * Passwords and access tokens are NEVER stored in `localStorage`, session storage, or logged.
   * Access tokens are held in-memory (`MemoryTokenStorage`).
   * Clean `logout()` zeroes out active in-memory tokens.
   * Tokens are NEVER passed in URL parameters or query strings.

---

## 6. Accessibility & Responsive Strategy

* **Landmarks:** Every view renders semantic HTML elements (`<header>`, `<nav>`, `<aside>`, `<main id="main-content">`, `<footer>`).
* **Skip Link:** Keyboard users can press Tab to immediately focus `.skip-to-content` and bypass navigation.
* **Focus States:** High-visibility `:focus-visible` ring using `--focus` with an outline offset.
* **Reduced Motion:** Dedicated `@media (prefers-reduced-motion: reduce)` block disables transitions and animations.
* **Responsive Layouts:**
  * Desktop / Wide (>1024px): Multi-column layouts with fixed-width navigation sidebar.
  * Tablet (768px – 1024px): Condensed sidebar and 2-column card grids.
  * Mobile (<768px): Vertical stacking, hidden non-essential chrome, and horizontal scroll containment for analytical data.

---

## 7. Quality Gates & Verification

All quality gates pass without warnings or workarounds:

| Gate | Tool | Command | Status |
|---|---|---|---|
| **Frontend Tests** | Node.js Test Runner | `npm test` | **26 passed, 0 failed** |
| **Frontend Lint** | Next.js ESLint | `npm run lint` | **Clean (0 errors, 0 warnings)** |
| **Frontend Types** | TypeScript Compiler | `npm run type-check` | **Clean (0 errors)** |
| **Frontend Build** | Next.js Compiler | `npm run build` | **Clean (10 static routes generated)** |
| **Backend Regression** | Pytest | `python -m pytest tests/` | **1281 passed, 1 skipped** |
| **Backend Lint** | Ruff | `ruff check app/ tests/` | **All checks passed** |
| **Backend Formatting** | Ruff Format | `ruff format --check app/ tests/` | **354 files formatted** |
| **Backend Types** | Mypy | `mypy app tests` | **Success (354 source files clean)** |

---

## 8. Limitations & Deferred Scope

* **No Full Dashboard:** Real-time dashboards, charts, and metric drill-downs belong to **Volume 19** (Market Dashboard).
* **No Advanced Visualizations:** Regime timelines, cluster scatter-plots, and transition heatmaps belong to **Volume 19**.
* **No Risk / Backtest Execution UI:** Interactive parameter tuning and performance tear-sheets belong to **Volume 20**.
* **No AI Research Chat:** Conversational quant research workspace belongs to **Volume 21**.
