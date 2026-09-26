"use client";

import React from "react";
import type { MarketRiskResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { formatPercentage } from "@/lib/api/risk";

export interface RiskReturnDistributionSectionProps {
  riskData: MarketRiskResponse;
}

export function RiskReturnDistributionSection({ riskData }: RiskReturnDistributionSectionProps) {
  const { return_statistics, var_metrics, expected_shortfall_metrics } = riskData;

  const confLevels = ["0.90", "0.95", "0.99"];

  return (
    <section className="risk-distribution-section" aria-labelledby="risk-distribution-title">
      <div className="section-header">
        <div>
          <h2 id="risk-distribution-title" className="section-title">Tail Risk & Return Dispersion</h2>
          <p className="section-subtitle">
            Empirical parametric tail analysis comparing Value at Risk (VaR) and Conditional VaR (Expected Shortfall) across regulatory confidence tiers.
          </p>
        </div>
      </div>

      <div className="risk-distribution-layout">
        {/* VaR & ES Comparison Table */}
        <div className="risk-table-container">
          <table className="risk-quantile-table" aria-label="Value at Risk and Expected Shortfall by Confidence Level">
            <thead>
              <tr>
                <th scope="col">Confidence Tier</th>
                <th scope="col">VaR Loss (1-Day)</th>
                <th scope="col">Return Quantile</th>
                <th scope="col">Expected Shortfall</th>
                <th scope="col">Tail Observations</th>
                <th scope="col">Evaluation Method</th>
              </tr>
            </thead>
            <tbody>
              {confLevels.map((confKey) => {
                const vm = var_metrics[confKey];
                const em = expected_shortfall_metrics[confKey];
                const pctLabel = `${(parseFloat(confKey) * 100).toFixed(0)}%`;

                return (
                  <tr key={confKey}>
                    <td className="font-semibold">
                      <span className="conf-badge">{pctLabel} Confidence</span>
                    </td>
                    <td className="tabular-nums font-mono text-danger font-semibold">
                      {vm ? formatPercentage(vm.var_loss) : "—"}
                    </td>
                    <td className="tabular-nums font-mono text-muted">
                      {vm ? formatPercentage(vm.return_quantile) : "—"}
                    </td>
                    <td className="tabular-nums font-mono text-warning font-semibold">
                      {em ? formatPercentage(em.expected_shortfall) : "—"}
                    </td>
                    <td className="tabular-nums text-muted">
                      {vm ? `${vm.tail_observations} / ${vm.total_observations} bars` : "—"}
                    </td>
                    <td>
                      <Badge variant="outline" size="sm">
                        {vm?.method || "Historical"}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Return Dispersion Summary Card */}
        <div className="risk-dispersion-card">
          <h4 className="dispersion-heading">Return Distribution Statistics</h4>
          <p className="dispersion-sub">Calculated from {return_statistics.observation_count} discrete daily observations.</p>

          <div className="dispersion-metrics-list">
            <div className="dispersion-item">
              <span className="dispersion-label">Minimum 1-Day Return</span>
              <span className="dispersion-val text-danger font-mono font-semibold">
                {formatPercentage(return_statistics.minimum_return)}
              </span>
            </div>

            <div className="dispersion-item">
              <span className="dispersion-label">Median 1-Day Return</span>
              <span className="dispersion-val font-mono">
                {formatPercentage(return_statistics.median_return)}
              </span>
            </div>

            <div className="dispersion-item">
              <span className="dispersion-label">Sample Mean Return</span>
              <span className={`dispersion-val font-mono font-semibold ${return_statistics.mean_return >= 0 ? "text-success" : "text-danger"}`}>
                {return_statistics.mean_return >= 0 ? "+" : ""}{formatPercentage(return_statistics.mean_return)}
              </span>
            </div>

            <div className="dispersion-item">
              <span className="dispersion-label">Maximum 1-Day Return</span>
              <span className="dispersion-val text-success font-mono font-semibold">
                +{formatPercentage(return_statistics.maximum_return)}
              </span>
            </div>

            <div className="dispersion-item">
              <span className="dispersion-label">Standard Deviation (Daily)</span>
              <span className="dispersion-val font-mono">
                {formatPercentage(return_statistics.standard_deviation)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
