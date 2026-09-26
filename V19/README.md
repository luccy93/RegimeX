# RegimeX — Volume 19: Market Intelligence Dashboard

## Official Commit 01
`feat(web): add market intelligence dashboard`

> **Scope Declaration:**
> **V19 Commit 01 establishes the production Market Intelligence Dashboard on top of the V18 design system.**
> **Advanced interactive regime visualization is intentionally deferred to V19 Commit 02.**

---

## 1. Overview & Objective

Volume 19 Commit 01 delivers the first domain-specific frontend experience for RegimeX: the **Market Intelligence Dashboard** at `/app/markets`.

The dashboard provides an institutional quantitative workspace for analyzing:
- Discoverable tradeable markets across asset classes
- Time-series OHLCV market data and historical price action
- Point-in-time statistical regime assignments and persistence metrics
- Empirical regime confidence scores emitted by backend models
- Historical regime profile distributions across the observation window
- Active feature distributions (mean, median, standard deviation, min, max)
- Strict data health, sample window verification, and model provenance
- Seamless navigation into future analytics (Transition Matrix in Commit 02, Risk Analytics in V20)

All data is consumed exclusively from the production **FastAPI v1 REST endpoints** (`/api/v1/markets`, `/api/v1/markets/{symbol}/data`, `/api/v1/markets/{symbol}/regime`). No fake or client-estimated data is introduced.

---

## 2. Information Architecture & Hierarchy

The page is structured to provide an immediate, clear analytical hierarchy:

```text
Market Identification & Catalog Selection
  ↓
Current Regime Context & Confidence
  ↓
Market Snapshot Metrics (Price, Return, Volatility, Regime, Confidence)
  ↓
Price / Data History (Interactive SVG Line & Area Visualization with Tooltip HUD)
  ↓
Regime Context & Duration / Persistence Analytics
  ↓
Historical Regime Breakdown & Empirical Distribution
  ↓
Data Health, Timestamp Verification & Engine Provenance
```

---

## 3. Component Architecture

The dashboard is built from modular, typed, accessible domain components located in `apps/web/components/markets/`:

```text
apps/web/
├── app/
│   └── app/
│       └── markets/
│           └── page.tsx              # Server Component (Header, Breadcrumbs, Suspense boundary)
├── components/
│   └── markets/
│       ├── MarketDashboard.tsx       # Client Coordinator (URL sync, API fetching, error handling)
│       ├── MarketSelector.tsx        # Searchable instrument dropdown & combobox
│       ├── MarketOverviewHeader.tsx  # Market title, status banner, active regime pill
│       ├── MarketSnapshot.tsx        # 5 MetricCards (Price, Return, Volatility, Regime, Confidence)
│       ├── MarketPriceChart.tsx      # SVG price history chart on ChartSlot foundation
│       ├── CurrentRegimeCard.tsx     # Current regime context, confidence meter, feature statistics
│       ├── RegimeHistory.tsx         # Observed regime profiles, distribution bar, and run metrics
│       ├── DataHealth.tsx            # API feed status, observation window, and engine provenance
│       └── index.ts                  # Public barrel export
└── lib/
    └── utils/
        ├── formatters.ts             # formatPrice, formatPercent, formatDate, formatDuration, formatNumber
        └── regime.ts                 # formatRegimeLabel, getRegimeStatusVariant, getRegimeBadgeClass
```

### Server / Client Boundaries
- `app/app/markets/page.tsx` is an App Router **Server Component**. It establishes page metadata, breadcrumbs landmark navigation, and wraps dynamic client components in a React `<Suspense>` boundary with a zero-layout-shift skeleton fallback.
- `MarketDashboard.tsx` is a **Client Component** (`"use client"`). It coordinates browser URL state (`?symbol=SPY`), executes concurrent API requests, orchestrates request cancellation via `AbortController`, and manages loading, error, and empty states.

---

## 4. API Dependencies & Data Integration

The dashboard consumes existing FastAPI v1 endpoints via the typed frontend client (`apps/web/lib/api/`):

| Endpoint | Method | Purpose | Response Model |
| :--- | :--- | :--- | :--- |
| `/api/v1/markets` | `GET` | Instrument catalog discovery | `MarketListResponse` |
| `/api/v1/markets/{symbol}/data` | `GET` | Historical OHLCV bars (1d interval, UTC) | `MarketDataResponse` |
| `/api/v1/markets/{symbol}/regime` | `GET` | Active regime assignment & profiles | `MarketRegimeResponse` |

