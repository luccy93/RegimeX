"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type {
  MarketItemResponse,
  MarketDataResponse,
  MarketRegimeResponse,
} from "@/lib/api/types";
import { listMarkets, getMarketData, getMarketRegime } from "@/lib/api/markets";
import { RegimeXApiError } from "@/lib/api/errors";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

import { MarketOverviewHeader } from "./MarketOverviewHeader";
import { MarketSnapshot } from "./MarketSnapshot";
import { MarketPriceChart } from "./MarketPriceChart";
import { CurrentRegimeCard } from "./CurrentRegimeCard";
import { RegimeHistory } from "./RegimeHistory";
import { DataHealth } from "./DataHealth";

export function MarketDashboard() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL State: ?symbol=XYZ
  const urlSymbol = searchParams.get("symbol");

  // Markets Catalog State
  const [markets, setMarkets] = useState<MarketItemResponse[]>([]);
  const [isLoadingMarkets, setIsLoadingMarkets] = useState<boolean>(true);
  const [marketsError, setMarketsError] = useState<string | null>(null);

  // Active Symbol State
  const [selectedSymbol, setSelectedSymbol] = useState<string>(urlSymbol?.toUpperCase() || "");

  // Market Data (OHLCV) State
  const [marketData, setMarketData] = useState<MarketDataResponse | null>(null);
  const [isLoadingMarketData, setIsLoadingMarketData] = useState<boolean>(false);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [marketDataRequestId, setMarketDataRequestId] = useState<string | undefined>(undefined);

  // Regime Context State
  const [regimeData, setRegimeData] = useState<MarketRegimeResponse | null>(null);
  const [isLoadingRegime, setIsLoadingRegime] = useState<boolean>(false);
  const [regimeError, setRegimeError] = useState<string | null>(null);
  const [regimeRequestId, setRegimeRequestId] = useState<string | undefined>(undefined);

  // Active AbortControllers to cancel requests and prevent race conditions
  const activeFetchController = useRef<AbortController | null>(null);

  // 1. Fetch Markets Catalog
  const fetchMarketCatalog = useCallback(async () => {
    setIsLoadingMarkets(true);
    setMarketsError(null);

    try {
      const response = await listMarkets({ limit: 100 });
      const items = response.items || [];
      setMarkets(items);

      // Determine initial selected market
      if (items.length > 0) {
        const querySym = urlSymbol?.toUpperCase();
        const found = items.find((m) => m.symbol.toUpperCase() === querySym);

        if (found) {
          setSelectedSymbol(found.symbol);
        } else if (!querySym) {
          // Default deterministically to first available market
          const defaultSym = items[0].symbol;
          setSelectedSymbol(defaultSym);
          router.replace(`/app/markets?symbol=${encodeURIComponent(defaultSym)}`, {
            scroll: false,
          });
        } else {
          // Requested symbol not found in catalog
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

  // 2. Fetch Selected Market Data and Regime Intelligence
  const fetchMarketDetails = useCallback(
    async (symbol: string) => {
      if (!symbol) return;

      // Abort previous in-flight requests
      if (activeFetchController.current) {
        activeFetchController.current.abort();
      }
      const controller = new AbortController();
      activeFetchController.current = controller;

      setIsLoadingMarketData(true);
      setIsLoadingRegime(true);
      setMarketDataError(null);
      setRegimeError(null);

      // Create UTC 1-year analysis window
      const now = new Date();
      const oneYearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
      const startIso = oneYearAgo.toISOString();
      const endIso = now.toISOString();

      // Parallel fetch for market bars and regime detection
      const dataPromise = getMarketData(
        symbol,
        {
          start: startIso,
          end: endIso,
          interval: "1d",
          limit: 1000,
        },
        { signal: controller.signal }
      )
        .then((res) => {
          if (!controller.signal.aborted) {
            setMarketData(res);
            setIsLoadingMarketData(false);
          }
        })
        .catch((err) => {
          if (controller.signal.aborted) return;
          const msg =
            err instanceof RegimeXApiError
              ? err.message
              : `Unable to load historical market data for ${symbol}.`;
          const reqId = err instanceof RegimeXApiError ? err.requestId : undefined;
          setMarketDataError(msg);
          setMarketDataRequestId(reqId);
          setIsLoadingMarketData(false);
        });

      const regimePromise = getMarketRegime(
        symbol,
        {
          start: startIso,
          end: endIso,
          interval: "1d",
          limit: 1000,
        },
        { signal: controller.signal }
      )
        .then((res) => {
          if (!controller.signal.aborted) {
            setRegimeData(res);
            setIsLoadingRegime(false);
          }
        })
        .catch((err) => {
          if (controller.signal.aborted) return;
          const msg =
            err instanceof RegimeXApiError
              ? err.message
              : `Unable to calculate regime context for ${symbol}.`;
          const reqId = err instanceof RegimeXApiError ? err.requestId : undefined;
          setRegimeError(msg);
          setRegimeRequestId(reqId);
          setIsLoadingRegime(false);
        });

      await Promise.allSettled([dataPromise, regimePromise]);
    },
    []
  );

  useEffect(() => {
    if (selectedSymbol) {
      fetchMarketDetails(selectedSymbol);
    }
    return () => {
      if (activeFetchController.current) {
        activeFetchController.current.abort();
      }
    };
  }, [selectedSymbol, fetchMarketDetails]);

  // Handle market selection change
  const handleSelectMarket = (symbol: string) => {
    const clean = symbol.trim().toUpperCase();
    setSelectedSymbol(clean);
    router.replace(`/app/markets?symbol=${encodeURIComponent(clean)}`, {
      scroll: false,
    });
  };

  // Find metadata for current market
  const activeMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  // Global catalog error state
  if (marketsError && markets.length === 0) {
    return (
      <div className="market-dashboard-error-boundary">
        <ErrorState
          title="Market Service Unavailable"
          message={marketsError}
          onRetry={fetchMarketCatalog}
          retryLabel="Retry Connection"
        />
      </div>
    );
  }

  // Global empty catalog state
  if (!isLoadingMarkets && markets.length === 0) {
    return (
      <div className="market-dashboard-empty-boundary">
        <EmptyState
          title="No Markets Available"
          description="The market discovery service returned an empty catalog. Verify provider feeds or database connectivity."
          action={
            <Button variant="secondary" onClick={fetchMarketCatalog}>
              Refresh Catalog
            </Button>
          }
        />
      </div>
    );
  }

  // Selected symbol not in catalog warning
  const isUnknownSymbol =
    !isLoadingMarkets &&
    markets.length > 0 &&
    selectedSymbol &&
    !activeMarket;

  return (
    <div className="market-dashboard-root animate-fade-in">
      {/* 1. Page Header & Market Selector */}
      <MarketOverviewHeader
        markets={markets}
        selectedSymbol={selectedSymbol}
        selectedMarket={activeMarket}
        regimeData={regimeData}
        onSelectMarket={handleSelectMarket}
        isLoadingMarkets={isLoadingMarkets}
        isLoadingData={isLoadingMarketData || isLoadingRegime}
        marketError={marketsError}
        onRetryMarkets={fetchMarketCatalog}
      />

      {/* Symbol not in catalog warning notice */}
      {isUnknownSymbol && (
        <div className="market-unknown-warning" role="alert">
          <span className="market-unknown-icon" aria-hidden="true">⚠️</span>
          <span>
            Symbol <strong>{selectedSymbol}</strong> is not listed in the discoverable catalog.
            Attempting direct time-series retrieval…
          </span>
        </div>
      )}

      {/* 2. Snapshot Metrics Grid (Price, Return, Volatility, Regime, Confidence) */}
      <MarketSnapshot
        marketData={marketData}
        regimeData={regimeData}
        currency={activeMarket?.currency || "USD"}
        isLoading={isLoadingMarketData || isLoadingRegime}
      />

      {/* 3. Primary Market Price Chart */}
      <section className="market-dashboard-section" aria-label="Market Price Chart">
        <MarketPriceChart
          symbol={selectedSymbol}
          bars={marketData?.items ?? []}
          currency={activeMarket?.currency || "USD"}
          interval={marketData?.interval || "1d"}
          isLoading={isLoadingMarketData}
          error={marketDataError}
          requestId={marketDataRequestId}
          onRetry={() => fetchMarketDetails(selectedSymbol)}
        />
      </section>

      {/* 4. Regime Context & Historical Breakdown */}
      <section
        className="market-dashboard-regime-grid"
        aria-label="Regime Intelligence Context"
      >
        <div className="market-grid-col">
          <CurrentRegimeCard
            symbol={selectedSymbol}
            regimeData={regimeData}
            isLoading={isLoadingRegime}
            error={regimeError}
            requestId={regimeRequestId}
            onRetry={() => fetchMarketDetails(selectedSymbol)}
          />
        </div>

        <div className="market-grid-col">
          <RegimeHistory
            symbol={selectedSymbol}
            regimeData={regimeData}
            isLoading={isLoadingRegime}
          />
        </div>
      </section>

      {/* 5. Data Health & Model Provenance */}
      <section className="market-dashboard-section" aria-label="Data Health & Provenance">
        <DataHealth
          symbol={selectedSymbol}
          marketData={marketData}
          regimeData={regimeData}
          isLoading={isLoadingMarketData || isLoadingRegime}
        />
      </section>
    </div>
  );
}
