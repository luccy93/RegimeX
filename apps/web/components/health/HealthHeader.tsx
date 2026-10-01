import React from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface HealthHeaderProps {
  systemStatus: string;
  lastUpdated: string | null;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export function HealthHeader({
  systemStatus,
  lastUpdated,
  onRefresh,
  isLoading = false,
}: HealthHeaderProps) {
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

  return (
    <header className="page-header" aria-label="System Health Overview Header">
      <div className="page-header-row">
        <div className="page-header-title-group">
          <div className="flex items-center gap-3">
            <h1 className="page-title text-2xl font-bold">System Health & Telemetry</h1>
            <Badge
              variant={getBadgeVariant(systemStatus)}
              size="md"
              aria-label={`System status: ${systemStatus}`}
            >
              ● {systemStatus}
            </Badge>
          </div>
          <p className="page-description text-sm text-neutral-400 mt-1">
            Operational telemetry and health monitoring for market data feeds, upstream providers,
            pipeline stages, and regime detection models. Operational diagnostics only — not investment advice.
          </p>
        </div>

        <div className="page-header-actions flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-neutral-400" aria-label={`Last updated: ${lastUpdated}`}>
              Last evaluated: {new Date(lastUpdated).toLocaleTimeString()}
            </span>
          )}
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              aria-label="Refresh operational health data"
            >
              {isLoading ? "Evaluating..." : "Refresh"}
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
