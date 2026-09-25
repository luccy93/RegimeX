import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export const metadata = {
  title: "Risk Analytics",
  description: "RegimeX Portfolio Risk Intelligence",
};

export default function RiskPage() {
  return (
    <div className="module-placeholder-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Risk", isCurrent: true },
        ]}
      />

      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">Portfolio Risk Analytics</h1>
          <Badge variant="outline" size="md">
            Scheduled for V20
          </Badge>
        </div>
        <p className="page-subtitle">
          Cross-regime Value at Risk (VaR), Conditional VaR (CVaR), and drawdown analytics.
        </p>
      </header>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Module Foundation Established</CardTitle>
          <CardDescription>
            Domain engines for historical VaR, parametric VaR, CVaR, and maximum drawdown profiles verified in Volume 10.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="placeholder-info-box">
            <p className="placeholder-info-text">
              Multi-asset portfolio allocation, cross-regime risk decomposition, and scenario stress testing
              visualizations are scheduled for Volume 20 (Risk Intelligence Workspace).
            </p>
          </div>
          <div className="placeholder-actions">
            <Link href="/app">
              <Button variant="secondary">Back to Overview</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
