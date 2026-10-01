import React from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { PipelineHealthDTO } from "@/lib/api/types";

export interface PipelineHealthSectionProps {
  pipeline: PipelineHealthDTO | null;
}

export function PipelineHealthSection({ pipeline }: PipelineHealthSectionProps) {
  if (!pipeline) return null;

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

  const stagesList = Object.entries(pipeline.stages);

  return (
    <section className="pipeline-health-section mt-6" aria-label="Data Pipeline Stages">
      <div className="section-header mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-neutral-100">Data Pipeline Stages</h2>
          <p className="text-xs text-neutral-400">
            End-to-end processing pipeline operational status from provider ingestion to feature extraction.
          </p>
        </div>
        <Badge variant={getBadgeVariant(pipeline.overall_status)} size="md">
          Pipeline: {pipeline.overall_status}
        </Badge>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {stagesList.map(([stageKey, stageInfo]) => (
          <Card key={stageKey} className="border border-neutral-800 bg-neutral-950 p-3 text-center">
            <span className="text-xs font-mono font-semibold text-neutral-300 block mb-2 uppercase">
              {stageInfo.stage}
            </span>
            <Badge variant={getBadgeVariant(stageInfo.status)} size="sm">
              {stageInfo.status}
            </Badge>
          </Card>
        ))}
      </div>
    </section>
  );
}
