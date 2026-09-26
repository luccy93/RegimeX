"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import {
  formatRegimeLabel,
  getRegimeColor,
  getRegimeBadgeClass,
} from "@/lib/utils/regime";
import { formatPercent } from "@/lib/utils/formatters";

export interface RegimeDistributionSectionProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

export function RegimeDistributionSection({
  regimeData,
  isLoading = false,
}: RegimeDistributionSectionProps) {
  if (isLoading) {
    return (
      <Card variant="elevated" className="regime-distribution-card" aria-busy="true">
        <CardHeader>
          <Skeleton shape="text" style={{ width: "14rem", height: "1.5rem" }} />
          <Skeleton shape="text" style={{ width: "22rem", marginTop: "0.5rem" }} />
        </CardHeader>
        <CardContent>
          <Skeleton shape="rect" style={{ height: "2.5rem", borderRadius: "0.5rem", marginBottom: "1.5rem" }} />
          <div className="regime-distribution-chips-grid">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} shape="rect" style={{ height: "4.5rem", borderRadius: "0.5rem" }} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!regimeData) return null;

  const profiles = Object.values(regimeData.profiles ?? {});
  const totalObservations = regimeData.total_observations;

  if (profiles.length === 0 || totalObservations <= 0) {
    return (
      <Card variant="elevated" className="regime-distribution-card">
        <CardHeader>
          <CardTitle>Regime Distribution</CardTitle>
          <CardDescription>Observed regime breakdown across historical sample.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="regime-empty-message">No regime distribution observations recorded.</p>
        </CardContent>
      </Card>
    );
  }

  // Calculate percentages strictly from counts / total_observations * 100
  const distributionItems = profiles.map((p) => {
    const calculatedPct =
      totalObservations > 0 ? (p.observation_count / totalObservations) * 100 : 0;
    const color = getRegimeColor(p.regime_label, p.regime_id);
    const isCurrent = p.regime_id === regimeData.current_regime;

    return {
      profile: p,
      percentage: calculatedPct,
      color,
      isCurrent,
    };
  });

  return (
    <Card variant="elevated" className="regime-distribution-card">
      <CardHeader>
        <div className="flex-between">
          <div>
            <CardTitle>Regime Distribution</CardTitle>
            <CardDescription>
              Empirical observation share across {totalObservations} total bars.
            </CardDescription>
          </div>
          <Badge variant="outline" size="sm">
            {profiles.length} Regimes Observed
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* Horizontal Composite Proportional Bar */}
        <div
          className="regime-distribution-bar-track"
          role="progressbar"
          aria-label="Regime distribution proportions"
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {distributionItems.map(({ profile, percentage, color }) => {
            if (percentage <= 0) return null;
            return (
              <div
                key={profile.regime_id}
                className="regime-distribution-segment"
                style={{
                  width: `${percentage}%`,
                  backgroundColor: color.hex,
                }}
                title={`${formatRegimeLabel(profile.regime_label, profile.regime_id)}: ${percentage.toFixed(1)}% (${profile.observation_count} bars)`}
              />
            );
          })}
        </div>

        {/* Breakdown Cards Grid */}
        <div className="regime-distribution-chips-grid" role="list" aria-label="Regime observation shares">
          {distributionItems.map(({ profile, percentage, color, isCurrent }) => (
            <div
              key={profile.regime_id}
              className={`regime-dist-chip ${isCurrent ? "regime-dist-chip-active" : ""}`}
              role="listitem"
            >
              <div className="dist-chip-header">
                <span
                  className="dist-chip-swatch"
                  style={{ backgroundColor: color.hex }}
                  aria-hidden="true"
                />
                <span className="dist-chip-name">
                  {formatRegimeLabel(profile.regime_label, profile.regime_id)}
                </span>
                {isCurrent && (
                  <Badge size="sm" className="dist-chip-current-badge">
                    Current
                  </Badge>
                )}
              </div>

              <div className="dist-chip-stats">
                <span className="dist-chip-pct tabular-nums" style={{ color: color.hex }}>
                  {percentage.toFixed(1)}%
                </span>
                <span className="dist-chip-counts tabular-nums">
                  {profile.observation_count} / {totalObservations} bars
                </span>
              </div>

              {/* Individual sub-progress bar */}
              <div className="dist-chip-track" aria-hidden="true">
                <div
                  className="dist-chip-fill"
                  style={{ width: `${Math.min(100, percentage)}%`, backgroundColor: color.hex }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
