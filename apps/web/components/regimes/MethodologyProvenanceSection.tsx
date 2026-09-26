"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils/formatters";

export interface MethodologyProvenanceSectionProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

export function MethodologyProvenanceSection({
  regimeData,
}: MethodologyProvenanceSectionProps) {
  if (!regimeData) return null;

  // Extract feature names
  const activeFeatures = regimeData.current_context?.current_features
    ? Object.keys(regimeData.current_context.current_features)
    : [];

  return (
    <Card variant="elevated" className="regime-methodology-card">
      <CardHeader>
        <CardTitle>Analytical Methodology &amp; Provenance</CardTitle>
        <CardDescription>
          Reproducibility specifications, algorithmic parameters, and data integrity parameters.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="methodology-grid">
          <div className="methodology-item">
            <span className="methodology-label">Regime Engine</span>
            <span className="methodology-value font-mono">
              {regimeData.model_name || "Unavailable"}
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Model Version</span>
            <span className="methodology-value font-mono">
              {regimeData.model_version || "Unavailable"}
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Algorithm</span>
            <span className="methodology-value font-mono">
              {regimeData.algorithm || "Unavailable"}
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Observation Interval</span>
            <span className="methodology-value font-mono">
              1d (Daily Close)
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Analysis Start</span>
            <span className="methodology-value font-mono">
              {regimeData.analysis_start ? formatDate(regimeData.analysis_start, "date-only") : "Unavailable"}
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Analysis End</span>
            <span className="methodology-value font-mono">
              {regimeData.analysis_end ? formatDate(regimeData.analysis_end, "date-only") : "Unavailable"}
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Total Observations</span>
            <span className="methodology-value font-mono tabular-nums">
              {regimeData.total_observations.toLocaleString("en-US")} bars
            </span>
          </div>

          <div className="methodology-item">
            <span className="methodology-label">Primary Features</span>
            <span className="methodology-value font-mono">
              {activeFeatures.length > 0 ? activeFeatures.join(", ") : "return_1d, volatility_20d"}
            </span>
          </div>
        </div>

        <div className="methodology-notes-box">
          <h4 className="methodology-notes-title">Governance &amp; Diagnostic Scope</h4>
          <ul className="methodology-bullet-list">
            <li>
              <strong>Descriptive &amp; Diagnostic:</strong> This analytics workspace provides historical categorization and structural statistical breakdowns. No directional trading signals, forward-looking predictions, or investment advice are generated.
            </li>
            <li>
              <strong>Non-Imputed Statistics:</strong> Feature statistics (mean, median, standard deviation, extrema) respect nullable values and explicitly avoid zero-imputation when data is absent or non-finite.
            </li>
            <li>
              <strong>Empirical Transition Dynamics:</strong> Transition probabilities and entropy metrics are computed strictly from verified consecutive observation pairs within the requested historical window.
            </li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
