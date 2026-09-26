"use client";

import React, { useMemo } from "react";
import type { EquitySnapshotDTO } from "@/lib/api/types";
import { ChartSlot } from "@/components/ui/ChartSlot";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";
import { formatCurrency, formatPercentage } from "@/lib/api/backtesting";

export interface EquityCurveChartProps {
  equityCurve: EquitySnapshotDTO[];
  initialCash: number;
}

export function EquityCurveChart({ equityCurve, initialCash }: EquityCurveChartProps) {
  const chart = useMemo(() => {
    if (!equityCurve || equityCurve.length === 0) return null;

    const width = 800;
    const height = 280;
    const padding = { top: 20, right: 30, bottom: 40, left: 75 };

    const innerWidth = width - padding.left - padding.right;
    const innerHeight = height - padding.top - padding.bottom;

    // Split height: 70% for equity curve, 30% for drawdown track
    const equityHeight = innerHeight * 0.65;
    const ddTop = padding.top + equityHeight + 15;
    const ddHeight = innerHeight * 0.25;

    // Equity range
    let minEquity = initialCash;
    let maxEquity = initialCash;
    let minDd = 0;

    for (const snap of equityCurve) {
      if (snap.equity < minEquity) minEquity = snap.equity;
      if (snap.equity > maxEquity) maxEquity = snap.equity;
      if (snap.drawdown < minDd) minDd = snap.drawdown;
    }

    // Add 5% padding to equity
    const equityRange = maxEquity - minEquity || 1000;
    const yMinEq = Math.max(0, minEquity - equityRange * 0.05);
    const yMaxEq = maxEquity + equityRange * 0.05;

    if (minDd > -0.05) minDd = -0.05;

    const n = equityCurve.length;
    const xScale = (idx: number) => padding.left + (idx / Math.max(1, n - 1)) * innerWidth;

    // Equity Y-scale (higher is higher up)
    const yEqScale = (val: number) =>
      padding.top + (1 - (val - yMinEq) / (yMaxEq - yMinEq)) * equityHeight;

    // Drawdown Y-scale (0 is top of DD area, minDd is bottom)
    const yDdScale = (val: number) =>
      ddTop + (val / minDd) * ddHeight;

    // Equity path
    const eqPathCoords: string[] = [];
    const eqAreaCoords: string[] = [`${xScale(0)},${padding.top + equityHeight}`];

    equityCurve.forEach((snap, idx) => {
      const x = xScale(idx);
      const y = yEqScale(snap.equity);
      eqPathCoords.push(`${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`);
      eqAreaCoords.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
    });
    eqAreaCoords.push(`L ${xScale(n - 1).toFixed(1)} ${padding.top + equityHeight} Z`);

    // Drawdown path
    const ddPathCoords: string[] = [];
    const ddAreaCoords: string[] = [`${xScale(0)},${ddTop}`];

    equityCurve.forEach((snap, idx) => {
      const x = xScale(idx);
      const y = yDdScale(snap.drawdown);
      ddPathCoords.push(`${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`);
      ddAreaCoords.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
    });
    ddAreaCoords.push(`L ${xScale(n - 1).toFixed(1)} ${ddTop} Z`);

    // Baseline Y for initialCash
    const baselineY = yEqScale(initialCash);

    // Ticks
    const eqTicks = [
      yMinEq,
      yMinEq + (yMaxEq - yMinEq) * 0.5,
      yMaxEq,
    ];

    return {
      width,
      height,
      padding,
      eqPath: eqPathCoords.join(" "),
      eqArea: eqAreaCoords.join(" "),
      ddPath: ddPathCoords.join(" "),
      ddArea: ddAreaCoords.join(" "),
      baselineY,
      eqTicks,
      yEqScale,
      yDdScale,
      ddTop,
      minDd,
      firstDate: equityCurve[0]?.timestamp,
      lastDate: equityCurve[n - 1]?.timestamp,
      finalEquity: equityCurve[n - 1]?.equity,
      maxEquity,
      minEquity,
    };
  }, [equityCurve, initialCash]);

  return (
    <section className="equity-curve-section" aria-labelledby="equity-curve-title">
      <div className="section-header">
        <div>
          <h2 id="equity-curve-title" className="section-title">Portfolio Equity Trajectory & Drawdown</h2>
          <p className="section-subtitle">
            Cumulative mark-to-market net equity with initial capital baseline and synchronized underwater drawdown track.
          </p>
        </div>
        {chart && (
          <Badge variant={chart.finalEquity >= initialCash ? "success" : "danger"} size="md">
            Final: {formatCurrency(chart.finalEquity)}
          </Badge>
        )}
      </div>

      <div className="equity-curve-chart-wrapper">
        <ChartSlot
          title="Equity Curve ($) & Drawdown Subplot (%)"
          description="Upper track: Net account liquidation value. Lower track: Percentage decline from previous equity high-water mark."
          height="tall"
        >
          {chart ? (
            <div className="equity-svg-container" style={{ width: "100%", height: "100%", position: "relative" }}>
              <svg
                viewBox={`0 0 ${chart.width} ${chart.height}`}
                preserveAspectRatio="none"
                className="equity-svg"
                style={{ width: "100%", height: "100%", display: "block" }}
              >
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-primary, #3b82f6)" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="var(--color-primary, #3b82f6)" stopOpacity="0.02" />
                  </linearGradient>
                  <linearGradient id="backtestDdGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-danger, #ef4444)" stopOpacity="0.1" />
                    <stop offset="100%" stopColor="var(--color-danger, #ef4444)" stopOpacity="0.4" />
                  </linearGradient>
                </defs>

                {/* Equity Grid Lines & Labels */}
                {chart.eqTicks.map((tickVal, idx) => {
                  const y = chart.yEqScale(tickVal);
                  return (
                    <g key={idx}>
                      <line
                        x1={chart.padding.left}
                        y1={y}
                        x2={chart.width - chart.padding.right}
                        y2={y}
                        stroke="var(--color-border-subtle, rgba(255,255,255,0.08))"
                        strokeDasharray="3,3"
                        strokeWidth="1"
                      />
                      <text
                        x={chart.padding.left - 8}
                        y={y + 4}
                        textAnchor="end"
                        fill="var(--color-text-muted, #94a3b8)"
                        fontSize="10"
                        fontFamily="monospace"
                      >
                        ${(tickVal / 1000).toFixed(1)}k
                      </text>
                    </g>
                  );
                })}

                {/* Baseline initial capital line */}
                <line
                  x1={chart.padding.left}
                  y1={chart.baselineY}
                  x2={chart.width - chart.padding.right}
                  y2={chart.baselineY}
                  stroke="var(--color-border-strong, rgba(255,255,255,0.3))"
                  strokeDasharray="4,4"
                  strokeWidth="1"
                />
                <text
                  x={chart.width - chart.padding.right}
                  y={chart.baselineY - 4}
                  textAnchor="end"
                  fill="var(--color-text-muted, #94a3b8)"
                  fontSize="10"
                >
                  Capital Basis: ${chart.baselineY ? (initialCash / 1000).toFixed(0) : 100}k
                </text>

                {/* Equity Area Fill */}
                <path d={chart.eqArea} fill="url(#equityGradient)" />

                {/* Equity Curve Line */}
                <path
                  d={chart.eqPath}
                  fill="none"
                  stroke="var(--color-primary, #3b82f6)"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Drawdown Subplot Separator & Reference */}
                <line
                  x1={chart.padding.left}
                  y1={chart.ddTop}
                  x2={chart.width - chart.padding.right}
                  y2={chart.ddTop}
                  stroke="var(--color-border-subtle, rgba(255,255,255,0.15))"
                  strokeWidth="1"
                />
                <text
                  x={chart.padding.left - 8}
                  y={chart.ddTop + 4}
                  textAnchor="end"
                  fill="var(--color-text-muted, #94a3b8)"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  0%
                </text>
                <text
                  x={chart.padding.left - 8}
                  y={chart.yDdScale(chart.minDd) + 4}
                  textAnchor="end"
                  fill="var(--color-text-muted, #94a3b8)"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {(chart.minDd * 100).toFixed(0)}%
                </text>

                {/* Drawdown Area & Line */}
                <path d={chart.ddArea} fill="url(#backtestDdGradient)" />
                <path
                  d={chart.ddPath}
                  fill="none"
                  stroke="var(--color-danger, #ef4444)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* X Axis dates */}
                {chart.firstDate && chart.lastDate && (
                  <g>
                    <text
                      x={chart.padding.left}
                      y={chart.height - 8}
                      textAnchor="start"
                      fill="var(--color-text-muted, #94a3b8)"
                      fontSize="11"
                    >
                      {formatDate(chart.firstDate, "date-only")}
                    </text>
                    <text
                      x={chart.width - chart.padding.right}
                      y={chart.height - 8}
                      textAnchor="end"
                      fill="var(--color-text-muted, #94a3b8)"
                      fontSize="11"
                    >
                      {formatDate(chart.lastDate, "date-only")}
                    </text>
                  </g>
                )}
              </svg>
            </div>
          ) : (
            <div className="equity-empty-chart">Insufficient simulation snapshots to render equity curve.</div>
          )}
        </ChartSlot>
      </div>
    </section>
  );
}
