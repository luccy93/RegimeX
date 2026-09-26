"use client";

import React from "react";
import type { MarketItemResponse, MarketRiskResponse } from "@/lib/api/types";
import { MarketSelector } from "@/components/markets/MarketSelector";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";

export interface RiskHeaderProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  onSelectMarket: (symbol: string) => void;
  isLoadingMarkets?: boolean;
  marketsError?: string | null;
  onRetryMarkets?: () => void;
  riskData?: MarketRiskResponse | null;
  isLoadingRisk?: boolean;
}

export function RiskHeader({
  markets,
  selectedSymbol,
  onSelectMarket,
  isLoadingMarkets = false,
  marketsError = null,
  onRetryMarkets,
  riskData,
  isLoadingRisk = false,
}: RiskHeaderProps) {
  const selectedMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  const hasAnalysisWindow = riskData?.start_timestamp && riskData?.end_timestamp;

  return (
    <header className="risk-workspace-header">
      <div className="risk-header-top-row">
        <div className="risk-header-titles">
          <div className="risk-header-title-row">
            <h1 className="page-title">Portfolio Risk Analytics</h1>
            <Badge variant="outline" size="sm" className="risk-header-badge">
              V20 Risk Intelligence
            </Badge>
          </div>
          <p className="page-subtitle">
            Comprehensive historical risk profiling, drawdown tracks, VaR quantiles, and Expected Shortfall.
          </p>
        </div>

        {/* Market Selector */}
        <div className="risk-header-selector-box">
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
      <div className="risk-header-context-strip" aria-label="Risk analysis context">
        <div className="risk-context-item">
          <span className="risk-context-label">Active Instrument</span>
          <span className="risk-context-value">
            {selectedMarket
              ? `${selectedMarket.symbol} (${selectedMarket.description || selectedMarket.asset_class})`
              : selectedSymbol || "—"}
          </span>
        </div>

        <div className="risk-context-divider" aria-hidden="true" />

        <div className="risk-context-item">
          <span className="risk-context-label">Analysis Window</span>
          <span className="risk-context-value">
            {hasAnalysisWindow
              ? `${formatDate(riskData.start_timestamp, "date-only")} → ${formatDate(riskData.end_timestamp, "date-only")}`
              : isLoadingRisk
              ? "Loading window…"
              : "Unavailable"}
          </span>
        </div>

        <div className="risk-context-divider" aria-hidden="true" />

        <div className="risk-context-item">
          <span className="risk-context-label">Sample Observations</span>
          <span className="risk-context-value tabular-nums">
            {riskData ? `${riskData.observation_count} bars` : isLoadingRisk ? "…" : "—"}
          </span>
        </div>

        <div className="risk-context-divider" aria-hidden="true" />

        <div className="risk-context-item">
          <span className="risk-context-label">Annualization Basis</span>
          <span className="risk-context-value tabular-nums">
            {riskData ? `${riskData.volatility.periods_per_year} periods/yr` : isLoadingRisk ? "…" : "252"}
          </span>
        </div>

        <div className="risk-context-divider" aria-hidden="true" />

        <div className="risk-context-item">
          <span className="risk-context-label">Target Return</span>
          <span className="risk-context-value tabular-nums">
            {riskData ? `${(riskData.downside_risk.target_return * 100).toFixed(2)}%` : "0.00%"}
          </span>
        </div>
      </div>
    </header>
  );
}
