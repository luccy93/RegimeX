/**
 * RegimeX Web — Regime Timeline Computation Utilities
 * ====================================================
 * Derives regime timeline segments from MarketRegimeResponse and OHLCV data.
 *
 * The backend provides regime profiles (aggregate statistics) but does not
 * emit a per-bar regime assignment timeline. This module reconstructs a
 * plausible regime timeline from the available data:
 *   - RegimeProfileDTO provides first_seen / last_seen / observation_count / run_count
 *   - CurrentRegimeContextDTO provides current_regime_id + current_timestamp +
 *     observations_in_current_run
 *
 * Because the backend does not provide a bar-by-bar regime_id sequence,
 * we construct a "regime run" based timeline using the profile metadata.
 * Each run represents a contiguous period where a single regime was active.
 *
 * This is a best-effort reconstruction for visualization; actual bar-level
 * assignment would require a dedicated backend endpoint.
 */

import type {
  MarketRegimeResponse,
  OHLCVBarResponse,
  RegimeProfileDTO,
} from "@/lib/api/types";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/** A single contiguous regime segment in the timeline */
export interface RegimeSegment {
  regimeId: number;
  regimeLabel: string;
  startIndex: number;   // index into bars array
  endIndex: number;     // index into bars array (inclusive)
  startTimestamp: string;
  endTimestamp: string;
  barCount: number;
  isCurrent: boolean;
}

/** A regime change transition point */
export interface RegimeTransition {
  barIndex: number;
  timestamp: string;
  fromRegimeId: number;
  fromRegimeLabel: string;
  toRegimeId: number;
  toRegimeLabel: string;
}

/** Complete timeline computation result */
export interface RegimeTimelineData {
  segments: RegimeSegment[];
  transitions: RegimeTransition[];
  regimeIds: number[];
  totalBars: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Computation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Constructs regime timeline segments from regime profiles and OHLCV bars.
 *
 * Strategy:
 *   1. Sort regime profiles by first_seen date
 *   2. Map each bar to the regime whose active window encompasses it
 *   3. Merge consecutive same-regime bars into segments
 *   4. Derive transition points from segment boundaries
 *
 * Falls back gracefully when profile metadata is incomplete.
 */
export function computeRegimeTimeline(
  regimeData: MarketRegimeResponse | null | undefined,
  bars: OHLCVBarResponse[]
): RegimeTimelineData {
  const empty: RegimeTimelineData = {
    segments: [],
    transitions: [],
    regimeIds: [],
    totalBars: 0,
  };

  if (!regimeData || !bars || bars.length === 0) {
    return empty;
  }

  const profiles = Object.values(regimeData.profiles ?? {});
  const currentContext = regimeData.current_context;

  if (profiles.length === 0) {
    return empty;
  }

  // Sort profiles by first_seen chronologically
  const sortedProfiles = [...profiles]
    .filter((p) => p.first_seen && p.last_seen)
    .sort((a, b) => {
      const aTime = new Date(a.first_seen!).getTime();
      const bTime = new Date(b.first_seen!).getTime();
      return aTime - bTime;
    });

  if (sortedProfiles.length === 0) {
    // No temporal data available — assign all bars to current regime
    const seg: RegimeSegment = {
      regimeId: regimeData.current_regime,
      regimeLabel: regimeData.current_regime_label,
      startIndex: 0,
      endIndex: bars.length - 1,
      startTimestamp: bars[0].timestamp,
      endTimestamp: bars[bars.length - 1].timestamp,
      barCount: bars.length,
      isCurrent: true,
    };
    return {
      segments: [seg],
      transitions: [],
      regimeIds: [regimeData.current_regime],
      totalBars: bars.length,
    };
  }

  // Assign each bar to a regime using the profile active windows
  const barAssignments: number[] = new Array(bars.length);

  for (let i = 0; i < bars.length; i++) {
    const barTime = new Date(bars[i].timestamp).getTime();
    let assignedRegime = regimeData.current_regime; // default fallback

    for (const profile of sortedProfiles) {
      const firstSeen = new Date(profile.first_seen!).getTime();
      const lastSeen = new Date(profile.last_seen!).getTime();

      if (barTime >= firstSeen && barTime <= lastSeen) {
        assignedRegime = profile.regime_id;
        // Don't break: later profiles may also contain this bar,
        // but last match wins (most recent regime takes precedence)
      }
    }

    barAssignments[i] = assignedRegime;
  }

  // If there's a current run from context, ensure the last N bars are assigned to current regime
  if (currentContext && currentContext.observations_in_current_run > 0) {
    const runLength = Math.min(currentContext.observations_in_current_run, bars.length);
    for (let i = bars.length - runLength; i < bars.length; i++) {
      barAssignments[i] = currentContext.current_regime_id;
    }
  }

  // Build a profile label lookup
  const labelLookup: Record<number, string> = {};
  for (const p of profiles) {
    labelLookup[p.regime_id] = p.regime_label;
  }
  labelLookup[regimeData.current_regime] = regimeData.current_regime_label;

  // Merge consecutive same-regime bars into segments
  const segments: RegimeSegment[] = [];
  let segStart = 0;

  for (let i = 1; i <= bars.length; i++) {
    if (i === bars.length || barAssignments[i] !== barAssignments[segStart]) {
      const regimeId = barAssignments[segStart];
      segments.push({
        regimeId,
        regimeLabel: labelLookup[regimeId] ?? `REGIME_${regimeId}`,
        startIndex: segStart,
        endIndex: i - 1,
        startTimestamp: bars[segStart].timestamp,
        endTimestamp: bars[i - 1].timestamp,
        barCount: i - segStart,
        isCurrent: i === bars.length && regimeId === regimeData.current_regime,
      });
      segStart = i;
    }
  }

  // Derive transitions from segment boundaries
  const transitions: RegimeTransition[] = [];
  for (let i = 1; i < segments.length; i++) {
    const prev = segments[i - 1];
    const curr = segments[i];
    transitions.push({
      barIndex: curr.startIndex,
      timestamp: curr.startTimestamp,
      fromRegimeId: prev.regimeId,
      fromRegimeLabel: prev.regimeLabel,
      toRegimeId: curr.regimeId,
      toRegimeLabel: curr.regimeLabel,
    });
  }

  // Collect unique regime IDs
  const regimeIdSet = new Set(barAssignments);
  const regimeIds = Array.from(regimeIdSet).sort((a, b) => a - b);

  return {
    segments,
    transitions,
    regimeIds,
    totalBars: bars.length,
  };
}

/**
 * Computes regime distribution percentages from segments.
 * Returns a map from regimeId to percentage [0..100].
 */
export function computeRegimeDistribution(
  segments: RegimeSegment[],
  totalBars: number
): Map<number, number> {
  const distribution = new Map<number, number>();
  if (totalBars === 0) return distribution;

  for (const seg of segments) {
    const existing = distribution.get(seg.regimeId) || 0;
    distribution.set(seg.regimeId, existing + seg.barCount);
  }

  // Convert counts to percentages
  for (const [id, count] of distribution) {
    distribution.set(id, (count / totalBars) * 100);
  }

  return distribution;
}
