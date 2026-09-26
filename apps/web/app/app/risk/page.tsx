import React, { Suspense } from "react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { RiskWorkspace } from "@/components/risk/RiskWorkspace";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";

export const metadata = {
  title: "Risk Analytics",
  description: "Comprehensive historical risk profiling, drawdown tracks, VaR quantiles, and Expected Shortfall.",
};

function RiskWorkspaceSkeleton() {
  return (
    <div className="risk-workspace-skeleton" aria-busy="true" aria-label="Loading portfolio risk workspace">
      {/* Header skeleton */}
      <div className="risk-workspace-header">
        <div className="risk-header-top-row">
          <div>
            <Skeleton shape="text" style={{ width: "16rem", height: "2rem", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "24rem", height: "1rem" }} />
          </div>
          <Skeleton shape="rect" style={{ width: "14rem", height: "2.5rem" }} />
        </div>
        <Skeleton shape="rect" style={{ height: "3.5rem", marginTop: "1rem" }} />
      </div>

      {/* Overview metric cards skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <div className="risk-metrics-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} variant="elevated">
              <CardHeader>
                <Skeleton shape="text" style={{ width: "50%", height: "1rem" }} />
              </CardHeader>
              <CardContent>
                <Skeleton shape="text" style={{ width: "70%", height: "2rem", marginBottom: "0.5rem" }} />
                <Skeleton shape="text" style={{ width: "90%", height: "0.875rem" }} />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Drawdown chart skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="bordered">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "18rem", height: "1.5rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "14rem" }} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function RiskPage() {
  return (
    <div className="risk-page-container">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Risk Analytics", isCurrent: true },
        ]}
      />

      <Suspense fallback={<RiskWorkspaceSkeleton />}>
        <RiskWorkspace />
      </Suspense>
    </div>
  );
}
