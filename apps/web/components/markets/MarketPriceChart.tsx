"use client";

import React, { useState, useId, useMemo } from "react";
import type { OHLCVBarResponse } from "@/lib/api/types";
import { ChartSlot } from "@/components/ui/ChartSlot";
import { ErrorState } from "@/components/ui/ErrorState";
import { formatPrice, formatDate, formatNumber } from "@/lib/utils/formatters";

export interface MarketPriceChartProps {
  symbol: string;
  bars: OHLCVBarResponse[];
  currency?: string;
  interval?: string;
  isLoading?: boolean;
  error?: string | null;
  requestId?: string;
  onRetry?: () => void;
}

export function MarketPriceChart({
  symbol,
  bars,
  currency = "USD",
  interval = "1d",
  isLoading = false,
  error = null,
  requestId,
  onRetry,
}: MarketPriceChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const gradientId = useId();

  // Chart coordinate space constants
  const viewBoxWidth = 1000;
  const viewBoxHeight = 360;
  const padding = { top: 30, right: 30, bottom: 40, left: 70 };
  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  // Compute min/max and scales
  const { minPrice, maxPrice, priceRange, points, pathD, areaD, yTicks, xTicks } =
    useMemo(() => {
      if (!bars || bars.length === 0) {
        return {
          minPrice: 0,
          maxPrice: 0,
          priceRange: 1,
          points: [],
          pathD: "",
          areaD: "",
          yTicks: [],
          xTicks: [],
        };
      }

      let min = Infinity;
      let max = -Infinity;

      for (const bar of bars) {
        if (bar.low < min) min = bar.low;
        if (bar.high > max) max = bar.high;
      }

      // Add a 5% margin to prevent clipping at top/bottom
      const range = max - min || 1;
      const bufferedMin = Math.max(0, min - range * 0.05);
      const bufferedMax = max + range * 0.05;
      const bufferedRange = bufferedMax - bufferedMin;

      const pts = bars.map((bar, index) => {
        const x =
          bars.length > 1
            ? padding.left + (index / (bars.length - 1)) * innerWidth
            : padding.left + innerWidth / 2;
        const y =
          padding.top +
          (1 - (bar.close - bufferedMin) / bufferedRange) * innerHeight;
        return { x, y, bar };
      });

      // Construct line path SVG
      let linePath = "";
      if (pts.length > 0) {
        linePath = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`;
        for (let i = 1; i < pts.length; i++) {
          linePath += ` L ${pts[i].x.toFixed(2)} ${pts[i].y.toFixed(2)}`;
        }
      }

      // Construct area fill SVG
      let fillPath = "";
      if (pts.length > 0) {
        const bottomY = padding.top + innerHeight;
        fillPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(2)} ${bottomY} L ${pts[0].x.toFixed(2)} ${bottomY} Z`;
      }

      // Generate 5 Y-axis ticks
      const yTickCount = 5;
      const yValues: { price: number; y: number }[] = [];
      for (let i = 0; i < yTickCount; i++) {
        const fraction = i / (yTickCount - 1);
        const price = bufferedMin + fraction * bufferedRange;
        const y = padding.top + (1 - fraction) * innerHeight;
        yValues.push({ price, y });
      }

      // Generate 5 evenly spaced X-axis date ticks
      const xTickCount = Math.min(5, bars.length);
      const xValues: { dateStr: string; x: number }[] = [];
      for (let i = 0; i < xTickCount; i++) {
        const index = Math.floor((i / (xTickCount - 1 || 1)) * (bars.length - 1));
        const bar = bars[index];
        const x =
          bars.length > 1
            ? padding.left + (index / (bars.length - 1)) * innerWidth
            : padding.left + innerWidth / 2;
        xValues.push({
          dateStr: formatDate(bar.timestamp, "short"),
          x,
        });
      }

      return {
        minPrice: min,
        maxPrice: max,
        priceRange: range,
        points: pts,
        pathD: linePath,
        areaD: fillPath,
        yTicks: yValues,
        xTicks: xValues,
      };
    }, [bars, innerWidth, innerHeight, padding.left, padding.top]);

  // Handle mouse interaction on SVG to find nearest bar
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!bars || bars.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * viewBoxWidth;

    // Constrain to chart bounds
    const clampedX = Math.max(padding.left, Math.min(viewBoxWidth - padding.right, svgX));
    const normalized = (clampedX - padding.left) / innerWidth;
    const closestIdx = Math.round(normalized * (bars.length - 1));
    const safeIdx = Math.max(0, Math.min(bars.length - 1, closestIdx));
    setHoveredIndex(safeIdx);
  };

  const handleMouseLeave = () => {
    setHoveredIndex(null);
  };

  // Active bar for tooltip
  const activePoint =
    hoveredIndex !== null && points[hoveredIndex]
      ? points[hoveredIndex]
      : points.length > 0
      ? points[points.length - 1]
      : null;

  if (error) {
    return (
      <div className="market-chart-card">
        <ErrorState
          title={`Market Data Unavailable (${symbol})`}
          message={error}
          requestId={requestId}
          onRetry={onRetry}
          retryLabel="Retry Market Data"
        />
      </div>
    );
  }

  const titleText = `${symbol} — Historical Price Action`;
  const descriptionText = `Aggregated ${interval} OHLCV time-series (${bars.length} bars)`;

  return (
    <div className="market-chart-card">
      <ChartSlot
        title={titleText}
        description={descriptionText}
        height={viewBoxHeight}
        isLoading={isLoading}
        emptyLabel={`No market price records found for ${symbol}`}
      >
        {bars.length > 0 && (
          <div className="market-chart-visualizer">
            {/* Real-time Hover HUD / Stats Strip */}
            {activePoint && (
              <div className="market-chart-hud" aria-live="polite">
                <div className="market-chart-hud-item">
                  <span className="market-chart-hud-label">Date (UTC)</span>
                  <span className="market-chart-hud-val">
                    {formatDate(activePoint.bar.timestamp, "long")}
                  </span>
                </div>
                <div className="market-chart-hud-item">
                  <span className="market-chart-hud-label">Close</span>
                  <span className="market-chart-hud-val highlight">
                    {formatPrice(activePoint.bar.close, currency)}
                  </span>
                </div>
                <div className="market-chart-hud-item">
                  <span className="market-chart-hud-label">Open</span>
                  <span className="market-chart-hud-val">
                    {formatPrice(activePoint.bar.open, currency)}
                  </span>
                </div>
                <div className="market-chart-hud-item">
                  <span className="market-chart-hud-label">High / Low</span>
                  <span className="market-chart-hud-val">
                    {formatPrice(activePoint.bar.high, currency)} / {formatPrice(activePoint.bar.low, currency)}
                  </span>
                </div>
                <div className="market-chart-hud-item">
                  <span className="market-chart-hud-label">Volume</span>
                  <span className="market-chart-hud-val">
                    {formatNumber(activePoint.bar.volume, { compact: true })}
                  </span>
                </div>
              </div>
            )}

            {/* SVG Visual Canvas */}
            <div className="market-chart-svg-container">
              <svg
                viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
                className="market-chart-svg"
                preserveAspectRatio="none"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                role="img"
                aria-label={`Price chart for ${symbol}, showing ${bars.length} daily bars`}
              >
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.32" />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Horizontal Grid Lines & Y-axis labels */}
                {yTicks.map((tick, i) => (
                  <g key={`ytick-${i}`} className="chart-grid-group">
                    <line
                      x1={padding.left}
                      y1={tick.y}
                      x2={viewBoxWidth - padding.right}
                      y2={tick.y}
                      stroke="rgba(255, 255, 255, 0.08)"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={padding.left - 12}
                      y={tick.y + 4}
                      textAnchor="end"
                      className="chart-axis-text"
                    >
                      {formatPrice(tick.price, currency)}
                    </text>
                  </g>
                ))}

                {/* Vertical X-axis Date Ticks */}
                {xTicks.map((tick, i) => (
                  <g key={`xtick-${i}`} className="chart-grid-group">
                    <line
                      x1={tick.x}
                      y1={padding.top}
                      x2={tick.x}
                      y2={padding.top + innerHeight}
                      stroke="rgba(255, 255, 255, 0.04)"
                    />
                    <text
                      x={tick.x}
                      y={padding.top + innerHeight + 22}
                      textAnchor="middle"
                      className="chart-axis-text"
                    >
                      {tick.dateStr}
                    </text>
                  </g>
                ))}

                {/* Area Gradient Fill */}
                <path d={areaD} fill={`url(#${gradientId})`} />

                {/* Primary Price Stroke */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Hover Crosshair & Data Indicator */}
                {hoveredIndex !== null && activePoint && (
                  <g className="chart-hover-indicator" aria-hidden="true">
                    {/* Vertical dashed crosshair line */}
                    <line
                      x1={activePoint.x}
                      y1={padding.top}
                      x2={activePoint.x}
                      y2={padding.top + innerHeight}
                      stroke="#60a5fa"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    {/* Glowing point on line */}
                    <circle
                      cx={activePoint.x}
                      cy={activePoint.y}
                      r="6"
                      fill="#3b82f6"
                      stroke="#ffffff"
                      strokeWidth="2"
                    />
                  </g>
                )}
              </svg>
            </div>

            {/* Accessibility table (screen-reader accessible) */}
            <div className="sr-only">
              <table>
                <caption>Historical OHLCV for {symbol}</caption>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Close</th>
                    <th>Open</th>
                    <th>High</th>
                    <th>Low</th>
                    <th>Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {bars.slice(-10).map((b) => (
                    <tr key={b.timestamp}>
                      <td>{b.timestamp}</td>
                      <td>{b.close}</td>
                      <td>{b.open}</td>
                      <td>{b.high}</td>
                      <td>{b.low}</td>
                      <td>{b.volume}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </ChartSlot>
    </div>
  );
}
