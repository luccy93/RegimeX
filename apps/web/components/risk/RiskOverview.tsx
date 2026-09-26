"use client";

import React from "react";
import type { MarketRiskResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatPercentage, formatDecimal } from "@/lib/api/risk";

export interface RiskOverviewProps {
  riskData: MarketRiskResponse;
}

export function RiskOverview({ riskData }: RiskOverviewProps) {
  const { volatility, drawdown, downside_risk, return_statistics, var_metrics, expected_shortfall_metrics } = riskData;

  const var95 = var_metrics["0.95"];
  const es95 = expected_shortfall_metrics["0.95"];

  return (
    <section className="risk-overview-section" aria-labelledby="risk-overview-title">
      <div className="section-header">
        <h2 id="risk-overview-title" className="section-title">Risk Profile Overview</h2>
        <Badge variant="outline" size="sm">Point-in-Time Metrics</Badge>
      </div>

      <div className="risk-metrics-grid">
        {/* Annualized Volatility */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Annualized Volatility</span>
            <Badge variant="outline" size="sm">252 Periods</Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className="risk-metric-value tabular-nums">
              {formatPercentage(volatility.annualized_volatility)}
            </div>
            <div className="risk-metric-subtext">
              Period Volatility: <span className="tabular-nums font-semibold">{formatPercentage(volatility.period_volatility)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Maximum Drawdown */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Maximum Drawdown</span>
            <Badge variant={drawdown.is_recovered ? "success" : "danger"} size="sm">
              {drawdown.is_recovered ? "Recovered" : "Active Loss"}
            </Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className="risk-metric-value risk-metric-loss tabular-nums">
              {formatPercentage(drawdown.max_drawdown)}
            </div>
            <div className="risk-metric-subtext">
              Peak-to-Trough Magnitude: <span className="tabular-nums font-semibold">{formatPercentage(drawdown.drawdown_magnitude)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Value at Risk (95%) */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Value at Risk (95% 1-Day)</span>
            <Badge variant="outline" size="sm">Loss-Oriented</Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className="risk-metric-value risk-metric-var tabular-nums">
              {var95 ? formatPercentage(var95.var_loss) : "—"}
            </div>
            <div className="risk-metric-subtext">
              Return Quantile: <span className="tabular-nums font-semibold">{var95 ? formatPercentage(var95.return_quantile) : "—"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Expected Shortfall (95%) */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Expected Shortfall (95% 1-Day)</span>
            <Badge variant="warning" size="sm">Tail Risk</Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className="risk-metric-value risk-metric-es tabular-nums">
              {es95 ? formatPercentage(es95.expected_shortfall) : "—"}
            </div>
            <div className="risk-metric-subtext">
              Tail Mean Return: <span className="tabular-nums font-semibold">{es95 ? formatPercentage(es95.tail_mean_return) : "—"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Downside Deviation */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Downside Deviation</span>
            <Badge variant="outline" size="sm">Target 0.0%</Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className="risk-metric-value tabular-nums">
              {formatPercentage(downside_risk.downside_deviation)}
            </div>
            <div className="risk-metric-subtext">
              Below Target: <span className="tabular-nums font-semibold">{downside_risk.downside_observation_count} / {downside_risk.observation_count} bars</span>
            </div>
          </CardContent>
        </Card>

        {/* Mean Return */}
        <Card variant="elevated" className="risk-metric-card">
          <CardHeader className="risk-metric-card-header">
            <span className="risk-metric-label">Mean Daily Return</span>
            <Badge variant="outline" size="sm">Discrete</Badge>
          </CardHeader>
          <CardContent className="risk-metric-card-content">
            <div className={`risk-metric-value tabular-nums ${return_statistics.mean_return >= 0 ? "risk-metric-positive" : "risk-metric-negative"}`}>
              {return_statistics.mean_return >= 0 ? "+" : ""}{formatPercentage(return_statistics.mean_return)}
            </div>
            <div className="risk-metric-subtext">
              Median: <span className="tabular-nums font-semibold">{formatPercentage(return_statistics.median_return)}</span> (StdDev: {formatPercentage(return_statistics.standard_deviation)})
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
