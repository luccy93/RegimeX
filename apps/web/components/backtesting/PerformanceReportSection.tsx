"use client";

import React from "react";
import type { PerformanceReportDTO } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils/formatters";

export interface PerformanceReportSectionProps {
  report: PerformanceReportDTO;
}

export function PerformanceReportSection({ report }: PerformanceReportSectionProps) {
  const { methodology, limitations, metric_definitions } = report;

  return (
    <section className="performance-report-section" aria-labelledby="report-section-title">
      <div className="section-header">
        <div>
          <h2 id="report-section-title" className="section-title">Deterministic Performance Report</h2>
          <p className="section-subtitle">
            Immutable V15 reporting audit trail, execution methodology, model limitations, and metric definitions.
          </p>
        </div>
        <div className="report-badges">
          <Badge variant="outline" size="sm" className="font-mono">
            ID: {report.report_id.slice(0, 8)}…
          </Badge>
          <Badge variant="outline" size="sm">
            Ver: {report.report_version}
          </Badge>
        </div>
      </div>

      <div className="performance-report-grid">
        {/* Methodology Card */}
        <Card variant="bordered" className="report-card">
          <CardHeader>
            <CardTitle className="report-card-title">Execution Methodology & Policies</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="report-methodology-list">
              <div className="methodology-entry">
                <dt className="methodology-dt">Execution Engine</dt>
                <dd className="methodology-dd font-mono">{methodology.execution_engine_source}</dd>
              </div>
              <div className="methodology-entry">
                <dt className="methodology-dt">Risk Engine Source</dt>
                <dd className="methodology-dd font-mono">{methodology.risk_engine_source}</dd>
              </div>
              <div className="methodology-entry">
                <dt className="methodology-dt">Return Calculation</dt>
                <dd className="methodology-dd font-mono">{methodology.return_type}</dd>
              </div>
              <div className="methodology-entry">
                <dt className="methodology-dt">Trade Definition</dt>
                <dd className="methodology-dd font-mono">{methodology.trade_definition}</dd>
              </div>
              <div className="methodology-entry">
                <dt className="methodology-dt">Common Period Policy</dt>
                <dd className="methodology-dd font-mono">{methodology.common_period_policy}</dd>
              </div>
              <div className="methodology-entry">
                <dt className="methodology-dt">Report Generated At</dt>
                <dd className="methodology-dd font-mono">{formatDate(report.generated_at, "short")}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* Limitations & Disclaimers Card */}
        <Card variant="bordered" className="report-card">
          <CardHeader>
            <CardTitle className="report-card-title">Simulation Limitations & Disclaimers</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="report-limitations-list">
              {limitations.map((item, idx) => (
                <li key={idx} className="limitation-item">
                  <span className="limitation-bullet" aria-hidden="true">•</span>
                  <span className="limitation-text">{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Metric Definitions Glossary */}
      {metric_definitions && metric_definitions.length > 0 && (
        <div className="metric-definitions-wrapper" style={{ marginTop: "1.25rem" }}>
          <h4 className="table-heading">Metric Definitions & Directional Semantics</h4>
          <div className="risk-table-container">
            <table className="risk-quantile-table" aria-label="Strategy metric definitions">
              <thead>
                <tr>
                  <th scope="col">Metric Name</th>
                  <th scope="col">Description</th>
                  <th scope="col">Unit</th>
                  <th scope="col">Preferred Direction</th>
                  <th scope="col">Engine Source</th>
                </tr>
              </thead>
              <tbody>
                {metric_definitions.map((m, idx) => (
                  <tr key={idx}>
                    <td className="font-semibold font-mono">{m.metric_name}</td>
                    <td className="text-muted">{m.description}</td>
                    <td className="font-mono text-muted">{m.unit}</td>
                    <td>
                      <Badge
                        variant={
                          m.direction_semantics === "HIGHER_IS_BETTER"
                            ? "success"
                            : m.direction_semantics === "LOWER_IS_BETTER"
                            ? "warning"
                            : "outline"
                        }
                        size="sm"
                      >
                        {m.direction_semantics}
                      </Badge>
                    </td>
                    <td className="font-mono text-muted text-xs">{m.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
