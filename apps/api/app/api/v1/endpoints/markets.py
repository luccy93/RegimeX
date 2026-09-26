"""
RegimeX API v1 — Market Intelligence Endpoints
==============================================
Read-oriented endpoints exposing market discovery and time-series data.

Endpoints:
  GET /api/v1/markets
  GET /api/v1/markets/{symbol}/data
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.v1.models import (
    BacktestRiskMetricsDTO,
    BacktestTradeDTO,
    CurrentRegimeContextDTO,
    DownsideRiskMetricsDTO,
    DrawdownMetricsDTO,
    EquitySnapshotDTO,
    ExpectedShortfallMetricsDTO,
    FeatureStatisticDTO,
    GlobalTransitionAnalyticsDTO,
    MarketBacktestResponse,
    MarketDataResponse,
    MarketItemResponse,
    MarketListResponse,
    MarketRegimeResponse,
    MarketRiskResponse,
    MarketTransitionResponse,
    MethodologyDTO,
    MetricDefinitionDTO,
    OHLCVBarResponse,
    PerformanceReportDTO,
    RankedDestinationDTO,
    RegimeProfileDTO,
    ReturnStatisticsDTO,
    RiskPricePointDTO,
    TradeStatisticsDTO,
    TransitionProbabilityDTO,
    TransitionRegimeAnalyticsDTO,
    VaRMetricsDTO,
    VolatilityMetricsDTO,
)
from app.core.dependencies import (
    BacktestingServiceDep,
    MarketIntelligenceDep,
    MarketServiceDep,
    PortfolioRiskServiceDep,
)
from app.core.errors import BadRequestError, ValidationError
from app.modules.backtesting.domain.models import (
    ExecutionPriceConvention,
    MarketEvent,
)
from app.modules.market_data.domain.models import AssetClass, DataInterval

router = APIRouter(prefix="/markets", tags=["Market Intelligence"])


@router.get(
    "",
    response_model=MarketListResponse,
    summary="List discoverable market instruments",
    description="Retrieve catalog of instruments, optionally filtered by asset class.",
)
async def list_markets(
    market_service: MarketServiceDep,
    asset_class: Annotated[
        str | None,
        Query(description="Optional asset class filter (e.g. 'equity_us', 'crypto', 'index')"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximum number of items")] = 100,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> MarketListResponse:
    """List supported market instruments."""
    parsed_asset_class: AssetClass | None = None
    if asset_class is not None:
        clean_ac = asset_class.strip().lower()
        try:
            parsed_asset_class = AssetClass(clean_ac)
        except ValueError as exc:
            raise ValidationError(
                f"Invalid asset_class {asset_class!r}. "
                f"Supported: {[ac.value for ac in AssetClass]}",
                details={"asset_class": asset_class},
            ) from exc

    instruments = await market_service.list_markets(asset_class=parsed_asset_class)
    items = [
        MarketItemResponse(
            symbol=inst.symbol,
            asset_class=inst.asset_class.value,
            exchange=inst.exchange,
            currency=inst.currency,
            description=inst.description,
        )
        for inst in instruments
    ]
    total_count = len(items)
    paginated_items = items[offset : offset + limit]
    return MarketListResponse(
        items=paginated_items,
        total=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{symbol}/data",
    response_model=MarketDataResponse,
    summary="Retrieve historical OHLCV market data",
    description=(
        "Retrieve time-series OHLCV bars for an instrument across a validated time window. "
        "Timestamps must be timezone-aware (UTC). Requires start < end."
    ),
)
async def get_market_data(
    symbol: Annotated[str, Path(min_length=1, max_length=50, description="Instrument symbol")],
    start: Annotated[datetime, Query(description="Start time (inclusive, UTC-aware)")],
    end: Annotated[datetime, Query(description="End time (exclusive, UTC-aware)")],
    market_service: MarketServiceDep,
    interval: Annotated[
        str,
        Query(description="Data aggregation interval (e.g. '1m', '5m', '1h', '1d', '1w')"),
    ] = "1d",
    limit: Annotated[
        int,
        Query(ge=1, le=5000, description="Maximum number of bars to return per request"),
    ] = 1000,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> MarketDataResponse:
    """Retrieve historical market data bars."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise BadRequestError("Instrument symbol cannot be empty or whitespace.")

    # Timezone awareness validation
    if start.tzinfo is None:
        raise ValidationError(
            f"Query start datetime must be timezone-aware UTC (got naive datetime: {start!r}).",
            details={"parameter": "start", "value": start.isoformat()},
        )
    if end.tzinfo is None:
        raise ValidationError(
            f"Query end datetime must be timezone-aware UTC (got naive datetime: {end!r}).",
            details={"parameter": "end", "value": end.isoformat()},
        )

    # Convert to UTC
    start_utc = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)

    if start_utc >= end_utc:
        raise ValidationError(
            f"Query end ({end_utc.isoformat()}) must be strictly after "
            f"start ({start_utc.isoformat()}).",
            details={"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        )

    # Interval validation
    try:
        parsed_interval = DataInterval(interval.strip().lower())
    except ValueError as exc:
        intervals = [i.value for i in DataInterval]
        raise ValidationError(
            f"Invalid interval {interval!r}. Supported intervals: {intervals}",
            details={"interval": interval},
        ) from exc

    records, total_count = await market_service.get_market_data(
        symbol=clean_symbol,
        start=start_utc,
        end=end_utc,
        interval=parsed_interval,
        limit=limit,
        offset=offset,
    )

    bar_items = [
        OHLCVBarResponse(
            timestamp=r.timestamp,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
        )
        for r in records
    ]

    return MarketDataResponse(
        symbol=clean_symbol,
        interval=parsed_interval.value,
        start=start_utc,
        end=end_utc,
        count=len(bar_items),
        total=total_count,
        items=bar_items,
    )


@router.get(
    "/{symbol}/regime",
    response_model=MarketRegimeResponse,
    summary="Retrieve current market regime and historical profile",
    description=(
        "Retrieve descriptive point-in-time regime intelligence for a tradeable symbol. "
        "Calculates current regime context, duration statistics, occurrence frequencies, "
        "and feature distributions using existing regime intelligence models."
    ),
)
async def get_market_regime(
    symbol: Annotated[str, Path(min_length=1, max_length=50, description="Instrument symbol")],
    market_intelligence: MarketIntelligenceDep,
    start: Annotated[
        datetime | None,
        Query(description="Start time (inclusive, UTC-aware)"),
    ] = None,
    end: Annotated[
        datetime | None,
        Query(description="End time (exclusive, UTC-aware)"),
    ] = None,
    interval: Annotated[
        str,
        Query(description="Data aggregation interval (e.g. '1d')"),
    ] = "1d",
    limit: Annotated[
        int,
        Query(ge=1, le=5000, description="Maximum number of bars to analyze"),
    ] = 1000,
) -> MarketRegimeResponse:
    """Retrieve current regime context and historical regime profiles."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise BadRequestError("Instrument symbol cannot be empty or whitespace.")

    # Timezone validation
    if start is not None and start.tzinfo is None:
        raise ValidationError(
            f"Query start datetime must be timezone-aware UTC (got naive datetime: {start!r}).",
            details={"parameter": "start", "value": start.isoformat()},
        )
    if end is not None and end.tzinfo is None:
        raise ValidationError(
            f"Query end datetime must be timezone-aware UTC (got naive datetime: {end!r}).",
            details={"parameter": "end", "value": end.isoformat()},
        )

    end_utc = end.astimezone(UTC) if end is not None else datetime.now(UTC)
    start_utc = start.astimezone(UTC) if start is not None else end_utc - timedelta(days=365)

    if start_utc >= end_utc:
        raise ValidationError(
            f"Query end ({end_utc.isoformat()}) must be strictly after "
            f"start ({start_utc.isoformat()}).",
            details={"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        )

    # Interval validation
    try:
        parsed_interval = DataInterval(interval.strip().lower())
    except ValueError as exc:
        intervals = [i.value for i in DataInterval]
        raise ValidationError(
            f"Invalid interval {interval!r}. Supported intervals: {intervals}",
            details={"interval": interval},
        ) from exc

    summary, confidence = await market_intelligence.get_market_regime(
        symbol=clean_symbol,
        start=start_utc,
        end=end_utc,
        interval=parsed_interval,
        limit=limit,
    )

    # Translate domain RegimeHistorySummary to API DTOs
    profiles_dto: dict[int, RegimeProfileDTO] = {}
    for r_id, p in summary.regime_profiles.items():
        stats_dto: dict[str, FeatureStatisticDTO] = {
            f_name: FeatureStatisticDTO(
                feature_name=f_stat.feature_name,
                observation_count=f_stat.observation_count,
                mean=f_stat.mean,
                median=f_stat.median,
                std=f_stat.std,
                min=f_stat.min,
                max=f_stat.max,
            )
            for f_name, f_stat in p.feature_statistics.items()
        }
        profiles_dto[r_id] = RegimeProfileDTO(
            regime_id=p.regime_id,
            regime_label=p.regime_label,
            observation_count=p.observation_count,
            frequency=p.frequency,
            percentage=p.percentage,
            first_seen=p.first_seen,
            last_seen=p.last_seen,
            run_count=p.run_count,
            average_duration=p.average_duration,
            median_duration=p.median_duration,
            min_duration=p.min_duration,
            max_duration=p.max_duration,
            feature_statistics=stats_dto,
        )

    if summary.current_regime is not None:
        cur = summary.current_regime
        current_context_dto = CurrentRegimeContextDTO(
            current_regime_id=cur.current_regime_id,
            current_regime_label=cur.current_regime_label,
            current_timestamp=cur.current_timestamp,
            observations_in_current_run=cur.observations_in_current_run,
            historical_frequency=cur.historical_frequency,
            historical_average_duration=cur.historical_average_duration,
            historical_max_duration=cur.historical_max_duration,
            historical_min_duration=cur.historical_min_duration,
            historical_run_count=cur.historical_run_count,
            current_features=cur.current_features,
        )
        current_regime_id = cur.current_regime_id
        current_regime_label = cur.current_regime_label
    else:
        current_regime_id = 0
        current_regime_label = "UNKNOWN"
        current_context_dto = CurrentRegimeContextDTO(
            current_regime_id=0,
            current_regime_label="UNKNOWN",
            current_timestamp=end_utc,
            observations_in_current_run=1,
            historical_frequency=0.0,
            historical_average_duration=0.0,
            historical_max_duration=0,
            historical_min_duration=0,
            historical_run_count=0,
            current_features=None,
        )

    active_profile_dto = profiles_dto.get(current_regime_id)
    active_statistics_dto = active_profile_dto.feature_statistics if active_profile_dto else {}

    return MarketRegimeResponse(
        symbol=clean_symbol,
        current_regime=current_regime_id,
        current_regime_label=current_regime_label,
        confidence=confidence,
        current_context=current_context_dto,
        profile=active_profile_dto,
        profiles=profiles_dto,
        statistics=active_statistics_dto,
        regimes_observed=list(summary.regimes_observed),
        total_observations=summary.total_observations,
        model_name=summary.model_name,
        model_version=summary.model_version,
        algorithm=summary.algorithm,
        analysis_start=summary.analysis_start,
        analysis_end=summary.analysis_end,
    )


@router.get(
    "/{symbol}/regime/transitions",
    response_model=MarketTransitionResponse,
    summary="Retrieve regime transition analytics and persistence metrics",
    description=(
        "Retrieve historical regime transition matrix, persistence probabilities, "
        "change rates, destination rankings, and transition entropy for a symbol."
    ),
)
async def get_regime_transitions(
    symbol: Annotated[str, Path(min_length=1, max_length=50, description="Instrument symbol")],
    market_intelligence: MarketIntelligenceDep,
    start: Annotated[
        datetime | None,
        Query(description="Start time (inclusive, UTC-aware)"),
    ] = None,
    end: Annotated[
        datetime | None,
        Query(description="End time (exclusive, UTC-aware)"),
    ] = None,
    interval: Annotated[
        str,
        Query(description="Data aggregation interval (e.g. '1d')"),
    ] = "1d",
    limit: Annotated[
        int,
        Query(ge=1, le=5000, description="Maximum number of bars to analyze"),
    ] = 1000,
) -> MarketTransitionResponse:
    """Retrieve empirical regime transition analytics."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise BadRequestError("Instrument symbol cannot be empty or whitespace.")

    # Timezone validation
    if start is not None and start.tzinfo is None:
        raise ValidationError(
            f"Query start datetime must be timezone-aware UTC (got naive datetime: {start!r}).",
            details={"parameter": "start", "value": start.isoformat()},
        )
    if end is not None and end.tzinfo is None:
        raise ValidationError(
            f"Query end datetime must be timezone-aware UTC (got naive datetime: {end!r}).",
            details={"parameter": "end", "value": end.isoformat()},
        )

    end_utc = end.astimezone(UTC) if end is not None else datetime.now(UTC)
    start_utc = start.astimezone(UTC) if start is not None else end_utc - timedelta(days=365)

    if start_utc >= end_utc:
        raise ValidationError(
            f"Query end ({end_utc.isoformat()}) must be strictly after "
            f"start ({start_utc.isoformat()}).",
            details={"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        )

    # Interval validation
    try:
        parsed_interval = DataInterval(interval.strip().lower())
    except ValueError as exc:
        intervals = [i.value for i in DataInterval]
        raise ValidationError(
            f"Invalid interval {interval!r}. Supported intervals: {intervals}",
            details={"interval": interval},
        ) from exc

    analytics = await market_intelligence.get_transition_analytics(
        symbol=clean_symbol,
        start=start_utc,
        end=end_utc,
        interval=parsed_interval,
        limit=limit,
    )

    # Translate domain TransitionAnalyticsResult to API DTOs
    regime_analytics_dto: dict[int, TransitionRegimeAnalyticsDTO] = {}
    for r_id, ra in analytics.regime_analytics.items():
        rankings_dto = [
            RankedDestinationDTO(
                target_regime=rk.target_regime,
                target_label=rk.target_label,
                probability=rk.probability,
                count=rk.count,
                rank=rk.rank,
            )
            for rk in ra.rankings
        ]
        regime_analytics_dto[r_id] = TransitionRegimeAnalyticsDTO(
            regime_id=ra.regime_id,
            regime_label=ra.regime_label,
            outgoing_transition_count=ra.outgoing_transition_count,
            incoming_transition_count=ra.incoming_transition_count,
            self_transition_count=ra.self_transition_count,
            regime_change_count=ra.regime_change_count,
            persistence_probability=ra.persistence_probability,
            change_rate=ra.change_rate,
            most_likely_destination=ra.most_likely_destination,
            most_likely_destination_probability=ra.most_likely_destination_probability,
            destination_count=ra.destination_count,
            source_count=ra.source_count,
            transition_entropy=ra.transition_entropy,
            rankings=rankings_dto,
        )

    ga = analytics.global_analytics
    global_dto = GlobalTransitionAnalyticsDTO(
        total_observations=ga.total_observations,
        total_consecutive_transitions=ga.total_consecutive_transitions,
        total_regime_changes=ga.total_regime_changes,
        total_self_transitions=ga.total_self_transitions,
        global_change_rate=ga.global_change_rate,
        global_persistence_rate=ga.global_persistence_rate,
        number_of_regimes=ga.number_of_regimes,
        number_of_observed_transition_edges=ga.number_of_observed_transition_edges,
    )

    probabilities_dto: list[TransitionProbabilityDTO] = []
    regimes_tuple = analytics.transition_result.probability_matrix.regimes
    for src in regimes_tuple:
        for tgt in regimes_tuple:
            tp = analytics.transition_result.get_transition_probability(src, tgt)
            probabilities_dto.append(
                TransitionProbabilityDTO(
                    source_regime=tp.source_regime,
                    target_regime=tp.target_regime,
                    count=tp.count,
                    total_transitions_from_source=tp.total_transitions_from_source,
                    probability=tp.probability,
                )
            )

    prob_matrix = [list(row) for row in analytics.transition_result.probability_matrix.matrix]
    count_matrix = [list(row) for row in analytics.transition_result.count_matrix.matrix]
    change_counts = [list(row) for row in analytics.regime_change_counts]
    change_probs = [list(row) for row in analytics.regime_change_probabilities]

    return MarketTransitionResponse(
        symbol=clean_symbol,
        regimes=list(analytics.transition_result.probability_matrix.regimes),
        probability_matrix=prob_matrix,
        count_matrix=count_matrix,
        regime_change_counts=change_counts,
        regime_change_probabilities=change_probs,
        regime_analytics=regime_analytics_dto,
        global_analytics=global_dto,
        probabilities=probabilities_dto,
    )


# =============================================================================
# Risk Analytics & Backtesting Endpoints (V13 / V14 / V15 / V20)
# =============================================================================


@router.get(
    "/{symbol}/risk",
    response_model=MarketRiskResponse,
    summary="Retrieve portfolio risk analytics for an instrument",
    description=(
        "Evaluates V13 portfolio risk analytics (return statistics, realized volatility, "
        "downside deviation, maximum drawdown, VaR and Expected Shortfall) on historical "
        "market data for a queried instrument."
    ),
)
async def get_market_risk(
    symbol: Annotated[str, Path(min_length=1, max_length=50, description="Instrument symbol")],
    market_service: MarketServiceDep,
    risk_service: PortfolioRiskServiceDep,
    start: Annotated[
        datetime | None, Query(description="Start time (inclusive, UTC-aware)")
    ] = None,
    end: Annotated[datetime | None, Query(description="End time (exclusive, UTC-aware)")] = None,
    interval: Annotated[str, Query(description="Data aggregation interval (e.g. '1d')")] = "1d",
    limit: Annotated[int, Query(ge=2, le=5000, description="Maximum bars to analyze")] = 1000,
    periods_per_year: Annotated[
        float, Query(gt=0, description="Annualization factor (e.g. 252.0 for daily)")
    ] = 252.0,
    target_return: Annotated[float, Query(description="Downside deviation target return")] = 0.0,
) -> MarketRiskResponse:
    """Retrieve comprehensive portfolio risk intelligence for an instrument."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise BadRequestError("Instrument symbol cannot be empty or whitespace.")

    # Timezone validation
    if start is not None and start.tzinfo is None:
        raise ValidationError(
            f"Query start datetime must be timezone-aware UTC (got naive datetime: {start!r}).",
            details={"parameter": "start", "value": start.isoformat()},
        )
    if end is not None and end.tzinfo is None:
        raise ValidationError(
            f"Query end datetime must be timezone-aware UTC (got naive datetime: {end!r}).",
            details={"parameter": "end", "value": end.isoformat()},
        )

    end_utc = end.astimezone(UTC) if end is not None else datetime.now(UTC)
    start_utc = start.astimezone(UTC) if start is not None else end_utc - timedelta(days=365)

    if start_utc >= end_utc:
        raise ValidationError(
            f"Query end ({end_utc.isoformat()}) must be strictly after "
            f"start ({start_utc.isoformat()}).",
            details={"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        )

    try:
        parsed_interval = DataInterval(interval.strip().lower())
    except ValueError as exc:
        intervals = [i.value for i in DataInterval]
        raise ValidationError(
            f"Invalid interval {interval!r}. Supported intervals: {intervals}",
            details={"interval": interval},
        ) from exc

    records, _ = await market_service.get_market_data(
        symbol=clean_symbol,
        start=start_utc,
        end=end_utc,
        interval=parsed_interval,
        limit=limit,
    )

    if len(records) < 2:
        raise ValidationError(
            f"Insufficient historical data for symbol {clean_symbol!r} "
            f"(found {len(records)} bars, minimum 2 required).",
            details={"symbol": clean_symbol, "bars_found": len(records)},
        )

    prices = tuple(b.close for b in records)
    timestamps = tuple(b.timestamp for b in records)

    result = risk_service.analyze_price_series(
        prices=prices,
        timestamps=timestamps,
        symbol=clean_symbol,
        periods_per_year=periods_per_year,
        target_return=target_return,
        var_confidences=(0.90, 0.95, 0.99),
    )

    # Compute high-fidelity price points and point-in-time drawdown track
    price_points: list[RiskPricePointDTO] = []
    running_peak = prices[0]
    for i, rec in enumerate(records):
        if rec.close > running_peak:
            running_peak = rec.close
        dd = (rec.close - running_peak) / running_peak if running_peak > 0 else 0.0
        p_ret = ((rec.close - records[i - 1].close) / records[i - 1].close) if i > 0 else None
        price_points.append(
            RiskPricePointDTO(
                timestamp=rec.timestamp,
                price=rec.close,
                period_return=p_ret,
                running_peak=running_peak,
                drawdown=dd,
            )
        )

    # Map VaR and ES by string confidence
    var_dtos: dict[str, VaRMetricsDTO] = {}
    for conf, vm in result.var_metrics.items():
        conf_key = f"{conf:.2f}"
        var_dtos[conf_key] = VaRMetricsDTO(
            confidence_level=vm.confidence_level,
            var_loss=vm.var_loss,
            return_quantile=vm.return_quantile,
            method=vm.method,
            tail_observations=vm.tail_observations,
            total_observations=vm.total_observations,
        )

    es_dtos: dict[str, ExpectedShortfallMetricsDTO] = {}
    for conf, em in result.expected_shortfall_metrics.items():
        conf_key = f"{conf:.2f}"
        es_dtos[conf_key] = ExpectedShortfallMetricsDTO(
            confidence_level=em.confidence_level,
            expected_shortfall=em.expected_shortfall,
            tail_mean_return=em.tail_mean_return,
            var_loss=em.var_loss,
            tail_observations=em.tail_observations,
            total_observations=em.total_observations,
        )

    downside_var = result.downside_risk.downside_deviation**2
    return MarketRiskResponse(
        symbol=clean_symbol,
        series_id=result.series_id,
        observation_count=result.observation_count,
        start_timestamp=result.start_timestamp,
        end_timestamp=result.end_timestamp,
        computed_at=result.computed_at,
        return_statistics=ReturnStatisticsDTO(
            mean_return=result.return_statistics.mean_return,
            median_return=result.return_statistics.median_return,
            standard_deviation=result.return_statistics.standard_deviation,
            minimum_return=result.return_statistics.minimum_return,
            maximum_return=result.return_statistics.maximum_return,
            observation_count=result.return_statistics.observation_count,
        ),
        volatility=VolatilityMetricsDTO(
            period_volatility=result.volatility.period_volatility,
            annualized_volatility=result.volatility.annualized_volatility,
            periods_per_year=result.volatility.periods_per_year,
        ),
        downside_risk=DownsideRiskMetricsDTO(
            downside_deviation=result.downside_risk.downside_deviation,
            semi_variance=downside_var,
            target_return=result.downside_risk.target_return,
            observation_count=result.downside_risk.total_observations,
            downside_observation_count=result.downside_risk.observations_below_target,
        ),
        drawdown=DrawdownMetricsDTO(
            max_drawdown=result.drawdown.max_drawdown,
            drawdown_magnitude=result.drawdown.drawdown_magnitude,
            peak_value=result.drawdown.peak_value,
            trough_value=result.drawdown.trough_value,
            peak_timestamp=result.drawdown.peak_timestamp,
            trough_timestamp=result.drawdown.trough_timestamp,
            recovery_timestamp=result.drawdown.recovery_timestamp,
            is_recovered=result.drawdown.is_recovered,
        ),
        var_metrics=var_dtos,
        expected_shortfall_metrics=es_dtos,
        price_points=price_points,
    )


@router.get(
    "/{symbol}/backtest",
    response_model=MarketBacktestResponse,
    summary="Execute systematic event-driven backtest simulation",
    description=(
        "Executes a deterministic event-driven backtest simulation (V14) with realistic "
        "transaction fees and slippage, and generates an immutable performance report (V15)."
    ),
)
async def get_market_backtest(
    symbol: Annotated[str, Path(min_length=1, max_length=50, description="Instrument symbol")],
    market_service: MarketServiceDep,
    market_intelligence: MarketIntelligenceDep,
    backtest_service: BacktestingServiceDep,
    strategy: Annotated[
        str,
        Query(description="Strategy identifier: 'BUY_AND_HOLD' or 'REGIME_ADAPTIVE'"),
    ] = "BUY_AND_HOLD",
    start: Annotated[
        datetime | None, Query(description="Start time (inclusive, UTC-aware)")
    ] = None,
    end: Annotated[datetime | None, Query(description="End time (exclusive, UTC-aware)")] = None,
    interval: Annotated[str, Query(description="Data aggregation interval (e.g. '1d')")] = "1d",
    limit: Annotated[int, Query(ge=3, le=5000, description="Maximum bars to simulate")] = 1000,
    initial_cash: Annotated[float, Query(gt=0, description="Initial starting capital")] = 100_000.0,
    commission_rate: Annotated[
        float, Query(ge=0, description="Commission rate per trade fill")
    ] = 0.0005,
    slippage_rate: Annotated[
        float, Query(ge=0, description="Slippage rate per trade fill")
    ] = 0.0005,
    execution_convention: Annotated[
        str, Query(description="'CURRENT_CLOSE' or 'NEXT_OPEN'")
    ] = "CURRENT_CLOSE",
    periods_per_year: Annotated[
        float, Query(gt=0, description="Annualization factor (e.g. 252.0 for daily)")
    ] = 252.0,
) -> MarketBacktestResponse:
    """Execute systematic event-driven backtest simulation and return performance report."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise BadRequestError("Instrument symbol cannot be empty or whitespace.")

    # Timezone validation
    if start is not None and start.tzinfo is None:
        raise ValidationError(
            f"Query start datetime must be timezone-aware UTC (got naive datetime: {start!r}).",
            details={"parameter": "start", "value": start.isoformat()},
        )
    if end is not None and end.tzinfo is None:
        raise ValidationError(
            f"Query end datetime must be timezone-aware UTC (got naive datetime: {end!r}).",
            details={"parameter": "end", "value": end.isoformat()},
        )

    end_utc = end.astimezone(UTC) if end is not None else datetime.now(UTC)
    start_utc = start.astimezone(UTC) if start is not None else end_utc - timedelta(days=365)

    if start_utc >= end_utc:
        raise ValidationError(
            f"Query end ({end_utc.isoformat()}) must be strictly after "
            f"start ({start_utc.isoformat()}).",
            details={"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        )

    try:
        parsed_interval = DataInterval(interval.strip().lower())
    except ValueError as exc:
        intervals = [i.value for i in DataInterval]
        raise ValidationError(
            f"Invalid interval {interval!r}. Supported intervals: {intervals}",
            details={"interval": interval},
        ) from exc

    # Parse execution convention case-insensitively
    clean_convention = execution_convention.strip().lower()
    try:
        parsed_convention = ExecutionPriceConvention(clean_convention)
    except ValueError as exc:
        conventions = [c.value.upper() for c in ExecutionPriceConvention]
        raise ValidationError(
            f"Invalid execution convention {execution_convention!r}. Supported: {conventions}",
            details={"execution_convention": execution_convention},
        ) from exc

    records, _ = await market_service.get_market_data(
        symbol=clean_symbol,
        start=start_utc,
        end=end_utc,
        interval=parsed_interval,
        limit=limit,
    )

    if len(records) < 3:
        raise ValidationError(
            f"Insufficient historical data for backtesting simulation "
            f"(minimum 3 bars required, found {len(records)}).",
            details={"symbol": clean_symbol, "bars_found": len(records)},
        )

    events = [MarketEvent.from_ohlcv(b) for b in records]

    # Resolve strategy & run simulation via BacktestingService
    clean_strat = strategy.strip().upper()
    regimes_seq: list[int] | None = None

    if clean_strat == "REGIME_ADAPTIVE":
        try:
            summary, _ = await market_intelligence.get_market_regime(
                symbol=clean_symbol,
                start=start_utc,
                end=end_utc,
                interval=parsed_interval,
                limit=limit,
            )
            cur_id = summary.current_regime.current_regime_id if summary.current_regime else 0
            regimes_seq = [cur_id] * len(events)
        except Exception:
            regimes_seq = [0] * len(events)

    result, summary_metric, report, strategy_id, strategy_name = backtest_service.run_simulation(
        events=events,
        strategy_id=clean_strat,
        initial_cash=initial_cash,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        execution_convention=parsed_convention,
        regimes=regimes_seq,
        periods_per_year=periods_per_year,
    )

    trades_metric = summary_metric.trades

    # Convert equity snapshots and calculate running drawdown
    equity_curve_dtos: list[EquitySnapshotDTO] = []
    peak_eq = result.initial_cash
    for s in result.equity_curve:
        if s.equity > peak_eq:
            peak_eq = s.equity
        s_dd = (s.equity - peak_eq) / peak_eq if peak_eq > 0 else 0.0
        equity_curve_dtos.append(
            EquitySnapshotDTO(
                timestamp=s.timestamp,
                cash=s.cash,
                market_value=s.market_value,
                equity=s.equity,
                fees=s.fees,
                realized_pnl=s.realized_pnl,
                unrealized_pnl=s.unrealized_pnl,
                drawdown=s_dd,
            )
        )

    # Executed trades / fills
    trade_dtos = [
        BacktestTradeDTO(
            timestamp=f.timestamp,
            symbol=f.symbol,
            side=f.side.value,
            quantity=f.quantity,
            price=f.price,
            commission=f.commission,
            slippage=f.slippage,
        )
        for f in result.fills
    ]

    metric_defs = [
        MetricDefinitionDTO(
            metric_name=m.metric_name,
            description=m.description,
            unit=m.unit,
            direction_semantics=m.direction_semantics,
            source=m.source,
        )
        for m in report.metric_definitions
    ]

    methodology_dto = MethodologyDTO(
        common_period_policy=report.methodology.common_period_policy,
        trade_definition=report.methodology.trade_definition,
        risk_engine_source=report.methodology.risk_engine_source,
        return_type=report.methodology.return_type,
        execution_engine_source=report.methodology.execution_engine_source,
    )

    report_dto = PerformanceReportDTO(
        report_id=report.report_id,
        report_version=report.report_version,
        generated_at=report.generated_at,
        methodology=methodology_dto,
        limitations=list(report.limitations),
        metric_definitions=metric_defs,
    )

    return MarketBacktestResponse(
        symbol=clean_symbol,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        execution_convention=parsed_convention.value.upper(),
        initial_cash=result.initial_cash,
        final_cash=result.final_cash,
        final_equity=summary_metric.final_equity,
        total_return=summary_metric.total_return,
        annualized_return=summary_metric.annualized_return,
        absolute_pnl=summary_metric.absolute_pnl,
        realized_pnl=summary_metric.realized_pnl,
        unrealized_pnl=summary_metric.unrealized_pnl,
        total_fees=summary_metric.total_fees,
        slippage_rate=slippage_rate,
        commission_rate=commission_rate,
        trades=TradeStatisticsDTO(
            order_count=trades_metric.order_count,
            fill_count=trades_metric.fill_count,
            completed_trade_count=trades_metric.completed_trade_count,
            winning_trades=trades_metric.winning_trades,
            losing_trades=trades_metric.losing_trades,
            win_rate=trades_metric.win_rate,
            total_realized_pnl=trades_metric.total_realized_pnl,
            average_trade_pnl=trades_metric.average_trade_pnl,
            largest_winning_trade=trades_metric.largest_winning_trade,
            largest_losing_trade=trades_metric.largest_losing_trade,
        ),
        risk_metrics=BacktestRiskMetricsDTO(
            volatility=summary_metric.volatility,
            annualized_volatility=summary_metric.annualized_volatility,
            maximum_drawdown=summary_metric.maximum_drawdown,
            drawdown_magnitude=summary_metric.drawdown_magnitude,
            var_95=summary_metric.var_95,
            expected_shortfall_95=summary_metric.expected_shortfall_95,
        ),
        equity_curve=equity_curve_dtos,
        executed_trades=trade_dtos,
        report=report_dto,
    )
