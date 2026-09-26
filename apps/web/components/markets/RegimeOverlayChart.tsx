"use client";

import React, { useState, useId, useMemo, useCallback } from "react";
import type { OHLCVBarResponse, MarketRegimeResponse } from "@/lib/api/types";
import { ChartSlot } from "@/components/ui/ChartSlot";
import { ErrorState } from "@/components/ui/ErrorState";
import {
  formatRegimeLabel,
  getRegimeColor,
} from "@/lib/utils/regime";
import {
  computeRegimeTimeline,
} from "@/lib/utils/regime-timeline";
import { formatPrice, formatDate, formatNumber } from "@/lib/utils/formatters";

export interface RegimeOverlayChartProps {
  symbol: string;
  bars: OHLCVBarResponse[];
  regimeData?: MarketRegimeResponse | null;
  currency?: string;
  interval?: string;
  isLoading?: boolean;
  error?: string | null;
  requestId?: string;
  onRetry?: () => void;
  /** Callback when the user hovers over a bar index */
  onHoverIndex?: (index: number | null) => void;
  /** Currently hovered index (from external synchronization) */
  hoveredIndex?: number | null;
}

/**
 * Price chart with regime-colored background bands and transition markers.
 *
 * This is an enhanced version of MarketPriceChart that overlays
 * regime segments as background fill regions behind the price line,
 * adds regime change marker lines, and supports synchronized hover.
 */
