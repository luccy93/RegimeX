"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  formatRegimeLabel,
  getRegimeStatusVariant,
  getRegimeBadgeClass,
} from "@/lib/utils/regime";
import {
  formatPercent,
  formatDuration,
  formatDate,
  formatNumber,
} from "@/lib/utils/formatters";

export interface CurrentRegimeCardProps {
  symbol: string;
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
  error?: string | null;
  requestId?: string;
  onRetry?: () => void;
}

export function CurrentRegimeCard({
  symbol,
  regimeData,
  isLoading = false,
  error = null,
  requestId,
  onRetry,
}: CurrentRegimeCardProps) {
  if (error) {
    return (
      <Card variant="elevated" className="current-regime-card">
        <CardHeader>
          <CardTitle>Current Regime State</CardTitle>
          <CardDescription>Statistical market state classification</CardDescription>
        </CardHeader>
        <CardContent>
          <ErrorState
            title={`Regime Classification Unavailable (${symbol})`}
            message={error}
            requestId={requestId}
            onRetry={onRetry}
            retryLabel="Retry Regime Detection"
          />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card variant="elevated" className="current-regime-card">
        <CardHeader>
          <Skeleton shape="text" style={{ width: "40%" }} />
          <Skeleton shape="text" style={{ width: "60%" }} />
        </CardHeader>
        <CardContent>
          <div className="current-regime-loading-skeleton">
            <Skeleton shape="rect" style={{ height: "4rem", marginBottom: "1rem" }} />
            <Skeleton shape="rect" style={{ height: "6rem", marginBottom: "1rem" }} />
            <Skeleton shape="rect" style={{ height: "8rem" }} />
          </div>
        </CardContent>
      </Card>
    );
  }

  const rawLabel = regimeData?.current_regime_label;
  const rawId = regimeData?.current_regime;
  const label = formatRegimeLabel(rawLabel, rawId);
  const statusVariant = getRegimeStatusVariant(rawLabel);
  const badgeClass = getRegimeBadgeClass(rawLabel);

  const confidence = regimeData?.confidence;
  const confidencePercent =
    confidence !== null && confidence !== undefined && typeof confidence === "number"
      ? formatPercent(confidence, { isRatio: confidence <= 1.0, decimals: 1 })
      : "Unavailable";

  const context = regimeData?.current_context;
  const runDuration = context?.observations_in_current_run;
  const avgDuration = context?.historical_average_duration;
  const maxDuration = context?.historical_max_duration;
  const frequency = context?.historical_frequency;
  const runCount = context?.historical_run_count;

  // Active feature statistics
  const featureStats = regimeData?.statistics ?? {};
  const featureEntries = Object.entries(featureStats);

  return (
    <Card variant="elevated" className="current-regime-card">
      <CardHeader>
        <div className="current-regime-header-row">
          <div>
            <CardTitle>Current Regime Context</CardTitle>
            <CardDescription>
              Point-in-time statistical regime assignment for {symbol}
            </CardDescription>
          </div>
          <span className={`regime-badge ${badgeClass}`}>
            <StatusIndicator status={statusVariant} size="sm" showLabel={false} />
            <span>{label}</span>
          </span>
        </div>
      </CardHeader>

      <CardContent>
        {/* Primary Classification Callout */}
        <div className="regime-callout-grid">
          {/* Regime Name & Label */}
          <div className="regime-callout-item">
            <span className="regime-callout-label">Assigned Regime</span>
            <div className="regime-callout-value-row">
              <span className="regime-callout-title">{label}</span>
              {rawLabel && (
                <Badge variant="outline" size="sm" className="regime-code-badge">
                  {rawLabel}
                </Badge>
              )}
            </div>
            <p className="regime-callout-meta">
              Model: {regimeData?.model_name || "Ensemble"} ({regimeData?.algorithm || "Statistical"})
            </p>
          </div>

          {/* Model Confidence */}
          <div className="regime-callout-item">
            <span className="regime-callout-label">Model Confidence</span>
            <div className="regime-callout-value-row">
              <span className="regime-callout-title">{confidencePercent}</span>
            </div>
            {confidence !== null && confidence !== undefined ? (
              <div className="regime-confidence-track">
                <div
                  className="regime-confidence-fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, (confidence <= 1.0 ? confidence * 100 : confidence)))}%`,
                  }}
                />
              </div>
            ) : (
              <p className="regime-callout-meta">Confidence score not emitted by model</p>
            )}
          </div>
        </div>

        {/* Persistence & Historical Duration Metrics */}
        <div className="regime-metrics-section">
          <h4 className="regime-section-title">Regime Persistence &amp; Duration</h4>
          <div className="regime-metrics-grid">
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Current Persistence</span>
              <span className="metric-pill-value">{formatDuration(runDuration)}</span>
            </div>
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Historical Average</span>
              <span className="metric-pill-value">{formatDuration(avgDuration)}</span>
            </div>
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Historical Max</span>
              <span className="metric-pill-value">{formatDuration(maxDuration)}</span>
            </div>
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Historical Frequency</span>
              <span className="metric-pill-value">
                {frequency !== undefined ? formatPercent(frequency, { isRatio: frequency <= 1.0 }) : "—"}
              </span>
            </div>
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Historical Runs</span>
              <span className="metric-pill-value">{runCount !== undefined ? `${runCount} runs` : "—"}</span>
            </div>
            <div className="regime-metric-pill">
              <span className="metric-pill-label">Context Timestamp</span>
              <span className="metric-pill-value">
                {context?.current_timestamp ? formatDate(context.current_timestamp, "short") : "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Active Feature Statistics */}
        <div className="regime-feature-section">
          <div className="regime-feature-header">
            <h4 className="regime-section-title">Active Feature Distributions</h4>
            <span className="regime-feature-count">
              {featureEntries.length} parameter{featureEntries.length === 1 ? "" : "s"}
            </span>
          </div>

          {featureEntries.length > 0 ? (
            <div className="regime-feature-table-wrapper">
              <table className="regime-feature-table">
                <thead>
                  <tr>
                    <th>Feature Name</th>
                    <th>Mean</th>
                    <th>Median</th>
                    <th>Std Dev (σ)</th>
                    <th>Min</th>
                    <th>Max</th>
                  </tr>
                </thead>
                <tbody>
                  {featureEntries.map(([fName, stat]) => (
                    <tr key={fName}>
                      <td className="feature-name-cell">
                        <code>{stat.feature_name || fName}</code>
                      </td>
                      <td>{formatNumber(stat.mean, { decimals: 4 })}</td>
                      <td>{formatNumber(stat.median, { decimals: 4 })}</td>
                      <td>{formatNumber(stat.std, { decimals: 4 })}</td>
                      <td>{formatNumber(stat.min, { decimals: 4 })}</td>
                      <td>{formatNumber(stat.max, { decimals: 4 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="regime-feature-empty">
              No continuous feature distributions provided for the active regime.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
