"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import {
  formatRegimeLabel,
  getRegimeColor,
} from "@/lib/utils/regime";
import { formatPercent } from "@/lib/utils/formatters";

export interface RegimeConfidenceBarProps {
  regimeData?: MarketRegimeResponse | null;
  isLoading?: boolean;
}

/**
 * Confidence gauge visualization for the current regime assignment.
 *
 * Displays a horizontal bar with:
 *   - Regime-colored fill proportional to confidence level
 *   - Numeric confidence percentage
 *   - Regime label and model metadata
 *   - Threshold zones (Low / Medium / High confidence)
 */
export function RegimeConfidenceBar({
  regimeData,
  isLoading = false,
}: RegimeConfidenceBarProps) {
  if (isLoading || !regimeData) return null;

  const confidence = regimeData.confidence;
  const hasConfidence =
    confidence !== null && confidence !== undefined && typeof confidence === "number";

  if (!hasConfidence) return null;

  const normalizedConfidence = confidence <= 1.0 ? confidence * 100 : confidence;
  const clampedWidth = Math.min(100, Math.max(0, normalizedConfidence));
  const label = formatRegimeLabel(regimeData.current_regime_label, regimeData.current_regime);
  const color = getRegimeColor(regimeData.current_regime_label, regimeData.current_regime);

  // Confidence zone classification
  const zone =
    normalizedConfidence >= 80 ? "high" :
    normalizedConfidence >= 50 ? "medium" : "low";
  const zoneLabel =
    zone === "high" ? "High Confidence" :
    zone === "medium" ? "Moderate Confidence" : "Low Confidence";

  return (
    <Card variant="elevated" className="regime-confidence-card">
      <CardHeader>
        <div className="regime-confidence-header-row">
          <div>
            <CardTitle>Regime Confidence</CardTitle>
            <CardDescription>
              Model classification confidence for current regime assignment
            </CardDescription>
          </div>
          <span className={`regime-confidence-zone regime-confidence-zone-${zone}`}>
            {zoneLabel}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="regime-confidence-content">
          {/* Main Gauge */}
          <div className="regime-confidence-gauge">
            <div className="regime-confidence-gauge-header">
              <span className="regime-confidence-gauge-label">
                <span
                  className="regime-confidence-gauge-dot"
                  style={{ backgroundColor: color.hex }}
                />
                {label}
              </span>
              <span className="regime-confidence-gauge-value">
                {formatPercent(confidence, { isRatio: confidence <= 1.0, decimals: 1 })}
              </span>
            </div>

            <div
              className="regime-confidence-gauge-track"
              role="progressbar"
              aria-valuenow={normalizedConfidence}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Regime confidence: ${normalizedConfidence.toFixed(1)}%`}
            >
              {/* Threshold zones */}
              <div className="regime-confidence-zone-low" />
              <div className="regime-confidence-zone-medium" />
              <div className="regime-confidence-zone-high" />

              {/* Active fill */}
              <div
                className="regime-confidence-gauge-fill"
                style={{
                  width: `${clampedWidth}%`,
                  backgroundColor: color.hex,
                }}
              />

              {/* Threshold markers at 50% and 80% */}
              <div className="regime-confidence-threshold" style={{ left: "50%" }}>
                <span className="regime-confidence-threshold-label">50%</span>
              </div>
              <div className="regime-confidence-threshold" style={{ left: "80%" }}>
                <span className="regime-confidence-threshold-label">80%</span>
              </div>
            </div>
          </div>

          {/* Model provenance */}
          <div className="regime-confidence-meta">
            <span>
              Model: {regimeData.model_name || "Ensemble"} • Algorithm: {regimeData.algorithm || "Statistical"}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
