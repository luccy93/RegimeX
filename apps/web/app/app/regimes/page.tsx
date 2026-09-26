import React, { Suspense } from "react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { RegimeWorkspace } from "@/components/regimes/RegimeWorkspace";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";

export const metadata = {
  title: "Regime Analytics",
  description: "Analyze market regimes, persistence, transitions, and regime-specific behavior.",
};

function RegimeWorkspaceSkeleton() {
  return (
    <div className="regime-workspace-skeleton" aria-busy="true" aria-label="Loading regime analytics workspace">
      {/* Header skeleton */}
      <div className="regime-workspace-header">
        <div className="regime-header-top-row">
          <div>
            <Skeleton shape="text" style={{ width: "16rem", height: "2rem", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "24rem", height: "1rem" }} />
          </div>
          <Skeleton shape="rect" style={{ width: "14rem", height: "2.5rem" }} />
        </div>
        <Skeleton shape="rect" style={{ height: "3.5rem", marginTop: "1rem" }} />
      </div>

      {/* Current regime card skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="elevated">
          <CardHeader>
            <div className="flex-between">
              <Skeleton shape="text" style={{ width: "14rem", height: "1.5rem" }} />
              <Skeleton shape="rect" style={{ width: "6rem", height: "1.75rem" }} />
            </div>
            <Skeleton shape="text" style={{ width: "20rem", marginTop: "0.5rem" }} />
          </CardHeader>
          <CardContent>
            <div className="current-regime-metrics-grid">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="metric-box">
                  <Skeleton shape="text" style={{ width: "60%", marginBottom: "0.5rem" }} />
                  <Skeleton shape="text" style={{ width: "80%", height: "1.5rem" }} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Distribution skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="elevated">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "12rem" }} />
            <Skeleton shape="text" style={{ width: "18rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "2.5rem", marginBottom: "1rem" }} />
            <Skeleton shape="rect" style={{ height: "4.5rem" }} />
          </CardContent>
        </Card>
      </div>

      {/* Tables skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="elevated">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "16rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "12rem" }} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function RegimesPage() {
  return (
    <div className="regime-analytics-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Regimes", isCurrent: true },
        ]}
      />

      <Suspense fallback={<RegimeWorkspaceSkeleton />}>
        <RegimeWorkspace />
      </Suspense>
    </div>
  );
}
