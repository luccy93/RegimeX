import React, { Suspense } from "react";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { ResearchWorkspace } from "@/components/research/ResearchWorkspace";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";

export const metadata = {
  title: "AI Research Assistant",
  description:
    "Grounded quantitative market research assistant operating over platform regimes, transition matrices, portfolio risk, and historical backtests.",
};

function ResearchWorkspaceSkeleton() {
  return (
    <div
      className="research-workspace-skeleton"
      aria-busy="true"
      aria-label="Loading AI Research Assistant"
    >
      <div className="research-header-skeleton">
        <div style={{ marginBottom: "1rem" }}>
          <Skeleton shape="text" style={{ width: "20rem", height: "2.25rem", marginBottom: "0.5rem" }} />
          <Skeleton shape="text" style={{ width: "32rem", height: "1rem" }} />
        </div>
        <Skeleton shape="rect" style={{ height: "3rem", width: "100%", marginBottom: "1.5rem" }} />
      </div>

      <div style={{ flex: 1, minHeight: "350px", marginBottom: "1.5rem" }}>
        <Card variant="bordered">
          <CardHeader>
            <Skeleton shape="text" style={{ width: "16rem", height: "1.5rem" }} />
          </CardHeader>
          <CardContent>
            <Skeleton shape="rect" style={{ height: "18rem", width: "100%" }} />
          </CardContent>
        </Card>
      </div>

      <div className="research-composer-skeleton">
        <Skeleton shape="rect" style={{ height: "4.5rem", width: "100%" }} />
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <div className="research-page-container">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "AI Research Assistant", isCurrent: true },
        ]}
      />

      <Suspense fallback={<ResearchWorkspaceSkeleton />}>
        <ResearchWorkspace />
      </Suspense>
    </div>
  );
}
