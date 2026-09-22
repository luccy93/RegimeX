"""
RegimeX Portfolio Risk — Return Statistics Unit Tests
=====================================================
Tests descriptive return statistics (mean, median, sample std, min, max).
"""

from __future__ import annotations

import statistics

import pytest
from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
    NonFiniteValueError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class TestReturnStatistics:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_statistics_matches_exact_expected_values(self) -> None:
        rets = [0.01, -0.02, 0.03, -0.01, 0.04]
        stats = self.engine.compute_statistics(rets)

        assert stats.observation_count == 5
        assert abs(stats.mean_return - statistics.mean(rets)) < 1e-12
        assert abs(stats.median_return - statistics.median(rets)) < 1e-12
        # Verify Bessel correction (ddof=1)
        assert abs(stats.standard_deviation - statistics.stdev(rets)) < 1e-12
        assert stats.minimum_return == -0.02
        assert stats.maximum_return == 0.04

    def test_insufficient_returns_raises_error(self) -> None:
        with pytest.raises(InsufficientRiskDataError) as exc_info:
            self.engine.compute_statistics([0.05])
        assert exc_info.value.required_samples == 2
        assert exc_info.value.available_samples == 1

        with pytest.raises(InsufficientRiskDataError):
            self.engine.compute_statistics([])

    def test_non_finite_returns_rejected(self) -> None:
        with pytest.raises(NonFiniteValueError):
            self.engine.compute_statistics([0.01, float("nan"), 0.02])

    def test_constant_returns_has_zero_standard_deviation(self) -> None:
        rets = [0.02, 0.02, 0.02, 0.02]
        stats = self.engine.compute_statistics(rets)
        assert stats.standard_deviation == 0.0
        assert stats.mean_return == 0.02
        assert stats.median_return == 0.02
