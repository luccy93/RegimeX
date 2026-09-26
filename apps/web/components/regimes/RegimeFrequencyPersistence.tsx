"use client";

import React from "react";
import type { MarketRegimeResponse, MarketTransitionResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Tooltip } from "@/components/ui/Tooltip";
import {
  formatRegimeLabel,
  getRegimeBadgeClass,
  getRegimeColor,
} from "@/lib/utils/regime";
import { formatPercent, formatDate } from "@/lib/utils/formatters";

export interface RegimeFrequencyPersistenceProps {
  regimeData?: MarketRegimeResponse | null;
  transitionData?: MarketTransitionResponse | null;
  isLoading?: boolean;
}

interface FrequencyTableRow extends Record<string, unknown> {
  regimeId: number;
  regimeLabel: string;
  observationCount: number;
  frequency: number;
  persistenceProbability: number | null;
  runCount: number;
  firstSeen: string | null;
  lastSeen: string | null;
  isCurrent: boolean;
}

export function RegimeFrequencyPersistence({
  regimeData,
  transitionData,
  isLoading = false,
}: RegimeFrequencyPersistenceProps) {
  if (isLoading) {
    return (
      <Card variant="elevated" className="regime-table-card" aria-busy="true">
        <CardHeader>
          <div className="flex-between">
            <CardTitle>Regime Frequency &amp; Persistence</CardTitle>
          </div>
          <CardDescription>Historical observation frequency and Markovian persistence rates.</CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={[]}
            columns={[]}
            isLoading={true}
            loadingRowCount={4}
          />
        </CardContent>
      </Card>
    );
  }

  if (!regimeData) return null;

  const profiles = Object.values(regimeData.profiles ?? {});
  const currentRegimeId = regimeData.current_regime;

  const tableData: FrequencyTableRow[] = profiles.map((p) => {
    // Get persistence probability from transition analytics if available
    const regimeAnalytics = transitionData?.regime_analytics?.[p.regime_id];
    const persistenceProb = regimeAnalytics?.persistence_probability ?? null;

    return {
      regimeId: p.regime_id,
      regimeLabel: p.regime_label,
      observationCount: p.observation_count,
      frequency: p.frequency,
      persistenceProbability: persistenceProb,
      runCount: p.run_count,
      firstSeen: p.first_seen,
      lastSeen: p.last_seen,
      isCurrent: p.regime_id === currentRegimeId,
    };
  });

  const columns: DataTableColumn<FrequencyTableRow>[] = [
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
            {row.isCurrent && (
              <Badge variant="outline" size="sm" className="regime-active-pill">
                Active
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      key: "observationCount",
      header: "Observations",
      align: "right",
      numeric: true,
      render: (row) => row.observationCount.toLocaleString("en-US"),
    },
    {
      key: "frequency",
      header: "Frequency",
      align: "right",
      numeric: true,
      render: (row) => formatPercent(row.frequency, { isRatio: true, decimals: 1 }),
    },
    {
      key: "persistenceProbability",
      header: "Persistence Rate",
      align: "right",
      numeric: true,
      render: (row) => {
        if (row.persistenceProbability === null) {
          return <span className="text-muted">—</span>;
        }
        return (
          <span className="tabular-nums font-medium">
            {formatPercent(row.persistenceProbability, { isRatio: true, decimals: 1 })}
          </span>
        );
      },
    },
    {
      key: "runCount",
      header: "Run Count",
      align: "right",
      numeric: true,
      render: (row) => row.runCount.toLocaleString("en-US"),
    },
    {
      key: "firstSeen",
      header: "First Seen",
      align: "left",
      render: (row) => (row.firstSeen ? formatDate(row.firstSeen, "date-only") : "—"),
    },
    {
      key: "lastSeen",
      header: "Last Seen",
      align: "left",
      render: (row) => (row.lastSeen ? formatDate(row.lastSeen, "date-only") : "—"),
    },
  ];

  return (
    <Card variant="elevated" className="regime-table-card">
      <CardHeader>
        <div className="flex-between">
          <div>
            <CardTitle>Regime Frequency &amp; Persistence</CardTitle>
            <CardDescription>
              Empirical occurrence frequencies and continuous self-transition probabilities.
            </CardDescription>
          </div>
          <Tooltip content="Persistence rate measures P(S_{t+1}=k | S_t=k), distinct from run duration.">
            <span className="info-helper-badge">ℹ Definition</span>
          </Tooltip>
        </div>
      </CardHeader>

      <CardContent>
        <DataTable
          data={tableData}
          columns={columns}
          rowKey="regimeId"
          striped
          caption="Regime observation frequency and empirical persistence table"
          emptyMessage="No regime frequency statistics available."
        />
        <div className="table-semantic-note">
          <p className="note-text">
            <strong>Statistical distinction:</strong> Persistence rate denotes the step-to-step conditional probability of remaining in state <em>k</em>, whereas duration measures the span of consecutive observations before a regime change occurs.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
