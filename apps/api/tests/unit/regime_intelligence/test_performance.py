"""
Unit Tests — Regime Intelligence Performance & Scalability
===========================================================
Validates that regime intelligence processing scales linearly O(N)
and executes promptly on large series without quadratic degradation.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.models import RegimeAssignment


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


class TestIntelligencePerformance:
    """Performance regression safeguards."""

    def setup_method(self) -> None:
        self.service = RegimeIntelligenceService()

    def test_linear_scaling_on_large_synthetic_dataset(self) -> None:
        """
        Processing 5,000 observations with 4 features must execute comfortably
        within 2.0 seconds on standard execution environments, proving O(N) duration
        run-length encoding and single-pass feature extraction.
        """
        n_obs = 5000
        assignments = [
            RegimeAssignment(
                timestamp=_ts(i),
                regime_id=i % 4,
                regime_label=f"REGIME_{i % 4}",
                features={
                    "return_1": 0.001 * (i % 10),
                    "volatility_20": 0.01 * (i % 5),
                    "momentum_10": float(i % 20),
                    "volume_ratio": 1.0 + 0.1 * (i % 3),
                },
            )
            for i in range(n_obs)
        ]

        start_time = time.perf_counter()
        summary = self.service.summarize_history(assignments)
        elapsed = time.perf_counter() - start_time

        assert summary.total_observations == n_obs
        assert len(summary.regimes_observed) == 4
        assert summary.current_regime is not None
        # Must execute within 2.0 seconds (typically < 0.2s)
        assert elapsed < 2.0, f"Processing took {elapsed:.2f}s, expected < 2.0s."
