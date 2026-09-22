"""
RegimeX Portfolio Risk — Volatility Unit Tests
==============================================
Tests realized volatility and explicit annualization factor scaling.
"""

from __future__ import annotations

import math
import statistics

import pytest
from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class TestVolatility:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_realized_period_volatility_matches_sample_std(self) -> None:
        rets = [0.01, -0.015, 0.02, -0.005, 0.03]
        vol = self.engine.compute_volatility(rets)

        expected_std = statistics.stdev(rets)
        assert abs(vol.period_volatility - expected_std) < 1e-12
        assert vol.annualized_volatility is None
        assert vol.periods_per_year is None

    def test_annualized_volatility_explicit_factor(self) -> None:
        rets = [0.01, -0.01, 0.02, -0.02]
        vol = self.engine.compute_volatility(rets, periods_per_year=252.0)

        expected_period = statistics.stdev(rets)
        expected_ann = expected_period * math.sqrt(252.0)

        assert abs(vol.period_volatility - expected_period) < 1e-12
        assert vol.annualized_volatility is not None
        assert abs(vol.annualized_volatility - expected_ann) < 1e-12
        assert vol.periods_per_year == 252.0

    def test_crypto_365_annualization_factor(self) -> None:
        rets = [0.05, -0.03, 0.02, -0.01]
        vol = self.engine.compute_volatility(rets, periods_per_year=365.0)

        expected_ann = statistics.stdev(rets) * math.sqrt(365.0)
        assert vol.annualized_volatility is not None
        assert abs(vol.annualized_volatility - expected_ann) < 1e-12

    def test_invalid_periods_per_year_rejected(self) -> None:
        rets = [0.01, -0.01, 0.02]
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=0.0)
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=-252.0)
        with pytest.raises(ValueError):
            self.engine.compute_volatility(rets, periods_per_year=float("nan"))

    def test_zero_volatility_for_constant_returns(self) -> None:
        rets = [0.01, 0.01, 0.01, 0.01]
        vol = self.engine.compute_volatility(rets, periods_per_year=252.0)
        assert vol.period_volatility == 0.0
        assert vol.annualized_volatility == 0.0

    def test_insufficient_returns_raises_error(self) -> None:
        with pytest.raises(InsufficientRiskDataError):
            self.engine.compute_volatility([0.02])
