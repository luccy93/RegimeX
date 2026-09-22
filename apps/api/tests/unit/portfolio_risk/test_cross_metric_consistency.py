"""
RegimeX Portfolio Risk — Cross-Metric Consistency Tests
=======================================================
Verifies cross-metric relationships and mathematical invariants:
- ES_alpha >= VaR_alpha across all distributions (symmetric, heavy-tailed, skewed).
- Sign conventions: var_loss = -return_quantile and expected_shortfall = -tail_mean_return.
- Monotonic confidence level ordering: VaR_0.99 >= VaR_0.95 >= VaR_0.90.
- Monotonic ES ordering: ES_0.99 >= ES_0.95 >= ES_0.90.
- Tail observation consistency between VaR and Expected Shortfall.
"""

from __future__ import annotations

import numpy as np
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


class TestCrossMetricConsistency:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_es_greater_or_equal_var_gaussian_distribution(self) -> None:
        np.random.seed(101)
        rets = list(np.random.normal(0.0005, 0.015, size=500))

        for conf in [0.90, 0.95, 0.99]:
            var = self.engine.compute_var(rets, confidence_level=conf)
            es = self.engine.compute_expected_shortfall(rets, confidence_level=conf)

            # In loss space, ES >= VaR
            assert es.expected_shortfall >= var.var_loss - 1e-12
            assert var.var_loss == -var.return_quantile
            assert es.expected_shortfall == -es.tail_mean_return
            assert es.tail_observations >= 1

    def test_es_greater_or_equal_var_heavy_tail_distribution(self) -> None:
        np.random.seed(202)
        # Student-t distribution with df=3 has very heavy tails
        rets = list(np.random.standard_t(df=3, size=1000) * 0.02)

        for conf in [0.90, 0.95, 0.99]:
            var = self.engine.compute_var(rets, confidence_level=conf)
            es = self.engine.compute_expected_shortfall(rets, confidence_level=conf)

            assert es.expected_shortfall >= var.var_loss
            assert es.var_loss == var.var_loss

    def test_es_greater_or_equal_var_all_negative_returns(self) -> None:
        rets = [-0.10, -0.08, -0.06, -0.05, -0.04, -0.03, -0.02, -0.01] * 10
        var = self.engine.compute_var(rets, confidence_level=0.95)
        es = self.engine.compute_expected_shortfall(rets, confidence_level=0.95)

        assert var.var_loss > 0.0
        assert es.expected_shortfall >= var.var_loss

    def test_es_greater_or_equal_var_small_sample(self) -> None:
        # Small sample of 10 observations
        rets = [-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05]
        var = self.engine.compute_var(rets, confidence_level=0.90)
        es = self.engine.compute_expected_shortfall(rets, confidence_level=0.90)

        assert es.expected_shortfall >= var.var_loss

    def test_monotonic_confidence_ordering(self) -> None:
        np.random.seed(303)
        rets = list(np.random.normal(0.001, 0.02, size=300))

        v90 = self.engine.compute_var(rets, 0.90).var_loss
        v95 = self.engine.compute_var(rets, 0.95).var_loss
        v99 = self.engine.compute_var(rets, 0.99).var_loss

        assert v99 >= v95 >= v90

        es90 = self.engine.compute_expected_shortfall(rets, 0.90).expected_shortfall
        es95 = self.engine.compute_expected_shortfall(rets, 0.95).expected_shortfall
        es99 = self.engine.compute_expected_shortfall(rets, 0.99).expected_shortfall

        assert es99 >= es95 >= es90

    def test_identical_tail_quantile_usage(self) -> None:
        rets = [-0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04] * 5
        var = self.engine.compute_var(rets, confidence_level=0.95)
        es = self.engine.compute_expected_shortfall(rets, confidence_level=0.95)

        assert es.var_loss == var.var_loss
