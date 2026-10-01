"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { AppHeader } from "@/components/layout/AppHeader";
import {
  HealthHeader,
  SystemHealthOverview,
  DataHealthSection,
  ProviderHealthSection,
  PipelineHealthSection,
  ModelHealthSection,
} from "@/components/health";
import { Spinner } from "@/components/ui/Spinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { healthApi } from "@/lib/api/health";
import type {
  DataHealthResponseDTO,
  ModelHealthResponseDTO,
  PipelineHealthDTO,
  ProviderHealthDTO,
  SystemHealthSummaryResponseDTO,
} from "@/lib/api/types";

export default function HealthPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SystemHealthSummaryResponseDTO | null>(null);
  const [dataFeeds, setDataFeeds] = useState<DataHealthResponseDTO[]>([]);
  const [models, setModels] = useState<ModelHealthResponseDTO[]>([]);
  const [providers, setProviders] = useState<ProviderHealthDTO[]>([]);
  const [pipeline, setPipeline] = useState<PipelineHealthDTO | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchHealthData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumRes, dataRes, modRes, provRes, pipeRes] = await Promise.all([
        healthApi.getSummary(),
        healthApi.listDataHealth(),
        healthApi.listModelHealth(),
        healthApi.listProviders(),
        healthApi.getPipeline(),
      ]);

      setSummary(sumRes);
      setDataFeeds(dataRes.items || []);
      setModels(modRes.items || []);
      setProviders(provRes.items || []);
      setPipeline(pipeRes);
      setLastUpdated(new Date().toISOString());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load operational health data.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealthData();
  }, [fetchHealthData]);

  const isEmpty =
    !isLoading &&
    !error &&
    dataFeeds.length === 0 &&
    models.length === 0 &&
    providers.length === 0;

  return (
    <div className="app-shell flex h-screen bg-neutral-950 text-neutral-100">
      <AppSidebar currentPath="/app/health" />

      <div className="app-shell-main flex-1 flex flex-col overflow-hidden">
        <AppHeader />

        <main
          className="app-shell-content flex-1 overflow-y-auto p-6 lg:p-8 space-y-6"
          id="main-content"
          role="main"
          aria-label="Operational Health & Telemetry Dashboard"
        >
          <HealthHeader
            systemStatus={summary?.status || (isLoading ? "EVALUATING" : "UNKNOWN")}
            lastUpdated={lastUpdated}
            onRefresh={fetchHealthData}
            isLoading={isLoading}
          />

          {isLoading && !summary && (
            <div className="flex flex-col items-center justify-center py-24 space-y-4">
              <Spinner size="lg" aria-label="Evaluating system health metrics" />
              <p className="text-sm text-neutral-400">Evaluating operational health telemetry...</p>
            </div>
          )}

          {error && !summary && (
            <ErrorState
              title="Health Telemetry Unavailable"
              message={error}
              onRetry={fetchHealthData}
            />
          )}

          {isEmpty && (
            <EmptyState
              title="No Monitored Feeds"
              description="No data feeds or models are currently reporting operational health."
              action={
                <Button onClick={fetchHealthData} variant="primary" size="sm">
                  Refresh Telemetry
                </Button>
              }
            />
          )}

          {!isLoading && summary && (
            <>
              <SystemHealthOverview summary={summary} />
              <DataHealthSection dataFeeds={dataFeeds} />
              <ModelHealthSection models={models} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ProviderHealthSection providers={providers} />
                <PipelineHealthSection pipeline={pipeline} />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
