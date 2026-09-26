"use client";

import React, { useState, useMemo, useCallback } from "react";
import type { OHLCVBarResponse, MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { RegimeLegend } from "./RegimeLegend";
import {
  formatRegimeLabel,
  getRegimeColor,
} from "@/lib/utils/regime";
import {
  computeRegimeTimeline,
  type RegimeSegment,
} from "@/lib/utils/regime-timeline";
import { formatDate } from "@/lib/utils/formatters";

export interface RegimeTimelineProps {
  symbol: string;
  bars: OHLCVBarResponse[];
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
  onHoverIndex?: (index: number | null) => void;
  hoveredIndex?: number | null;
  className?: string;
}

/**
 * Interactive Regime Timeline Swimlane.
 *
 * Displays a horizontal timeline divided into colored segments representing
 * continuous regime regimes over the market's trading history.
 *
 * Features:
 *   - Continuous colored segments mapped to detected regimes
 *   - Regime change transition markers (diamond glyphs)
 *   - Interactive hover inspection with synchronized cursor
 *   - Synchronized hover state with the primary price chart
 *   - Regime legend with active state badge
 */
export function RegimeTimeline({
  symbol,
  bars,
  regimeData,
  isLoading = false,
  onHoverIndex,
  hoveredIndex: externalHoveredIndex,
  className,
}: RegimeTimelineProps) {
  const [internalHoveredIndex, setInternalHoveredIndex] = useState<number | null>(null);
  const hoveredIndex = externalHoveredIndex ?? internalHoveredIndex;

  // ViewBox layout dimensions
  const viewBoxWidth = 1000;
  const viewBoxHeight = 64;
  const padding = { top: 6, right: 30, bottom: 20, left: 70 };
  const innerWidth = viewBoxWidth - padding.left - padding.right;
  const innerHeight = viewBoxHeight - padding.top - padding.bottom;

  // Compute timeline segments
  const timeline = useMemo(
    () => computeRegimeTimeline(regimeData, bars),
    [regimeData, bars]
  );

  // Map bar index to X coordinate
  const barToX = useCallback(
    (index: number) => {
      if (!bars || bars.length <= 1) return padding.left + innerWidth / 2;
      return padding.left + (index / (bars.length - 1)) * innerWidth;
    },
    [bars, padding.left, innerWidth]
  );

  // Mouse hover event handlers
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

  // Compute date ticks along the bottom
  const dateTicks = useMemo(() => {
    if (!bars || bars.length === 0) return [];
    const count = Math.min(5, bars.length);
    const ticks: { dateStr: string; x: number }[] = [];
    for (let i = 0; i < count; i++) {
      const index = Math.floor((i / (count - 1 || 1)) * (bars.length - 1));
      ticks.push({
        dateStr: formatDate(bars[index].timestamp, "short"),
        x: barToX(index),
      });
    }
    return ticks;
  }, [bars, barToX]);

  // If no regime data or bars, return null per test expectations
  if (!regimeData || !bars || bars.length === 0 || isLoading) {
    return null;
  }

  // Find active bar and active regime segment for inspection
  const effectiveIndex =
    hoveredIndex !== null ? hoveredIndex : bars.length - 1;
  const activeBar = bars[effectiveIndex] ?? bars[bars.length - 1];
  const activeRegime: RegimeSegment | null =
    timeline.segments.find(
      (seg) => effectiveIndex >= seg.startIndex && effectiveIndex <= seg.endIndex
    ) ?? (timeline.segments.length > 0 ? timeline.segments[timeline.segments.length - 1] : null);

  const activeColor = activeRegime
    ? getRegimeColor(activeRegime.regimeLabel, activeRegime.regimeId)
    : null;

  return (
    <Card
      variant="elevated"
      className={`regime-timeline-container ${className ?? ""}`}
    >
      <CardHeader>
        <div className="regime-timeline-header">
          <div className="regime-timeline-title-row">
            <CardTitle className="regime-timeline-title">Regime Timeline</CardTitle>
            <CardDescription className="regime-timeline-subtitle">
              {symbol} historical regime sequence ({timeline.segments.length}{" "}
              {timeline.segments.length === 1 ? "regime segment" : "regime segments"})
            </CardDescription>
          </div>
          <RegimeLegend regimeData={regimeData} />
        </div>
      </CardHeader>
      <CardContent>
        {/* Hover Inspector */}
        {activeBar && activeRegime && activeColor && (
          <div className="regime-timeline-inspector" aria-live="polite">
            <div className="regime-timeline-inspector-item">
              <span className="regime-timeline-inspector-label">Date</span>
              <span className="regime-timeline-inspector-val">
                {formatDate(activeBar.timestamp, "short")}
              </span>
            </div>
            <div className="regime-timeline-inspector-item">
              <span
                className="regime-timeline-inspector-swatch"
                style={{ backgroundColor: activeColor.hex }}
              />
              <span className="regime-timeline-inspector-label">Regime</span>
              <span className="regime-timeline-inspector-val regime-timeline-inspector-regime">
                {formatRegimeLabel(activeRegime.regimeLabel, activeRegime.regimeId)}
              </span>
            </div>
            <div className="regime-timeline-inspector-item">
              <span className="regime-timeline-inspector-label">Duration</span>
              <span className="regime-timeline-inspector-val">
                {activeRegime.barCount} {activeRegime.barCount === 1 ? "bar" : "bars"}
              </span>
            </div>
            {activeRegime.isCurrent && (
              <span className="regime-timeline-inspector-current-badge">Active Regime</span>
            )}
          </div>
        )}

        {/* Timeline SVG Swimlane */}
        <div className="regime-timeline-svg-wrapper">
          <svg
            viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
            className="regime-timeline-svg"
            preserveAspectRatio="none"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            role="img"
            aria-label={`Regime timeline swimlane for ${symbol}`}
          >
            {/* Timeline Background Track */}
            <rect
              x={padding.left}
              y={padding.top}
              width={innerWidth}
              height={innerHeight}
              fill="rgba(255, 255, 255, 0.04)"
              rx="4"
            />

            {/* Segments */}
            {timeline.segments.map((seg, i) => {
              const x1 = barToX(seg.startIndex);
              const x2 =
                i === timeline.segments.length - 1
                  ? padding.left + innerWidth
                  : barToX(timeline.segments[i + 1].startIndex);
              const segWidth = Math.max(2, x2 - x1);
              const color = getRegimeColor(seg.regimeLabel, seg.regimeId);
              const isHovered = activeRegime?.startIndex === seg.startIndex;

              return (
                <rect
                  key={`seg-${i}`}
                  x={x1}
                  y={padding.top}
                  width={segWidth}
                  height={innerHeight}
                  fill={color.hex}
                  opacity={isHovered ? 0.95 : 0.75}
                  rx={i === 0 ? "4" : undefined}
                  className="regime-timeline-segment"
                >
                  <title>
                    {`${formatRegimeLabel(seg.regimeLabel, seg.regimeId)}: ${formatDate(seg.startTimestamp, "short")} - ${formatDate(seg.endTimestamp, "short")} (${seg.barCount} bars)`}
                  </title>
                </rect>
              );
            })}

            {/* Transition Markers */}
            {timeline.transitions.map((tr, i) => {
              const x = barToX(tr.barIndex);
              const midY = padding.top + innerHeight / 2;
              const toColor = getRegimeColor(tr.toRegimeLabel, tr.toRegimeId);

              return (
                <g key={`tr-${i}`} className="regime-transition-marker">
                  <polygon
                    points={`${x},${midY - 6} ${x + 5},${midY} ${x},${midY + 6} ${x - 5},${midY}`}
                    fill={toColor.hex}
                    stroke="#ffffff"
                    strokeWidth="1.2"
                    className="regime-transition-diamond"
                  >
                    <title>
                      {`Transition: ${formatRegimeLabel(tr.fromRegimeLabel, tr.fromRegimeId)} → ${formatRegimeLabel(tr.toRegimeLabel, tr.toRegimeId)}`}
                    </title>
                  </polygon>
                </g>
              );
            })}

            {/* Synchronized Hover Crosshair */}
            {hoveredIndex !== null && (
              <line
                x1={barToX(hoveredIndex)}
                y1={padding.top}
                x2={barToX(hoveredIndex)}
                y2={padding.top + innerHeight}
                stroke="#60a5fa"
                strokeWidth="1.5"
                className="regime-timeline-crosshair"
              />
            )}

            {/* Date Ticks */}
            {dateTicks.map((tick, i) => (
              <text
                key={`tick-${i}`}
                x={tick.x}
                y={padding.top + innerHeight + 13}
                textAnchor="middle"
                className="chart-axis-text"
              >
                {tick.dateStr}
              </text>
            ))}
          </svg>
        </div>
      </CardContent>
    </Card>
  );
}
