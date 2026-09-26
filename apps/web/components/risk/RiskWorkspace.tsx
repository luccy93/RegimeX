"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { MarketItemResponse, MarketRiskResponse } from "@/lib/api/types";
import { listMarkets } from "@/lib/api/markets";
import { getMarketRisk } from "@/lib/api/risk";
import { RegimeXApiError } from "@/lib/api/errors";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

import { RiskHeader } from "./RiskHeader";
import { RiskOverview } from "./RiskOverview";
import { RiskDrawdownSection } from "./RiskDrawdownSection";
import { RiskReturnDistributionSection } from "./RiskReturnDistributionSection";
import { RiskMethodologySection } from "./RiskMethodologySection";

export function RiskWorkspace() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL State: ?symbol=XYZ
  const urlSymbol = searchParams.get("symbol");

  // Markets Catalog State
  const [markets, setMarkets] = useState<MarketItemResponse[]>([]);
  const [isLoadingMarkets, setIsLoadingMarkets] = useState<boolean>(true);
  const [marketsError, setMarketsError] = useState<string | null>(null);

  // Active Selected Symbol
  const [selectedSymbol, setSelectedSymbol] = useState<string>(urlSymbol?.toUpperCase() || "");

  // Risk Data State
  const [riskData, setRiskData] = useState<MarketRiskResponse | null>(null);
  const [isLoadingRisk, setIsLoadingRisk] = useState<boolean>(false);
  const [riskError, setRiskError] = useState<string | null>(null);

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
          router.replace(`/app/risk?symbol=${encodeURIComponent(defaultSym)}`, {
            scroll: false,
          });
        } else {
          // Keep requested symbol even if not in standard catalog
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
  }, [urlSymbol, router]);

  useEffect(() => {
    fetchMarketCatalog();
  }, [fetchMarketCatalog]);

  // Keep selectedSymbol in sync with URL if user navigates back/forward
  useEffect(() => {
    if (urlSymbol && urlSymbol.toUpperCase() !== selectedSymbol.toUpperCase()) {
      setSelectedSymbol(urlSymbol.toUpperCase());
    }
  }, [urlSymbol, selectedSymbol]);

  // 2. Fetch Risk Data for Active Symbol
  const fetchRiskData = useCallback(async (symbol: string) => {
    if (!symbol) return;

    if (activeFetchController.current) {
      activeFetchController.current.abort();
    }
    const controller = new AbortController();
    activeFetchController.current = controller;

    setIsLoadingRisk(true);
    setRiskError(null);

    try {
      const data = await getMarketRisk(symbol, {}, { signal: controller.signal });
      setRiskData(data);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return; // ignore aborted request
      }
      const msg =
        err instanceof RegimeXApiError
          ? err.message
          : "Failed to evaluate portfolio risk analytics.";
      setRiskError(msg);
    } finally {
      setIsLoadingRisk(false);
    }
  }, []);

  useEffect(() => {
    if (selectedSymbol) {
      fetchRiskData(selectedSymbol);
    }
  }, [selectedSymbol, fetchRiskData]);

  // Handle market selection change
  const handleSelectMarket = (symbol: string) => {
    const cleanSym = symbol.trim().toUpperCase();
    if (!cleanSym || cleanSym === selectedSymbol) return;

    setSelectedSymbol(cleanSym);
    router.push(`/app/risk?symbol=${encodeURIComponent(cleanSym)}`, {
      scroll: false,
    });
  };

  return (
    <div className="risk-workspace">
      {/* Workspace Header & Context */}
      <RiskHeader
        markets={markets}
        selectedSymbol={selectedSymbol}
        onSelectMarket={handleSelectMarket}
        isLoadingMarkets={isLoadingMarkets}
        marketsError={marketsError}
        onRetryMarkets={fetchMarketCatalog}
        riskData={riskData}
        isLoadingRisk={isLoadingRisk}
      />

      {/* Main Workspace Body */}
      <main className="risk-workspace-body">
        {/* Loading Spinner */}
        {isLoadingRisk && !riskData && (
          <div className="risk-loading-container" role="status" aria-live="polite">
            <Spinner size="lg" />
            <p className="risk-loading-text">Computing V13 portfolio risk intelligence for {selectedSymbol}…</p>
          </div>
        )}

        {/* Error State */}
        {riskError && !riskData && (
          <div className="risk-error-container">
            <ErrorState
              title="Risk Evaluation Error"
              message={riskError}
              onRetry={() => fetchRiskData(selectedSymbol)}
            />
          </div>
        )}

        {/* Empty State */}
        {!isLoadingRisk && !riskError && !riskData && (
          <EmptyState
            title="No Risk Analytics Available"
            description="Select an instrument above to compute return statistics, volatility, drawdown tracking, and tail risk metrics."
            action={
              markets.length > 0 ? (
                <Button variant="primary" onClick={() => handleSelectMarket(markets[0].symbol)}>
                  Analyze {markets[0].symbol}
                </Button>
              ) : undefined
            }
          />
        )}

        {/* Render Workspace Sections */}
        {riskData && (
          <div className="risk-content-stack">
            {/* Overview Metric Cards */}
            <RiskOverview riskData={riskData} />

            {/* Point-in-time Drawdown Track Visualization */}
            <RiskDrawdownSection riskData={riskData} />

            {/* Multi-quantile Tail Risk & Return Dispersion */}
            <RiskReturnDistributionSection riskData={riskData} />

            {/* Methodology & Regulatory Disclosures */}
            <RiskMethodologySection />
          </div>
        )}
      </main>
    </div>
  );
}