### Parameter Constraints & Handling
- **Interval**: Fixed to `1d` daily aggregation for the macro regime dashboard.
- **Timestamps**: Strictly timezone-aware UTC ISO 8601 strings (`start` < `end`). The frontend formats dates in UTC via `Intl.DateTimeFormat` with `timeZone: "UTC"`.
- **Concurrency & Cancellation**: When the user switches symbols, previous in-flight requests are immediately aborted using `AbortController.abort()`, preventing race-condition overwrites.

---

## 5. Market URL State & Navigation

- **URL Pattern**: `/app/markets?symbol=SPY`
- **Synchronization**: `next/navigation` hooks (`useSearchParams`, `useRouter`) ensure refresh persistence, browser back/forward navigation, and shareable deep links.
- **Deterministic Default**: If no symbol query parameter is present in the URL, the dashboard deterministically selects the first valid instrument from the catalog (typically `SPY`) and replaces the URL without full-page reloads.
- **Validation**: If a requested symbol is not present in the catalog, a non-blocking warning notice is displayed while attempting direct time-series retrieval.

---

## 6. Regime Semantics & Labeling Invariants

In strict compliance with V19 design rules:
1. **No Assumed Mapping**: Numerical regime IDs (`REGIME_0`, `REGIME_1`) are **never** arbitrarily assumed to mean Bullish or Bearish. They render as `"Regime 0"`, `"Regime 1"` with neutral styling.
2. **Semantic Tokens**: Semantic color variants (`bullish`, `bearish`, `transitioning`, `neutral`, `high-volatility`, `low-volatility`) are applied only when explicit semantic tokens or keywords are provided by backend metadata.
3. **Unknown States**: Unclassified or empty regimes render as `"Unknown"` with neutral styling.
4. **Confidence**: Emitted confidence scores (e.g. `0.884`) are displayed as percentage ratios (`88.4%`). When `null`, the UI explicitly displays `"Unavailable"`—no synthetic confidence formula is fabricated.

---

## 7. Responsive Layout Strategy

- **Desktop (>= 1280px)**: 5-column metric snapshot grid; full-width price action visualizer; 2-column side-by-side regime context and historical profiles; 4-column data health grid.
- **Tablet (768px - 1024px)**: 2-to-3-column metric cards; stacked single-column regime grid; 2-column data health layout.
- **Mobile (< 768px)**: Single-column metric stacking; collapsible market selector; horizontally scrollable HUD strip; safe SVG chart scaling without unintended viewport overflow.

---

## 8. Accessibility & Reduced Motion

- **Landmarks & Headings**: Semantic HTML5 structure (`main`, `header`, `section`, `table`).
- **Combobox & Listbox**: Full ARIA roles (`role="listbox"`, `role="option"`, `aria-selected`, `aria-expanded`, `aria-haspopup`) with Escape-key dismiss.
- **Visual Fallbacks**: SVG charts include an accessible screen-reader-only data table summarising the recent OHLCV bar series.
- **Focus Rings**: High-contrast 2px focus indicators on all interactive triggers and inputs.
- **Reduced Motion**: Disables transitions and animations when `prefers-reduced-motion: reduce` is active.

---

## 9. Quality Verification & Test Suite

All quality gates pass without warnings or errors:

- **Frontend Tests (`npm test`)**: 80 passing tests across 15 test files:
  - `tests/market-selector.test.ts`: Loading, empty, available catalog, and selection.
  - `tests/market-snapshot.test.ts`: Real API-shaped metrics, unavailable values, NaN protection, skeleton loading.
  - `tests/regime-card.test.ts`: Known regimes, unknown regimes, confidence meter, error boundaries.
  - `tests/market-price-chart.test.ts`: SVG path generation, HUD strip, empty/loading/error states, accessible table.
  - `tests/regime-history-and-health.test.ts`: Distribution bar, profiles table, feed health, and provenance.
  - `tests/market-dashboard.test.ts`: Page landmark integration, header state transitions.
  - `tests/formatters.test.ts`: Price, percent, UTC date, duration, and number precision.
- **TypeScript (`npm run type-check`)**: Strict type-checking clean (`tsc --noEmit`).
- **Linting (`npm run lint`)**: Clean Next.js ESLint execution.
- **Production Build (`npm run build`)**: Optimized Next.js production build succeeded.
- **Backend Quality**: 1,281 pytest passing, Ruff clean, Ruff format check clean, Mypy clean.
