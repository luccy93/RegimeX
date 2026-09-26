"use client";

import React from "react";
import type { TradeStatisticsDTO, BacktestTradeDTO } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";
import { formatCurrency, formatPercentage } from "@/lib/api/backtesting";

export interface TradeStatisticsSectionProps {
  trades: TradeStatisticsDTO;
  executedTrades: BacktestTradeDTO[];
}

export function TradeStatisticsSection({ trades, executedTrades }: TradeStatisticsSectionProps) {
  return (
    <section className="trade-statistics-section" aria-labelledby="trades-section-title">
      <div className="section-header">
        <div>
          <h2 id="trades-section-title" className="section-title">Trade Execution & Win/Loss Statistics</h2>
          <p className="section-subtitle">
            Order execution history, fill reconciliation, and trade-level profit attribution.
          </p>
        </div>
        <Badge variant="outline" size="sm">
          {trades.fill_count} Fills Recorded
        </Badge>
      </div>

      {/* Trade metrics grid */}
      <div className="trade-metrics-grid">
        <div className="trade-stat-box">
          <span className="trade-stat-label">Orders / Fills</span>
          <span className="trade-stat-value tabular-nums font-mono">
            {trades.order_count} / {trades.fill_count}
          </span>
          <span className="trade-stat-sub">100% Fill Efficiency</span>
        </div>

        <div className="trade-stat-box">
          <span className="trade-stat-label">Completed Trades</span>
          <span className="trade-stat-value tabular-nums font-mono">
            {trades.completed_trade_count}
          </span>
          <span className="trade-stat-sub">
            {trades.winning_trades} Win / {trades.losing_trades} Loss
          </span>
        </div>

        <div className="trade-stat-box">
          <span className="trade-stat-label">Win Rate</span>
          <span className={`trade-stat-value tabular-nums font-mono font-semibold ${trades.win_rate >= 0.5 ? "text-success" : "text-danger"}`}>
            {formatPercentage(trades.win_rate)}
          </span>
          <span className="trade-stat-sub">Realized: {formatCurrency(trades.total_realized_pnl)}</span>
        </div>

        <div className="trade-stat-box">
          <span className="trade-stat-label">Average Trade PnL</span>
          <span className={`trade-stat-value tabular-nums font-mono ${trades.average_trade_pnl >= 0 ? "text-success" : "text-danger"}`}>
            {trades.average_trade_pnl >= 0 ? "+" : ""}{formatCurrency(trades.average_trade_pnl)}
          </span>
          <span className="trade-stat-sub">Per completed position</span>
        </div>

        <div className="trade-stat-box">
          <span className="trade-stat-label">Largest Winning Trade</span>
          <span className="trade-stat-value tabular-nums font-mono text-success font-semibold">
            +{formatCurrency(trades.largest_winning_trade)}
          </span>
          <span className="trade-stat-sub">Peak gain</span>
        </div>

        <div className="trade-stat-box">
          <span className="trade-stat-label">Largest Losing Trade</span>
          <span className="trade-stat-value tabular-nums font-mono text-danger font-semibold">
            {formatCurrency(trades.largest_losing_trade)}
          </span>
          <span className="trade-stat-sub">Worst loss</span>
        </div>
      </div>

      {/* Executed Fills Table */}
      <div className="executed-trades-table-wrapper" style={{ marginTop: "1.25rem" }}>
        <h4 className="table-heading">Executed Fills & Transaction Detail</h4>

        {executedTrades.length === 0 ? (
          <div className="empty-trades-notice">No trade fills were executed during this backtest simulation period.</div>
        ) : (
          <div className="risk-table-container">
            <table className="risk-quantile-table" aria-label="Executed trade fills log">
              <thead>
                <tr>
                  <th scope="col">Timestamp</th>
                  <th scope="col">Instrument</th>
                  <th scope="col">Side</th>
                  <th scope="col">Quantity</th>
                  <th scope="col">Fill Price</th>
                  <th scope="col">Commission</th>
                  <th scope="col">Slippage</th>
                </tr>
              </thead>
              <tbody>
                {executedTrades.map((t, idx) => {
                  const isBuy = t.side.toUpperCase() === "BUY";
                  return (
                    <tr key={idx}>
                      <td className="tabular-nums font-mono text-muted">
                        {formatDate(t.timestamp, "short")}
                      </td>
                      <td className="font-semibold">{t.symbol}</td>
                      <td>
                        <Badge variant={isBuy ? "success" : "danger"} size="sm">
                          {t.side.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="tabular-nums font-mono">{t.quantity.toLocaleString()}</td>
                      <td className="tabular-nums font-mono">${t.price.toFixed(2)}</td>
                      <td className="tabular-nums font-mono text-muted">${t.commission.toFixed(2)}</td>
                      <td className="tabular-nums font-mono text-muted">${t.slippage.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
