import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export const metadata = {
  title: "Regimes",
  description: "RegimeX Market Regime Detection & Transitions",
};

export default function RegimesPage() {
  return (
    <div className="module-placeholder-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Regimes", isCurrent: true },
        ]}
      />

      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">Regime Detection &amp; Transitions</h1>
          <Badge variant="outline" size="md">
            Scheduled for V19
          </Badge>
        </div>
        <p className="page-subtitle">
          Canonical regime classifications, duration metrics, and Markovian transition analytics.
        </p>
      </header>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Module Foundation Established</CardTitle>
          <CardDescription>
            Gaussian Mixture Models, Hidden Markov Models, KMeans ensemble voters, and empirical transition matrices are verified.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="placeholder-info-box">
            <p className="placeholder-info-text">
              Interactive regime timeline charts, cluster scatter plots, and transition heatmaps
              are scheduled for Volume 19 (Regime Intelligence Dashboard).
            </p>
            <div className="placeholder-api-endpoints">
              <span className="placeholder-api-label">Connected API Endpoints:</span>
              <ul className="placeholder-api-list">
                <li><code>GET /api/v1/markets/{`{symbol}`}/regime</code> — Current regime &amp; profiles</li>
                <li><code>GET /api/v1/markets/{`{symbol}`}/regime/transitions</code> — Empirical transition matrices</li>
              </ul>
            </div>
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
