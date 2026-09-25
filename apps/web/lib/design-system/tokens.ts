/**
 * RegimeX Web — Design System Token Manifest
 * Volume 18 — Commit 02
 *
 * Typed TypeScript mirror of the CSS custom properties defined in globals.css.
 * Provides:
 *   - Runtime token access (for canvas drawing, dynamic styles, etc.)
 *   - Single source of truth cross-referenced in globals.css
 *   - Type-safe constants for downstream consumers (chart, test, storybook)
 *
 * All values must stay in sync with the :root block in globals.css.
 * DO NOT import this in components that consume CSS variables — use CSS instead.
 * Use this module only when CSS variables are inaccessible (e.g. canvas APIs).
 */

// ─────────────────────────────────────────────────────────────────────────────
// 1. Surface & Background Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const surface = {
  background: "#090d16",
  surface: "#0f172a",
  surfaceMuted: "#0b1120",
  surfaceElevated: "#162036",
  surfaceGlass: "rgba(15, 23, 42, 0.72)",
  surfaceGlassStrong: "rgba(15, 23, 42, 0.88)",
  surfaceOverlay: "rgba(9, 13, 22, 0.6)",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 2. Border Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const border = {
  border: "#1e293b",
  borderSubtle: "#131c2e",
  borderFocus: "#3b82f6",
  borderStrong: "#334155",
  borderGlass: "rgba(255, 255, 255, 0.06)",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 3. Typography / Foreground Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const foreground = {
  foreground: "#f8fafc",
  mutedForeground: "#94a3b8",
  textMuted: "#64748b",
  textDisabled: "#475569",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 4. Brand / Interactive Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const brand = {
  primary: "#2563eb",
  primaryHover: "#1d4ed8",
  primaryLight: "#3b82f6",
  primaryForeground: "#ffffff",
  primarySubtle: "rgba(37, 99, 235, 0.12)",
  focus: "#60a5fa",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 5. Semantic State Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const semanticColors = {
  success: "#10b981",
  successSubtle: "rgba(16, 185, 129, 0.12)",
  successForeground: "#34d399",
  successBorder: "rgba(16, 185, 129, 0.3)",

  warning: "#f59e0b",
  warningSubtle: "rgba(245, 158, 11, 0.12)",
  warningForeground: "#fbbf24",
  warningBorder: "rgba(245, 158, 11, 0.3)",

  danger: "#ef4444",
  dangerSubtle: "rgba(239, 68, 68, 0.12)",
  dangerForeground: "#f87171",
  dangerBorder: "rgba(239, 68, 68, 0.3)",

  info: "#0284c7",
  infoSubtle: "rgba(2, 132, 199, 0.12)",
  infoForeground: "#38bdf8",
  infoBorder: "rgba(2, 132, 199, 0.3)",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 6. Market Regime Domain Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const regimeColors = {
  /** Bull / Low-Volatility / Risk-On regimes */
  bullish: "#10b981",
  bullishSubtle: "rgba(16, 185, 129, 0.15)",
  bullishForeground: "#34d399",

  /** Bear / High-Volatility / Risk-Off regimes */
  bearish: "#ef4444",
  bearishSubtle: "rgba(239, 68, 68, 0.15)",
  bearishForeground: "#f87171",

  /** Transition / Uncertainty regimes */
  transitioning: "#f59e0b",
  transitioningSubtle: "rgba(245, 158, 11, 0.15)",
  transitioningForeground: "#fbbf24",

  /** Neutral / Sideways / Mixed regimes */
  neutral: "#94a3b8",
  neutralSubtle: "rgba(148, 163, 184, 0.15)",
  neutralForeground: "#cbd5e1",

  /** High-Volatility specific accent */
  highVolatility: "#c084fc",
  highVolatilitySubtle: "rgba(192, 132, 252, 0.12)",
  highVolatilityForeground: "#d8b4fe",

  /** Low-Volatility / Compression */
  lowVolatility: "#22d3ee",
  lowVolatilitySubtle: "rgba(34, 211, 238, 0.12)",
  lowVolatilityForeground: "#67e8f9",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 7. Data Visualization Palette
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Ordered 8-color palette for multi-series chart traces.
 * Colors are perceptually distinct and accessible on dark backgrounds.
 */
export const chartPalette = [
  "#3b82f6", // blue-500 — primary series
  "#10b981", // emerald-500 — secondary series
  "#f59e0b", // amber-500 — tertiary series
  "#8b5cf6", // violet-500 — quaternary series
  "#ef4444", // red-500 — quinary / alert series
  "#22d3ee", // cyan-400 — senary series
  "#f97316", // orange-500 — septenary series
  "#a3e635", // lime-400 — octonary series
] as const;

export type ChartPaletteIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;

// ─────────────────────────────────────────────────────────────────────────────
// 8. Typography Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const typography = {
  fontFamilySans:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  fontFamilyMono:
    'ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, "Liberation Mono", monospace',

  fontSizeXs: "0.75rem",   // 12px
  fontSizeSm: "0.875rem",  // 14px
  fontSizeBase: "1rem",    // 16px
  fontSizeLg: "1.125rem",  // 18px
  fontSizeXl: "1.25rem",   // 20px
  fontSize2xl: "1.5rem",   // 24px
  fontSize3xl: "1.875rem", // 30px
  fontSize4xl: "2.25rem",  // 36px

  fontWeightNormal: 400,
  fontWeightMedium: 500,
  fontWeightSemibold: 600,
  fontWeightBold: 700,

  lineHeightTight: 1.25,
  lineHeightBase: 1.5,
  lineHeightRelaxed: 1.7,
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 9. Spacing Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const spacing = {
  spacing1: "0.25rem",  // 4px
  spacing2: "0.5rem",   // 8px
  spacing3: "0.75rem",  // 12px
  spacing4: "1rem",     // 16px
  spacing5: "1.25rem",  // 20px
  spacing6: "1.5rem",   // 24px
  spacing8: "2rem",     // 32px
  spacing10: "2.5rem",  // 40px
  spacing12: "3rem",    // 48px
  spacing16: "4rem",    // 64px
  spacing20: "5rem",    // 80px
  spacing24: "6rem",    // 96px
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 10. Border Radius Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const radius = {
  sm: "0.25rem",   // 4px
  base: "0.375rem",// 6px
  md: "0.5rem",    // 8px
  lg: "0.75rem",   // 12px
  xl: "1rem",      // 16px
  full: "9999px",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 11. Shadow Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const shadows = {
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
  base: "0 2px 4px 0 rgba(0, 0, 0, 0.3)",
  md: "0 4px 12px 0 rgba(0, 0, 0, 0.4)",
  lg: "0 10px 24px 0 rgba(0, 0, 0, 0.55)",
  glass: "0 4px 24px 0 rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
  glow: "0 0 20px rgba(37, 99, 235, 0.25)",
  glowGreen: "0 0 20px rgba(16, 185, 129, 0.2)",
  glowRed: "0 0 20px rgba(239, 68, 68, 0.2)",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 12. Motion / Transition Tokens
// ─────────────────────────────────────────────────────────────────────────────

export const motion = {
  durationInstant: "75ms",
  durationFast: "150ms",
  durationBase: "200ms",
  durationSlow: "300ms",
  durationVerySlow: "500ms",

  easingDefault: "ease",
  easingLinear: "linear",
  easingIn: "cubic-bezier(0.4, 0, 1, 1)",
  easingOut: "cubic-bezier(0, 0, 0.2, 1)",
  easingInOut: "cubic-bezier(0.4, 0, 0.2, 1)",
  easingSpring: "cubic-bezier(0.34, 1.56, 0.64, 1)",

  transitionFast: "150ms ease",
  transitionBase: "200ms ease",
  transitionSlow: "300ms ease",
  transitionSpring: "300ms cubic-bezier(0.34, 1.56, 0.64, 1)",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 13. Z-Index Hierarchy
// ─────────────────────────────────────────────────────────────────────────────

export const zIndex = {
  base: 0,
  raised: 5,
  dropdown: 10,
  sticky: 20,
  header: 30,
  modal: 40,
  tooltip: 50,
  toast: 60,
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 14. Layout Constants
// ─────────────────────────────────────────────────────────────────────────────

export const layout = {
  headerHeight: "4rem",
  sidebarWidth: "16.5rem",
  maxWidthContent: "80rem",
  maxWidthProse: "68ch",
  maxWidthNarrow: "48rem",
  chartMinHeight: "18rem",
  chartDefaultHeight: "22rem",
  chartTallHeight: "32rem",
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 15. Aggregated Token Map
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Full aggregated design token export.
 * Use individual named exports where possible for better tree-shaking.
 */
export const tokens = {
  surface,
  border,
  foreground,
  brand,
  semanticColors,
  regimeColors,
  chartPalette,
  typography,
  spacing,
  radius,
  shadows,
  motion,
  zIndex,
  layout,
} as const;

export type Tokens = typeof tokens;
