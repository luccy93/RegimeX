"""
RegimeX Regime Intelligence — Duration Analytics Engine
========================================================
Run-length encoding and duration analytics for chronologically ordered regime sequences.

Duration semantics:
- A run is defined as a maximal contiguous subsequence of identical regime assignments.
- Duration unit: discrete observations (bars), documented as ``duration_observations``.
- No calendar day extrapolation is performed to prevent interval ambiguity.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence

from app.modules.regime_intelligence.domain.errors import InsufficientRegimeDataError


class DurationAnalyzerImpl:
    """Production implementation of DurationAnalyzerProtocol."""

    def compute_runs(
        self,
        regime_series: Sequence[int],
    ) -> dict[int, list[int]]:
        """
        Compute run lengths (consecutive observation counts) for each observed regime.

        Args:
            regime_series: Chronologically ordered sequence of canonical regime IDs.

        Returns:
            Mapping of regime_id to list of run lengths in chronological order.
        """
        if not regime_series:
            return {}

        runs: dict[int, list[int]] = defaultdict(list)
        current_regime = regime_series[0]
        current_length = 1

        for r_id in regime_series[1:]:
            if r_id == current_regime:
                current_length += 1
            else:
                runs[current_regime].append(current_length)
                current_regime = r_id
                current_length = 1

        # Append final run
        runs[current_regime].append(current_length)

        return dict(runs)

    def compute_current_run(
        self,
        regime_series: Sequence[int],
    ) -> tuple[int, int]:
        """
        Compute the active regime ID and its trailing consecutive observation count.

        Args:
            regime_series: Chronologically ordered sequence of canonical regime IDs.

        Returns:
            tuple[int, int]: (current_regime_id, observations_in_current_run)

        Raises:
            InsufficientRegimeDataError: If regime_series is empty.
        """
        if not regime_series:
            raise InsufficientRegimeDataError(
                required_samples=1,
                available_samples=0,
                details={"message": "Cannot determine current run on empty regime history."},
            )

        current_regime = regime_series[-1]
        trailing_length = 0

        for r_id in reversed(regime_series):
            if r_id == current_regime:
                trailing_length += 1
            else:
                break

        return current_regime, trailing_length

    @staticmethod
    def summarize_runs(
        runs: list[int],
    ) -> tuple[int, float, float, int, int]:
        """
        Compute run summary metrics: (run_count, average, median, min, max).

        Args:
            runs: List of integer run durations.

        Returns:
            tuple of (run_count, average_duration, median_duration, min_duration, max_duration).
        """
        if not runs:
            return 0, 0.0, 0.0, 0, 0

        run_count = len(runs)
        avg_dur = float(statistics.mean(runs))
        med_dur = float(statistics.median(runs))
        min_dur = min(runs)
        max_dur = max(runs)

        return run_count, avg_dur, med_dur, min_dur, max_dur
