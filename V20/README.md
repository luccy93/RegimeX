# RegimeX — Volume 20: Regime Analytics Workspace

## Official Commit 01
`feat(web): add regime analytics workspace`

> **Scope Declaration:**
> **V20 Commit 01 establishes the dedicated regime analytics workspace at `/app/regimes`.**
> **V20 Commit 02 will add risk and backtesting dashboards.**

---

## 1. Overview & Objective

Volume 20 Commit 01 transforms raw statistical regime classifications and empirical Markov transitions into a dedicated analytical workspace at `/app/regimes`.

Building on the market intelligence foundation established in V19, the workspace is designed specifically for quantitative investigation into:
- Current point-in-time regime assignments and empirical model confidence
- Observed regime distributions across verified sample windows
- Regime frequency, run counts, and continuous persistence probabilities
- Extreme and expected duration characteristics (mean, median, min, max, current run)
- Detailed feature statistics (mean, median, standard deviation, extrema) across regimes
- Empirical 1-step Markov transition probability matrices
- Regime change dynamics vs. diagonal persistence (self-transitions)
- Transition destination rankings and dispersion entropy
- Complete analytical methodology and model provenance

This is strictly a **descriptive and diagnostic analysis workspace**, not a trading interface or prediction engine. No buy/sell recommendations, forward-looking price targets, or subjective risk ratings are generated.

---

## 2. Route & Navigation

* **Route:** `/app/regimes`
* **URL-Driven State:** Market selection is persisted via query parameter:
  ```text
  /app/regimes?symbol=SPY
  ```
* **Browser Navigation:** Browser back, forward, and refresh synchronize state deterministically through Next.js `useSearchParams()` and `useRouter()`.
* **Default Instrument Selection:** If no symbol is specified in the URL, the workspace deterministically initializes with the first available instrument from the catalog.

---

## 3. Information Architecture & Workspace Layout

The workspace is organized into a modular analytical hierarchy:

```text
Regime Analytics Workspace (/app/regimes)
│
├── 1. Header & Market Selector
│      ├── Page title & subtitle
│      ├── Market selector dropdown (search, asset class filtering)
│      └── Context strip (active symbol, analysis window, sample size, regime count)
│
├── 2. Current Regime Summary
│      ├── Active regime label & ID
│      ├── Model confidence gauge (percentage & evaluation tier)
│      ├── Current duration vs. historical average & maximum duration
│      ├── Historical frequency & run count
│      └── Point-in-time active feature vector
│
├── 3. Regime Distribution
│      ├── Horizontal proportional observation track
│      └── Segment cards showing observation share (count / total * 100)
│
├── 4. Regime Frequency & Persistence
│      ├── Frequency & persistence analytical data table
│      ├── Step-to-step persistence probability: P(S_{t+1} = k | S_t = k)
│      └── Historical discovery window (first seen, last seen)
│
├── 5. Duration Analysis
│      ├── Comparative duration extents (average vs. maximum)
│      ├── Tabular duration statistics (mean, median, min, max, current run)
│      └── Discrete duration distribution disclosure
│
├── 6. Regime Profile Comparison & Feature Statistics
│      ├── Cross-regime feature statistics matrix (mean, median, std, extrema)
│      ├── Multi-stat filter view (Mean, Median, Std Dev, Min, Max, All)
│      └── Strict non-imputation standard (null values preserved as "—")
│
├── 7. Regime Change & Transition Analytics
│      ├── Global transition counters (changes, self-transitions, rates, edges)
│      ├── 1-step Markov transition probability matrix
│      │   ├── Diagonal: Persistence / Self-transition
│      │   └── Off-diagonal: Regime change
│      ├── Probability [0-1] and percentage (%) display toggle
│      ├── Transition destination rankings per regime
│      ├── Transition entropy in nats (destination dispersion)
│      └── Isolated error boundary with independent retry action
│
└── 8. Analytical Methodology & Provenance
       ├── Engine model name, model version, and underlying algorithm
       ├── Feature set, observation interval, and temporal sample bounds
       └── Explicit diagnostic scope and reproducibility declaration
```

---

## 4. API Dependencies & Data Layer

All analytical metrics are derived directly from the production FastAPI backend without synthetic or client-estimated approximations:

| Endpoint | Method | Purpose in Workspace |
| :--- | :---: | :--- |
| `/api/v1/markets` | `GET` | Instrument catalog discovery and market selector options |
| `/api/v1/markets/{symbol}/regime` | `GET` | Current regime state, duration metrics, frequency, and feature profiles |
| `/api/v1/markets/{symbol}/regime/transitions` | `GET` | Empirical transition matrix, change counts, persistence rates, entropy |

