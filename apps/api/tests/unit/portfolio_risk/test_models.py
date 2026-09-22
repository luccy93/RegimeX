"""
RegimeX Portfolio Risk — Domain Models Unit Tests
=================================================
Tests domain model validation invariants, immutability, and boundary rules.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.portfolio_risk.domain.models import (
    DownsideRiskMetrics,
    DrawdownMetrics,
    ExpectedShortfallMetrics,
    PortfolioWeights,
    PriceSeries,
    ReturnObservation,
    ReturnSeries,
    ReturnStatistics,
    VaRMetrics,
    VolatilityMetrics,
)
from pydantic import ValidationError


def _ts(offset_days: int) -> datetime:
    return datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=offset_days)


class TestReturnObservation:
    def test_valid_observation(self) -> None:
        obs = ReturnObservation(timestamp=_ts(0), return_value=0.015)
        assert obs.return_value == 0.015
        assert obs.timestamp == _ts(0)

    def test_naive_timestamp_rejected(self) -> None:
        naive = datetime(2025, 1, 1)
        with pytest.raises(ValidationError):
            ReturnObservation(timestamp=naive, return_value=0.01)

    def test_non_finite_return_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnObservation(timestamp=_ts(0), return_value=float("nan"))
        with pytest.raises(ValidationError):
            ReturnObservation(timestamp=_ts(0), return_value=float("inf"))


class TestReturnSeries:
    def test_valid_return_series(self) -> None:
        series = ReturnSeries(
            timestamps=(_ts(0), _ts(1), _ts(2)),
            values=(0.01, -0.02, 0.015),
            symbol="AAPL",
        )
        assert series.length == 3
        assert len(series) == 3
        assert series[1] == -0.02
        assert series.symbol == "AAPL"

    def test_mismatched_lengths_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnSeries(timestamps=(_ts(0), _ts(1)), values=(0.01,))

    def test_empty_series_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnSeries(timestamps=(), values=())

    def test_non_finite_in_series_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnSeries(timestamps=(_ts(0), _ts(1)), values=(0.01, float("nan")))

    def test_unsorted_timestamps_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnSeries(timestamps=(_ts(1), _ts(0)), values=(0.01, 0.02))

    def test_duplicate_timestamps_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnSeries(timestamps=(_ts(0), _ts(0)), values=(0.01, 0.02))


class TestPriceSeries:
    def test_valid_price_series(self) -> None:
        series = PriceSeries(
            timestamps=(_ts(0), _ts(1), _ts(2)),
            prices=(100.0, 102.5, 101.0),
            symbol="SPY",
        )
        assert series.length == 3
        assert series[0] == 100.0

    def test_non_positive_price_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PriceSeries(timestamps=(_ts(0), _ts(1)), prices=(100.0, 0.0))
        with pytest.raises(ValidationError):
            PriceSeries(timestamps=(_ts(0), _ts(1)), prices=(100.0, -5.0))


class TestReturnStatistics:
    def test_valid_statistics(self) -> None:
        stats = ReturnStatistics(
            mean_return=0.005,
            median_return=0.004,
            standard_deviation=0.015,
            minimum_return=-0.03,
            maximum_return=0.04,
            observation_count=100,
        )
        assert stats.mean_return == 0.005
        assert stats.observation_count == 100

    def test_invalid_extrema_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReturnStatistics(
                mean_return=0.005,
                median_return=0.004,
                standard_deviation=0.015,
                minimum_return=0.05,  # min > max
                maximum_return=0.04,
                observation_count=100,
            )


class TestVolatilityMetrics:
    def test_period_volatility_only(self) -> None:
        vol = VolatilityMetrics(period_volatility=0.012)
        assert vol.period_volatility == 0.012
        assert vol.annualized_volatility is None
        assert vol.periods_per_year is None

    def test_annualized_volatility_validation(self) -> None:
        vol = VolatilityMetrics(
            period_volatility=0.01,
            annualized_volatility=0.1587,
            periods_per_year=252.0,
        )
        assert vol.annualized_volatility == 0.1587

    def test_inconsistent_annualization_parameters_rejected(self) -> None:
        # periods_per_year provided without annualized_volatility
        with pytest.raises(ValidationError):
            VolatilityMetrics(period_volatility=0.01, periods_per_year=252.0)
        # annualized_volatility provided without periods_per_year
        with pytest.raises(ValidationError):
            VolatilityMetrics(period_volatility=0.01, annualized_volatility=0.15)


class TestDownsideRiskMetrics:
    def test_valid_downside_metrics(self) -> None:
        d = DownsideRiskMetrics(
            target_return=0.0,
            downside_deviation=0.015,
            observations_below_target=10,
            total_observations=50,
        )
        assert d.downside_deviation == 0.015
        assert d.observations_below_target == 10

    def test_below_target_exceeding_total_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DownsideRiskMetrics(
                target_return=0.0,
                downside_deviation=0.015,
                observations_below_target=60,
                total_observations=50,
            )


class TestDrawdownMetrics:
    def test_valid_drawdown_metrics(self) -> None:
        dd = DrawdownMetrics(
            max_drawdown=-0.20,
            drawdown_magnitude=0.20,
            peak_value=120.0,
            trough_value=96.0,
            peak_timestamp=_ts(1),
            trough_timestamp=_ts(5),
            recovery_timestamp=_ts(10),
            is_recovered=True,
        )
        assert dd.max_drawdown == -0.20
        assert dd.drawdown_magnitude == 0.20
        assert dd.is_recovered is True

    def test_magnitude_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DrawdownMetrics(
                max_drawdown=-0.20,
                drawdown_magnitude=0.25,  # Mismatch
                peak_value=120.0,
                trough_value=96.0,
            )

    def test_trough_greater_than_peak_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DrawdownMetrics(
                max_drawdown=0.0,
                drawdown_magnitude=0.0,
                peak_value=100.0,
                trough_value=105.0,  # trough > peak
            )


class TestVaRAndESMetrics:
    def test_valid_var_metrics(self) -> None:
        var = VaRMetrics(
            confidence_level=0.95,
            var_loss=0.032,
            return_quantile=-0.032,
            tail_observations=5,
            total_observations=100,
        )
        assert var.var_loss == 0.032
        assert var.return_quantile == -0.032

    def test_var_loss_sign_inconsistency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            VaRMetrics(
                confidence_level=0.95,
                var_loss=0.032,
                return_quantile=-0.040,  # Mismatched sign/magnitude
                tail_observations=5,
                total_observations=100,
            )

    def test_valid_expected_shortfall(self) -> None:
        es = ExpectedShortfallMetrics(
            confidence_level=0.95,
            expected_shortfall=0.045,
            tail_mean_return=-0.045,
            var_loss=0.035,
            tail_observations=5,
            total_observations=100,
        )
        assert es.expected_shortfall == 0.045
        assert es.expected_shortfall >= es.var_loss

    def test_es_loss_less_than_var_loss_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExpectedShortfallMetrics(
                confidence_level=0.95,
                expected_shortfall=0.025,  # Less than var_loss
                tail_mean_return=-0.025,
                var_loss=0.035,
                tail_observations=5,
                total_observations=100,
            )


class TestPortfolioWeights:
    def test_valid_weights(self) -> None:
        pw = PortfolioWeights(
            symbols=("AAPL", "MSFT", "GOOG"),
            weights=(0.5, 0.3, 0.2),
            is_normalized=True,
        )
        assert pw.asset_count == 3
        assert pw.get_weight("MSFT") == 0.3

    def test_weights_sum_not_one_rejected_when_normalized(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioWeights(
                symbols=("AAPL", "MSFT"),
                weights=(0.5, 0.4),  # sum=0.9
                is_normalized=True,
            )

    def test_unnormalized_weights_allowed_when_flag_false(self) -> None:
        pw = PortfolioWeights(
            symbols=("AAPL", "MSFT"),
            weights=(1.0, 1.0),
            is_normalized=False,
        )
        assert pw.get_weight("AAPL") == 1.0
