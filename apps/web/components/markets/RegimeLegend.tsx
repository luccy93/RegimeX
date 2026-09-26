"use client";

import React from "react";
import type { MarketRegimeResponse } from "@/lib/api/types";
import {
  formatRegimeLabel,
  getRegimeColor,
} from "@/lib/utils/regime";

export interface RegimeLegendProps {
  regimeData?: MarketRegimeResponse | null;
  className?: string;
}

/**
 * Renders a horizontal legend strip mapping regime labels to their assigned colors.
 * Highlights the currently active regime with a subtle accent.
 */
export function RegimeLegend({ regimeData, className }: RegimeLegendProps) {
  if (!regimeData) return null;

  const profiles = Object.values(regimeData.profiles ?? {});
  if (profiles.length === 0) return null;

  const currentRegimeId = regimeData.current_regime;

  return (
    <div
      className={`regime-legend ${className ?? ""}`}
      role="list"
      aria-label="Regime color legend"
    >
      {profiles.map((profile) => {
        const label = formatRegimeLabel(profile.regime_label, profile.regime_id);
        const color = getRegimeColor(profile.regime_label, profile.regime_id);
        const isCurrent = profile.regime_id === currentRegimeId;

        return (
          <div
            key={profile.regime_id}
            className={`regime-legend-item ${isCurrent ? "regime-legend-item-active" : ""}`}
            role="listitem"
            aria-current={isCurrent ? "true" : undefined}
          >
            <span
              className="regime-legend-swatch"
              style={{ backgroundColor: color.hex }}
              aria-hidden="true"
            />
            <span className="regime-legend-label">{label}</span>
            {isCurrent && (
              <span className="regime-legend-active-badge">Active</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
