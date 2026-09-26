"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { MarketItemResponse, MarketBacktestResponse } from "@/lib/api/types";
import { listMarkets } from "@/lib/api/markets";
import { getMarketBacktest } from "@/lib/api/backtesting";
import { RegimeXApiError } from "@/lib/api/errors";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

import { BacktestHeader } from "./BacktestHeader";
import { BacktestPerformanceOverview } from "./BacktestPerformanceOverview";
import { EquityCurveChart } from "./EquityCurveChart";
import { TradeStatisticsSection } from "./TradeStatisticsSection";
import { BacktestRiskSection } from "./BacktestRiskSection";
import { PerformanceReportSection } from "./PerformanceReportSection";

export function BacktestWorkspace() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL State: ?symbol=XYZ&strategy=BUY_AND_HOLD
  const urlSymbol = searchParams.get("symbol");
  const urlStrategy = searchParams.get("strategy");

  // Markets Catalog State
  const [markets, setMarkets] = useState<MarketItemResponse[]>([]);
  const [isLoadingMarkets, setIsLoadingMarkets] = useState<boolean>(true);
  const [marketsError, setMarketsError] = useState<string | null>(null);

  // Active Selected Symbol, Strategy, Convention
  const [selectedSymbol, setSelectedSymbol] = useState<string>(urlSymbol?.toUpperCase() || "");
  const [selectedStrategy, setSelectedStrategy] = useState<string>(
    urlStrategy?.toUpperCase() === "REGIME_ADAPTIVE" ? "REGIME_ADAPTIVE" : "BUY_AND_HOLD"
  );
  const [selectedConvention, setSelectedConvention] = useState<string>("CURRENT_CLOSE");

  // Backtest Simulation State
  const [backtestData, setBacktestData] = useState<MarketBacktestResponse | null>(null);
  const [isLoadingBacktest, setIsLoadingBacktest] = useState<boolean>(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  // AbortController to cancel in-flight requests on switch
  const activeFetchController = useRef<AbortController | null>(null);

  // 1. Fetch Markets Catalog
  const fetchMarketCatalog = useCallback(async () => {
    setIsLoadingMarkets(true);
    setMarketsError(null);

    try {
      const response = await listMarkets({ limit: 100 });
      const items = response.items || [];
      setMarkets(items);

      if (items.length > 0) {
        const querySym = urlSymbol?.toUpperCase();
        const found = items.find((m) => m.symbol.toUpperCase() === querySym);

        if (found) {
          setSelectedSymbol(found.symbol);
        } else if (!querySym) {
          // Default deterministically to first market in catalog
          const defaultSym = items[0].symbol;
          setSelectedSymbol(defaultSym);
          const strat = selectedStrategy || "BUY_AND_HOLD";
          router.replace(`/app/backtesting?symbol=${encodeURIComponent(defaultSym)}&strategy=${strat}`, {
            scroll: false,
          });
        } else {
          setSelectedSymbol(querySym);
        }
      }
    } catch (err) {
      const msg =
        err instanceof RegimeXApiError
          ? err.message
          : "Unable to retrieve discoverable market instruments.";
      setMarketsError(msg);
    } finally {
      setIsLoadingMarkets(false);
    }
  }, [urlSymbol, router, selectedStrategy]);

  useEffect(() => {
    fetchMarketCatalog();
  }, [fetchMarketCatalog]);

  // Sync selectedSymbol with URL
  useEffect(() => {
    if (urlSymbol && urlSymbol.toUpperCase() !== selectedSymbol.toUpperCase()) {
      setSelectedSymbol(urlSymbol.toUpperCase());
    }
  }, [urlSymbol, selectedSymbol]);

  // Sync selectedStrategy with URL
  useEffect(() => {
    if (urlStrategy) {
      const norm = urlStrategy.toUpperCase();
      if ((norm === "BUY_AND_HOLD" || norm === "REGIME_ADAPTIVE") && norm !== selectedStrategy) {
        setSelectedStrategy(norm);
      }
    }
  }, [urlStrategy, selectedStrategy]);

  // 2. Fetch Backtest Data for Active Parameters
  const fetchBacktestData = useCallback(
    async (symbol: string, strategy: string, convention: string) => {
      if (!symbol) return;

      if (activeFetchController.current) {
        activeFetchController.current.abort();
      }
      const controller = new AbortController();
      activeFetchController.current = controller;

      setIsLoadingBacktest(true);
      setBacktestError(null);

      try {
        const data = await getMarketBacktest(
          symbol,
          {
            strategy,
            execution_convention: convention,
          },
          { signal: controller.signal }
        );
        setBacktestData(data);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        const msg =
          err instanceof RegimeXApiError
            ? err.message
            : "Failed to execute backtesting simulation.";
        setBacktestError(msg);
      } finally {
        setIsLoadingBacktest(false);
      }
    },
    []
  );

  useEffect(() => {
    if (selectedSymbol) {
      fetchBacktestData(selectedSymbol, selectedStrategy, selectedConvention);
    }
  }, [selectedSymbol, selectedStrategy, selectedConvention, fetchBacktestData]);

  // Handle market selection change
  const handleSelectMarket = (symbol: string) => {
    const cleanSym = symbol.trim().toUpperCase();
    if (!cleanSym || cleanSym === selectedSymbol) return;

    setSelectedSymbol(cleanSym);
    router.push(`/app/backtesting?symbol=${encodeURIComponent(cleanSym)}&strategy=${selectedStrategy}`, {
      scroll: false,
    });
  };

  // Handle strategy selection change
  const handleSelectStrategy = (strat: string) => {
    if (strat === selectedStrategy) return;
    setSelectedStrategy(strat);
    if (selectedSymbol) {
      router.push(`/app/backtesting?symbol=${encodeURIComponent(selectedSymbol)}&strategy=${strat}`, {
        scroll: false,
      });
    }
  };

  // Handle convention selection change
  const handleSelectConvention = (conv: string) => {
    if (conv === selectedConvention) return;
    setSelectedConvention(conv);
  };

  return (
    <div className="backtest-workspace">
      {/* Workspace Header & Context */}
      <BacktestHeader
        markets={markets}
        selectedSymbol={selectedSymbol}
        onSelectMarket={handleSelectMarket}
        selectedStrategy={selectedStrategy}
        onSelectStrategy={handleSelectStrategy}
        selectedConvention={selectedConvention}
        onSelectConvention={handleSelectConvention}
        isLoadingMarkets={isLoadingMarkets}
        marketsError={marketsError}
        onRetryMarkets={fetchMarketCatalog}
        backtestData={backtestData}
        isLoadingBacktest={isLoadingBacktest}
      />

      {/* Main Workspace Body */}
      <main className="backtest-workspace-body">
        {/* Loading Spinner */}
        {isLoadingBacktest && !backtestData && (
          <div className="backtest-loading-container" role="status" aria-live="polite">
            <Spinner size="lg" />
            <p className="backtest-loading-text">
              Executing event-driven backtest simulation for {selectedSymbol} ({selectedStrategy})…
            </p>
          </div>
        )}

        {/* Error State */}
        {backtestError && !backtestData && (
          <div className="backtest-error-container">
            <ErrorState
              title="Simulation Error"
              message={backtestError}
              onRetry={() => fetchBacktestData(selectedSymbol, selectedStrategy, selectedConvention)}
            />
          </div>
        )}

        {/* Empty State */}
        {!isLoadingBacktest && !backtestError && !backtestData && (
          <EmptyState
            title="No Backtest Simulation Available"
            description="Select an instrument and strategy above to execute deterministic simulation and view performance analytics."
            action={
              markets.length > 0 ? (
                <Button variant="primary" onClick={() => handleSelectMarket(markets[0].symbol)}>
                  Simulate {markets[0].symbol}
                </Button>
              ) : undefined
            }
          />
        )}

        {/* Render Workspace Sections */}
        {backtestData && (
          <div className="backtest-content-stack">
            {/* Performance Overview Metric Cards */}
            <BacktestPerformanceOverview backtestData={backtestData} />

            {/* Mark-to-Market Equity Curve & Drawdown Subplot */}
            <EquityCurveChart
              equityCurve={backtestData.equity_curve}
              initialCash={backtestData.initial_cash}
            />

            {/* Trade Execution & Win/Loss Statistics */}
            <TradeStatisticsSection
              trades={backtestData.trades}
              executedTrades={backtestData.executed_trades}
            />

            {/* Strategy Risk Diagnostics */}
            <BacktestRiskSection riskMetrics={backtestData.risk_metrics} />

            {/* Deterministic Performance Report & Audit Provenance */}
            <PerformanceReportSection report={backtestData.report} />
          </div>
        )}
      </main>
    </div>
  );
}
