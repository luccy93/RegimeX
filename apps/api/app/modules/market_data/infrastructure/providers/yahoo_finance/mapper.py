"""
RegimeX Market Data — Yahoo Finance DataFrame Mapper
=====================================================
Translates vendor-specific pandas DataFrames into canonical OHLCVRecord domain objects.

Pandas Boundary:
- Pandas is restricted entirely to this infrastructure module.
- Domain models and application layers never see or import pandas.
- All timestamps are converted to timezone-aware UTC.
- Enforces strict structural checks; invalid vendor records raise ProviderDataError.
"""

from __future__ import annotations

import pandas as pd

from app.modules.market_data.domain.errors import ProviderDataError
from app.modules.market_data.domain.models import (
    MarketDataQuery,
    OHLCVRecord,
)

_REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def map_yahoo_finance_dataframe(
    df: pd.DataFrame | None,
    query: MarketDataQuery,
    provider_id: str = "yahoo_finance",
) -> tuple[OHLCVRecord, ...]:
    """
    Map a raw pandas DataFrame from Yahoo Finance into a tuple of canonical OHLCVRecord models.

    Args:
        df: Raw DataFrame returned by yfinance (or mock fixture).
        query: Canonical request for correlation and metadata.
        provider_id: Stable identifier of the provider.

    Returns:
        Sorted tuple of canonical OHLCVRecord objects within [query.start, query.end).

    Raises:
        ProviderDataError: If columns are missing, timestamps are invalid,
                           nulls/NaNs are present, or OHLC invariants are violated.
    """
    if df is None or df.empty:
        return ()

    working_df = df.copy()

    # Handle multi-level columns from yfinance.download
    if isinstance(working_df.columns, pd.MultiIndex):
        level_0_names = [str(c).title() for c in working_df.columns.get_level_values(0)]
        if any(c in level_0_names for c in ("Open", "Close", "High")):
            working_df.columns = working_df.columns.get_level_values(0)
        else:
            working_df.columns = working_df.columns.get_level_values(1)

    # Standardize column names (case-insensitive)
    col_map: dict[str, str] = {}
    for col in working_df.columns:
        norm = str(col).strip().title()
        if norm in _REQUIRED_COLUMNS:
            col_map[str(col)] = norm

    working_df = working_df.rename(columns=col_map)

    # Verify all 5 required OHLCV columns exist
    missing_cols = [c for c in _REQUIRED_COLUMNS if c not in working_df.columns]
    if missing_cols:
        raise ProviderDataError(
            f"Yahoo Finance response missing required column(s): {missing_cols}",
            provider_id=provider_id,
            details={"missing_columns": missing_cols},
        )

    # Validate timestamp index
    if not isinstance(working_df.index, pd.DatetimeIndex):
        try:
            working_df.index = pd.to_datetime(working_df.index)
        except Exception as err:
            raise ProviderDataError(
                f"Failed to parse index as DatetimeIndex: {err}",
                provider_id=provider_id,
            ) from err

    # Normalize timezone to UTC
    if working_df.index.tz is None:
        working_df.index = working_df.index.tz_localize("UTC")
    else:
        working_df.index = working_df.index.tz_convert("UTC")

    # Reject duplicate timestamps deterministically
    if working_df.index.has_duplicates:
        raise ProviderDataError(
            "Duplicate timestamps encountered in Yahoo Finance response.",
            provider_id=provider_id,
        )

    # Ensure chronological ascending order
    working_df = working_df.sort_index(ascending=True)

    # Check for NaN / null values across required columns
    subset = working_df[list(_REQUIRED_COLUMNS)]
    if subset.isna().any().any():
        raise ProviderDataError(
            "Yahoo Finance response contains NaN/null values in required OHLCV columns.",
            provider_id=provider_id,
        )

    records: list[OHLCVRecord] = []
    symbol = query.instrument.symbol

    for idx, row in working_df.iterrows():
        ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx

        # Respect query range: [query.start, query.end)
        if ts < query.start or ts >= query.end:
            continue

        open_val = float(row["Open"])
        high_val = float(row["High"])
        low_val = float(row["Low"])
        close_val = float(row["Close"])
        vol_val = float(row["Volume"])

        # Check basic non-negativity before constructing domain model
        if open_val <= 0 or high_val <= 0 or low_val <= 0 or close_val <= 0:
            raise ProviderDataError(
                f"Non-positive price found for {symbol} at {ts.isoformat()}: "
                f"O={open_val}, H={high_val}, L={low_val}, C={close_val}",
                provider_id=provider_id,
            )

        if vol_val < 0:
            raise ProviderDataError(
                f"Negative volume found for {symbol} at {ts.isoformat()}: V={vol_val}",
                provider_id=provider_id,
            )

        try:
            record = OHLCVRecord(
                symbol=symbol,
                timestamp=ts,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=vol_val,
                interval=query.interval,
                adjustment_policy=query.adjustment_policy,
                source_provider_id=provider_id,
            )
            records.append(record)
        except ValueError as err:
            raise ProviderDataError(
                f"OHLCV invariant violated for {symbol} at {ts.isoformat()}: {err}",
                provider_id=provider_id,
            ) from err

    return tuple(records)
