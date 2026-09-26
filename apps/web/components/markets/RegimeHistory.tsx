"use client";

import React from "react";
import type { MarketRegimeResponse, RegimeProfileDTO } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import {
  formatRegimeLabel,
  getRegimeStatusVariant,
  getRegimeBadgeClass,
} from "@/lib/utils/regime";
import {
  formatPercent,
  formatDuration,
  formatDate,
} from "@/lib/utils/formatters";

export interface RegimeHistoryProps {
  symbol: string;
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

export function RegimeHistory({
  symbol,
  regimeData,
  isLoading = false,
}: RegimeHistoryProps) {
  if (isLoading) {
    return (
      <Card variant="elevated" className="regime-history-card">
        <CardHeader>
          <CardTitle>Historical Regime Distribution</CardTitle>
          <CardDescription>Empirical distribution across the observation window</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="regime-history-loading">
            <p className="regime-history-loading-text">Loading regime profiles…</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const profilesMap = regimeData?.profiles ?? {};
  const profiles: RegimeProfileDTO[] = Object.values(profilesMap);
  const currentRegimeId = regimeData?.current_regime;
  const totalObservations = regimeData?.total_observations ?? 0;

  if (profiles.length === 0) {
    return (
      <Card variant="elevated" className="regime-history-card">
        <CardHeader>
          <CardTitle>Historical Regime Distribution</CardTitle>
          <CardDescription>
            Historical regime distribution across the analysis window
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="regime-history-empty">
            <p>No historical regime profiles available for {symbol}.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated" className="regime-history-card">
      <CardHeader>
        <div className="regime-history-title-row">
          <div>
            <CardTitle>Observed Regime Profiles &amp; Distribution</CardTitle>
            <CardDescription>
              {profiles.length} distinct regime state{profiles.length === 1 ? "" : "s"} observed across{" "}
              {totalObservations} total observation{totalObservations === 1 ? "" : "s"}
            </CardDescription>
          </div>
          {regimeData?.analysis_start && regimeData?.analysis_end && (
            <Badge variant="outline" size="sm">
              {formatDate(regimeData.analysis_start, "short")} → {formatDate(regimeData.analysis_end, "short")}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {/* Cumulative Regime Distribution Bar */}
        <div className="regime-dist-section">
          <div className="regime-dist-header">
            <span className="regime-dist-caption">Sample Distribution</span>
            <span className="regime-dist-sub">100% of analyzed period</span>
          </div>

          <div
            className="regime-dist-bar-track"
            role="progressbar"
            aria-label="Regime distribution proportions"
          >
            {profiles.map((p) => {
              const pct = p.percentage ?? p.frequency * 100;
              const badgeClass = getRegimeBadgeClass(p.regime_label);
              return (
                <div
                  key={p.regime_id}
                  className={`regime-dist-segment ${badgeClass}`}
                  style={{ width: `${Math.max(2, pct)}%` }}
                  title={`${formatRegimeLabel(p.regime_label, p.regime_id)}: ${pct.toFixed(1)}%`}
                />
              );
            })}
          </div>
        </div>

        {/* Detailed Regime Profiles Table */}
        <div className="regime-profiles-table-wrapper">
          <table className="regime-profiles-table">
            <thead>
              <tr>
                <th>Regime</th>
                <th>Status</th>
                <th>Frequency</th>
                <th>Observations</th>
                <th>Run Count</th>
                <th>Avg Duration</th>
                <th>Max Duration</th>
                <th>Active Window</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((p) => {
                const label = formatRegimeLabel(p.regime_label, p.regime_id);
                const statusVariant = getRegimeStatusVariant(p.regime_label);
                const isCurrent = p.regime_id === currentRegimeId;
                const pct = p.percentage ?? p.frequency * 100;

                return (
                  <tr
                    key={p.regime_id}
                    className={isCurrent ? "regime-row-active" : undefined}
                  >
                    <td className="regime-col-label">
                      <div className="regime-name-cell">
                        <StatusIndicator status={statusVariant} size="sm" showLabel={false} />
                        <span className="regime-name-title">{label}</span>
                        {isCurrent && (
                          <Badge variant="success" size="sm">
                            Active
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td>
                      <code className="regime-code">{p.regime_label}</code>
                    </td>
                    <td className="tabular-nums font-medium">
                      {formatPercent(pct, { isRatio: false })}
                    </td>
                    <td className="tabular-nums">{p.observation_count}</td>
                    <td className="tabular-nums">{p.run_count}</td>
                    <td className="tabular-nums">{formatDuration(p.average_duration)}</td>
                    <td className="tabular-nums">{formatDuration(p.max_duration)}</td>
                    <td className="regime-col-window">
                      {p.first_seen && p.last_seen ? (
                        <span>
                          {formatDate(p.first_seen, "short")} → {formatDate(p.last_seen, "short")}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
