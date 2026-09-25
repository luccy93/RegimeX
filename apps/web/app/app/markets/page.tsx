import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";

export const metadata = {
  title: "Markets",
  description: "RegimeX Market Discovery and Data",
};

export default function MarketsPage() {
  return (
    <div className="module-placeholder-page">
      <Breadcrumbs
        items={[
          { label: "Console", href: "/app" },
          { label: "Markets", isCurrent: true },
        ]}
      />

      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">Market Discovery &amp; Data</h1>
          <Badge variant="outline" size="md">
            Scheduled for V19
          </Badge>
        </div>
        <p className="page-subtitle">
          Explore tradeable instruments, symbol catalogues, and historical OHLCV data.
        </p>
      </header>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Module Foundation Established</CardTitle>
          <CardDescription>
            The backend REST endpoints and typed frontend contracts for market discovery are operational.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="placeholder-info-box">
            <p className="placeholder-info-text">
              The full market catalogue browser, symbol search, and interactive candlestick chart
              are planned for Volume 19 (Market Dashboard).
            </p>
            <div className="placeholder-api-endpoints">
              <span className="placeholder-api-label">Connected API Endpoints:</span>
              <ul className="placeholder-api-list">
                <li><code>GET /api/v1/markets</code> — Discover instruments by asset class</li>
                <li><code>GET /api/v1/markets/{`{symbol}`}/data</code> — Query time-series OHLCV bars</li>
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
