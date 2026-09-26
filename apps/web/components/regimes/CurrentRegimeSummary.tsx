"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import {
  formatRegimeLabel,
  getRegimeBadgeClass,
  getRegimeStatusVariant,
  getRegimeColor,
} from "@/lib/utils/regime";
import {
  formatPercent,
  formatDate,
  formatDuration,
  formatNumber,
} from "@/lib/utils/formatters";

export interface CurrentRegimeSummaryProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

export function CurrentRegimeSummary({
  regimeData,
  isLoading = false,
}: CurrentRegimeSummaryProps) {
  if (isLoading) {
    return (
      <Card variant="elevated" className="current-regime-summary-card" aria-busy="true">
        <CardHeader>
          <div className="flex-between">
            <Skeleton shape="text" style={{ width: "12rem", height: "1.5rem" }} />
            <Skeleton shape="rect" style={{ width: "6rem", height: "1.75rem" }} />
          </div>
          <Skeleton shape="text" style={{ width: "20rem", marginTop: "0.5rem" }} />
        </CardHeader>
        <CardContent>
          <div className="current-regime-metrics-grid">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="metric-box">
                <Skeleton shape="text" style={{ width: "60%", marginBottom: "0.5rem" }} />
                <Skeleton shape="text" style={{ width: "80%", height: "1.5rem" }} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!regimeData) return null;

  const currentLabel = regimeData.current_regime_label;
  const currentId = regimeData.current_regime;
  const context = regimeData.current_context;
  const confidence = regimeData.confidence;
  const color = getRegimeColor(currentLabel, currentId);

  // Confidence percentage & evaluation
  const hasConfidence = confidence !== null && confidence !== undefined && Number.isFinite(confidence);
  const confidenceDisplay = hasConfidence
    ? formatPercent(confidence, { isRatio: true, decimals: 1 })
    : "Unavailable";

  // Comparison context (descriptive, strictly non-predictive)
  const currentDuration = context?.observations_in_current_run ?? 0;
  const avgDuration = context?.historical_average_duration ?? 0;
  const maxDuration = context?.historical_max_duration ?? 0;
  const durationComparisonRatio = avgDuration > 0 ? (currentDuration / avgDuration) : null;

  return (
    <Card variant="elevated" className="current-regime-summary-card">
      <CardHeader>
        <div className="current-regime-header-row">
          <div className="current-regime-title-group">
            <div className="flex-align-center gap-2">
              <StatusIndicator
                status={getRegimeStatusVariant(currentLabel)}
                showLabel={false}
                size="md"
                pulse={hasConfidence}
              />
              <CardTitle className="current-regime-title">
                {formatRegimeLabel(currentLabel, currentId)}
              </CardTitle>
              <Badge className={getRegimeBadgeClass(currentLabel)}>
                ID: {currentId}
              </Badge>
            </div>
            <CardDescription className="current-regime-desc">
              Point-in-time classification assigned by {regimeData.model_name || "backend model"}.
            </CardDescription>
          </div>

          {/* Confidence Badge */}
          <div className="current-regime-confidence-badge" title="Model confidence score">
            <span className="confidence-label">Model Confidence</span>
            <span className="confidence-value tabular-nums" style={{ color: color.hex }}>
              {confidenceDisplay}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Core Statistical Context Grid */}
        <div className="current-regime-metrics-grid">
          <div className="metric-box">
            <span className="metric-box-label">Current Duration</span>
            <span className="metric-box-val tabular-nums">
              {formatDuration(currentDuration, "bar")}
            </span>
            <span className="metric-box-sub">consecutive observations</span>
          </div>

          <div className="metric-box">
            <span className="metric-box-label">Historical Avg Duration</span>
            <span className="metric-box-val tabular-nums">
              {formatDuration(avgDuration, "bar")}
            </span>
            <span className="metric-box-sub">
              {durationComparisonRatio !== null
                ? `${(durationComparisonRatio * 100).toFixed(0)}% of historical mean`
                : "benchmark duration"}
            </span>
          </div>

          <div className="metric-box">
            <span className="metric-box-label">Historical Max Duration</span>
            <span className="metric-box-val tabular-nums">
              {formatDuration(maxDuration, "bar")}
            </span>
            <span className="metric-box-sub">longest observed run</span>
          </div>

          <div className="metric-box">
            <span className="metric-box-label">Historical Frequency</span>
            <span className="metric-box-val tabular-nums">
              {formatPercent(context?.historical_frequency, { isRatio: true, decimals: 1 })}
            </span>
            <span className="metric-box-sub">share of total sample</span>
          </div>

          <div className="metric-box">
            <span className="metric-box-label">Historical Run Count</span>
            <span className="metric-box-val tabular-nums">
              {context?.historical_run_count ?? "—"}
            </span>
            <span className="metric-box-sub">distinct occurrences</span>
          </div>

          <div className="metric-box">
            <span className="metric-box-label">As of Timestamp</span>
            <span className="metric-box-val-sm tabular-nums">
              {context?.current_timestamp ? formatDate(context.current_timestamp, "long") : "—"}
            </span>
            <span className="metric-box-sub">UTC verification timestamp</span>
          </div>
        </div>

        {/* Current Active Features Snapshot (Respects Nullable Statistics) */}
        {context?.current_features && Object.keys(context.current_features).length > 0 && (
          <div className="current-features-strip">
            <span className="current-features-heading">Active Feature Vector:</span>
            <div className="current-features-list">
              {Object.entries(context.current_features).map(([featName, featVal]) => {
                const isNull = featVal === null || featVal === undefined || !Number.isFinite(featVal);
                let formattedVal = "—";
                if (!isNull && typeof featVal === "number") {
                  if (featName.includes("return")) {
                    formattedVal = formatPercent(featVal, { isRatio: true, decimals: 2, includeSign: true });
                  } else if (featName.includes("volatility")) {
                    formattedVal = formatPercent(featVal, { isRatio: true, decimals: 2 });
                  } else {
                    formattedVal = formatNumber(featVal, { decimals: 4 });
                  }
                }

                return (
                  <div key={featName} className="current-feature-item">
                    <span className="feature-name">{featName}</span>
                    <span className="feature-val tabular-nums">{formattedVal}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
