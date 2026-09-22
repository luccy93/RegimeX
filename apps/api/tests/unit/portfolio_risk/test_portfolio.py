"""
RegimeX Portfolio Risk — Multi-Asset Portfolio Returns Unit Tests
================================================================
Tests multi-asset portfolio return aggregation, weights validation, and timestamp alignment.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.portfolio_risk.domain.errors import (
    MismatchedAssetAlignmentError,
    MismatchedWeightsError,
)
from app.modules.portfolio_risk.domain.models import PortfolioWeights, ReturnSeries
from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestPortfolioReturns:
    def setup_method(self) -> None:
        self.engine = PortfolioRiskEngine()

    def test_single_asset_portfolio(self) -> None:
        ts = (_ts(0), _ts(1), _ts(2))
        s_a = ReturnSeries(timestamps=ts, values=(0.01, -0.02, 0.03), symbol="SPY")
        weights = PortfolioWeights(symbols=("SPY",), weights=(1.0,))

        port = self.engine.compute_portfolio_returns({"SPY": s_a}, weights)
        assert len(port) == 3
        assert port.values == (0.01, -0.02, 0.03)

    def test_two_asset_equal_weights(self) -> None:
        ts = (_ts(0), _ts(1))
        # Asset A: 0.10, -0.10
        # Asset B: -0.05, 0.20
        # 50/50: 0.5*0.10 + 0.5*(-0.05) = 0.025
        #        0.5*(-0.10) + 0.5*(0.20) = 0.050
        s_a = ReturnSeries(timestamps=ts, values=(0.10, -0.10), symbol="A")
        s_b = ReturnSeries(timestamps=ts, values=(-0.05, 0.20), symbol="B")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.5, 0.5))

        port = self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)
        assert len(port) == 2
        assert abs(port[0] - 0.025) < 1e-12
        assert abs(port[1] - 0.050) < 1e-12

    def test_missing_asset_symbol_in_data_rejected(self) -> None:
        ts = (_ts(0), _ts(1))
        s_a = ReturnSeries(timestamps=ts, values=(0.10, -0.10), symbol="A")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.5, 0.5))

        with pytest.raises(MismatchedWeightsError):
            self.engine.compute_portfolio_returns({"A": s_a}, weights)

    def test_mismatched_asset_timestamps_rejected(self) -> None:
        # Asset A has timestamps at day 0 and day 1
        # Asset B has timestamps at day 0 and day 2
        s_a = ReturnSeries(timestamps=(_ts(0), _ts(1)), values=(0.01, 0.02), symbol="A")
        s_b = ReturnSeries(timestamps=(_ts(0), _ts(2)), values=(0.01, 0.02), symbol="B")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.5, 0.5))

        with pytest.raises(MismatchedAssetAlignmentError):
            self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)

    def test_mismatched_asset_lengths_rejected(self) -> None:
        s_a = ReturnSeries(timestamps=(_ts(0), _ts(1)), values=(0.01, 0.02), symbol="A")
        s_b = ReturnSeries(timestamps=(_ts(0),), values=(0.01,), symbol="B")
        weights = PortfolioWeights(symbols=("A", "B"), weights=(0.5, 0.5))

        with pytest.raises(MismatchedAssetAlignmentError):
            self.engine.compute_portfolio_returns({"A": s_a, "B": s_b}, weights)
