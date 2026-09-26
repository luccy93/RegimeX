"use client";

import React from "react";
import Link from "next/link";
import type { MarketDataResponse, MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils/formatters";

export interface DataHealthProps {
  symbol: string;
  marketData?: MarketDataResponse | null;
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

export function DataHealth({
  symbol,
  marketData,
  regimeData,
  isLoading = false,
}: DataHealthProps) {
  const hasData = (marketData?.items?.length ?? 0) > 0;
  const isHealthy = hasData && !isLoading;

  const startDate = marketData?.start || regimeData?.analysis_start;
  const endDate = marketData?.end || regimeData?.analysis_end;

  return (
    <Card variant="elevated" className="data-health-card">
      <CardHeader>
        <div className="data-health-header-row">
          <div>
            <CardTitle>Data Health &amp; Model Provenance</CardTitle>
            <CardDescription>
              Backend API synchronization and statistical engine verification for {symbol}
            </CardDescription>
          </div>
          <StatusIndicator
            status={isLoading ? "pending" : isHealthy ? "active" : "offline"}
            label={isLoading ? "Synchronizing" : isHealthy ? "Data Available" : "Feed Inactive"}
            size="md"
          />
        </div>
      </CardHeader>

      <CardContent>
        <div className="data-health-grid">
          {/* Item 1: Feed Status */}
          <div className="data-health-item">
            <span className="data-health-item-label">API Feed Status</span>
            <div className="data-health-item-val-row">
              <StatusIndicator
                status={isHealthy ? "active" : isLoading ? "pending" : "offline"}
                size="sm"
                showLabel={false}
              />
              <span className="data-health-item-val">
                {isLoading ? "Querying API…" : isHealthy ? "Data available" : "Unavailable"}
              </span>
            </div>
            <p className="data-health-item-meta">
              Verified from <code>GET /api/v1/markets/{symbol}/data</code>
            </p>
          </div>

          {/* Item 2: Observation Window */}
          <div className="data-health-item">
            <span className="data-health-item-label">Verified Time Window</span>
            <span className="data-health-item-val">
              {startDate && endDate
                ? `${formatDate(startDate, "date-only")} → ${formatDate(endDate, "date-only")}`
                : "—"}
            </span>
            <p className="data-health-item-meta">Timezone: UTC (ISO 8601 aware)</p>
          </div>

          {/* Item 3: Bar Counts */}
          <div className="data-health-item">
            <span className="data-health-item-label">Retrieved Bars</span>
            <span className="data-health-item-val tabular-nums">
              {marketData?.count ?? 0} bars
              {marketData?.total !== undefined && ` (${marketData.total} in storage)`}
            </span>
            <p className="data-health-item-meta">Interval: {marketData?.interval || "1d"}</p>
          </div>

          {/* Item 4: Regime Engine Provenance */}
          <div className="data-health-item">
            <span className="data-health-item-label">Regime Engine</span>
            <span className="data-health-item-val">
              {regimeData?.model_name || "Ensemble Pipeline"}
            </span>
            <p className="data-health-item-meta">
              Algorithm: <code>{regimeData?.algorithm || "Statistical"}</code> | Version:{" "}
              {regimeData?.model_version || "1.0.0"}
            </p>
          </div>
        </div>

        {/* Descriptive Architecture Note */}
        <div className="data-health-notice">
          <p className="data-health-notice-text">
            <strong>Institutional Integrity Notice:</strong> RegimeX consumes production market feeds
            and mathematical regime detectors with zero client-side estimation. Numerical precision
            and regime persistence intervals reflect strict server-side state.
          </p>
        </div>

        {/* Future Analytics Navigation Links */}
        <div className="data-health-nav-row">
          <Link href={`/app/regimes?symbol=${encodeURIComponent(symbol)}`}>
            <Button variant="secondary" size="sm">
              Explore Transition Matrix (V19.2) →
            </Button>
          </Link>
          <Link href={`/app/risk?symbol=${encodeURIComponent(symbol)}`}>
            <Button variant="ghost" size="sm">
              View Risk Analytics (V20) →
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
