/**
 * RegimeX Web — Data Formatting Utilities
 * ========================================
 * Institutional-grade formatting functions for prices, percentages, dates,
 * durations, and numeric statistics.
 *
 * Guarantees:
 *   - Strict timezone-aware UTC preservation for dates.
 *   - Locale-aware number and currency formatting.
 *   - Safe handling of null, undefined, NaN, and Infinity (no undefined/NaN leakage).
 *   - Predictable decimal precision.
 */

export interface FormatPercentOptions {
  /** Whether the input value is a unit ratio (e.g., 0.12 = 12%) or percentage (12 = 12%). Default true. */
  isRatio?: boolean;
  /** Number of decimal places. Default 2. */
  decimals?: number;
  /** Explicitly include positive sign '+' for positive values. Default false. */
  includeSign?: boolean;
}

export interface FormatNumberOptions {
  /** Number of decimal places. Default 2. */
  decimals?: number;
  /** Compact notation (e.g. 1.2M, 45.3K). Default false. */
  compact?: boolean;
}

export type DateFormatVariant = "short" | "long" | "date-only" | "time-only" | "iso";

/**
 * Formats a currency/price value.
 * Example: formatPrice(512.45, "USD") -> "$512.45"
 */
export function formatPrice(
  value: number | null | undefined,
  currency: string = "USD"
): string {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
}

/**
 * Formats a percentage value.
 * Example: formatPercent(0.0425, { includeSign: true }) -> "+4.25%"
 */
export function formatPercent(
  value: number | null | undefined,
  options: FormatPercentOptions = {}
): string {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }

  const { isRatio = true, decimals = 2, includeSign = false } = options;
  const normalized = isRatio ? value * 100 : value;
  const formatted = Math.abs(normalized).toFixed(decimals);

  if (normalized > 0) {
    return includeSign ? `+${formatted}%` : `${formatted}%`;
  }
  if (normalized < 0) {
    return `−${formatted}%`;
  }
  return `${formatted}%`;
}

/**
 * Formats a timezone-aware ISO date string strictly in UTC.
 * Example: formatDate("2026-09-26T12:00:00Z", "short") -> "Sep 26, 2026"
 */
export function formatDate(
  isoString: string | null | undefined,
  variant: DateFormatVariant = "short"
): string {
  if (!isoString) return "—";

  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";

  if (variant === "iso") {
    return date.toISOString();
  }

  if (variant === "date-only") {
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    const day = String(date.getUTCDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  if (variant === "time-only") {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "UTC",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date) + " UTC";
  }

  if (variant === "long") {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "UTC",
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date) + " UTC";
  }

  // "short" default: "Sep 26, 2026"
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

/**
 * Formats an observation count or duration in bars/days.
 * Example: formatDuration(10, "bar") -> "10 bars"
 */
export function formatDuration(
  count: number | null | undefined,
  unit: string = "bar"
): string {
  if (count === null || count === undefined || typeof count !== "number" || !Number.isFinite(count)) {
    return "—";
  }

  const rounded = Math.round(count * 10) / 10;
  const isSingular = Math.abs(rounded - 1) < 0.001;
  const label = isSingular ? unit : `${unit}s`;
  return `${rounded} ${label}`;
}

/**
 * Formats general numeric values with precision control and optional compact notation.
 * Example: formatNumber(45200000, { compact: true }) -> "45.2M"
 */
export function formatNumber(
  value: number | null | undefined,
  options: FormatNumberOptions = {}
): string {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }

  const { decimals = 2, compact = false } = options;

  if (compact) {
    return new Intl.NumberFormat("en-US", {
      notation: "compact",
      compactDisplay: "short",
      maximumFractionDigits: decimals,
    }).format(value);
  }

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Formats a transition probability value (0 to 1).
 * Example: formatProbability(0.724) -> "0.724"
 */
export function formatProbability(
  value: number | null | undefined,
  decimals: number = 3
): string {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }
  return value.toFixed(decimals);
}

/**
 * Formats a transition entropy value in nats.
 * Example: formatEntropy(1.241) -> "1.24 nats"
 */
export function formatEntropy(
  value: number | null | undefined,
  decimals: number = 2
): string {
  if (value === null || value === undefined || typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }
  return `${value.toFixed(decimals)} nats`;
}