### Focused Data Layer (`apps/web/lib/api/regimes.ts`)

A dedicated API wrapper provides typed methods and defensive data validation:
- `getRegimeAnalytics(symbol, params)`: Queries regime context and profile statistics.
- `fetchRegimeTransitions(symbol, params)`: Queries empirical transition matrices.
- `isValidFiniteNumber(val)`: Verifies numeric inputs against NaN / Infinity.
- `isValidProbability(val)`: Enforces probabilities in $[0, 1]$.
- `isValidTransitionMatrix(matrix, expectedSize)`: Validates $N \times N$ matrix dimensions and values.
- `computeRegimeDistributionPercentages(profiles, totalObservations)`: Computes percentages strictly as $\frac{\text{count}}{\text{total}} \times 100$ without division-by-zero risk.

---

## 5. Statistical Rigor & Data Integrity Standards

1. **Non-Imputation Standard (Section 15):**
   The backend explicitly avoids zero-imputation for missing feature statistics. Missing, null, or non-finite values are never converted to `0` or `0.00%`. They are rendered as `—` (em-dash) or `Unavailable`.

2. **Persistence vs. Duration (Section 11 & 21):**
   - **Persistence Rate:** The conditional 1-step probability of remaining in state $k$ given state $k$ at time $t$:
     $$P(S_{t+1} = k \mid S_t = k)$$
     Reflected on the diagonal of the transition matrix.
   - **Duration:** The length of continuous observation runs in state $k$, measured strictly in observation bars.

3. **Transition Entropy (Section 22):**
   Computed as Shannon entropy over outgoing transition distributions in nats:
   $$H(S_k) = -\sum_{j} P_{kj} \ln P_{kj}$$
   Entropy measures destination dispersion (degree of multi-state branching). It is strictly descriptive and is never labeled as "risk" or "danger".

4. **Discrete Duration Distribution (Section 13):**
   Because individual run duration histograms are not exposed in the summary payload, the workspace explicitly communicates:
   *"Detailed duration distribution unavailable — empirical discrete histogram data is not exposed in the API summary payload."*
   No synthetic or pseudo-random histograms are fabricated.

5. **No Predictive Claims (Section 23 & 26):**
   All historical duration comparisons (e.g. current run vs. historical average) are framed descriptively. No speculative statements ("a change is likely soon") are permitted.

---

## 6. Error Isolation & Resilient UX

- **Independent Section Loading:** The workspace uses granular loading skeletons (`Card`, `DataTable`, `MetricCard`, `Skeleton`) so that fast responses render immediately.
- **Isolated Transition Failure:** If `/api/v1/markets/{symbol}/regime/transitions` returns an error (e.g., 404 or insufficient sample length), the regime profile summary and feature statistics continue to display normally. An isolated error alert with a dedicated retry button is rendered only within the transition section.
- **Empty States:** Gracefully handles empty catalogs, unclassified symbols, and instruments with zero transition events.

---

## 7. Accessibility & Responsive Design

- **Semantic Landmarks:** Proper HTML5 `<header>`, `<section>`, `<aside>`, `<h1>`, `<h2>`, and `<h3>` heading hierarchies.
- **Screen Reader Support:** Accessible captions on analytical tables (`caption` element), `scope="col"` and `scope="row"` headers, and `sr-only` landmark descriptions.
- **Color Independence:** Regime states are identified by text labels and badges in addition to semantic colors.
- **Tabular Numerals:** All financial statistics and probabilities use CSS tabular numerals (`font-family: var(--font-mono)`).
- **Responsive Breakpoints:**
  - **Desktop (1200px+):** Multi-column metrics grids, side-by-side matrices.
  - **Tablet (768px - 1024px):** 2-column stacked metric cards, responsive table wrapping.
  - **Mobile (< 768px):** Single-column stacked metrics, horizontal scrolling on wide data tables with zero page-level horizontal overflow.

---

## 8. Verification & Quality Gates

### Frontend Quality Suite (`apps/web`)

```bash
npm test         # 133 passing unit & integration tests
npm run lint     # Next.js ESLint clean (0 errors, 0 warnings)
npm run type-check # TypeScript 5.5 compiler clean (tsc --noEmit)
npm run build    # Next.js 14 production bundle verified
```

### Backend Quality Suite (`apps/api`)

```bash
python -m pytest tests/ -v --tb=short
python -m ruff check app tests
python -m ruff format --check app tests
python -m mypy app tests
```

---

## 9. Next Steps

- **V20 Commit 01:** Established the dedicated regime analytics workspace at `/app/regimes`.
- **V20 Commit 02:** Will deliver the quantitative risk analytics dashboard and backtesting execution interface.
