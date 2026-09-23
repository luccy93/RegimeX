"""
RegimeX API v1 — Market Intelligence Endpoints
==============================================
Read-oriented endpoints exposing market discovery and time-series data.

Endpoints:
  GET /api/v1/markets
  GET /api/v1/markets/{symbol}/data
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.v1.models import (
    MarketDataResponse,
    MarketItemResponse,
    MarketListResponse,
    OHLCVBarResponse,
)
from app.core.dependencies import MarketServiceDep
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
