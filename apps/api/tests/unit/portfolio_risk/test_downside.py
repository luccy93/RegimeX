"""
RegimeX Portfolio Risk — Downside Risk Unit Tests
=================================================
Tests downside semi-deviation below configurable target returns.
"""

from __future__ import annotations

import math

import pytest
from app.modules.portfolio_risk.domain.errors import (
    NonFiniteValueError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class TestDownsideRisk:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_all_returns_above_target_has_zero_downside_deviation(self) -> None:
        rets = [0.01, 0.02, 0.03, 0.05]
        downside = self.engine.compute_downside_risk(rets, target_return=0.0)

        assert downside.downside_deviation == 0.0
        assert downside.observations_below_target == 0
        assert downside.total_observations == 4
        assert downside.target_return == 0.0

    def test_mixed_returns_downside_deviation(self) -> None:
        # returns: [0.02, -0.01, -0.03, 0.04]
        # target: 0.0
        # deviations below target: 0.0, -0.01, -0.03, 0.0
        # squared: 0, 0.0001, 0.0009, 0 -> sum = 0.0010
        # mean squared: 0.0010 / 4 = 0.00025
        # sqrt(0.00025) = 0.015811388300841896
        rets = [0.02, -0.01, -0.03, 0.04]
        downside = self.engine.compute_downside_risk(rets, target_return=0.0)

        expected = math.sqrt(((-0.01) ** 2 + (-0.03) ** 2) / 4.0)
        assert abs(downside.downside_deviation - expected) < 1e-12
        assert downside.observations_below_target == 2
        assert downside.total_observations == 4

    def test_configurable_non_zero_target(self) -> None:
        # Target: 0.02
        # returns: [0.01, 0.03, 0.00]
        # below target: 0.01 (diff -0.01), 0.00 (diff -0.02)
        # squared: 0.0001 + 0.0004 = 0.0005
        # mean: 0.0005 / 3
        rets = [0.01, 0.03, 0.00]
        downside = self.engine.compute_downside_risk(rets, target_return=0.02)

        expected = math.sqrt(((-0.01) ** 2 + (-0.02) ** 2) / 3.0)
        assert abs(downside.downside_deviation - expected) < 1e-12
        assert downside.observations_below_target == 2

    def test_all_negative_returns(self) -> None:
        rets = [-0.01, -0.02, -0.03]
        downside = self.engine.compute_downside_risk(rets, target_return=0.0)
        expected = math.sqrt((0.0001 + 0.0004 + 0.0009) / 3.0)
        assert abs(downside.downside_deviation - expected) < 1e-12
        assert downside.observations_below_target == 3

    def test_non_finite_target_rejected(self) -> None:
        rets = [0.01, -0.02]
        with pytest.raises(NonFiniteValueError):
            self.engine.compute_downside_risk(rets, target_return=float("nan"))
