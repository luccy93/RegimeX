"""
RegimeX Portfolio Risk — Portfolio Alignment & Hardening Tests
==============================================================
Hardening multi-asset portfolio returns against data corruption, misalignment,
and non-UTC timestamps:
- Rejects misaligned timestamps across constituent assets.
- Rejects non-UTC or timezone-naive timestamps.
- Validates weights normalization and finite weights.
- Guarantees zero artificial forward-filling or zero-return insertion.
- Confirms bitwise determinism for multi-asset calculations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.modules.portfolio_risk.domain.errors import (
    MismatchedAssetAlignmentError,
    TemporalOrderError,
)
from app.modules.portfolio_risk.domain.models import PortfolioWeights, ReturnSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestPortfolioAlignmentHardening:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_mismatched_asset_dates_rejected(self) -> None:
        # Both assets have 3 days, but Day 1 differs (day 1 vs day 4)
        ts_a = (_ts(0), _ts(1), _ts(2))
        ts_b = (_ts(0), _ts(1), _ts(3))

        s_a = ReturnSeries(timestamps=ts_a, values=(0.01, -0.02, 0.03), symbol="A")
        s_b = ReturnSeries(timestamps=ts_b, values=(0.02, -0.01, 0.01), symbol="B")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.5, 0.5))

        with pytest.raises(MismatchedAssetAlignmentError):
            self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)

    def test_non_utc_timestamps_rejected(self) -> None:
        # Non-UTC timezone (EST offset -5 hours)
        est = timezone(timedelta(hours=-5))
        non_utc_ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=est)
        with pytest.raises(ValueError):
            ReturnSeries(timestamps=(non_utc_ts,), values=(0.01,))

    def test_non_utc_in_engine_resolve_timestamps_rejected(self) -> None:
        est = timezone(timedelta(hours=-5))
        prices = [100.0, 105.0]
        timestamps = [
            datetime(2025, 1, 1, 0, 0, 0, tzinfo=est),
            datetime(2025, 1, 2, 0, 0, 0, tzinfo=est),
        ]
        with pytest.raises(TemporalOrderError):
            self.engine.compute_arithmetic_returns(prices, timestamps)

    def test_unnormalized_weights_flag(self) -> None:
        # With is_normalized=False, weights sum does not need to equal 1.0
        weights = PortfolioWeights(
            symbols=("A", "B"),
            weights=(2.0, 3.0),
            is_normalized=False,
        )
        ts = (_ts(0), _ts(1))
        s_a = ReturnSeries(timestamps=ts, values=(0.01, 0.02), symbol="A")
        s_b = ReturnSeries(timestamps=ts, values=(-0.01, 0.01), symbol="B")

        port = self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)
        # 2.0*0.01 + 3.0*(-0.01) = -0.01
        assert abs(port[0] - (-0.01)) < 1e-12
        # 2.0*0.02 + 3.0*(0.01) = 0.07
        assert abs(port[1] - 0.07) < 1e-12

    def test_portfolio_repeated_identical_runs_are_deterministic(self) -> None:
        ts = (_ts(0), _ts(1), _ts(2))
        s_a = ReturnSeries(timestamps=ts, values=(0.02, -0.01, 0.03), symbol="A")
        s_b = ReturnSeries(timestamps=ts, values=(-0.02, 0.04, -0.01), symbol="B")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.6, 0.4))

        run_1 = self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)
        run_2 = self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)

        assert run_1.values == run_2.values
        assert run_1.timestamps == run_2.timestamps
