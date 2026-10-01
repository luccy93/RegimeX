import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ModelHealthResponseDTO } from "@/lib/api/types";

export interface ModelHealthSectionProps {
  models: ModelHealthResponseDTO[];
}

export function ModelHealthSection({ models }: ModelHealthSectionProps) {
  const getBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case "HEALTHY":
        return "success";
      case "DEGRADED":
        return "warning";
      case "UNHEALTHY":
        return "danger";
      default:
        return "default";
    }
  };

  return (
    <section className="model-health-section mt-6" aria-label="Regime Models Health">
      <div className="section-header mb-4">
        <h2 className="text-lg font-bold text-neutral-100">Regime Models Operational Health</h2>
        <p className="text-xs text-neutral-400">
          Inference invariants, stability, confidence distributions, and prediction distribution drift.
          Operational monitoring only — not investment advice.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {models.map((model) => (
          <Card key={model.model_id} className="border border-neutral-800 bg-neutral-950">
            <CardHeader className="pb-3 border-b border-neutral-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base text-neutral-100 capitalize">
                    {model.model_id}
                  </span>
                  <span className="text-xs text-neutral-400">
                    ({model.validity.valid_predictions}/{model.validity.total_predictions} valid)
                  </span>
                </div>
                <Badge variant={getBadgeVariant(model.status)} size="sm">
                  {model.status}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="pt-3 space-y-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-neutral-900 p-2 rounded border border-neutral-800">
                  <span className="text-neutral-400 block mb-1">Switching Freq</span>
                  <span className="font-semibold text-neutral-200">
                    {(model.stability.regime_switching_frequency * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="bg-neutral-900 p-2 rounded border border-neutral-800">
                  <span className="text-neutral-400 block mb-1">Mean Conf</span>
                  <span className="font-semibold text-neutral-200">
                    {model.confidence.mean_confidence !== null
                      ? `${(model.confidence.mean_confidence * 100).toFixed(1)}%`
                      : "N/A"}
                  </span>
                </div>

                <div className="bg-neutral-900 p-2 rounded border border-neutral-800">
                  <span className="text-neutral-400 block mb-1">Failure Rate</span>
                  <span className="font-semibold text-neutral-200">
                    {(model.execution.failure_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Regime Distribution */}
              {Object.keys(model.regime_distribution.regime_percentages).length > 0 && (
                <div className="bg-neutral-900 p-2.5 rounded border border-neutral-800 text-xs">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-neutral-400 font-medium">Empirical Regime Distribution</span>
                    <span className="text-[10px] text-neutral-500">
                      Entropy: {model.regime_distribution.entropy.toFixed(2)} nats
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {Object.entries(model.regime_distribution.regime_percentages).map(
                      ([regId, pct]) => (
                        <div key={regId} className="flex items-center gap-2 text-[11px]">
                          <span className="w-16 text-neutral-400">Regime {regId}:</span>
                          <div className="flex-1 bg-neutral-800 h-2 rounded overflow-hidden">
                            <div
                              className="bg-indigo-500 h-full rounded"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="w-10 text-right text-neutral-300 font-mono">
                            {pct.toFixed(0)}%
                          </span>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* Drift Monitoring */}
              {model.drift && (
                <div className="bg-neutral-900 p-2.5 rounded border border-neutral-800 text-xs flex items-center justify-between">
                  <div>
                    <span className="text-neutral-400 block">Distribution Drift ({model.drift.method})</span>
                    <span className="text-[11px] text-neutral-500">
                      Score: {model.drift.drift_score.toFixed(3)} | Threshold: {model.drift.threshold.toFixed(2)}
                    </span>
                  </div>
                  <Badge variant={model.drift.is_drift_detected ? "warning" : "success"} size="sm">
                    {model.drift.is_drift_detected ? "Drift Detected" : "Stable"}
                  </Badge>
                </div>
              )}

              {model.summary && (
                <p className="text-[11px] text-neutral-400 bg-neutral-900/50 p-2 rounded border border-neutral-800/60">
                  {model.summary}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
