"use client";

import React, { useState } from "react";
import type { MarketRegimeResponse, FeatureStatisticDTO } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  formatRegimeLabel,
  getRegimeBadgeClass,
  getRegimeColor,
} from "@/lib/utils/regime";
import {
  formatPercent,
  formatNumber,
} from "@/lib/utils/formatters";

export interface RegimeProfileComparisonProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

type StatViewMode = "mean" | "median" | "std" | "min" | "max" | "all";

interface FeatureComparisonRow extends Record<string, unknown> {
  featureName: string;
  metricLabel: string;
  [regimeKey: string]: unknown;
}

/**
 * Formats a feature statistic value defensively without zero-imputation.
 * If value is null, undefined, or non-finite, returns "—".
 */
function formatFeatureVal(
  val: number | null | undefined,
  featureName: string
): string {
  if (val === null || val === undefined || typeof val !== "number" || !Number.isFinite(val)) {
    return "—";
  }

  const lowerName = featureName.toLowerCase();
  if (lowerName.includes("return")) {
    return formatPercent(val, { isRatio: true, decimals: 2, includeSign: true });
  }
  if (lowerName.includes("volatility") || lowerName.includes("vol_")) {
    return formatPercent(val, { isRatio: true, decimals: 2 });
  }
  if (Math.abs(val) < 0.01 && val !== 0) {
    return val.toFixed(4);
  }
  return formatNumber(val, { decimals: 3 });
}

