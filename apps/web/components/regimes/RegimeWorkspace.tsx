"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type {
  MarketItemResponse,
  MarketRegimeResponse,
  MarketTransitionResponse,
} from "@/lib/api/types";
import { listMarkets } from "@/lib/api/markets";
import { getRegimeAnalytics, fetchRegimeTransitions } from "@/lib/api/regimes";
import { RegimeXApiError } from "@/lib/api/errors";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

import { RegimeWorkspaceHeader } from "./RegimeWorkspaceHeader";
import { CurrentRegimeSummary } from "./CurrentRegimeSummary";
import { RegimeDistributionSection } from "./RegimeDistributionSection";
import { RegimeFrequencyPersistence } from "./RegimeFrequencyPersistence";
import { RegimeDurationSection } from "./RegimeDurationSection";
import { RegimeProfileComparison } from "./RegimeProfileComparison";
import { TransitionAnalyticsSection } from "./TransitionAnalyticsSection";
import { MethodologyProvenanceSection } from "./MethodologyProvenanceSection";

export function RegimeWorkspace() {
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

  // Regime Context & Profile State
  const [regimeData, setRegimeData] = useState<MarketRegimeResponse | null>(null);
  const [isLoadingRegime, setIsLoadingRegime] = useState<boolean>(false);
  const [regimeError, setRegimeError] = useState<string | null>(null);

  // Transition Analytics State (Isolated from regimeData)
  const [transitionData, setTransitionData] = useState<MarketTransitionResponse | null>(null);
  const [isLoadingTransitions, setIsLoadingTransitions] = useState<boolean>(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Active AbortControllers to cancel in-flight requests on switch
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
          router.replace(`/app/regimes?symbol=${encodeURIComponent(defaultSym)}`, {
            scroll: false,
          });
        } else {
          // Keep requested symbol even if not in standard list
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

  // 2. Fetch Regime Data and Transitions for Active Symbol
  const fetchRegimeWorkspaceData = useCallback(
    async (symbol: string) => {
      if (!symbol) return;

      // Abort previous in-flight requests
      if (activeFetchController.current) {
        activeFetchController.current.abort();
      }
      const controller = new AbortController();
      activeFetchController.current = controller;

      // Reset errors & start loading
      setIsLoadingRegime(true);
      setRegimeError(null);
      setIsLoadingTransitions(true);
      setTransitionError(null);

      // Execute Regime fetch
      const regimePromise = getRegimeAnalytics(symbol, {}, { signal: controller.signal })
        .then((data) => {
          if (!controller.signal.aborted) {
            setRegimeData(data);
          }
        })
        .catch((err) => {
          if (!controller.signal.aborted) {
            const msg =
              err instanceof RegimeXApiError
                ? err.message
                : `Failed to load regime context for ${symbol}.`;
            setRegimeError(msg);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsLoadingRegime(false);
          }
        });

      // Execute Transition fetch independently (Section 32: Error Isolation)
      const transitionPromise = fetchRegimeTransitions(symbol, {}, { signal: controller.signal })
        .then((data) => {
          if (!controller.signal.aborted) {
            setTransitionData(data);
          }
        })
        .catch((err) => {
          if (!controller.signal.aborted) {
            const msg =
              err instanceof RegimeXApiError
                ? err.message
                : `Empirical transition analytics unavailable for ${symbol}.`;
            setTransitionError(msg);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsLoadingTransitions(false);
          }
        });

      await Promise.allSettled([regimePromise, transitionPromise]);
    },
    []
  );

  useEffect(() => {
    if (selectedSymbol) {
      fetchRegimeWorkspaceData(selectedSymbol);
    }
  }, [selectedSymbol, fetchRegimeWorkspaceData]);

  // Handle market change from selector
  const handleSelectMarket = (symbol: string) => {
    const clean = symbol.trim().toUpperCase();
    if (clean === selectedSymbol.toUpperCase()) return;

    setSelectedSymbol(clean);
    router.push(`/app/regimes?symbol=${encodeURIComponent(clean)}`, {
      scroll: false,
    });
  };

  // Global catalog failure state
  if (marketsError && markets.length === 0 && !isLoadingMarkets) {
    return (
      <div className="regime-workspace-root">
        <ErrorState
          title="Market Catalog Unavailable"
          message={marketsError}
          onRetry={fetchMarketCatalog}
          retryLabel="Retry Loading Catalog"
        />
      </div>
    );
  }

  // No market selected empty state
  if (!selectedSymbol && !isLoadingMarkets && markets.length === 0) {
    return (
      <div className="regime-workspace-root">
        <EmptyState
          title="No Discoverable Markets"
          description="The regime engine currently has no active instruments registered in the catalog."
        />
      </div>
    );
  }

  return (
    <div className="regime-workspace-root">
      {/* 1. Page Header & Market Selector */}
      <RegimeWorkspaceHeader
        markets={markets}
        selectedSymbol={selectedSymbol}
        onSelectMarket={handleSelectMarket}
        isLoadingMarkets={isLoadingMarkets}
        marketsError={marketsError}
        onRetryMarkets={fetchMarketCatalog}
        regimeData={regimeData}
        isLoadingRegime={isLoadingRegime}
      />

      {/* Main Analytical Layout */}
      {regimeError && !regimeData && !isLoadingRegime ? (
        <div className="regime-error-section">
          <ErrorState
            title={`Regime Classification Failed for ${selectedSymbol}`}
            message={regimeError}
            onRetry={() => fetchRegimeWorkspaceData(selectedSymbol)}
            retryLabel="Retry Analysis"
          />
        </div>
      ) : (
        <div className="regime-workspace-content">
          {/* 2. Current Regime Summary */}
          <section aria-labelledby="current-regime-heading">
            <h2 id="current-regime-heading" className="sr-only">
              Current Market Regime Summary
            </h2>
            <CurrentRegimeSummary
              regimeData={regimeData}
              isLoading={isLoadingRegime}
            />
          </section>

          {/* 3. Regime Distribution */}
          <section aria-labelledby="regime-distribution-heading">
            <h2 id="regime-distribution-heading" className="sr-only">
              Regime Distribution Analysis
            </h2>
            <RegimeDistributionSection
              regimeData={regimeData}
              isLoading={isLoadingRegime}
            />
          </section>

          {/* 4. Regime Frequency & Persistence */}
          <section aria-labelledby="regime-frequency-heading">
            <h2 id="regime-frequency-heading" className="sr-only">
              Regime Frequency &amp; Persistence Analytics
            </h2>
            <RegimeFrequencyPersistence
              regimeData={regimeData}
              transitionData={transitionData}
              isLoading={isLoadingRegime}
            />
          </section>

          {/* 5. Duration Analysis */}
          <section aria-labelledby="regime-duration-heading">
            <h2 id="regime-duration-heading" className="sr-only">
              Regime Duration Analysis
            </h2>
            <RegimeDurationSection
              regimeData={regimeData}
              isLoading={isLoadingRegime}
            />
          </section>

          {/* 6. Regime Profile Comparison & Feature Statistics */}
          <section aria-labelledby="regime-profiles-heading">
            <h2 id="regime-profiles-heading" className="sr-only">
              Regime Profile Comparison &amp; Feature Statistics
            </h2>
            <RegimeProfileComparison
              regimeData={regimeData}
              isLoading={isLoadingRegime}
            />
          </section>

          {/* 7. Regime Change & Transition Analytics (Isolated Error & Loading) */}
          <section aria-labelledby="regime-transitions-heading">
            <h2 id="regime-transitions-heading" className="sr-only">
              Transition Matrix &amp; Destination Analytics
            </h2>
            <TransitionAnalyticsSection
              transitionData={transitionData}
              regimeData={regimeData}
              isLoading={isLoadingTransitions}
              error={transitionError}
              onRetry={() => fetchRegimeWorkspaceData(selectedSymbol)}
            />
          </section>

          {/* 8. Methodology & Provenance */}
          <section aria-labelledby="regime-provenance-heading">
            <h2 id="regime-provenance-heading" className="sr-only">
              Analytical Methodology &amp; Provenance
            </h2>
            <MethodologyProvenanceSection
              regimeData={regimeData}
              isLoading={isLoadingRegime}
            />
          </section>
        </div>
      )}
    </div>
  );
}
