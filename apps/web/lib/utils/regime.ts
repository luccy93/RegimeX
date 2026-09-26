/**
 * RegimeX Web — Regime Semantics & Labeling Utility
 * ==================================================
 * Provides deterministic mapping of regime labels, IDs, and semantic tokens.
 *
 * Rules (per V19 Scope & Section 16):
 *   - Never assume 0 = Bull, 1 = Bear, 2 = Neutral unless the API explicitly establishes that mapping.
 *   - Canonical backend labels (e.g. REGIME_0, REGIME_1) render as "Regime 0", "Regime 1" with neutral styling.
 *   - Semantic tokens (bullish, bearish, transitioning, neutral, high-volatility, low-volatility)
 *     are applied only when explicitly conveyed by API metadata.
 *   - Unknown regimes render as "Unknown" with neutral styling.
 */

import type { StatusVariant } from "@/components/ui/StatusIndicator";

/**
 * Formats a raw regime label into a human-readable title.
 * Examples:
 *   "REGIME_0" -> "Regime 0"
 *   "REGIME_1" -> "Regime 1"
 *   "BULLISH" -> "Bullish"
 *   "LOW_VOLATILITY" -> "Low Volatility"
 *   "UNKNOWN" -> "Unknown"
 */
export function formatRegimeLabel(
  label: string | null | undefined,
  regimeId?: number | null
): string {
  if (!label || label.trim() === "" || label.toUpperCase() === "UNKNOWN") {
    return "Unknown";
  }

  const clean = label.trim();
  const upper = clean.toUpperCase();

  // Match pattern like REGIME_0, REGIME_1, R0, R1
  const canonicalMatch = upper.match(/^REGIME_?(\d+)$/i) || upper.match(/^R(\d+)$/i);
  if (canonicalMatch) {
    return `Regime ${canonicalMatch[1]}`;
  }

  // Convert SCREAMING_SNAKE_CASE to Title Case
  return clean
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Maps a regime label to a design system StatusIndicator variant.
 */
export function getRegimeStatusVariant(label: string | null | undefined): StatusVariant {
  if (!label) return "neutral";
  const upper = label.toUpperCase();

  if (upper.includes("BULL") || upper.includes("RISK_ON") || upper.includes("LOW_VOL")) {
    return "bullish";
  }
  if (upper.includes("BEAR") || upper.includes("RISK_OFF")) {
    return "bearish";
  }
  if (upper.includes("TRANSITION")) {
    return "transitioning";
  }
  if (upper.includes("NEUTRAL") || upper.includes("SIDEWAYS")) {
    return "neutral";
  }

  // For un-annotated canonical IDs (e.g. "REGIME_0", "REGIME_1"), use neutral
  return "neutral";
}

/**
 * Maps a regime label to its CSS badge class name from globals.css.
 */
export function getRegimeBadgeClass(label: string | null | undefined): string {
  if (!label) return "regime-neutral";
  const upper = label.toUpperCase();

  if (upper.includes("BULL") || upper.includes("RISK_ON")) {
    return "regime-bullish";
  }
  if (upper.includes("BEAR") || upper.includes("RISK_OFF")) {
    return "regime-bearish";
  }
  if (upper.includes("TRANSITION")) {
    return "regime-transitioning";
  }
  if (upper.includes("HIGH_VOL")) {
    return "regime-high-vol";
  }
  if (upper.includes("LOW_VOL")) {
    return "regime-low-vol";
  }

  return "regime-neutral";
}

/**
 * Maps a regime ID to a chart palette color index (0-7).
 */
export function getRegimeColorIndex(regimeId: number): number {
  return Math.abs(regimeId) % 8;
}

/**
 * Regime color entry for direct rendering (SVG, Canvas).
 */
export interface RegimeColorEntry {
  /** CSS variable reference (e.g. "var(--regime-bullish)") */
  cssVar: string;
  /** Raw hex color for use in SVG/Canvas where CSS vars are inaccessible */
  hex: string;
  /** Subtle/translucent version for background bands */
  hexSubtle: string;
  /** CSS variable for subtle variant */
  cssVarSubtle: string;
}

/**
 * Hardcoded color palette keyed by regime "class", indexed by
 * chart palette index for canonical regime IDs.
 */
const REGIME_PALETTE: RegimeColorEntry[] = [
  { cssVar: "var(--chart-0)", hex: "#3b82f6", hexSubtle: "rgba(59, 130, 246, 0.12)", cssVarSubtle: "var(--chart-0)" },
  { cssVar: "var(--chart-1)", hex: "#10b981", hexSubtle: "rgba(16, 185, 129, 0.12)", cssVarSubtle: "var(--chart-1)" },
  { cssVar: "var(--chart-2)", hex: "#f59e0b", hexSubtle: "rgba(245, 158, 11, 0.12)", cssVarSubtle: "var(--chart-2)" },
  { cssVar: "var(--chart-3)", hex: "#8b5cf6", hexSubtle: "rgba(139, 92, 246, 0.12)", cssVarSubtle: "var(--chart-3)" },
  { cssVar: "var(--chart-4)", hex: "#ef4444", hexSubtle: "rgba(239, 68, 68, 0.12)", cssVarSubtle: "var(--chart-4)" },
  { cssVar: "var(--chart-5)", hex: "#22d3ee", hexSubtle: "rgba(34, 211, 238, 0.12)", cssVarSubtle: "var(--chart-5)" },
  { cssVar: "var(--chart-6)", hex: "#f97316", hexSubtle: "rgba(249, 115, 22, 0.12)", cssVarSubtle: "var(--chart-6)" },
  { cssVar: "var(--chart-7)", hex: "#a3e635", hexSubtle: "rgba(163, 230, 53, 0.12)", cssVarSubtle: "var(--chart-7)" },
];

/** Semantic regime color map keyed by label keyword. */
const SEMANTIC_REGIME_COLORS: Record<string, RegimeColorEntry> = {
  BULL: { cssVar: "var(--regime-bullish)", hex: "#10b981", hexSubtle: "rgba(16, 185, 129, 0.12)", cssVarSubtle: "var(--regime-bullish-subtle)" },
  RISK_ON: { cssVar: "var(--regime-bullish)", hex: "#10b981", hexSubtle: "rgba(16, 185, 129, 0.12)", cssVarSubtle: "var(--regime-bullish-subtle)" },
  LOW_VOL: { cssVar: "var(--regime-low-vol)", hex: "#22d3ee", hexSubtle: "rgba(34, 211, 238, 0.12)", cssVarSubtle: "var(--regime-low-vol-subtle)" },
  BEAR: { cssVar: "var(--regime-bearish)", hex: "#ef4444", hexSubtle: "rgba(239, 68, 68, 0.12)", cssVarSubtle: "var(--regime-bearish-subtle)" },
  RISK_OFF: { cssVar: "var(--regime-bearish)", hex: "#ef4444", hexSubtle: "rgba(239, 68, 68, 0.12)", cssVarSubtle: "var(--regime-bearish-subtle)" },
  TRANSITION: { cssVar: "var(--regime-transitioning)", hex: "#f59e0b", hexSubtle: "rgba(245, 158, 11, 0.12)", cssVarSubtle: "var(--regime-transitioning-subtle)" },
  HIGH_VOL: { cssVar: "var(--regime-high-vol)", hex: "#c084fc", hexSubtle: "rgba(192, 132, 252, 0.12)", cssVarSubtle: "var(--regime-high-vol-subtle)" },
  NEUTRAL: { cssVar: "var(--regime-neutral)", hex: "#94a3b8", hexSubtle: "rgba(148, 163, 184, 0.12)", cssVarSubtle: "var(--regime-neutral-subtle)" },
  SIDEWAYS: { cssVar: "var(--regime-neutral)", hex: "#94a3b8", hexSubtle: "rgba(148, 163, 184, 0.12)", cssVarSubtle: "var(--regime-neutral-subtle)" },
};

/**
 * Returns the rendering color for a regime, resolving semantic labels first,
 * then falling back to palette index for canonical regime IDs.
 */
export function getRegimeColor(
  label: string | null | undefined,
  regimeId: number
): RegimeColorEntry {
  if (label) {
    const upper = label.toUpperCase();
    for (const [keyword, entry] of Object.entries(SEMANTIC_REGIME_COLORS)) {
      if (upper.includes(keyword)) {
        return entry;
      }
    }
  }

  // Fallback to chart palette by index
  const idx = getRegimeColorIndex(regimeId);
  return REGIME_PALETTE[idx];
}
