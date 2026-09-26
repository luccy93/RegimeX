"use client";

import React from "react";
import type { MarketDataResponse, MarketRegimeResponse } from "@/lib/api/types";
import { MetricCard } from "@/components/ui/MetricCard";
import {
  formatPrice,
  formatPercent,
  formatDuration,
} from "@/lib/utils/formatters";
import { formatRegimeLabel } from "@/lib/utils/regime";

export interface MarketSnapshotProps {
  marketData?: MarketDataResponse | null;
  regimeData?: MarketRegimeResponse | null;
  currency?: string;
  isLoading?: boolean;
}

export function MarketSnapshot({
  marketData,
  regimeData,
  currency = "USD",
  isLoading = false,
}: MarketSnapshotProps) {
  // 1. Current Price calculation
  const bars = marketData?.items ?? [];
  const latestBar = bars.length > 0 ? bars[bars.length - 1] : null;
  const prevBar = bars.length > 1 ? bars[bars.length - 2] : null;

  const currentPriceFormatted = latestBar ? formatPrice(latestBar.close, currency) : "—";

  // 2. Latest Return calculation
  let returnFormatted = "—";
  let returnTrend: "up" | "down" | "flat" | "none" = "none";
  let returnChange: string | undefined = undefined;

  if (latestBar && prevBar && prevBar.close > 0) {
    const rawReturn = (latestBar.close - prevBar.close) / prevBar.close;
    returnFormatted = formatPercent(rawReturn, { includeSign: true, isRatio: true });
    returnChange = returnFormatted;
    if (rawReturn > 0.0001) {
      returnTrend = "up";
    } else if (rawReturn < -0.0001) {
      returnTrend = "down";
    } else {
      returnTrend = "flat";
    }
  }

  // 3. Volatility calculation
  // Check if regime feature statistics expose a volatility metric
  let volatilityFormatted = "—";
  let volatilityDesc = "Feature not exposed";
  const stats = regimeData?.statistics ?? {};

  const volFeature =
    stats["volatility_20d"] ??
    stats["volatility"] ??
    stats["realized_volatility"] ??
    stats["return_volatility"];

  if (volFeature && volFeature.mean !== null && volFeature.mean !== undefined) {
    volatilityFormatted = formatPercent(volFeature.mean, { isRatio: volFeature.mean < 1.0 });
    volatilityDesc = `${volFeature.feature_name} (mean)`;
  } else if (stats["return_1d"] && stats["return_1d"].std !== null && stats["return_1d"].std !== undefined) {
    // Annualized daily return standard deviation or raw std
    volatilityFormatted = formatPercent(stats["return_1d"].std, { isRatio: true });
    volatilityDesc = "return_1d (std dev)";
  }

  // 4. Current Regime
  const regimeLabel = formatRegimeLabel(
    regimeData?.current_regime_label,
    regimeData?.current_regime
  );
  const runDuration = regimeData?.current_context?.observations_in_current_run;
  const regimeDesc = runDuration !== undefined
    ? `Duration: ${formatDuration(runDuration)}`
    : "Point-in-time classification";

  // 5. Confidence
  const confidence = regimeData?.confidence;
  const confidenceFormatted =
    confidence !== null && confidence !== undefined && typeof confidence === "number"
      ? formatPercent(confidence, { isRatio: confidence <= 1.0, decimals: 1 })
      : "Unavailable";

  const confidenceDesc =
    confidence !== null && confidence !== undefined
      ? `${regimeData?.algorithm || "Model"} confidence`
      : "Not provided by model";

  return (
    <section className="market-snapshot-section" aria-label="Market Snapshot Metrics">
      <div className="market-snapshot-grid">
        {/* Metric 1: Current Price */}
        <MetricCard
          label="Current Price"
          value={currentPriceFormatted}
          description={latestBar ? `Close as of ${latestBar.timestamp.slice(0, 10)}` : "Historical close"}
          isLoading={isLoading}
        />

        {/* Metric 2: Latest Return */}
        <MetricCard
          label="Latest Return"
          value={returnFormatted}
          trend={returnTrend}
          change={returnChange}
          description="Period close-to-close"
          isLoading={isLoading}
        />

        {/* Metric 3: Volatility */}
        <MetricCard
          label="Regime Volatility"
          value={volatilityFormatted}
          description={volatilityDesc}
          isLoading={isLoading}
        />

        {/* Metric 4: Current Regime */}
        <MetricCard
          label="Current Regime"
          value={regimeLabel}
          description={regimeDesc}
          isLoading={isLoading}
        />

        {/* Metric 5: Confidence */}
        <MetricCard
          label="Regime Confidence"
          value={confidenceFormatted}
          description={confidenceDesc}
          isLoading={isLoading}
        />
      </div>
    </section>
  );
}
