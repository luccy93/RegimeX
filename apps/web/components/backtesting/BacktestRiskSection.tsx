"use client";

import React from "react";
import type { BacktestRiskMetricsDTO } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatPercentage } from "@/lib/api/backtesting";

export interface BacktestRiskSectionProps {
  riskMetrics: BacktestRiskMetricsDTO;
}

export function BacktestRiskSection({ riskMetrics }: BacktestRiskSectionProps) {
  return (
    <section className="backtest-risk-section" aria-labelledby="backtest-risk-title">
      <div className="section-header">
        <div>
          <h2 id="backtest-risk-title" className="section-title">Strategy Risk Diagnostics</h2>
          <p className="section-subtitle">
            Portfolio risk metrics evaluated strictly on strategy returns and net equity path.
          </p>
        </div>
        <Badge variant="outline" size="sm">Equity Curve Risk</Badge>
      </div>

      <div className="risk-metrics-grid">
        <Card variant="bordered" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Annualized Volatility</span>
            <Badge variant="outline" size="sm">252 Periods</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value tabular-nums font-mono">
              {formatPercentage(riskMetrics.annualized_volatility)}
            </div>
            <div className="backtest-metric-subtext">
              Period Volatility: <span className="tabular-nums font-semibold">{formatPercentage(riskMetrics.volatility)}</span>
            </div>
          </CardContent>
        </Card>

        <Card variant="bordered" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Max Equity Drawdown</span>
            <Badge variant="danger" size="sm">Peak-to-Trough</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value text-danger tabular-nums font-mono font-semibold">
              {formatPercentage(riskMetrics.maximum_drawdown)}
            </div>
            <div className="backtest-metric-subtext">
              Magnitude: <span className="tabular-nums font-semibold">{formatPercentage(riskMetrics.drawdown_magnitude)}</span>
            </div>
          </CardContent>
        </Card>

        <Card variant="bordered" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Value at Risk (95% 1-Day)</span>
            <Badge variant="outline" size="sm">Loss-Oriented</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value text-danger tabular-nums font-mono font-semibold">
              {formatPercentage(riskMetrics.var_95)}
            </div>
            <div className="backtest-metric-subtext">
              Worst 5% daily loss cutoff on strategy returns
            </div>
          </CardContent>
        </Card>

        <Card variant="bordered" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Expected Shortfall (95%)</span>
            <Badge variant="warning" size="sm">Tail Risk</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value text-warning tabular-nums font-mono font-semibold">
              {formatPercentage(riskMetrics.expected_shortfall_95)}
            </div>
            <div className="backtest-metric-subtext">
              Mean tail loss exceeding the 95% VaR threshold
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
