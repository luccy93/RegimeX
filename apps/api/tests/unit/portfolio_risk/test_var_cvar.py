"""
RegimeX Portfolio Risk — VaR & Expected Shortfall Unit Tests
============================================================
Tests historical Value at Risk (VaR) and Expected Shortfall (CVaR).
"""

from __future__ import annotations

import pytest
from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
    InvalidConfidenceLevelError,
)
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class TestVaRAndExpectedShortfall:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_known_distribution_var_and_es(self) -> None:
        # Create a controlled distribution of 100 returns from -0.10 to +0.09
        # rets = [-0.10, -0.09, ..., +0.09] (100 discrete values)
        rets = [round(-0.10 + i * 0.0019, 6) for i in range(100)]

        var_95 = self.engine.compute_var(rets, confidence_level=0.95)
        es_95 = self.engine.compute_expected_shortfall(rets, confidence_level=0.95)

        # At 95% confidence, tail probability is 5%
        # The 5th percentile is negative, so var_loss is positive
        assert var_95.confidence_level == 0.95
        assert var_95.var_loss > 0.0
        assert var_95.var_loss == -var_95.return_quantile
        assert var_95.tail_observations >= 1

        # ES must be >= VaR in loss space
        assert es_95.confidence_level == 0.95
        assert es_95.expected_shortfall >= var_95.var_loss
        assert es_95.expected_shortfall == -es_95.tail_mean_return
        assert es_95.tail_observations >= 1

    def test_multiple_confidence_levels_ordering(self) -> None:
        # 99% VaR must be greater than or equal to 95% VaR, which is >= 90% VaR
        # generate 100 diverse returns
        rets = [-0.08, -0.05, -0.04, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03] * 10

        var_90 = self.engine.compute_var(rets, confidence_level=0.90)
        var_95 = self.engine.compute_var(rets, confidence_level=0.95)
        var_99 = self.engine.compute_var(rets, confidence_level=0.99)

        assert var_99.var_loss >= var_95.var_loss >= var_90.var_loss

        es_90 = self.engine.compute_expected_shortfall(rets, confidence_level=0.90)
        es_95 = self.engine.compute_expected_shortfall(rets, confidence_level=0.95)
        es_99 = self.engine.compute_expected_shortfall(rets, confidence_level=0.99)

        assert es_99.expected_shortfall >= es_95.expected_shortfall >= es_90.expected_shortfall

    def test_invalid_confidence_levels_rejected(self) -> None:
        rets = [-0.02, 0.01, 0.03, -0.01]
        with pytest.raises(InvalidConfidenceLevelError):
            self.engine.compute_var(rets, confidence_level=0.0)
        with pytest.raises(InvalidConfidenceLevelError):
            self.engine.compute_var(rets, confidence_level=1.0)
        with pytest.raises(InvalidConfidenceLevelError):
            self.engine.compute_var(rets, confidence_level=-0.5)
        with pytest.raises(InvalidConfidenceLevelError):
            self.engine.compute_var(rets, confidence_level=1.5)
        with pytest.raises(InvalidConfidenceLevelError):
            self.engine.compute_var(rets, confidence_level=float("nan"))

    def test_insufficient_data_for_var_rejected(self) -> None:
        with pytest.raises(InsufficientRiskDataError):
            self.engine.compute_var([-0.05], confidence_level=0.95)
        with pytest.raises(InsufficientRiskDataError):
            self.engine.compute_expected_shortfall([-0.05], confidence_level=0.95)

    def test_var_positive_returns_scenario(self) -> None:
        # If all returns are positive (+0.01 to +0.05), the 5th percentile is still positive
        # In this case, var_loss is negative (meaning even worst-case tail is a gain)
        rets = [0.01, 0.02, 0.03, 0.04, 0.05] * 10
        var = self.engine.compute_var(rets, confidence_level=0.95)
        assert var.return_quantile > 0.0
        assert var.var_loss < 0.0
