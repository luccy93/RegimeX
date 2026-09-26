"use client";

import React from "react";
import type { MarketBacktestResponse } from "@/lib/api/types";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency, formatPercentage } from "@/lib/api/backtesting";

export interface BacktestPerformanceOverviewProps {
  backtestData: MarketBacktestResponse;
}

export function BacktestPerformanceOverview({ backtestData }: BacktestPerformanceOverviewProps) {
  const isPositive = backtestData.total_return >= 0;

  return (
    <section className="backtest-overview-section" aria-labelledby="backtest-overview-title">
      <div className="section-header">
        <h2 id="backtest-overview-title" className="section-title">Performance Summary</h2>
        <Badge variant={isPositive ? "success" : "danger"} size="sm">
          {isPositive ? "Positive Net Return" : "Capital Loss"}
        </Badge>
      </div>

      <div className="backtest-metrics-grid">
        {/* Net Equity */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Final Equity</span>
            <Badge variant={isPositive ? "success" : "danger"} size="sm">
              {formatPercentage(backtestData.total_return)}
            </Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value tabular-nums font-mono font-semibold">
              {formatCurrency(backtestData.final_equity)}
            </div>
            <div className="backtest-metric-subtext">
              Net PnL:{" "}
              <span className={`tabular-nums font-semibold ${backtestData.absolute_pnl >= 0 ? "text-success" : "text-danger"}`}>
                {backtestData.absolute_pnl >= 0 ? "+" : ""}{formatCurrency(backtestData.absolute_pnl)}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Annualized Return */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Annualized Return</span>
            <Badge variant="outline" size="sm">CAGR Basis</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className={`backtest-metric-value tabular-nums font-mono font-semibold ${backtestData.annualized_return >= 0 ? "text-success" : "text-danger"}`}>
              {backtestData.annualized_return >= 0 ? "+" : ""}{formatPercentage(backtestData.annualized_return)}
            </div>
            <div className="backtest-metric-subtext">
              Total Cumulative: <span className="tabular-nums font-semibold">{formatPercentage(backtestData.total_return)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Realized vs Unrealized PnL */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">PnL Decomposition</span>
            <Badge variant="outline" size="sm">Closed vs Open</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value tabular-nums font-mono">
              {formatCurrency(backtestData.realized_pnl)}
            </div>
            <div className="backtest-metric-subtext">
              Unrealized: <span className="tabular-nums font-semibold">{formatCurrency(backtestData.unrealized_pnl)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Transaction Costs */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Execution Friction</span>
            <Badge variant="outline" size="sm">Fees & Slip</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value text-muted tabular-nums font-mono">
              {formatCurrency(backtestData.total_fees)}
            </div>
            <div className="backtest-metric-subtext">
              Commissions: <span className="tabular-nums font-semibold">{(backtestData.commission_rate * 10000).toFixed(0)} bps</span> | Slippage: <span className="tabular-nums font-semibold">{(backtestData.slippage_rate * 10000).toFixed(0)} bps</span>
            </div>
          </CardContent>
        </Card>

        {/* Maximum Drawdown */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Maximum Strategy Drawdown</span>
            <Badge variant="danger" size="sm">Equity Track</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value text-danger tabular-nums font-mono font-semibold">
              {formatPercentage(backtestData.risk_metrics.maximum_drawdown)}
            </div>
            <div className="backtest-metric-subtext">
              Decline Magnitude: <span className="tabular-nums font-semibold">{formatPercentage(backtestData.risk_metrics.drawdown_magnitude)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Strategy Volatility */}
        <Card variant="elevated" className="backtest-metric-card">
          <CardHeader className="backtest-metric-card-header">
            <span className="backtest-metric-label">Strategy Volatility (Ann.)</span>
            <Badge variant="outline" size="sm">252 Periods</Badge>
          </CardHeader>
          <CardContent className="backtest-metric-card-content">
            <div className="backtest-metric-value tabular-nums font-mono font-semibold">
              {formatPercentage(backtestData.risk_metrics.annualized_volatility)}
            </div>
            <div className="backtest-metric-subtext">
              Period Volatility: <span className="tabular-nums font-semibold">{formatPercentage(backtestData.risk_metrics.volatility)}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
