"use client";

import React, { useState } from "react";
import type { MarketTransitionResponse, MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  formatRegimeLabel,
  getRegimeBadgeClass,
  getRegimeColor,
} from "@/lib/utils/regime";
import {
  formatPercent,
  formatProbability,
  formatEntropy,
} from "@/lib/utils/formatters";

export interface TransitionAnalyticsSectionProps {
  transitionData?: MarketTransitionResponse | null;
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export function TransitionAnalyticsSection({
  transitionData,
  regimeData,
  isLoading = false,
  error = null,
  onRetry,
}: TransitionAnalyticsSectionProps) {
  const [matrixDisplayMode, setMatrixDisplayMode] = useState<"probability" | "percentage">("probability");

  // Isolated Loading State
  if (isLoading) {
    return (
      <div className="transition-analytics-section" aria-busy="true">
        <Card variant="elevated">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "16rem", height: "1.5rem" }} />
            <Skeleton shape="text" style={{ width: "24rem", marginTop: "0.5rem" }} />
          </CardHeader>
          <CardContent>
            <div className="global-transition-metrics-grid" style={{ marginBottom: "1.5rem" }}>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="metric-box">
                  <Skeleton shape="text" style={{ width: "50%", marginBottom: "0.5rem" }} />
                  <Skeleton shape="text" style={{ width: "70%", height: "1.75rem" }} />
                </div>
              ))}
            </div>
            <Skeleton shape="rect" style={{ height: "16rem", borderRadius: "0.5rem" }} />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Isolated Error State (Section 32: Error Isolation)
  if (error) {
    return (
      <div className="transition-analytics-section">
        <Card variant="elevated" className="transition-error-card">
          <CardHeader>
            <div className="flex-between">
              <div>
                <CardTitle className="text-warning">Regime Change &amp; Transition Analytics</CardTitle>
                <CardDescription>Empirical Markov transition matrices and destination dynamics.</CardDescription>
              </div>
              <Badge variant="outline" size="sm" className="border-warning text-warning">
                Endpoint Unavailable
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="isolated-error-box">
              <span className="isolated-error-icon" aria-hidden="true">⚠️</span>
              <div className="isolated-error-text">
                <p className="font-semibold text-foreground">Transition analytics currently unavailable</p>
                <p className="text-muted text-sm">{error}</p>
              </div>
              {onRetry && (
                <Button variant="secondary" size="sm" onClick={onRetry}>
                  Retry Transitions
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!transitionData) {
    return (
      <div className="transition-analytics-section">
        <Card variant="elevated">
          <CardHeader>
            <CardTitle>Regime Change &amp; Transition Analytics</CardTitle>
            <CardDescription>Historical Markov transition behavior and persistence.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="regime-empty-message">No transition data available for selected instrument.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const {
    regimes = [],
    probability_matrix = [],
    regime_analytics = {},
    global_analytics,
  } = transitionData;

  // Helper to resolve label for regime ID
  const getLabel = (regimeId: number): string => {
    if (regime_analytics[regimeId]?.regime_label) {
      return regime_analytics[regimeId].regime_label;
    }
    if (regimeData?.profiles?.[regimeId]?.regime_label) {
      return regimeData.profiles[regimeId].regime_label;
    }
    return `REGIME_${regimeId}`;
  };

  return (
    <div className="transition-analytics-section">
      <Card variant="elevated" className="transition-card">
        <CardHeader>
          <div className="flex-between">
            <div>
              <CardTitle>Regime Change &amp; Transition Analytics</CardTitle>
              <CardDescription>
                Empirical 1-step Markov transition matrix, destination dispersion, and persistence dynamics.
              </CardDescription>
            </div>
            <div className="matrix-toggle-group">
              <button
                type="button"
                className={`matrix-toggle-btn ${matrixDisplayMode === "probability" ? "active" : ""}`}
                onClick={() => setMatrixDisplayMode("probability")}
              >
                Probability [0-1]
              </button>
              <button
                type="button"
                className={`matrix-toggle-btn ${matrixDisplayMode === "percentage" ? "active" : ""}`}
                onClick={() => setMatrixDisplayMode("percentage")}
              >
                Percentage (%)
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Global Transition Summary Metrics (Section 18) */}
          {global_analytics && (
            <div className="global-transition-metrics-grid">
              <MetricCard
                label="Total Changes"
                value={global_analytics.total_regime_changes.toLocaleString("en-US")}
                unit="events"
                description="State changes across window"
                size="sm"
              />
              <MetricCard
                label="Self-Transitions"
                value={global_analytics.total_self_transitions.toLocaleString("en-US")}
                unit="events"
                description="Consecutive persistence steps"
                size="sm"
              />
              <MetricCard
                label="Change Rate"
                value={formatPercent(global_analytics.global_change_rate, { isRatio: true, decimals: 1 })}
                description="Empirical change frequency"
                size="sm"
              />
              <MetricCard
                label="Persistence Rate"
                value={formatPercent(global_analytics.global_persistence_rate, { isRatio: true, decimals: 1 })}
                description="Empirical persistence frequency"
                size="sm"
              />
              <MetricCard
                label="Consecutive Transitions"
                value={global_analytics.total_consecutive_transitions.toLocaleString("en-US")}
                unit="steps"
                description="Total adjacent observations"
                size="sm"
              />
              <MetricCard
                label="Observed Edges"
                value={global_analytics.number_of_observed_transition_edges}
                unit={`of ${regimes.length * regimes.length}`}
                description="Active transition paths"
                size="sm"
              />
            </div>
          )}

          {/* Transition Probability Matrix (Section 20 & 21) */}
          <div className="transition-matrix-wrapper">
            <div className="matrix-header-strip">
              <h3 className="matrix-heading">Empirical Transition Probability Matrix</h3>
              <div className="matrix-legend-hints">
                <span className="matrix-legend-item">
                  <span className="legend-swatch-diagonal" aria-hidden="true" />
                  <span>Diagonal: Self-Transition (Persistence)</span>
                </span>
                <span className="matrix-legend-item">
                  <span className="legend-swatch-offdiagonal" aria-hidden="true" />
                  <span>Off-Diagonal: Regime Change</span>
                </span>
              </div>
            </div>

            <div className="matrix-table-container">
              <table className="transition-matrix-table" aria-label="Transition probability matrix">
                <caption className="sr-only">
                  1-step Markov transition probability matrix mapping source regime to destination regime
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="matrix-origin-header">
                      From \ To
                    </th>
                    {regimes.map((targetId) => {
                      const label = getLabel(targetId);
                      const color = getRegimeColor(label, targetId);
                      return (
                        <th key={targetId} scope="col" className="matrix-target-header">
                          <div className="flex-align-center justify-end gap-1">
                            <span
                              className="dist-chip-swatch"
                              style={{ backgroundColor: color.hex }}
                              aria-hidden="true"
                            />
                            <span>{formatRegimeLabel(label, targetId)}</span>
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {regimes.map((sourceId, rowIdx) => {
                    const sourceLabel = getLabel(sourceId);
                    const sourceColor = getRegimeColor(sourceLabel, sourceId);
                    const rowProbs = probability_matrix[rowIdx] || [];

                    return (
                      <tr key={sourceId}>
                        <th scope="row" className="matrix-source-cell">
                          <div className="flex-align-center gap-2">
                            <span
                              className="dist-chip-swatch"
                              style={{ backgroundColor: sourceColor.hex }}
                              aria-hidden="true"
                            />
                            <span className="font-semibold">
                              {formatRegimeLabel(sourceLabel, sourceId)}
                            </span>
                            <Badge className={getRegimeBadgeClass(sourceLabel)} size="sm">
                              ID: {sourceId}
                            </Badge>
                          </div>
                        </th>

                        {regimes.map((targetId, colIdx) => {
                          const prob = rowProbs[colIdx] ?? null;
                          const isDiagonal = rowIdx === colIdx;
                          const formattedProb =
                            prob !== null
                              ? matrixDisplayMode === "percentage"
                                ? formatPercent(prob, { isRatio: true, decimals: 1 })
                                : formatProbability(prob, 3)
                              : "—";

                          return (
                            <td
                              key={targetId}
                              className={`matrix-prob-cell ${isDiagonal ? "matrix-cell-diagonal" : "matrix-cell-offdiagonal"}`}
                            >
                              <span className="prob-val tabular-nums font-mono">
                                {formattedProb}
                              </span>
                              {isDiagonal && (
                                <span className="cell-sub-tag" aria-hidden="true">
                                  persist
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Transition Destinations & Entropy Breakdown (Section 19 & 22) */}
          <div className="transition-destinations-grid">
            {regimes.map((sourceId) => {
              const ra = regime_analytics[sourceId];
              if (!ra) return null;

              const label = getLabel(sourceId);
              const color = getRegimeColor(label, sourceId);
              const mostLikelyTargetId = ra.most_likely_destination;
              const mostLikelyLabel =
                mostLikelyTargetId !== null ? getLabel(mostLikelyTargetId) : "None";

              return (
                <div key={sourceId} className="regime-destination-card">
                  <div className="destination-card-header">
                    <div className="flex-align-center gap-2">
                      <span
                        className="dist-chip-swatch"
                        style={{ backgroundColor: color.hex }}
                        aria-hidden="true"
                      />
                      <span className="font-semibold text-foreground">
                        {formatRegimeLabel(label, sourceId)}
                      </span>
                    </div>

                    {/* Transition Entropy (Section 22) */}
                    <div className="entropy-badge-box">
                      <Tooltip content="Entropy measures the dispersion of transition destinations. Higher entropy indicates transitions are spread across multiple destination regimes; lower entropy indicates transitions are concentrated.">
                        <span className="entropy-chip tabular-nums">
                          Entropy: {formatEntropy(ra.transition_entropy)} ℹ
                        </span>
                      </Tooltip>
                    </div>
                  </div>

                  {/* Primary destination summary */}
                  <div className="primary-destination-row">
                    <span className="dest-label">Most Frequent Destination:</span>
                    <span className="dest-value font-semibold">
                      {mostLikelyTargetId !== null
                        ? `${formatRegimeLabel(mostLikelyLabel, mostLikelyTargetId)} (${formatPercent(ra.most_likely_destination_probability, { isRatio: true, decimals: 1 })})`
                        : "None (Absorbing / Single State)"}
                    </span>
                  </div>

                  {/* Destination Rankings List */}
                  {ra.rankings && ra.rankings.length > 0 && (
                    <div className="destinations-rank-list">
                      <span className="dest-list-title">Transition Pathways:</span>
                      <ul className="dest-pathway-items" aria-label={`Transitions from ${label}`}>
                        {ra.rankings.map((rk) => {
                          const targetLabel = rk.target_label || getLabel(rk.target_regime);
                          const isSelf = rk.target_regime === sourceId;

                          return (
                            <li key={rk.target_regime} className="dest-pathway-item">
                              <span className="pathway-dest">
                                <span className="pathway-arrow" aria-hidden="true">→</span>
                                <span>{formatRegimeLabel(targetLabel, rk.target_regime)}</span>
                                {isSelf && (
                                  <span className="pathway-self-badge">(Self / Persist)</span>
                                )}
                              </span>
                              <span className="pathway-stats tabular-nums font-mono">
                                {formatPercent(rk.probability, { isRatio: true, decimals: 1 })}
                                <span className="text-muted text-xs"> ({rk.count}x)</span>
                              </span>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="table-semantic-note" style={{ marginTop: "1rem" }}>
            <p className="note-text">
              <strong>Methodology note:</strong> Transition probabilities are empirical relative frequencies calculated from consecutive state observations. Diagonal elements represent self-transition (persistence probability P(S[t+1] = k | S[t] = k)). Transition entropy measures destination dispersion in nats and is strictly descriptive.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
