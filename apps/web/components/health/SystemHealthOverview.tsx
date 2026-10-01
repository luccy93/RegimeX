import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { SystemHealthSummaryResponseDTO } from "@/lib/api/types";

export interface SystemHealthOverviewProps {
  summary: SystemHealthSummaryResponseDTO | null;
}

export function SystemHealthOverview({ summary }: SystemHealthOverviewProps) {
  if (!summary) return null;

  const getBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case "HEALTHY":
      case "AVAILABLE":
        return "success";
      case "DEGRADED":
      case "STALE":
        return "warning";
      case "UNHEALTHY":
      case "UNAVAILABLE":
        return "danger";
      default:
        return "default";
    }
  };

  const domainCards = [
    {
      title: "System Status",
      status: summary.status,
      icon: "🖥️",
      description: "Overall platform operational integrity",
    },
    {
      title: "Market Data",
      status: summary.components.market_data?.status || "UNKNOWN",
      icon: "📈",
      description: "Freshness, completeness & schema validation",
    },
    {
      title: "Regime Models",
      status: summary.components.models?.status || "UNKNOWN",
      icon: "🧭",
      description: "Prediction invariants, confidence & drift",
    },
    {
      title: "Upstream Providers",
      status: summary.components.providers?.status || "UNKNOWN",
      icon: "📡",
      description: "Vendor API availability and latency",
    },
    {
      title: "Data Pipeline",
      status: summary.components.pipeline?.status || "UNKNOWN",
      icon: "⚙️",
      description: "Ingestion, normalization & feature pipeline",
    },
  ];

  return (
    <section className="health-overview-section" aria-label="Operational Domains Summary">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {domainCards.map((card) => (
          <Card key={card.title} className="health-metric-card border border-neutral-800">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <span className="text-xl" aria-hidden="true">{card.icon}</span>
                <Badge variant={getBadgeVariant(card.status)} size="sm">
                  {card.status}
                </Badge>
              </div>
              <h3 className="text-sm font-semibold text-neutral-300 mt-2">{card.title}</h3>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-neutral-400">{card.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

