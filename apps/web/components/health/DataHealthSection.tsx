import React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { DataHealthResponseDTO } from "@/lib/api/types";

export interface DataHealthSectionProps {
  dataFeeds: DataHealthResponseDTO[];
}

export function DataHealthSection({ dataFeeds }: DataHealthSectionProps) {
  const getBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case "HEALTHY":
        return "success";
      case "DEGRADED":
      case "STALE":
        return "warning";
      case "UNHEALTHY":
        return "danger";
      default:
        return "default";
    }
  };

  const formatAge = (seconds: number | null) => {
    if (seconds === null || seconds === undefined) return "N/A";
    if (seconds < 60) return `${Math.round(seconds)}s ago`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h ago`;
    return `${(seconds / 86400).toFixed(1)}d ago`;
  };

  return (
    <section className="data-health-section mt-6" aria-label="Market Data Health Feeds">
      <div className="section-header flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-neutral-100">Market Data Health</h2>
          <p className="text-xs text-neutral-400">
            Observation freshness, completeness against calendar schedules, and V06 validation integrity.
          </p>
        </div>
      </div>

      {dataFeeds.length === 0 ? (
        <div className="p-6 text-center text-sm text-neutral-400 bg-neutral-900 border border-neutral-800 rounded-lg">
          No data health feeds currently registered.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dataFeeds.map((feed) => (
            <Card key={feed.symbol} className="border border-neutral-800 bg-neutral-950">
              <CardHeader className="pb-3 border-b border-neutral-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-neutral-100">{feed.symbol}</span>
                    <span className="text-xs text-neutral-400">({feed.freshness.calendar_id.toUpperCase()})</span>
                  </div>
                  <Badge variant={getBadgeVariant(feed.status)} size="sm">
                    {feed.status}
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="pt-3 space-y-3">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="bg-neutral-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-1">Freshness</span>
                    <span className="font-medium text-neutral-200">
                      {formatAge(feed.freshness.freshness_seconds)}
                    </span>
                    <span className="block text-[10px] text-neutral-500 mt-0.5">
                      Session: {feed.freshness.market_open ? "OPEN" : "CLOSED"}
                    </span>
                  </div>

                  <div className="bg-neutral-900 p-2.5 rounded border border-neutral-800">
                    <span className="text-neutral-400 block mb-1">Completeness</span>
                    <span className="font-medium text-neutral-200">
                      {(feed.completeness.completeness_ratio * 100).toFixed(1)}%
                    </span>
                    <span className="block text-[10px] text-neutral-500 mt-0.5">
                      Missing: {feed.completeness.missing_rows} | Dup: {feed.completeness.duplicate_rows}
                    </span>
                  </div>
                </div>

                <div className="bg-neutral-900 p-2.5 rounded border border-neutral-800 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-neutral-400">Validation Status</span>
                    <Badge variant={getBadgeVariant(feed.validity.status)} size="sm">
                      {feed.validity.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] text-neutral-400 mt-1">
                    <span>Critical: <strong className="text-neutral-200">{feed.validity.critical_issues_count}</strong></span>
                    <span>Warnings: <strong className="text-neutral-200">{feed.validity.warning_issues_count}</strong></span>
                    {feed.validity.failed_rule_ids.length > 0 && (
                      <span>Failed Rules: <strong className="text-rose-400">{feed.validity.failed_rule_ids.join(", ")}</strong></span>
                    )}
                  </div>
                </div>

                {feed.freshness.reason && (
                  <p className="text-[11px] text-neutral-400 bg-neutral-900/60 p-2 rounded border border-neutral-800/80">
                    ℹ {feed.freshness.reason}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
