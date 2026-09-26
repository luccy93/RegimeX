"use client";

import React from "react";
import type { MarketItemResponse, MarketBacktestResponse } from "@/lib/api/types";
import { MarketSelector } from "@/components/markets/MarketSelector";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/api/backtesting";

export interface BacktestHeaderProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  onSelectMarket: (symbol: string) => void;
  selectedStrategy: string;
  onSelectStrategy: (strategy: string) => void;
  selectedConvention: string;
  onSelectConvention: (convention: string) => void;
  isLoadingMarkets?: boolean;
  marketsError?: string | null;
  onRetryMarkets?: () => void;
  backtestData?: MarketBacktestResponse | null;
  isLoadingBacktest?: boolean;
}

export function BacktestHeader({
  markets,
  selectedSymbol,
  onSelectMarket,
  selectedStrategy,
  onSelectStrategy,
  selectedConvention,
  onSelectConvention,
  isLoadingMarkets = false,
  marketsError = null,
  onRetryMarkets,
  backtestData,
  isLoadingBacktest = false,
}: BacktestHeaderProps) {
  const selectedMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  return (
    <header className="backtest-workspace-header">
      <div className="backtest-header-top-row">
        <div className="backtest-header-titles">
          <div className="backtest-header-title-row">
            <h1 className="page-title">Systematic Backtesting</h1>
            <Badge variant="outline" size="sm" className="backtest-header-badge">
              V20 Event-Driven Engine
            </Badge>
          </div>
          <p className="page-subtitle">
            Deterministic event-driven execution simulation with realistic transaction friction and immutable reporting.
          </p>
        </div>

        {/* Controls: Strategy & Market */}
        <div className="backtest-header-controls">
          {/* Strategy Selection Buttons */}
          <div className="backtest-strategy-selector" role="group" aria-label="Strategy Selection">
            <button
              type="button"
              className={`strategy-toggle-btn ${selectedStrategy === "BUY_AND_HOLD" ? "strategy-btn-active" : ""}`}
              onClick={() => onSelectStrategy("BUY_AND_HOLD")}
              aria-pressed={selectedStrategy === "BUY_AND_HOLD"}
            >
              Benchmark Buy & Hold
            </button>
            <button
              type="button"
              className={`strategy-toggle-btn ${selectedStrategy === "REGIME_ADAPTIVE" ? "strategy-btn-active" : ""}`}
              onClick={() => onSelectStrategy("REGIME_ADAPTIVE")}
              aria-pressed={selectedStrategy === "REGIME_ADAPTIVE"}
            >
              Regime Adaptive
            </button>
          </div>

          {/* Market Selector */}
          <div className="backtest-header-selector-box">
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
      </div>

      {/* Execution Convention Toggle & Context metadata strip */}
      <div className="backtest-header-context-strip" aria-label="Backtest execution context">
        <div className="backtest-context-item">
          <span className="backtest-context-label">Active Instrument</span>
          <span className="backtest-context-value">
            {selectedMarket
              ? `${selectedMarket.symbol} (${selectedMarket.description || selectedMarket.asset_class})`
              : selectedSymbol || "—"}
          </span>
        </div>

        <div className="backtest-context-divider" aria-hidden="true" />

        <div className="backtest-context-item">
          <span className="backtest-context-label">Active Strategy</span>
          <span className="backtest-context-value">
            {backtestData ? backtestData.strategy_name : selectedStrategy}
          </span>
        </div>

        <div className="backtest-context-divider" aria-hidden="true" />

        <div className="backtest-context-item">
          <span className="backtest-context-label">Execution Price Fill</span>
          <div className="convention-toggle-container">
            <select
              aria-label="Execution price convention"
              className="convention-select"
              value={selectedConvention}
              onChange={(e) => onSelectConvention(e.target.value)}
            >
              <option value="CURRENT_CLOSE">CURRENT_CLOSE (Bar Close)</option>
              <option value="NEXT_OPEN">NEXT_OPEN (Next Open)</option>
            </select>
          </div>
        </div>

        <div className="backtest-context-divider" aria-hidden="true" />

        <div className="backtest-context-item">
          <span className="backtest-context-label">Starting Capital</span>
          <span className="backtest-context-value tabular-nums">
            {backtestData ? formatCurrency(backtestData.initial_cash) : "$100,000.00"}
          </span>
        </div>

        <div className="backtest-context-divider" aria-hidden="true" />

        <div className="backtest-context-item">
          <span className="backtest-context-label">Friction Model</span>
          <span className="backtest-context-value tabular-nums">
            5 bps Fee / 5 bps Slip
          </span>
        </div>
      </div>
    </header>
  );
}
