"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  formatRegimeLabel,
  getRegimeBadgeClass,
  getRegimeColor,
} from "@/lib/utils/regime";
import { formatDuration } from "@/lib/utils/formatters";

export interface RegimeDurationSectionProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

interface DurationTableRow extends Record<string, unknown> {
  regimeId: number;
  regimeLabel: string;
  averageDuration: number;
  medianDuration: number;
  minDuration: number;
  maxDuration: number;
  currentDuration: number | null;
  isCurrent: boolean;
}

export function RegimeDurationSection({
  regimeData,
  isLoading = false,
}: RegimeDurationSectionProps) {
  if (isLoading) {
    return (
      <Card variant="elevated" className="regime-duration-card" aria-busy="true">
        <CardHeader>
          <Skeleton shape="text" style={{ width: "12rem", height: "1.5rem" }} />
          <Skeleton shape="text" style={{ width: "20rem", marginTop: "0.5rem" }} />
        </CardHeader>
        <CardContent>
          <DataTable
            data={[]}
            columns={[]}
            isLoading={true}
            loadingRowCount={3}
          />
        </CardContent>
      </Card>
    );
  }

  if (!regimeData) return null;

  const profiles = Object.values(regimeData.profiles ?? {});
  const currentRegimeId = regimeData.current_regime;
  const currentContextRun = regimeData.current_context?.observations_in_current_run ?? null;

  const tableData: DurationTableRow[] = profiles.map((p) => {
    const isCurrent = p.regime_id === currentRegimeId;
    return {
      regimeId: p.regime_id,
      regimeLabel: p.regime_label,
      averageDuration: p.average_duration,
      medianDuration: p.median_duration,
      minDuration: p.min_duration,
      maxDuration: p.max_duration,
      currentDuration: isCurrent ? currentContextRun : null,
      isCurrent,
    };
  });

  const columns: DataTableColumn<DurationTableRow>[] = [
    {
      key: "regime",
      header: "Regime",
      render: (row) => {
        const color = getRegimeColor(row.regimeLabel, row.regimeId);
        return (
          <div className="flex-align-center gap-2">
            <span
              className="dist-chip-swatch"
              style={{ backgroundColor: color.hex }}
              aria-hidden="true"
            />
            <span className="font-semibold">
              {formatRegimeLabel(row.regimeLabel, row.regimeId)}
            </span>
            <Badge className={getRegimeBadgeClass(row.regimeLabel)} size="sm">
              ID: {row.regimeId}
            </Badge>
          </div>
        );
      },
    },
    {
      key: "averageDuration",
      header: "Average Duration",
      align: "right",
      numeric: true,
      render: (row) => formatDuration(row.averageDuration, "bar"),
    },
    {
      key: "medianDuration",
      header: "Median Duration",
      align: "right",
      numeric: true,
      render: (row) => formatDuration(row.medianDuration, "bar"),
    },
    {
      key: "minDuration",
      header: "Min Duration",
      align: "right",
      numeric: true,
      render: (row) => formatDuration(row.minDuration, "bar"),
    },
    {
      key: "maxDuration",
      header: "Max Duration",
      align: "right",
      numeric: true,
      render: (row) => formatDuration(row.maxDuration, "bar"),
    },
    {
      key: "currentDuration",
      header: "Current Run",
      align: "right",
      numeric: true,
      render: (row) => {
        if (row.currentDuration === null) return <span className="text-muted">—</span>;
        return (
          <span className="font-semibold text-primary">
            {formatDuration(row.currentDuration, "bar")}
          </span>
        );
      },
    },
  ];

  // Find max duration for relative scaling in comparative visual bars
  const highestObservedDuration = Math.max(
    ...profiles.map((p) => p.max_duration),
    1
  );

  return (
    <Card variant="elevated" className="regime-duration-card">
      <CardHeader>
        <div className="flex-between">
          <div>
            <CardTitle>Duration Analysis</CardTitle>
            <CardDescription>
              Mean, median, and extreme duration characteristics measured in observation bars.
            </CardDescription>
          </div>
          <Badge variant="outline" size="sm">
            Units: Observation Bars
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* Comparative Duration Visual Bars */}
        <div className="duration-visual-comparison-grid" aria-label="Visual duration comparison">
          {profiles.map((p) => {
            const color = getRegimeColor(p.regime_label, p.regime_id);
            const isCurrent = p.regime_id === currentRegimeId;
            const avgBarWidth = Math.min(100, (p.average_duration / highestObservedDuration) * 100);
            const maxBarWidth = Math.min(100, (p.max_duration / highestObservedDuration) * 100);

            return (
              <div key={p.regime_id} className={`duration-bar-item ${isCurrent ? "duration-bar-item-active" : ""}`}>
                <div className="duration-bar-header">
                  <div className="flex-align-center gap-2">
                    <span className="dist-chip-swatch" style={{ backgroundColor: color.hex }} aria-hidden="true" />
                    <span className="duration-regime-name font-medium">
                      {formatRegimeLabel(p.regime_label, p.regime_id)}
                    </span>
                    {isCurrent && <Badge size="sm" className="dist-chip-current-badge">Active</Badge>}
                  </div>
                  <div className="duration-metrics-summary tabular-nums">
                    <span>Avg: {formatDuration(p.average_duration, "bar")}</span>
                    <span className="text-muted">|</span>
                    <span>Max: {formatDuration(p.max_duration, "bar")}</span>
                  </div>
                </div>

                {/* Range bar visualizing average vs max duration */}
                <div className="duration-track-container" aria-hidden="true">
                  <div className="duration-track-bg">
                    {/* Max extent */}
                    <div
                      className="duration-extent-max"
                      style={{
                        width: `${maxBarWidth}%`,
                        backgroundColor: color.hexSubtle,
                        borderColor: color.hex,
                      }}
                      title={`Max Duration: ${p.max_duration} bars`}
                    />
                    {/* Average extent */}
                    <div
                      className="duration-extent-avg"
                      style={{
                        width: `${avgBarWidth}%`,
                        backgroundColor: color.hex,
                      }}
                      title={`Average Duration: ${p.average_duration.toFixed(1)} bars`}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Duration Data Table */}
        <div className="duration-table-wrapper" style={{ marginTop: "1.5rem" }}>
          <DataTable
            data={tableData}
            columns={columns}
            rowKey="regimeId"
            striped
            caption="Regime duration statistics comparison table"
            emptyMessage="No duration data available."
          />
        </div>

        {/* Section 13 Explicit Fallback: Detailed Duration Distribution unavailable */}
        <div className="duration-distribution-notice">
          <span className="notice-icon" aria-hidden="true">ℹ</span>
          <span className="notice-text">
            Detailed duration distribution unavailable — empirical discrete histogram data is not exposed in the API summary payload. Durations are computed from continuous run segment lengths.
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
