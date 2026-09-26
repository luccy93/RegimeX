"use client";

import React, { useMemo } from "react";
import type { MarketRiskResponse, RiskPricePointDTO } from "@/lib/api/types";
import { ChartSlot } from "@/components/ui/ChartSlot";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";
import { formatPercentage } from "@/lib/api/risk";

export interface RiskDrawdownSectionProps {
  riskData: MarketRiskResponse;
}

export function RiskDrawdownSection({ riskData }: RiskDrawdownSectionProps) {
  const { drawdown, price_points } = riskData;

  // Build SVG points for drawdown track
  const chartData = useMemo(() => {
    if (!price_points || price_points.length === 0) return null;

    const width = 800;
    const height = 220;
    const padding = { top: 20, right: 30, bottom: 30, left: 60 };

    const innerWidth = width - padding.left - padding.right;
    const innerHeight = height - padding.top - padding.bottom;

    // Drawdowns are <= 0. Find min drawdown (e.g. -0.25).
    let minDd = 0;
    for (const pt of price_points) {
      if (pt.drawdown < minDd) minDd = pt.drawdown;
    }
    // ensure at least -5% scale
    if (minDd > -0.05) minDd = -0.05;

    const n = price_points.length;
    const xScale = (idx: number) => padding.left + (idx / Math.max(1, n - 1)) * innerWidth;
    // 0 drawdown is at top (padding.top), minDd is at bottom (padding.top + innerHeight)
    const yScale = (dd: number) => padding.top + (dd / minDd) * innerHeight;

    const pathCoords: string[] = [];
    const areaCoords: string[] = [`${xScale(0)},${yScale(0)}`];

    price_points.forEach((pt, idx) => {
      const x = xScale(idx);
      const y = yScale(pt.drawdown);
      pathCoords.push(`${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`);
      areaCoords.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
    });

    areaCoords.push(`L ${xScale(n - 1).toFixed(1)} ${yScale(0).toFixed(1)} Z`);

    // Generate Y-axis grid ticks (e.g. 0%, -5%, -10%, etc.)
    const ticks = [0, minDd * 0.25, minDd * 0.5, minDd * 0.75, minDd];

    return {
      width,
      height,
      padding,
      path: pathCoords.join(" "),
      area: areaCoords.join(" "),
      ticks,
      yScale,
      zeroY: yScale(0),
      firstDate: price_points[0]?.timestamp,
      lastDate: price_points[n - 1]?.timestamp,
    };
  }, [price_points]);

  return (
    <section className="risk-drawdown-section" aria-labelledby="risk-drawdown-title">
      <div className="section-header">
        <div>
          <h2 id="risk-drawdown-title" className="section-title">Drawdown Track & Peak-to-Trough Profile</h2>
          <p className="section-subtitle">
            Point-in-time underwater equity curve depicting drawdown severity, duration, and recovery lifecycle.
          </p>
        </div>
        <Badge variant={drawdown.is_recovered ? "success" : "danger"} size="md">
          {drawdown.is_recovered ? "Recovered from Worst Peak" : "Active Underwater Phase"}
        </Badge>
      </div>

      <div className="risk-drawdown-grid">
        {/* Drawdown Chart */}
        <div className="risk-drawdown-chart-wrapper">
          <ChartSlot
            title="Historical Drawdown Track (%)"
            description="Normalized point-in-time percentage decline from preceding running high-water mark"
            height="standard"
          >
            {chartData ? (
              <div className="drawdown-svg-container" style={{ width: "100%", height: "100%", position: "relative" }}>
                <svg
                  viewBox={`0 0 ${chartData.width} ${chartData.height}`}
                  preserveAspectRatio="none"
                  className="drawdown-svg"
                  style={{ width: "100%", height: "100%", display: "block" }}
                >
                  <defs>
                    <linearGradient id="drawdownFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--color-danger, #ef4444)" stopOpacity="0.1" />
                      <stop offset="100%" stopColor="var(--color-danger, #ef4444)" stopOpacity="0.45" />
                    </linearGradient>
                  </defs>

                  {/* Y Grid lines */}
                  {chartData.ticks.map((tickVal, i) => {
                    const y = chartData.yScale(tickVal);
                    return (
                      <g key={i}>
                        <line
                          x1={chartData.padding.left}
                          y1={y}
                          x2={chartData.width - chartData.padding.right}
                          y2={y}
                          stroke="var(--color-border-subtle, rgba(255,255,255,0.08))"
                          strokeDasharray={tickVal === 0 ? "none" : "3,3"}
                          strokeWidth="1"
                        />
                        <text
                          x={chartData.padding.left - 8}
                          y={y + 4}
                          textAnchor="end"
                          fill="var(--color-text-muted, #94a3b8)"
                          fontSize="11"
                          fontFamily="monospace"
                        >
                          {(tickVal * 100).toFixed(1)}%
                        </text>
                      </g>
                    );
                  })}

                  {/* Zero reference line */}
                  <line
                    x1={chartData.padding.left}
                    y1={chartData.zeroY}
                    x2={chartData.width - chartData.padding.right}
                    y2={chartData.zeroY}
                    stroke="var(--color-border-strong, rgba(255,255,255,0.25))"
                    strokeWidth="1.5"
                  />

                  {/* Area fill under curve */}
                  <path d={chartData.area} fill="url(#drawdownFill)" />

                  {/* Drawdown line */}
                  <path
                    d={chartData.path}
                    fill="none"
                    stroke="var(--color-danger, #ef4444)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* X Axis dates */}
                  {chartData.firstDate && chartData.lastDate && (
                    <g>
                      <text
                        x={chartData.padding.left}
                        y={chartData.height - 8}
                        textAnchor="start"
                        fill="var(--color-text-muted, #94a3b8)"
                        fontSize="11"
                      >
                        {formatDate(chartData.firstDate, "date-only")}
                      </text>
                      <text
                        x={chartData.width - chartData.padding.right}
                        y={chartData.height - 8}
                        textAnchor="end"
                        fill="var(--color-text-muted, #94a3b8)"
                        fontSize="11"
                      >
                        {formatDate(chartData.lastDate, "date-only")}
                      </text>
                    </g>
                  )}
                </svg>
              </div>
            ) : (
              <div className="drawdown-empty-chart">Insufficient price points to render drawdown track.</div>
            )}
          </ChartSlot>
        </div>

        {/* Drawdown Details Panel */}
        <div className="risk-drawdown-details-panel">
          <div className="drawdown-detail-card">
            <h4 className="drawdown-detail-heading">Peak-to-Trough Anatomy</h4>
            
            <div className="drawdown-detail-row">
              <span className="drawdown-detail-label">Pre-Crash Peak</span>
              <div className="drawdown-detail-right">
                <span className="drawdown-detail-value font-mono">${drawdown.peak_value.toFixed(2)}</span>
                <span className="drawdown-detail-sub">{formatDate(drawdown.peak_timestamp, "date-only")}</span>
              </div>
            </div>

            <div className="drawdown-detail-row">
              <span className="drawdown-detail-label">Trough Depth</span>
              <div className="drawdown-detail-right">
                <span className="drawdown-detail-value font-mono">${drawdown.trough_value.toFixed(2)}</span>
                <span className="drawdown-detail-sub">{formatDate(drawdown.trough_timestamp, "date-only")}</span>
              </div>
            </div>

            <div className="drawdown-detail-row">
              <span className="drawdown-detail-label">Maximum Decline</span>
              <div className="drawdown-detail-right">
                <span className="drawdown-detail-value font-mono text-danger font-semibold">
                  {formatPercentage(drawdown.max_drawdown)}
                </span>
                <span className="drawdown-detail-sub">Magnitude: {formatPercentage(drawdown.drawdown_magnitude)}</span>
              </div>
            </div>

            <div className="drawdown-detail-row">
              <span className="drawdown-detail-label">Recovery Lifecycle</span>
              <div className="drawdown-detail-right">
                <span className="drawdown-detail-value">
                  {drawdown.is_recovered ? (
                    <Badge variant="success" size="sm">Fully Recovered</Badge>
                  ) : (
                    <Badge variant="danger" size="sm">Unrecovered</Badge>
                  )}
                </span>
                <span className="drawdown-detail-sub">
                  {drawdown.recovery_timestamp
                    ? formatDate(drawdown.recovery_timestamp, "date-only")
                    : "Running below peak"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
