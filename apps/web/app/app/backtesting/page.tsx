import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export const metadata = {
  title: "Backtesting",
  description: "RegimeX Systematic Backtesting Platform",
};

export default function BacktestingPage() {
  return (
    <div className="module-placeholder-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Backtesting", isCurrent: true },
        ]}
      />

      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">Systematic Backtesting</h1>
          <Badge variant="outline" size="md">
            Scheduled for V20
          </Badge>
        </div>
        <p className="page-subtitle">
          Event-driven strategy simulation across historical regimes with execution modeling.
        </p>
      </header>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Module Foundation Established</CardTitle>
          <CardDescription>
            Deterministic simulation engine, slippage models, transaction fee modeling, and performance metrics verified in Volume 11.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="placeholder-info-box">
            <p className="placeholder-info-text">
              Interactive strategy builder, regime filtering parameters, equity curve visualizations,
              and performance tear-sheets are scheduled for Volume 20 (Backtesting Workspace).
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
