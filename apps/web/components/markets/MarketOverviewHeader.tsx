"use client";

import React from "react";
import type { MarketItemResponse, MarketRegimeResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { MarketSelector } from "./MarketSelector";
import {
  formatRegimeLabel,
  getRegimeStatusVariant,
  getRegimeBadgeClass,
} from "@/lib/utils/regime";

export interface MarketOverviewHeaderProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  selectedMarket?: MarketItemResponse;
  regimeData?: MarketRegimeResponse | null;
  onSelectMarket: (symbol: string) => void;
  isLoadingMarkets?: boolean;
  isLoadingData?: boolean;
  marketError?: string | null;
  onRetryMarkets?: () => void;
}

export function MarketOverviewHeader({
  markets,
  selectedSymbol,
  selectedMarket,
  regimeData,
  onSelectMarket,
  isLoadingMarkets = false,
  isLoadingData = false,
  marketError = null,
  onRetryMarkets,
}: MarketOverviewHeaderProps) {
  const currentRegimeLabel = regimeData?.current_regime_label;
  const currentRegimeId = regimeData?.current_regime;
  const formattedRegime = formatRegimeLabel(currentRegimeLabel, currentRegimeId);
  const regimeStatus = getRegimeStatusVariant(currentRegimeLabel);
  const regimeBadgeClass = getRegimeBadgeClass(currentRegimeLabel);

  return (
    <header className="market-overview-header">
      {/* Top Title & Selector Row */}
      <div className="market-header-top-row">
        <div>
          <h1 className="page-title">Market Intelligence</h1>
          <p className="page-subtitle">
            Quantitative regime detection, historical price structure, and data health verification.
          </p>
        </div>

        {/* Market Selector Control */}
        <div className="market-header-selector-wrapper">
          <MarketSelector
            markets={markets}
            selectedSymbol={selectedSymbol}
            onSelectMarket={onSelectMarket}
            isLoading={isLoadingMarkets}
            error={marketError}
            onRetry={onRetryMarkets}
          />
        </div>
      </div>

      {/* Market Status Banner */}
      <div className="market-status-banner">
        <div className="market-status-banner-left">
          <div className="market-status-symbol-group">
            <span className="market-status-symbol">{selectedSymbol}</span>
            {selectedMarket && (
              <span className="market-status-name">{selectedMarket.description}</span>
            )}
          </div>

          <div className="market-status-tags">
            {selectedMarket && (
              <>
                <Badge variant="outline" size="sm">
                  {selectedMarket.asset_class.toUpperCase()}
                </Badge>
                {selectedMarket.exchange && (
                  <Badge variant="outline" size="sm">
                    {selectedMarket.exchange}
                  </Badge>
                )}
                {selectedMarket.currency && (
                  <Badge variant="outline" size="sm">
                    {selectedMarket.currency}
                  </Badge>
                )}
              </>
            )}
          </div>
        </div>

        <div className="market-status-banner-right">
          {/* Regime Badge */}
          <div className="market-status-regime-box">
            <span className="market-status-regime-caption">Current Regime:</span>
            {isLoadingData ? (
              <span className="market-status-regime-loading">Evaluating…</span>
            ) : (
              <span className={`market-regime-pill ${regimeBadgeClass}`}>
                <StatusIndicator
                  status={regimeStatus}
                  showLabel={false}
                  size="sm"
                />
                <span className="market-regime-pill-text">{formattedRegime}</span>
              </span>
            )}
          </div>

          {/* Data Feed Status */}
          <div className="market-status-feed-box">
            <StatusIndicator
              status={isLoadingData ? "pending" : "active"}
              label={isLoadingData ? "Updating" : "Data Available"}
              size="sm"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
