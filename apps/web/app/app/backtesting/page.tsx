import React, { Suspense } from "react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { BacktestWorkspace } from "@/components/backtesting/BacktestWorkspace";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";

export const metadata = {
  title: "Systematic Backtesting",
  description: "Deterministic event-driven execution simulation with realistic transaction friction and immutable reporting.",
};

function BacktestWorkspaceSkeleton() {
  return (
    <div className="backtest-workspace-skeleton" aria-busy="true" aria-label="Loading systematic backtesting workspace">
      {/* Header skeleton */}
      <div className="backtest-workspace-header">
        <div className="backtest-header-top-row">
          <div>
            <Skeleton shape="text" style={{ width: "18rem", height: "2rem", marginBottom: "0.5rem" }} />
            <Skeleton shape="text" style={{ width: "26rem", height: "1rem" }} />
          </div>
          <Skeleton shape="rect" style={{ width: "20rem", height: "2.5rem" }} />
        </div>
        <Skeleton shape="rect" style={{ height: "3.5rem", marginTop: "1rem" }} />
      </div>

      {/* Performance metric cards skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <div className="backtest-metrics-grid">
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

      {/* Equity chart skeleton */}
      <div style={{ marginTop: "1.5rem" }}>
        <Card variant="bordered">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "20rem", height: "1.5rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "20rem" }} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function BacktestingPage() {
  return (
    <div className="backtest-page-container">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Systematic Backtesting", isCurrent: true },
        ]}
      />

      <Suspense fallback={<BacktestWorkspaceSkeleton />}>
        <BacktestWorkspace />
      </Suspense>
    </div>
  );
}
