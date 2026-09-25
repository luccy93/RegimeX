import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export const metadata = {
  title: "Console Overview",
  description: "RegimeX Platform Console Overview",
};

export default function AppOverviewPage() {
  const modules = [
    {
      title: "Market Discovery & OHLCV",
      route: "/app/markets",
      status: "Scheduled for V19",
      backendStatus: "API Ready (GET /api/v1/markets)",
      description:
        "Time-series historical data exploration, symbol resolution, and bar aggregation.",
    },
    {
      title: "Regime Detection & Profiles",
      route: "/app/regimes",
      status: "Scheduled for V19",
      backendStatus: "API Ready (GET /api/v1/markets/{s}/regime)",
      description:
        "Point-in-time canonical regime classifications, duration metrics, and feature distribution statistics.",
    },
    {
      title: "Transition Analytics",
      route: "/app/regimes",
      status: "Scheduled for V19",
      backendStatus: "API Ready (GET /api/v1/markets/{s}/regime/transitions)",
      description:
        "Empirical transition matrices, persistence probabilities, and destination rankings.",
    },
    {
      title: "Portfolio Risk Intelligence",
      route: "/app/risk",
      status: "Scheduled for V20",
      backendStatus: "Domain Verified (V10)",
      description:
        "Cross-regime Value at Risk (VaR), Conditional VaR, and max drawdown analytics.",
    },
    {
      title: "Systematic Backtesting",
      route: "/app/backtesting",
      status: "Scheduled for V20",
      backendStatus: "Domain Verified (V11)",
      description:
        "Event-driven strategy simulation across historical regimes with tear-sheet reporting.",
    },
    {
      title: "AI Quantitative Research Assistant",
      route: "/app/research",
      status: "Scheduled for V21",
      backendStatus: "Planned",
      description:
        "Grounded conversational assistant querying domain engines and regime knowledge bases.",
    },
  ];

  return (
    <div className="console-overview">
      <header className="page-header">
        <div className="page-header-title-row">
          <h1 className="page-title">Platform Overview</h1>
          <Badge variant="success" size="md">
            Web Foundation Active
          </Badge>
        </div>
        <p className="page-subtitle">
          RegimeX Volume 18 initializes the Next.js production web shell, design system, and typed
          API client foundation. Interactive visualizers and analytical dashboards are scheduled
          for deployment in Volumes 19 and 20.
        </p>
      </header>

      {/* Platform Status Card */}
      <section className="console-section" aria-labelledby="status-summary-heading">
        <Card variant="elevated">
          <CardHeader>
            <CardTitle id="status-summary-heading">Platform Architecture Status</CardTitle>
            <CardDescription>
              Backend API services, domain layers, and transport contracts established through Volume 17.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-label">Web Client</span>
                <span className="stat-value">Next.js 14 App Router</span>
                <span className="stat-meta">TypeScript / Vanilla CSS</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">API Transport</span>
                <span className="stat-value">FastAPI v1</span>
                <span className="stat-meta">Typed JSON Envelope / Bearer JWT</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Domain Engines</span>
                <span className="stat-value">GMM / HMM / KMeans</span>
                <span className="stat-meta">VaR / CVaR / Backtest Engine</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Data Pipeline</span>
                <span className="stat-value">TimescaleDB / Redis</span>
                <span className="stat-meta">Normalized OHLCV Provider</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Roadmap Modules */}
      <section className="console-section" aria-labelledby="modules-heading">
        <h2 id="modules-heading" className="section-title">
          Application Modules &amp; Routes
        </h2>
        <div className="modules-grid">
          {modules.map((mod) => (
            <Card key={mod.title} variant="default" className="module-card">
              <CardHeader>
                <div className="module-card-badges">
                  <Badge variant="outline" size="sm">
                    {mod.status}
                  </Badge>
                  <Badge variant="info" size="sm">
                    {mod.backendStatus}
                  </Badge>
                </div>
                <CardTitle className="module-card-title">{mod.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{mod.description}</CardDescription>
                <div className="module-card-action">
                  <Link href={mod.route}>
                    <Button variant="outline" size="sm">
                      Inspect Route
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
