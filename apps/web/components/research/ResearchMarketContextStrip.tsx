"use client";

import React from "react";
import type { CurrentRegimeContextDTO, MarketItemResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { formatPercent } from "@/lib/utils/formatters";

export interface ResearchMarketContextStripProps {
  selectedSymbol: string;
  marketItem?: MarketItemResponse;
  regimeContext?: CurrentRegimeContextDTO | null;
  confidence?: number | null;
  isLoadingRegime?: boolean;
}

export function ResearchMarketContextStrip({
  selectedSymbol,
  marketItem,
  regimeContext,
  confidence,
  isLoadingRegime = false,
}: ResearchMarketContextStripProps) {
  if (!selectedSymbol) {
    return (
      <div className="research-context-strip research-context-strip-empty" role="region" aria-label="Market context">
        <span className="research-context-icon">🌐</span>
        <span className="research-context-label">Active Scope:</span>
        <span className="research-context-val">Global Platform Intelligence (No single market constraint)</span>
      </div>
    );
  }

  const regimeLabel = regimeContext?.current_regime_label || "EVALUATING";
  const regimeVariant: "success" | "danger" | "default" =
    regimeLabel.toUpperCase().includes("BULL")
      ? "success"
      : regimeLabel.toUpperCase().includes("BEAR")
      ? "danger"
      : "default";

  const formattedConfidence =
    confidence !== null && confidence !== undefined
      ? formatPercent(confidence, { decimals: 1 })
      : null;

  return (
    <div className="research-context-strip" role="region" aria-label={`Market context for ${selectedSymbol}`}>
      <div className="research-context-group">
        <span className="research-context-tag">Market:</span>
        <span className="research-context-symbol">{selectedSymbol}</span>
        {marketItem?.description && (
          <span className="research-context-desc">({marketItem.description})</span>
        )}
      </div>

      <span className="research-context-divider" aria-hidden="true">•</span>

      <div className="research-context-group">
        <span className="research-context-tag">Current Regime:</span>
        {isLoadingRegime ? (
          <span className="research-evaluating-text">Evaluating...</span>
        ) : (
          <Badge variant={regimeVariant} size="sm">
            {regimeLabel}
          </Badge>
        )}
      </div>

      {formattedConfidence && !isLoadingRegime && (
        <>
          <span className="research-context-divider" aria-hidden="true">•</span>
          <div className="research-context-group">
            <span className="research-context-tag">Confidence:</span>
            <span className="research-context-val">{formattedConfidence}</span>
          </div>
        </>
      )}

      {regimeContext?.observations_in_current_run !== undefined && !isLoadingRegime && (
        <>
          <span className="research-context-divider" aria-hidden="true">•</span>
          <div className="research-context-group">
            <span className="research-context-tag">Run Duration:</span>
            <span className="research-context-val">
              {regimeContext.observations_in_current_run} obs
            </span>
          </div>
        </>
      )}

      <div className="research-context-attached-badge">
        <Badge variant="outline" size="sm">
          Grounding Context Attached
        </Badge>
      </div>
    </div>
  );
}
