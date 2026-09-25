/**
 * RegimeX Web — StatusIndicator Component
 * Volume 18 — Commit 02
 *
 * Domain-specific status indicator for market regime states, API health,
 * and system lifecycle statuses. Renders an animated dot + label.
 *
 * Domain status variants:
 *   - "bullish"       → green pulsing dot  (bull market / low-vol regime)
 *   - "bearish"       → red dot           (bear market / high-vol regime)
 *   - "transitioning" → amber pulsing dot  (transition / uncertainty)
 *   - "neutral"       → slate dot          (mixed / sideways)
 *   - "active"        → green steady dot   (system online)
 *   - "degraded"      → amber dot          (partial degradation)
 *   - "offline"       → red dot            (system offline / error)
 *   - "pending"       → blue pulsing dot   (loading / initializing)
 */
import React from "react";
import { cn } from "@/lib/utils/cn";

export type StatusVariant =
  | "bullish"
  | "bearish"
  | "transitioning"
  | "neutral"
  | "active"
  | "degraded"
  | "offline"
  | "pending";

export interface StatusIndicatorProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusVariant;
  label?: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

const STATUS_ARIA_LABELS: Record<StatusVariant, string> = {
  bullish: "Bullish regime",
  bearish: "Bearish regime",
  transitioning: "Transitioning regime",
  neutral: "Neutral regime",
  active: "System active",
  degraded: "System degraded",
  offline: "System offline",
  pending: "Pending",
};

export function StatusIndicator({
  status,
  label,
  showLabel = true,
  size = "md",
  pulse,
  className,
  ...props
}: StatusIndicatorProps) {
  const isPulsing =
    pulse ??
    (status === "bullish" || status === "transitioning" || status === "pending");

  const ariaLabel = label || STATUS_ARIA_LABELS[status];

  return (
    <span
      className={cn("ui-status-indicator", `ui-status-${size}`, className)}
      aria-label={ariaLabel}
      {...props}
    >
      <span
        className={cn(
          "ui-status-dot",
          `ui-status-dot-${status}`,
          isPulsing && "ui-status-dot-pulse"
        )}
        aria-hidden="true"
      />
      {showLabel && (
        <span className="ui-status-label">
          {label || STATUS_ARIA_LABELS[status]}
        </span>
      )}
    </span>
  );
}
