/**
 * RegimeX Web — ChartSlot Component
 * Volume 18 — Commit 02
 *
 * Reserved chart container / placeholder for V19+ chart integrations.
 * Provides:
 *   - Dimensioned container with consistent aspect ratios
 *   - Loading skeleton state
 *   - "Coming Soon" placeholder variant
 *   - Children slot for V19 chart injection
 *
 * V19 will inject real chart components (Recharts / Visx) into these slots.
 * This component establishes the consistent sizing contract and loading patterns.
 *
 * Supported height presets:
 *   - "compact"  → 14rem
 *   - "standard" → 22rem  (default)
 *   - "tall"     → 32rem
 *   - number     → inline px height
 */
import React from "react";
import { cn } from "@/lib/utils/cn";
import { Skeleton } from "./Skeleton";
import { Spinner } from "./Spinner";

export type ChartSlotHeight = "compact" | "standard" | "tall" | number;

export interface ChartSlotProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Chart title for accessibility and header display */
  title?: string;
  /** Chart description */
  description?: string;
  /** Height preset or numeric px value */
  height?: ChartSlotHeight;
  /** Whether chart data is loading */
  isLoading?: boolean;
  /** Whether to show the "coming soon" placeholder */
  comingSoon?: boolean;
  /** Version label for the coming-soon state */
  comingSoonVersion?: string;
  /** Custom empty label */
  emptyLabel?: string;
}

const HEIGHT_MAP: Record<string, string> = {
  compact: "14rem",
  standard: "22rem",
  tall: "32rem",
};

function resolveHeight(height: ChartSlotHeight): string {
  if (typeof height === "number") return `${height}px`;
  return HEIGHT_MAP[height] ?? HEIGHT_MAP.standard;
}

export function ChartSlot({
  title,
  description,
  height = "standard",
  isLoading = false,
  comingSoon = false,
  comingSoonVersion,
  emptyLabel,
  children,
  className,
  ...props
}: ChartSlotProps) {
  const resolvedHeight = resolveHeight(height);

  return (
    <div className={cn("chart-slot", className)} {...props}>
      {(title || description) && (
        <div className="chart-slot-header">
          {title && <h4 className="chart-slot-title">{title}</h4>}
          {description && (
            <p className="chart-slot-description">{description}</p>
          )}
        </div>
      )}

      <div
        className={cn(
          "chart-slot-body",
          isLoading && "chart-slot-body-loading",
          comingSoon && "chart-slot-body-placeholder"
        )}
        style={{ height: resolvedHeight }}
        role="img"
        aria-label={title ? `${title} chart area` : "Chart area"}
      >
        {isLoading ? (
          <div className="chart-slot-loading-state">
            <Spinner size="lg" />
            <p className="chart-slot-loading-text">Loading chart data…</p>
          </div>
        ) : comingSoon ? (
          <div className="chart-slot-placeholder-content">
            <span className="chart-slot-placeholder-icon" aria-hidden="true">
              📊
            </span>
            <p className="chart-slot-placeholder-label">
              {emptyLabel ?? "Chart visualization"}
            </p>
            {comingSoonVersion && (
              <span className="chart-slot-placeholder-version">
                Scheduled for {comingSoonVersion}
              </span>
            )}
          </div>
        ) : children ? (
          children
        ) : (
          <div className="chart-slot-placeholder-content">
            <span className="chart-slot-placeholder-icon" aria-hidden="true">
              📈
            </span>
            <p className="chart-slot-placeholder-label">
              {emptyLabel ?? "No chart data"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