export function RegimeProfileComparison({
  regimeData,
  isLoading = false,
}: RegimeProfileComparisonProps) {
  const [selectedStat, setSelectedStat] = useState<StatViewMode>("mean");

  if (isLoading) {
    return (
      <Card variant="elevated" className="regime-profile-card" aria-busy="true">
        <CardHeader>
          <Skeleton shape="text" style={{ width: "16rem", height: "1.5rem" }} />
          <Skeleton shape="text" style={{ width: "24rem", marginTop: "0.5rem" }} />
        </CardHeader>
        <CardContent>
          <DataTable
            data={[]}
            columns={[]}
            isLoading={true}
            loadingRowCount={5}
          />
        </CardContent>
      </Card>
    );
  }

  if (!regimeData) return null;

  const profiles = Object.values(regimeData.profiles ?? {});
  if (profiles.length === 0) {
    return (
      <Card variant="elevated" className="regime-profile-card">
        <CardHeader>
          <CardTitle>Regime Profile Comparison</CardTitle>
          <CardDescription>Feature statistics comparison across market regimes.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="regime-empty-message">No regime profiles or feature statistics available.</p>
        </CardContent>
      </Card>
    );
  }

  // Collect all unique feature names across all regime profiles
  const featureNamesSet = new Set<string>();
  for (const p of profiles) {
    if (p.feature_statistics) {
      for (const fName of Object.keys(p.feature_statistics)) {
        featureNamesSet.add(fName);
      }
    }
  }
  const featureNames = Array.from(featureNamesSet).sort();

  if (featureNames.length === 0) {
    return (
      <Card variant="elevated" className="regime-profile-card">
        <CardHeader>
          <CardTitle>Regime Profile Comparison</CardTitle>
          <CardDescription>Feature statistics comparison across market regimes.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="regime-empty-message">
            No feature statistics registered for observed regimes in this window.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Build rows based on selectedStat
  const tableRows: FeatureComparisonRow[] = [];

  if (selectedStat === "all") {
    // Show each feature with subrows for Mean, Std, Median, Min, Max
    const statsToDisplay: Array<{ key: keyof FeatureStatisticDTO; label: string }> = [
      { key: "mean", label: "Mean (μ)" },
      { key: "std", label: "Std Dev (σ)" },
      { key: "median", label: "Median (M)" },
      { key: "min", label: "Min" },
      { key: "max", label: "Max" },
    ];

    for (const fName of featureNames) {
      for (const s of statsToDisplay) {
        const row: FeatureComparisonRow = {
          featureName: fName,
          metricLabel: s.label,
        };

        for (const p of profiles) {
          const statObj = p.feature_statistics?.[fName];
          const rawVal = statObj ? (statObj[s.key] as number | null | undefined) : null;
          row[`regime_${p.regime_id}`] = rawVal;
        }

        tableRows.push(row);
      }
    }
  } else {
    // Single stat per feature row
    const statKeyMap: Record<StatViewMode, keyof FeatureStatisticDTO> = {
      mean: "mean",
      median: "median",
      std: "std",
      min: "min",
      max: "max",
      all: "mean",
    };

    const targetKey = statKeyMap[selectedStat];
    const statLabels: Record<StatViewMode, string> = {
      mean: "Mean (μ)",
      median: "Median (M)",
      std: "Std Dev (σ)",
      min: "Minimum",
      max: "Maximum",
      all: "All",
    };

    for (const fName of featureNames) {
      const row: FeatureComparisonRow = {
        featureName: fName,
        metricLabel: statLabels[selectedStat],
      };

      for (const p of profiles) {
        const statObj = p.feature_statistics?.[fName];
        const rawVal = statObj ? (statObj[targetKey] as number | null | undefined) : null;
        row[`regime_${p.regime_id}`] = rawVal;
      }

      tableRows.push(row);
    }
  }

  // Construct dynamic columns: Feature Name, Metric Label (if all), then one column per regime
  const columns: DataTableColumn<FeatureComparisonRow>[] = [
    {
      key: "featureName",
      header: "Feature",
      align: "left",
      render: (row, index) => {
        // If "all" mode, only show feature name on the first subrow
        if (selectedStat === "all" && index % 5 !== 0) {
          return <span className="text-muted feature-sub-indent">↳</span>;
        }
        return <span className="font-semibold text-foreground">{row.featureName}</span>;
      },
    },
    ...(selectedStat === "all"
      ? [
          {
            key: "metricLabel",
            header: "Statistic",
            align: "left" as const,
            render: (row: FeatureComparisonRow) => (
              <span className="text-muted text-xs font-mono">{row.metricLabel}</span>
            ),
          },
        ]
      : []),
    ...profiles.map((p) => {
      const color = getRegimeColor(p.regime_label, p.regime_id);
      const isCurrent = p.regime_id === regimeData.current_regime;

      return {
        key: `regime_${p.regime_id}`,
        header: `${formatRegimeLabel(p.regime_label, p.regime_id)} (ID ${p.regime_id})`,
        align: "right" as const,
        numeric: true,
        headerClassName: isCurrent ? "regime-col-header-active" : undefined,
        render: (row: FeatureComparisonRow) => {
          const rawVal = row[`regime_${p.regime_id}`] as number | null | undefined;
          const formatted = formatFeatureVal(rawVal, row.featureName);

          return (
            <span
              className={`tabular-nums font-medium ${rawVal === null || rawVal === undefined ? "text-muted" : ""}`}
              style={rawVal !== null && rawVal !== undefined ? { color: color.hex } : undefined}
            >
              {formatted}
            </span>
          );
        },
      };
    }),
  ];

  return (
    <Card variant="elevated" className="regime-profile-card">
      <CardHeader>
        <div className="regime-profile-header-row">
          <div>
            <CardTitle>Regime Profile Comparison</CardTitle>
            <CardDescription>
              Quantitative feature statistics across all detected market regimes.
            </CardDescription>
          </div>

          {/* Stat selector buttons */}
          <div className="stat-selector-group" role="group" aria-label="Feature statistic selector">
            {(["mean", "median", "std", "min", "max", "all"] as StatViewMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                className={`stat-filter-btn ${selectedStat === mode ? "stat-filter-btn-active" : ""}`}
                onClick={() => setSelectedStat(mode)}
              >
                {mode === "std" ? "Std Dev" : mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="table-responsive-container">
          <DataTable
            data={tableRows}
            columns={columns}
            rowKey={(r, idx) => `${r.featureName}_${r.metricLabel}_${idx}`}
            striped
            caption="Comparison of feature statistics across observed regimes"
            emptyMessage="No feature comparison statistics available."
          />
        </div>

        <div className="table-semantic-note">
          <p className="note-text">
            <strong>Data integrity standard:</strong> Missing feature statistics are never zero-imputed. Values marked with <em>—</em> indicate that the statistic was not recorded or is non-finite for that regime.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
