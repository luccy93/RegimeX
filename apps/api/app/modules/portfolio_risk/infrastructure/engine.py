"""
RegimeX Portfolio Risk — Analytics Engine
=========================================
Production-grade implementation of the portfolio risk calculation engine.

Guarantees:
- Zero external ML dependencies (pure Python standard library and NumPy).
- Strict validation: prices > 0, timezone-aware UTC timestamps, finite numericals.
- Zero future lookahead bias in running peaks, drawdowns, and returns.
- Sample standard deviation (ddof=1) with Bessel's correction.
- Explicit loss-oriented VaR and CVaR / Expected Shortfall conventions.
- Multi-asset timestamp alignment without artificial forward-filling or imputation.
- Deterministic quantile calculations using linear interpolation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np

from app.modules.portfolio_risk.domain.errors import (
    InsufficientRiskDataError,
    InsufficientTailObservationsError,
    InvalidConfidenceLevelError,
    InvalidPriceSeriesError,
    InvalidReturnSeriesError,
    MismatchedAssetAlignmentError,
    MismatchedWeightsError,
    NonFiniteValueError,
    TemporalOrderError,
)
from app.modules.portfolio_risk.domain.interfaces import (
    PortfolioRiskEngineProtocol,
)
from app.modules.portfolio_risk.domain.models import (
    DownsideRiskMetrics,
    DrawdownMetrics,
    ExpectedShortfallMetrics,
    PortfolioRiskResult,
    PortfolioWeights,
    PriceSeries,
    ReturnSeries,
    ReturnStatistics,
    VaRMetrics,
    VolatilityMetrics,
)


class PortfolioRiskEngine(PortfolioRiskEngineProtocol):
    """
    Core calculation engine for portfolio risk analytics.

    Implements foundational risk metrics adhering to V13 Commit 01 specifications.
    """

    def compute_arithmetic_returns(
        self,
        prices: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        symbol: str | None = None,
    ) -> ReturnSeries:
        """
        Calculate discrete arithmetic percentage returns r_t = P_t / P_{t-1} - 1.

        Args:
            prices: Chronological sequence of asset prices.
            timestamps: Optional corresponding timestamps (length must match prices).
            symbol: Optional instrument identifier.

        Returns:
            Validated ReturnSeries of length len(prices) - 1.
        """
        self._validate_raw_prices(prices)

        n = len(prices)
        if n < 2:
            raise InsufficientRiskDataError(
                required_samples=2,
                available_samples=n,
                details={"reason": "Arithmetic returns require at least 2 price observations."},
            )

        validated_ts = self._resolve_timestamps(timestamps, n)

        # Vectorized return calculation
        p_arr = np.asarray(prices, dtype=np.float64)
        prev_p = p_arr[:-1]
        curr_p = p_arr[1:]
        rets = (curr_p - prev_p) / prev_p

        # Return timestamps start from index 1
        ret_timestamps = tuple(validated_ts[1:])
        ret_values = tuple(float(r) for r in rets)

        return ReturnSeries(
            timestamps=ret_timestamps,
            values=ret_values,
            symbol=symbol,
        )

    def compute_log_returns(
        self,
        prices: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        symbol: str | None = None,
    ) -> ReturnSeries:
        """
        Calculate continuously compounded log returns r_t = ln(P_t / P_{t-1}).

        Args:
            prices: Chronological sequence of strictly positive asset prices.
            timestamps: Optional corresponding timestamps.
            symbol: Optional instrument identifier.

        Returns:
            Validated ReturnSeries of length len(prices) - 1.
        """
        self._validate_raw_prices(prices)

        n = len(prices)
        if n < 2:
            raise InsufficientRiskDataError(
                required_samples=2,
                available_samples=n,
                details={"reason": "Log returns require at least 2 price observations."},
            )

        validated_ts = self._resolve_timestamps(timestamps, n)

        p_arr = np.asarray(prices, dtype=np.float64)
        prev_p = p_arr[:-1]
        curr_p = p_arr[1:]
        rets = np.log(curr_p / prev_p)

        ret_timestamps = tuple(validated_ts[1:])
        ret_values = tuple(float(r) for r in rets)

        return ReturnSeries(
            timestamps=ret_timestamps,
            values=ret_values,
            symbol=symbol,
        )

    def compute_statistics(
        self,
        returns: ReturnSeries | Sequence[float],
    ) -> ReturnStatistics:
        """
        Calculate descriptive summary statistics of returns.

        Uses sample standard deviation with Bessel's correction (ddof=1).
        Requires at least 2 returns.
        """
        rets_tuple, _ = self._extract_returns_and_timestamps(returns)
        n = len(rets_tuple)
        if n < 2:
            raise InsufficientRiskDataError(
                required_samples=2,
                available_samples=n,
                details={"reason": "Return statistics require at least 2 return observations."},
            )

        arr = np.asarray(rets_tuple, dtype=np.float64)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        std_val = float(np.std(arr, ddof=1))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))

        return ReturnStatistics(
            mean_return=mean_val,
            median_return=median_val,
            standard_deviation=max(0.0, std_val),
            minimum_return=min_val,
            maximum_return=max_val,
            observation_count=n,
        )

    def compute_volatility(
        self,
        returns: ReturnSeries | Sequence[float],
        periods_per_year: float | None = None,
    ) -> VolatilityMetrics:
        """
        Calculate realized period and annualized volatility.

        Args:
            returns: Return series or sequence of returns.
            periods_per_year: Explicit annualization factor (e.g. 252 for daily US equities).
                             Never hardcoded.
        """
        rets_tuple, _ = self._extract_returns_and_timestamps(returns)
        n = len(rets_tuple)
        if n < 2:
            raise InsufficientRiskDataError(
                required_samples=2,
                available_samples=n,
                details={"reason": "Volatility requires at least 2 return observations."},
            )

        arr = np.asarray(rets_tuple, dtype=np.float64)
        period_vol = float(np.std(arr, ddof=1))

        ann_vol: float | None = None
        if periods_per_year is not None:
            if (
                periods_per_year <= 0.0
                or math.isnan(periods_per_year)
                or math.isinf(periods_per_year)
            ):
                raise ValueError(
                    f"periods_per_year must be a finite positive number (got {periods_per_year})."
                )
            ann_vol = period_vol * math.sqrt(periods_per_year)

        return VolatilityMetrics(
            period_volatility=max(0.0, period_vol),
            annualized_volatility=ann_vol,
            periods_per_year=periods_per_year,
        )

    def compute_downside_risk(
        self,
        returns: ReturnSeries | Sequence[float],
        target_return: float = 0.0,
    ) -> DownsideRiskMetrics:
        """
        Calculate downside deviation below a target return threshold.

        Formula:
            downside_t = min(r_t - target_return, 0)
            downside_deviation = sqrt( (1 / N) * sum(downside_t^2) )
        """
        if math.isnan(target_return) or math.isinf(target_return):
            raise NonFiniteValueError(f"target_return must be finite (got {target_return}).")

        rets_tuple, _ = self._extract_returns_and_timestamps(returns)
        n = len(rets_tuple)
        if n < 1:
            raise InsufficientRiskDataError(
                required_samples=1,
                available_samples=0,
                details={"reason": "Downside risk requires at least 1 return observation."},
            )

        arr = np.asarray(rets_tuple, dtype=np.float64)
        diffs = arr - target_return
        neg_devs = np.minimum(diffs, 0.0)
        squared_devs = np.square(neg_devs)
        mean_squared_dev = float(np.mean(squared_devs))
        downside_dev = math.sqrt(max(0.0, mean_squared_dev))
        below_count = int(np.sum(arr < target_return))

        return DownsideRiskMetrics(
            target_return=target_return,
            downside_deviation=downside_dev,
            observations_below_target=below_count,
            total_observations=n,
        )

    def compute_drawdown_from_returns(
        self,
        returns: ReturnSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> DrawdownMetrics:
        """
        Calculate peak-to-trough drawdown from an equity curve initialized at 1.0.

        Guarantees:
        - Strictly historical running peak (zero lookahead).
        - Explicit peak, trough, and recovery timestamps if timestamps are supplied.
        """
        rets_tuple, ts_tuple = self._extract_returns_and_timestamps(returns, timestamps)
        n = len(rets_tuple)
        if n < 1:
            raise InsufficientRiskDataError(
                required_samples=1,
                available_samples=0,
                details={"reason": "Drawdown requires at least 1 return observation."},
            )

        # Validate returns not <= -1.0 (total loss / negative wealth)
        wealth = [1.0]
        current_w = 1.0
        for idx, r in enumerate(rets_tuple):
            if r < -1.0:
                raise InvalidReturnSeriesError(
                    f"Return at index {idx} ({r}) is less than -1.0 (-100% loss)."
                )
            current_w *= 1.0 + r
            wealth.append(current_w)

        # If timestamps are present, prepend a synthetic initial timestamp or map directly
        # Wealth array has length n + 1 (initial wealth at index 0, followed by n period ends)
        # We analyze drawdowns over the resulting wealth path
        return self._evaluate_drawdown(wealth=wealth, timestamps=ts_tuple)

    def compute_drawdown_from_prices(
        self,
        prices: PriceSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> DrawdownMetrics:
        """
        Calculate peak-to-trough drawdown directly from a price series.
        """
        if isinstance(prices, PriceSeries):
            p_tuple = prices.prices
            ts_tuple = prices.timestamps
        else:
            self._validate_raw_prices(prices)
            p_tuple = tuple(float(p) for p in prices)
            ts_tuple = tuple(self._resolve_timestamps(timestamps, len(prices)))

        n = len(p_tuple)
        if n < 1:
            raise InsufficientRiskDataError(
                required_samples=1,
                available_samples=0,
                details={"reason": "Drawdown requires at least 1 price observation."},
            )

        wealth = list(p_tuple)
        return self._evaluate_drawdown(wealth=wealth, timestamps=ts_tuple, is_price=True)

    def compute_var(
        self,
        returns: ReturnSeries | Sequence[float],
        confidence_level: float = 0.95,
    ) -> VaRMetrics:
        """
        Calculate historical Value at Risk at confidence_level.

        Sign convention:
        - Loss-oriented: var_loss = -return_quantile.
        - Positive value indicates a loss.
        """
        self._validate_confidence_level(confidence_level)

        rets_tuple, _ = self._extract_returns_and_timestamps(returns)
        n = len(rets_tuple)
        if n < 2:
            raise InsufficientRiskDataError(
                required_samples=2,
                available_samples=n,
                details={"reason": "VaR computation requires at least 2 return observations."},
            )

        # Expected tail probability
        p_tail = 1.0 - confidence_level
        arr = np.asarray(rets_tuple, dtype=np.float64)

        # Empirical quantile using deterministic linear interpolation
        quantile_val = float(np.quantile(arr, p_tail, method="linear"))
        var_loss_val = -quantile_val

        # Count observations in tail (<= quantile within tolerance)
        tail_count = int(np.sum(arr <= quantile_val + 1e-12))
        if tail_count < 1:
            raise InsufficientTailObservationsError(
                confidence_level=confidence_level,
                required_samples=1,
                available_samples=tail_count,
            )

        return VaRMetrics(
            confidence_level=confidence_level,
            var_loss=var_loss_val,
            return_quantile=quantile_val,
            method="historical",
            tail_observations=tail_count,
            total_observations=n,
        )

    def compute_expected_shortfall(
        self,
        returns: ReturnSeries | Sequence[float],
        confidence_level: float = 0.95,
    ) -> ExpectedShortfallMetrics:
        """
        Calculate historical Expected Shortfall / CVaR beyond VaR threshold.

        Sign convention:
        - Loss-oriented: expected_shortfall = -tail_mean_return.
        - Guarantees expected_shortfall >= var_loss in loss space.
        """
        var_metric = self.compute_var(returns, confidence_level)

        rets_tuple, _ = self._extract_returns_and_timestamps(returns)
        n = len(rets_tuple)
        arr = np.asarray(rets_tuple, dtype=np.float64)

        q = var_metric.return_quantile
        tail_mask = arr <= q + 1e-12
        tail_vals = arr[tail_mask]
        tail_count = len(tail_vals)

        if tail_count < 1:
            raise InsufficientTailObservationsError(
                confidence_level=confidence_level,
                required_samples=1,
                available_samples=0,
            )

        tail_mean = float(np.mean(tail_vals))
        es_loss = -tail_mean

        # Consistency guard against floating point discrepancies
        if es_loss < var_metric.var_loss:
            es_loss = var_metric.var_loss

        return ExpectedShortfallMetrics(
            confidence_level=confidence_level,
            expected_shortfall=es_loss,
            tail_mean_return=-es_loss,
            var_loss=var_metric.var_loss,
            tail_observations=tail_count,
            total_observations=n,
        )

    def compute_portfolio_returns(
        self,
        asset_returns: dict[str, ReturnSeries],
        weights: PortfolioWeights,
    ) -> ReturnSeries:
        """
        Calculate timestamp-aligned multi-asset weighted portfolio returns.

        Guarantees:
        - Every asset symbol in weights must be present in asset_returns.
        - Timestamps across all assets must align identically.
        - No forward-filling or arbitrary imputation.
        """
        if len(asset_returns) == 0:
            raise InsufficientRiskDataError(
                required_samples=1,
                available_samples=0,
                details={"reason": "Asset returns dictionary cannot be empty."},
            )

        # Validate all symbols present
        for sym in weights.symbols:
            if sym not in asset_returns:
                raise MismatchedWeightsError(
                    f"Asset symbol {sym!r} defined in weights is missing from asset_returns: "
                    f"{list(asset_returns.keys())}."
                )

        # Validate timestamp alignment
        first_sym = weights.symbols[0]
        reference_ts = asset_returns[first_sym].timestamps
        n_obs = len(reference_ts)

        for sym in weights.symbols:
            series = asset_returns[sym]
            if len(series.timestamps) != n_obs or series.timestamps != reference_ts:
                raise MismatchedAssetAlignmentError(
                    f"Asset {sym!r} timestamps do not align with reference asset {first_sym!r}. "
                    f"RegimeX strictly prohibits forward-filling or fake zero returns."
                )

        # Compute weighted return vector
        portfolio_rets = np.zeros(n_obs, dtype=np.float64)
        for sym, weight in zip(weights.symbols, weights.weights, strict=True):
            vals = np.asarray(asset_returns[sym].values, dtype=np.float64)
            portfolio_rets += weight * vals

        return ReturnSeries(
            timestamps=reference_ts,
            values=tuple(float(r) for r in portfolio_rets),
            symbol="portfolio",
        )

    def analyze_risk(
        self,
        data: ReturnSeries | PriceSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        is_price_series: bool = False,
        periods_per_year: float | None = None,
        target_return: float = 0.0,
        var_confidences: Sequence[float] = (0.90, 0.95, 0.99),
        series_id: str = "portfolio",
    ) -> PortfolioRiskResult:
        """
        Run the comprehensive portfolio risk analytics pipeline.
        """
        # 1. Obtain ReturnSeries and evaluate Drawdown
        drawdown_metric: DrawdownMetrics
        ret_series: ReturnSeries

        if isinstance(data, PriceSeries):
            ret_series = self.compute_arithmetic_returns(
                prices=data.prices,
                timestamps=data.timestamps,
                symbol=data.symbol or series_id,
            )
            drawdown_metric = self.compute_drawdown_from_prices(data)
        elif is_price_series and isinstance(data, Sequence):
            p_tuple = tuple(float(p) for p in data)
            ret_series = self.compute_arithmetic_returns(
                prices=p_tuple,
                timestamps=timestamps,
                symbol=series_id,
            )
            drawdown_metric = self.compute_drawdown_from_prices(p_tuple, timestamps)
        elif isinstance(data, ReturnSeries):
            ret_series = data
            drawdown_metric = self.compute_drawdown_from_returns(ret_series)
        elif isinstance(data, Sequence):
            rets_tuple = tuple(float(r) for r in data)
            ret_ts = self._resolve_timestamps(timestamps, len(rets_tuple))
            ret_series = ReturnSeries(
                timestamps=tuple(ret_ts),
                values=rets_tuple,
                symbol=series_id,
            )
            drawdown_metric = self.compute_drawdown_from_returns(ret_series)
        else:
            raise InvalidReturnSeriesError(f"Unsupported input data type: {type(data)}.")

        # 2. Return statistics
        stats = self.compute_statistics(ret_series)

        # 3. Volatility
        vol = self.compute_volatility(ret_series, periods_per_year=periods_per_year)

        # 4. Downside risk
        downside = self.compute_downside_risk(ret_series, target_return=target_return)

        # 5. VaR & Expected Shortfall at requested confidence levels
        var_dict: dict[float, VaRMetrics] = {}
        es_dict: dict[float, ExpectedShortfallMetrics] = {}

        for conf in var_confidences:
            var_dict[conf] = self.compute_var(ret_series, confidence_level=conf)
            es_dict[conf] = self.compute_expected_shortfall(ret_series, confidence_level=conf)

        start_ts = ret_series.timestamps[0] if ret_series.timestamps else None
        end_ts = ret_series.timestamps[-1] if ret_series.timestamps else None

        return PortfolioRiskResult(
            series_id=series_id,
            return_statistics=stats,
            volatility=vol,
            downside_risk=downside,
            drawdown=drawdown_metric,
            var_metrics=var_dict,
            expected_shortfall_metrics=es_dict,
            observation_count=len(ret_series),
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            computed_at=datetime.now(tz=UTC),
        )

    # =========================================================================
    # Internal Validation & Helper Methods
    # =========================================================================

    def _validate_raw_prices(self, prices: Sequence[float]) -> None:
        """Ensure prices are non-empty, finite, and strictly positive."""
        if len(prices) == 0:
            raise InvalidPriceSeriesError("Price series cannot be empty.")
        for idx, p in enumerate(prices):
            if math.isnan(p) or math.isinf(p):
                raise NonFiniteValueError(f"Price at index {idx} is non-finite: {p}.")
            if p <= 0.0:
                raise InvalidPriceSeriesError(
                    f"Price at index {idx} must be strictly positive (got {p})."
                )

    def _validate_confidence_level(self, confidence_level: float) -> None:
        """Validate confidence level is strictly between 0 and 1."""
        if math.isnan(confidence_level) or math.isinf(confidence_level):
            raise InvalidConfidenceLevelError(
                f"confidence_level must be finite (got {confidence_level})."
            )
        if not (0.0 < confidence_level < 1.0):
            raise InvalidConfidenceLevelError(
                f"confidence_level must be in open interval (0, 1) (got {confidence_level})."
            )

    def _resolve_timestamps(
        self,
        timestamps: Sequence[datetime] | None,
        expected_length: int,
    ) -> list[datetime]:
        """Validate or generate timezone-aware UTC timestamps."""
        if timestamps is not None:
            if len(timestamps) != expected_length:
                raise TemporalOrderError(
                    f"Timestamps length ({len(timestamps)}) != prices length ({expected_length})."
                )
            prev_ts: datetime | None = None
            out_ts: list[datetime] = []
            for idx, ts in enumerate(timestamps):
                if ts.tzinfo is None:
                    raise TemporalOrderError(
                        f"Timestamp at index {idx} must be timezone-aware (got naive: {ts!r})."
                    )
                if prev_ts is not None and ts <= prev_ts:
                    raise TemporalOrderError(
                        f"Timestamps must be strictly increasing: "
                        f"ts[{idx}] ({ts.isoformat()}) <= ts[{idx - 1}] ({prev_ts.isoformat()})."
                    )
                prev_ts = ts
                out_ts.append(ts)
            return out_ts

        # Fallback synthetic chronological UTC timestamps
        base = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
        return [base + timedelta(days=i) for i in range(expected_length)]

    def _extract_returns_and_timestamps(
        self,
        returns: ReturnSeries | Sequence[float],
        timestamps: Sequence[datetime] | None = None,
    ) -> tuple[tuple[float, ...], tuple[datetime, ...] | None]:
        """Extract validated return values and timestamps from ReturnSeries or sequence."""
        if isinstance(returns, ReturnSeries):
            return returns.values, returns.timestamps

        # Validate sequence
        if len(returns) == 0:
            raise InsufficientRiskDataError(
                required_samples=1,
                available_samples=0,
                details={"reason": "Return sequence cannot be empty."},
            )

        validated_rets: list[float] = []
        for idx, r in enumerate(returns):
            if math.isnan(r) or math.isinf(r):
                raise NonFiniteValueError(f"Return at index {idx} is non-finite: {r}.")
            validated_rets.append(float(r))

        ts_tuple: tuple[datetime, ...] | None = None
        if timestamps is not None:
            resolved = self._resolve_timestamps(timestamps, len(returns))
            ts_tuple = tuple(resolved)

        return tuple(validated_rets), ts_tuple

    def _evaluate_drawdown(
        self,
        wealth: Sequence[float],
        timestamps: Sequence[datetime] | None = None,
        is_price: bool = False,
    ) -> DrawdownMetrics:
        """
        Evaluate peak-to-trough drawdown dynamics from a wealth or price path.
        """
        n = len(wealth)
        w_arr = np.asarray(wealth, dtype=np.float64)

        # Running peak (zero lookahead)
        running_max = np.maximum.accumulate(w_arr)
        drawdowns = (w_arr - running_max) / running_max

        # Find trough of maximum drawdown
        trough_idx = int(np.argmin(drawdowns))
        max_dd = float(drawdowns[trough_idx])
        dd_magnitude = abs(max_dd)

        # If zero drawdown throughout (monotonically non-decreasing)
        if max_dd >= 0.0:
            peak_idx = 0
            peak_val = float(w_arr[0])
            trough_val = float(w_arr[0])
            peak_ts = timestamps[0] if timestamps else None
            trough_ts = timestamps[0] if timestamps else None
            return DrawdownMetrics(
                max_drawdown=0.0,
                drawdown_magnitude=0.0,
                peak_value=peak_val,
                trough_value=trough_val,
                peak_timestamp=peak_ts,
                trough_timestamp=trough_ts,
                recovery_timestamp=peak_ts,
                is_recovered=True,
            )

        # Find peak corresponding to this trough: maximum wealth at or before trough_idx
        peak_idx = int(np.argmax(w_arr[: trough_idx + 1]))
        peak_val = float(w_arr[peak_idx])
        trough_val = float(w_arr[trough_idx])

        # Check for recovery: earliest index after trough where wealth >= peak_val
        is_rec = False
        rec_idx: int | None = None
        for idx in range(trough_idx + 1, n):
            if w_arr[idx] >= peak_val:
                is_rec = True
                rec_idx = idx
                break

        # Map timestamps
        peak_ts = None
        trough_ts = None
        rec_ts = None

        if timestamps is not None:
            # When from returns: wealth has length len(returns) + 1
            # If timestamps length equals len(wealth) - 1, map wealth[1:] to timestamps
            if len(timestamps) == n:
                peak_ts = timestamps[peak_idx]
                trough_ts = timestamps[trough_idx]
                rec_ts = timestamps[rec_idx] if rec_idx is not None else None
            elif len(timestamps) == n - 1:
                # wealth[0] is baseline 1.0 (before period 0)
                # wealth[k] corresponds to timestamps[k-1] for k >= 1
                peak_ts = timestamps[max(0, peak_idx - 1)] if peak_idx > 0 else timestamps[0]
                trough_ts = timestamps[trough_idx - 1]
                rec_ts = timestamps[rec_idx - 1] if rec_idx is not None else None

        return DrawdownMetrics(
            max_drawdown=max_dd,
            drawdown_magnitude=dd_magnitude,
            peak_value=peak_val,
            trough_value=trough_val,
            peak_timestamp=peak_ts,
            trough_timestamp=trough_ts,
            recovery_timestamp=rec_ts,
            is_recovered=is_rec,
        )
