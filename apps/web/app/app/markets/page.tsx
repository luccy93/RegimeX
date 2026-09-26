import React, { Suspense } from "react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { MarketDashboard } from "@/components/markets/MarketDashboard";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";

export const metadata = {
  title: "Market Intelligence",
  description: "Explore market regimes, historical data, and volatility states with RegimeX.",
};

function MarketDashboardSkeleton() {
  return (
    <div className="market-dashboard-skeleton" aria-busy="true" aria-label="Loading market intelligence dashboard">
      {/* Header skeleton */}
      <div className="market-overview-header">
        <div className="market-header-top-row">
          <div>
            <Skeleton shape="text" style={{ width: "16rem", height: "2rem", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "24rem", height: "1rem" }} />
          </div>
          <Skeleton shape="rect" style={{ width: "14rem", height: "2.5rem" }} />
        </div>
        <Skeleton shape="rect" style={{ height: "4.5rem", marginTop: "1rem" }} />
      </div>

      {/* Snapshot metrics skeleton */}
      <div className="market-snapshot-grid" style={{ marginTop: "1.5rem" }}>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="metric-card">
            <Skeleton shape="text" style={{ width: "50%", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "70%", height: "1.75rem", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "40%" }} />
          </div>
        ))}
      </div>

      {/* Chart slot skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="elevated">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "12rem" }} />
            <Skeleton shape="text" style={{ width: "20rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "22rem" }} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function MarketsPage() {
  return (
    <div className="market-intelligence-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Markets", isCurrent: true },
        ]}
      />

      <Suspense fallback={<MarketDashboardSkeleton />}>
        <MarketDashboard />
      </Suspense>
    </div>
  );
}
