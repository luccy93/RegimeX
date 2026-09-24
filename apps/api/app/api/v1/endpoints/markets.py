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
    CurrentRegimeContextDTO,
    FeatureStatisticDTO,
    GlobalTransitionAnalyticsDTO,
    MarketDataResponse,
    MarketItemResponse,
    MarketListResponse,
    MarketRegimeResponse,
    MarketTransitionResponse,
    OHLCVBarResponse,
    RankedDestinationDTO,
    RegimeProfileDTO,
    TransitionProbabilityDTO,
    TransitionRegimeAnalyticsDTO,
)
from app.core.dependencies import MarketIntelligenceDep, MarketServiceDep
from app.core.errors import BadRequestError, ValidationError
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
