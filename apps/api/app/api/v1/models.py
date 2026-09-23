"""
RegimeX API v1 — Response & Request Models
==========================================
Canonical typed presentation schemas for API v1 endpoints.

Design Principles:
- Pydantic v2 BaseModel subclasses with frozen immutability.
- No internal domain object or ORM instance leakage.
- Explicit schemas supporting clean OpenAPI documentation generation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ApiError, ApiErrorDetail

# =============================================================================
# Root & Health Responses
# =============================================================================


class RootResponse(BaseModel):
    """API Root metadata response."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Platform API name")
    version: str = Field(description="Semantic platform release version")
    api_version: str = Field(description="Active API namespace version")
    status: str = Field(default="ok", description="Overall service status")


class HealthResponse(BaseModel):
    """Lightweight process liveness response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(default="ok", description="Process liveness state")


class ReadinessResponse(BaseModel):
    """Detailed operational readiness response."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Readiness status ('ready' or 'not_ready')")
    checks: dict[str, str] = Field(description="Status of individual infrastructure checks")
    timestamp: str | None = Field(default=None, description="ISO 8601 evaluation timestamp")


# =============================================================================
# Market Intelligence Responses
# =============================================================================


class MarketItemResponse(BaseModel):
    """Summary representation of a tradeable instrument."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Canonical instrument symbol")
    asset_class: str = Field(description="Asset classification")
    exchange: str = Field(description="Exchange or marketplace")
    currency: str = Field(description="Trading or quote currency")
    description: str = Field(default="", description="Descriptive instrument name")


class MarketListResponse(BaseModel):
    """Paginated collection of discoverable market instruments."""

    model_config = ConfigDict(frozen=True)

    items: list[MarketItemResponse] = Field(description="List of market instruments")
    total: int = Field(ge=0, description="Total number of items in list")
    limit: int = Field(default=100, ge=1, description="Pagination limit")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class OHLCVBarResponse(BaseModel):
    """Single discrete historical price and volume observation bar."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(description="Bar opening/observation timestamp in UTC")
    open: float = Field(gt=0.0, description="Opening price")
    high: float = Field(gt=0.0, description="Highest price")
    low: float = Field(gt=0.0, description="Lowest price")
    close: float = Field(gt=0.0, description="Closing price")
    volume: float = Field(ge=0.0, description="Traded volume")


class MarketDataResponse(BaseModel):
    """Time-series market data response."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(description="Queried instrument symbol")
    interval: str = Field(description="Bar observation interval (e.g. 1d, 1h)")
    start: datetime = Field(description="Start query bound (UTC)")
    end: datetime = Field(description="End query bound (UTC)")
    count: int = Field(ge=0, description="Number of bars returned in this page")
    total: int = Field(ge=0, description="Total matching observations")
    items: list[OHLCVBarResponse] = Field(description="Chronologically sorted OHLCV records")


__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "HealthResponse",
    "MarketDataResponse",
    "MarketItemResponse",
    "MarketListResponse",
    "OHLCVBarResponse",
    "ReadinessResponse",
    "RootResponse",
]
