"use client";

import React from "react";
import type { MarketItemResponse, MarketRegimeResponse } from "@/lib/api/types";
import { MarketSelector } from "@/components/markets/MarketSelector";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";

export interface RegimeWorkspaceHeaderProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  onSelectMarket: (symbol: string) => void;
  isLoadingMarkets?: boolean;
  marketsError?: string | null;
  onRetryMarkets?: () => void;
  regimeData?: MarketRegimeResponse | null;
  isLoadingRegime?: boolean;
}

export function RegimeWorkspaceHeader({
  markets,
  selectedSymbol,
  onSelectMarket,
  isLoadingMarkets = false,
  marketsError = null,
  onRetryMarkets,
  regimeData,
  isLoadingRegime = false,
}: RegimeWorkspaceHeaderProps) {
  const selectedMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  const hasAnalysisWindow =
    regimeData?.analysis_start && regimeData?.analysis_end;

  return (
    <header className="regime-workspace-header">
      <div className="regime-header-top-row">
        <div className="regime-header-titles">
          <div className="regime-header-title-row">
            <h1 className="page-title">Regime Analytics</h1>
            <Badge variant="outline" size="sm" className="regime-header-badge">
              V20 Workspace
            </Badge>
          </div>
          <p className="page-subtitle">
            Analyze market regimes, persistence, transitions, and regime-specific behavior.
          </p>
        </div>

        {/* Market Selector */}
        <div className="regime-header-selector-box">
          <MarketSelector
            markets={markets}
            selectedSymbol={selectedSymbol}
            onSelectMarket={onSelectMarket}
            isLoading={isLoadingMarkets}
            error={marketsError}
            onRetry={onRetryMarkets}
          />
        </div>
      </div>

      {/* Context metadata strip */}
      <div className="regime-header-context-strip" aria-label="Analysis context">
        <div className="regime-context-item">
          <span className="regime-context-label">Active Instrument</span>
          <span className="regime-context-value">
            {selectedMarket ? `${selectedMarket.symbol} (${selectedMarket.description || selectedMarket.asset_class})` : selectedSymbol || "—"}
          </span>
        </div>

        <div className="regime-context-divider" aria-hidden="true" />

        <div className="regime-context-item">
          <span className="regime-context-label">Analysis Window</span>
          <span className="regime-context-value">
            {hasAnalysisWindow
              ? `${formatDate(regimeData.analysis_start, "date-only")} → ${formatDate(regimeData.analysis_end, "date-only")}`
              : isLoadingRegime
              ? "Loading window…"
              : "Unavailable"}
          </span>
        </div>

        <div className="regime-context-divider" aria-hidden="true" />

        <div className="regime-context-item">
          <span className="regime-context-label">Sample Observations</span>
          <span className="regime-context-value tabular-nums">
            {regimeData ? `${regimeData.total_observations} bars` : isLoadingRegime ? "…" : "—"}
          </span>
        </div>

        <div className="regime-context-divider" aria-hidden="true" />

        <div className="regime-context-item">
          <span className="regime-context-label">Observed Regimes</span>
          <span className="regime-context-value tabular-nums">
            {regimeData ? `${regimeData.regimes_observed.length} distinct` : isLoadingRegime ? "…" : "—"}
          </span>
        </div>
      </div>
    </header>
  );
}