export function RegimeOverlayChart({
  symbol,
  bars,
  regimeData,
  currency = "USD",
  interval = "1d",
  isLoading = false,
  error = null,
  requestId,
  onRetry,
  onHoverIndex,
  hoveredIndex: externalHoveredIndex,
}: RegimeOverlayChartProps) {
  const [internalHoveredIndex, setInternalHoveredIndex] = useState<number | null>(null);
  const hoveredIndex = externalHoveredIndex ?? internalHoveredIndex;
  const gradientId = useId();

  // Chart coordinate space constants
  const viewBoxWidth = 1000;
  const viewBoxHeight = 400;
  const padding = { top: 30, right: 30, bottom: 40, left: 70 };
  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  // Compute timeline segments
  const timeline = useMemo(
    () => computeRegimeTimeline(regimeData, bars),
    [regimeData, bars]
  );

  // Compute price scales and paths
  const chartData = useMemo(() => {
    if (!bars || bars.length === 0) {
      return {
        minPrice: 0,
        maxPrice: 0,
        points: [] as { x: number; y: number; bar: OHLCVBarResponse }[],
        pathD: "",
        areaD: "",
        yTicks: [] as { price: number; y: number }[],
        xTicks: [] as { dateStr: string; x: number }[],
      };
    }

    let min = Infinity;
    let max = -Infinity;

    for (const bar of bars) {
      if (bar.low < min) min = bar.low;
      if (bar.high > max) max = bar.high;
    }

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

    // Line path
    let linePath = "";
    if (pts.length > 0) {
      linePath = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`;
      for (let i = 1; i < pts.length; i++) {
        linePath += ` L ${pts[i].x.toFixed(2)} ${pts[i].y.toFixed(2)}`;
      }
    }

    // Area fill path
    let fillPath = "";
    if (pts.length > 0) {
      const bottomY = padding.top + innerHeight;
      fillPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(2)} ${bottomY} L ${pts[0].x.toFixed(2)} ${bottomY} Z`;
    }

    // Y-axis ticks
    const yTickCount = 5;
    const yValues: { price: number; y: number }[] = [];
    for (let i = 0; i < yTickCount; i++) {
      const fraction = i / (yTickCount - 1);
      const price = bufferedMin + fraction * bufferedRange;
      const y = padding.top + (1 - fraction) * innerHeight;
      yValues.push({ price, y });
    }

    // X-axis ticks
    const xTickCount = Math.min(5, bars.length);
    const xValues: { dateStr: string; x: number }[] = [];
    for (let i = 0; i < xTickCount; i++) {
      const index = Math.floor((i / (xTickCount - 1 || 1)) * (bars.length - 1));
      const bar = bars[index];
      const x =
        bars.length > 1
          ? padding.left + (index / (bars.length - 1)) * innerWidth
          : padding.left + innerWidth / 2;
      xValues.push({ dateStr: formatDate(bar.timestamp, "short"), x });
    }

    return {
      minPrice: min,
      maxPrice: max,
      points: pts,
      pathD: linePath,
      areaD: fillPath,
      yTicks: yValues,
      xTicks: xValues,
    };
  }, [bars, innerWidth, innerHeight, padding.left, padding.top]);

  // Map bar index to X coordinate
  const barToX = useCallback(
    (index: number) => {
      if (bars.length <= 1) return padding.left + innerWidth / 2;
      return padding.left + (index / (bars.length - 1)) * innerWidth;
    },
    [bars.length, padding.left, innerWidth]
  );

  // Hover handler
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!bars || bars.length === 0) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const svgX = (clientX / rect.width) * viewBoxWidth;
      const clampedX = Math.max(padding.left, Math.min(viewBoxWidth - padding.right, svgX));
      const normalized = (clampedX - padding.left) / innerWidth;
      const idx = Math.round(normalized * (bars.length - 1));
      const safeIdx = Math.max(0, Math.min(bars.length - 1, idx));

      setInternalHoveredIndex(safeIdx);
      onHoverIndex?.(safeIdx);
    },
    [bars, padding.left, padding.right, innerWidth, viewBoxWidth, onHoverIndex]
  );

  const handleMouseLeave = useCallback(() => {
    setInternalHoveredIndex(null);
    onHoverIndex?.(null);
  }, [onHoverIndex]);

  // Active point for HUD
  const activePoint =
    hoveredIndex !== null && chartData.points[hoveredIndex]
      ? chartData.points[hoveredIndex]
      : chartData.points.length > 0
      ? chartData.points[chartData.points.length - 1]
      : null;

  // Find regime for hovered index
  const hoveredRegime = useMemo(() => {
    if (hoveredIndex === null) return null;
    return timeline.segments.find(
      (seg) => hoveredIndex >= seg.startIndex && hoveredIndex <= seg.endIndex
    ) ?? null;
  }, [hoveredIndex, timeline.segments]);

  if (error) {
    return (
      <div className="regime-overlay-chart-card">
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

  const hasRegimeData = timeline.segments.length > 0;
  const titleText = `${symbol} — Regime-Colored Price History`;
  const descriptionText = hasRegimeData
    ? `${interval} OHLCV (${bars.length} bars) with ${timeline.segments.length} regime overlay segments`
    : `${interval} OHLCV time-series (${bars.length} bars)`;

  return (
    <div className="regime-overlay-chart-card">
      <ChartSlot
        title={titleText}
        description={descriptionText}
        height={viewBoxHeight}
        isLoading={isLoading}
        emptyLabel={`No market price records found for ${symbol}`}
      >
        {bars.length > 0 && (
          <div className="regime-overlay-chart-visualizer">
            {/* HUD — hover stats strip */}
            {activePoint && (
              <div className="regime-overlay-hud" aria-live="polite">
                <div className="regime-overlay-hud-item">
                  <span className="regime-overlay-hud-label">Date</span>
                  <span className="regime-overlay-hud-val">
                    {formatDate(activePoint.bar.timestamp, "long")}
                  </span>
                </div>
                <div className="regime-overlay-hud-item">
                  <span className="regime-overlay-hud-label">Close</span>
                  <span className="regime-overlay-hud-val highlight">
                    {formatPrice(activePoint.bar.close, currency)}
                  </span>
                </div>
                <div className="regime-overlay-hud-item">
                  <span className="regime-overlay-hud-label">High / Low</span>
                  <span className="regime-overlay-hud-val">
                    {formatPrice(activePoint.bar.high, currency)} / {formatPrice(activePoint.bar.low, currency)}
                  </span>
                </div>
                <div className="regime-overlay-hud-item">
                  <span className="regime-overlay-hud-label">Volume</span>
                  <span className="regime-overlay-hud-val">
                    {formatNumber(activePoint.bar.volume, { compact: true })}
                  </span>
                </div>
                {hoveredRegime && (
                  <div className="regime-overlay-hud-item regime-overlay-hud-regime">
                    <span
                      className="regime-overlay-hud-regime-dot"
                      style={{ backgroundColor: getRegimeColor(hoveredRegime.regimeLabel, hoveredRegime.regimeId).hex }}
                    />
                    <span className="regime-overlay-hud-label">Regime</span>
                    <span className="regime-overlay-hud-val highlight">
                      {formatRegimeLabel(hoveredRegime.regimeLabel, hoveredRegime.regimeId)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* SVG Canvas */}
            <div className="regime-overlay-svg-container">
              <svg
                viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
                className="regime-overlay-svg"
                preserveAspectRatio="none"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                role="img"
                aria-label={`Regime-colored price chart for ${symbol}`}
              >
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.18" />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* LAYER 1: Regime Background Bands */}
                {timeline.segments.map((seg, i) => {
                  const x1 = barToX(seg.startIndex);
                  const x2 = barToX(seg.endIndex);
                  const color = getRegimeColor(seg.regimeLabel, seg.regimeId);
                  const segWidth = Math.max(1, x2 - x1);
                  const isHoveredSeg = hoveredRegime?.startIndex === seg.startIndex;

                  return (
                    <rect
                      key={`regime-band-${i}`}
                      x={x1}
                      y={padding.top}
                      width={segWidth}
                      height={innerHeight}
                      fill={color.hex}
                      opacity={isHoveredSeg ? 0.14 : 0.08}
                      className="regime-overlay-band"
                    />
                  );
                })}

                {/* LAYER 2: Transition Boundary Lines */}
                {timeline.transitions.map((tr, i) => {
                  const x = barToX(tr.barIndex);
                  return (
                    <line
                      key={`tr-line-${i}`}
                      x1={x}
                      y1={padding.top}
                      x2={x}
                      y2={padding.top + innerHeight}
                      stroke="rgba(255, 255, 255, 0.15)"
                      strokeWidth="1"
                      strokeDasharray="4 3"
                      className="regime-overlay-transition-line"
                    />
                  );
                })}

                {/* LAYER 3: Grid Lines & Y-axis Labels */}
                {chartData.yTicks.map((tick, i) => (
                  <g key={`ytick-${i}`}>
                    <line
                      x1={padding.left}
                      y1={tick.y}
                      x2={viewBoxWidth - padding.right}
                      y2={tick.y}
                      stroke="rgba(255, 255, 255, 0.06)"
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

                {/* X-axis Date Ticks */}
                {chartData.xTicks.map((tick, i) => (
                  <g key={`xtick-${i}`}>
                    <line
                      x1={tick.x}
                      y1={padding.top}
                      x2={tick.x}
                      y2={padding.top + innerHeight}
                      stroke="rgba(255, 255, 255, 0.03)"
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

                {/* LAYER 4: Area Gradient Fill */}
                <path d={chartData.areaD} fill={`url(#${gradientId})`} />

                {/* LAYER 5: Primary Price Line */}
                <path
                  d={chartData.pathD}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* LAYER 6: Regime Change Marker Triangles */}
                {timeline.transitions.map((tr, i) => {
                  const x = barToX(tr.barIndex);
                  const toColor = getRegimeColor(tr.toRegimeLabel, tr.toRegimeId);
                  const markerY = padding.top + 8;

                  return (
                    <g key={`change-marker-${i}`} className="regime-change-marker">
                      <polygon
                        points={`${x},${markerY - 5} ${x + 4},${markerY + 3} ${x - 4},${markerY + 3}`}
                        fill={toColor.hex}
                        stroke="rgba(255, 255, 255, 0.5)"
                        strokeWidth="0.6"
                      >
                        <title>
                          Regime change: {formatRegimeLabel(tr.fromRegimeLabel, tr.fromRegimeId)} → {formatRegimeLabel(tr.toRegimeLabel, tr.toRegimeId)}
                        </title>
                      </polygon>
                    </g>
                  );
                })}

                {/* LAYER 7: Hover Crosshair & Data Point */}
                {hoveredIndex !== null && activePoint && (
                  <g className="regime-overlay-hover-indicator" aria-hidden="true">
                    <line
                      x1={activePoint.x}
                      y1={padding.top}
                      x2={activePoint.x}
                      y2={padding.top + innerHeight}
                      stroke="#60a5fa"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    <circle
                      cx={activePoint.x}
                      cy={activePoint.y}
                      r="6"
                      fill="#3b82f6"
                      stroke="#ffffff"
                      strokeWidth="2"
                    />
                    {/* Regime color dot at bottom of crosshair */}
                    {hoveredRegime && (
                      <circle
                        cx={activePoint.x}
                        cy={padding.top + innerHeight + 6}
                        r="3.5"
                        fill={getRegimeColor(hoveredRegime.regimeLabel, hoveredRegime.regimeId).hex}
                        stroke="rgba(255, 255, 255, 0.4)"
                        strokeWidth="0.8"
                      />
                    )}
                  </g>
                )}
              </svg>
            </div>

            {/* Accessibility Table */}
            <div className="sr-only">
              <table>
                <caption>Regime-colored OHLCV for {symbol}</caption>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Close</th>
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
