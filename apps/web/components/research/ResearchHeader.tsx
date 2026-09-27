"use client";

import React from "react";
import type { MarketItemResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

export interface ResearchHeaderProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onClearConversation: () => void;
  messageCount: number;
  isLoading: boolean;
}

export function ResearchHeader({
  markets,
  selectedSymbol,
  onSelectSymbol,
  onClearConversation,
  messageCount,
  isLoading,
}: ResearchHeaderProps) {
  return (
    <header className="research-header" role="banner">
      <div className="research-header-top">
        <div className="research-header-title-box">
          <div className="research-header-title-row">
            <h1 className="research-page-title">AI Research Assistant</h1>
            <Badge variant="outline" size="sm" className="research-mode-badge">
              Grounded Analytics
            </Badge>
            <Badge variant="default" size="sm" className="research-prov-badge">
              Deterministic Evidence
            </Badge>
          </div>
          <p className="research-page-subtitle">
            Natural language quantitative research operating over platform market regimes, empirical transition matrices, portfolio risk metrics, and systematic backtests.
          </p>
        </div>

        <div className="research-header-controls">
          <div className="research-symbol-selector-wrap">
            <label htmlFor="research-market-select" className="sr-only">
              Select Market Context
            </label>
            <Select
              id="research-market-select"
              value={selectedSymbol}
              onChange={(e) => onSelectSymbol(e.target.value)}
              disabled={isLoading}
              aria-label="Select market context for research queries"
              className="research-symbol-select"
            >
              <option value="">Cross-Market / General Context</option>
              {markets.map((m) => (
                <option key={m.symbol} value={m.symbol}>
                  {m.symbol} — {m.description || m.exchange}
                </option>
              ))}
            </Select>
          </div>

          {messageCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={onClearConversation}
              disabled={isLoading}
              aria-label="Clear research conversation"
              className="research-clear-btn"
            >
              Clear Chat
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
