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
