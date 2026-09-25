/**
 * RegimeX Web — MetricCard Component
 * Volume 18 — Commit 02
 *
 * Domain-specific analytical metric card for displaying:
 *   - Regime classification stats
 *   - Risk metrics (VaR, CVaR, Sharpe)
 *   - Market statistics (volatility, return, Sharpe ratio)
 *   - API health counters
 *
 * Features:
 *   - Typed trend direction (up/down/flat)
 *   - Semantic color for trend
 *   - Optional sparkline slot (future chart integration)
 *   - Skeleton loading state
 *   - Accessible number formatting
 */
import React from "react";
import { cn } from "@/lib/utils/cn";
import { Skeleton } from "./Skeleton";

export type MetricTrend = "up" | "down" | "flat" | "none";

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Metric label / title */
  label: string;
  /** Primary metric value — pass a pre-formatted string */
  value: string | number;
  /** Optional secondary value or unit annotation */
  unit?: string;
  /** Optional description / sub-label */
  description?: string;
  /** Trend direction — drives semantic color */
  trend?: MetricTrend;
  /** Change text (e.g. "+2.4%" or "−0.8 σ") */
  change?: string;
  /** Invert trend semantics — bearish metrics where "down" is positive */
  invertTrendSemantics?: boolean;
  /** Whether the card is loading */
  isLoading?: boolean;
  /** Optional React node for sparkline / mini chart slot */
  sparkline?: React.ReactNode;
  /** Optional icon or emoji prefix */
  icon?: React.ReactNode;
  /** Card size variant */
  size?: "sm" | "md" | "lg";
}

function TrendArrow({ trend }: { trend: MetricTrend }) {
  if (trend === "up")   return <span aria-hidden="true" className="metric-trend-arrow">↑</span>;
  if (trend === "down") return <span aria-hidden="true" className="metric-trend-arrow">↓</span>;
  if (trend === "flat") return <span aria-hidden="true" className="metric-trend-arrow">→</span>;
  return null;
}

export function MetricCard({
  label,
  value,
  unit,
  description,
  trend = "none",
  change,
  invertTrendSemantics = false,
  isLoading = false,
  sparkline,
  icon,
  size = "md",
  className,
  ...props
}: MetricCardProps) {
  // Resolve semantic color for trend
  const resolvedTrend =
    invertTrendSemantics
      ? trend === "up"   ? "down"
        : trend === "down" ? "up"
        : trend
      : trend;

  const trendClass =
    resolvedTrend === "up"   ? "metric-trend-positive"
    : resolvedTrend === "down" ? "metric-trend-negative"
    : resolvedTrend === "flat" ? "metric-trend-flat"
    : "";

  if (isLoading) {
    return (
      <div className={cn("metric-card", `metric-card-${size}`, className)} {...props}>
        <Skeleton shape="text" style={{ width: "60%", marginBottom: "0.5rem" }} />
        <Skeleton shape="text" style={{ width: "40%", height: "1.75rem" }} />
        <Skeleton shape="text" style={{ width: "30%", marginTop: "0.5rem" }} />
      </div>
    );
  }

  return (
    <div
      className={cn("metric-card", `metric-card-${size}`, className)}
      {...props}
    >
      <div className="metric-card-header">
        {icon && <span className="metric-card-icon" aria-hidden="true">{icon}</span>}
        <span className="metric-card-label">{label}</span>
      </div>

      <div className="metric-card-value-row">
        <span className="metric-card-value tabular-nums">
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
        {unit && <span className="metric-card-unit">{unit}</span>}
      </div>

      {(change || trend !== "none") && (
        <div className={cn("metric-card-change", trendClass)}>
          <TrendArrow trend={trend} />
          {change && <span className="metric-card-change-text">{change}</span>}
        </div>
      )}

      {description && (
        <p className="metric-card-description">{description}</p>
      )}

      {sparkline && (
        <div className="metric-card-sparkline" aria-hidden="true">
          {sparkline}
        </div>
      )}
    </div>
  );
}
