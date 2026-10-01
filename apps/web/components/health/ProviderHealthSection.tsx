import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ProviderHealthDTO } from "@/lib/api/types";

export interface ProviderHealthSectionProps {
  providers: ProviderHealthDTO[];
}

export function ProviderHealthSection({ providers }: ProviderHealthSectionProps) {
  const getBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case "AVAILABLE":
        return "success";
      case "DEGRADED":
        return "warning";
      case "UNAVAILABLE":
        return "danger";
      default:
        return "default";
    }
  };

  return (
    <section className="provider-health-section mt-6" aria-label="Upstream Market Data Providers">
      <div className="section-header mb-4">
        <h2 className="text-lg font-bold text-neutral-100">Upstream Data Providers</h2>
        <p className="text-xs text-neutral-400">
          Vendor API availability, failure streaks, and latency monitoring.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {providers.map((prov) => (
          <Card key={prov.provider_id} className="border border-neutral-800 bg-neutral-950">
            <CardHeader className="pb-2 border-b border-neutral-800">
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm font-semibold text-neutral-200">
                  {prov.provider_id}
                </span>
                <Badge variant={getBadgeVariant(prov.status)} size="sm">
                  {prov.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-3 space-y-2 text-xs">
              <div className="flex justify-between text-neutral-400">
                <span>Requests Total:</span>
                <span className="font-semibold text-neutral-200">{prov.request_count}</span>
              </div>
              <div className="flex justify-between text-neutral-400">
                <span>Success / Failure:</span>
                <span className="font-semibold text-neutral-200">
                  {prov.success_count} / {prov.failure_count}
                </span>
              </div>
              <div className="flex justify-between text-neutral-400">
                <span>Failure Rate:</span>
                <span className="font-semibold text-neutral-200">
                  {(prov.failure_rate * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between text-neutral-400">
                <span>Avg Latency:</span>
                <span className="font-semibold text-neutral-200">
                  {prov.avg_latency_ms.toFixed(0)} ms
                </span>
              </div>
              {prov.consecutive_failures > 0 && (
                <div className="flex justify-between text-rose-400">
                  <span>Consecutive Failures:</span>
                  <span className="font-semibold">{prov.consecutive_failures}</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

