"""
RegimeX Backtesting — Canonical Domain Models
=============================================
Defines immutable, strongly-typed domain models for event-driven backtesting.

Architectural position: ``domain/models.py``
- Pure Python and Pydantic v2.
- Zero external ML/DL or web framework dependencies.
- Strict timezone-aware UTC datetime validation.
- Clean integration with V13 Portfolio Risk Engine (PriceSeries, ReturnSeries).
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.market_data.domain.models import OHLCVRecord
from app.modules.portfolio_risk.domain.models import (
    PriceSeries,
    ReturnSeries,
    ReturnType,
)

if TYPE_CHECKING:
    from app.modules.portfolio_risk.domain.interfaces import PortfolioRiskEngineProtocol
    from app.modules.portfolio_risk.domain.models import PortfolioRiskResult


# =============================================================================
# Enums
# =============================================================================


class OrderSide(StrEnum):
    """Trading order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Order type for historical execution."""

    MARKET = "market"


class EventType(StrEnum):
    """Canonical event types processed in the backtesting simulation."""

    MARKET = "market"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"
    PORTFOLIO = "portfolio"


class ExecutionPriceConvention(StrEnum):
    """Execution timing and price settlement convention."""

    CURRENT_CLOSE = "current_close"
    NEXT_OPEN = "next_open"


# =============================================================================
# Helpers
# =============================================================================


def _validate_utc(v: datetime | None, field_name: str = "timestamp") -> datetime | None:
    if v is not None and isinstance(v, datetime):
        if v.tzinfo is None or v.utcoffset() != timedelta(0):
            raise ValueError(f"{field_name} must be UTC-aware (got: {v!r}).")
    return v


def _validate_finite(v: float, field_name: str) -> float:
    if math.isnan(v) or math.isinf(v):
        raise ValueError(f"{field_name} must be finite (got {v}).")
    return v


# =============================================================================
# Events
# =============================================================================


class MarketEvent(BaseModel):
    """
    Market data observation delivered to the simulation at a discrete timestamp.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    open: Annotated[float, Field(gt=0.0, description="Opening price")]
    high: Annotated[float, Field(gt=0.0, description="Highest price")]
    low: Annotated[float, Field(gt=0.0, description="Lowest price")]
    close: Annotated[float, Field(gt=0.0, description="Closing price")]
    volume: Annotated[float, Field(ge=0.0, description="Bar volume")]
    event_type: EventType = EventType.MARKET

    @field_validator("timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "timestamp")
        assert res is not None
        return res

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("open", "high", "low", "close", "volume")
    @classmethod
    def check_finite(cls, v: float) -> float:
        return _validate_finite(v, "price/volume")

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> MarketEvent:
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) cannot be less than low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be greater than or equal to open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be less than or equal to open and close")
        return self

    @classmethod
    def from_ohlcv(cls, record: OHLCVRecord) -> MarketEvent:
        """Construct a MarketEvent from a canonical OHLCVRecord."""
        return cls(
            timestamp=record.timestamp,
            symbol=record.symbol,
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=record.volume,
        )


class SignalEvent(BaseModel):
    """
    Strategy decision emitted upon receiving market observations.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    direction: Annotated[int, Field(ge=-1, le=1, description="1 for long, 0 flat, -1 short")]
    strength: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    target_weight: Annotated[float | None, Field(ge=-1.0, le=1.0)] = None
    event_type: EventType = EventType.SIGNAL

    @field_validator("timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "timestamp")
        assert res is not None
        return res

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()


class OrderRequest(BaseModel):
    """
    Typed order request generated by a strategy or portfolio manager.
    """

    model_config = ConfigDict(frozen=True)

    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    side: OrderSide
    quantity: Annotated[float, Field(gt=0.0, description="Order quantity strictly > 0")]
    order_type: OrderType = OrderType.MARKET
    event_type: EventType = EventType.ORDER

    @field_validator("timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "timestamp")
        assert res is not None
        return res

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def check_quantity_finite(cls, v: float) -> float:
        return _validate_finite(v, "quantity")


class FillEvent(BaseModel):
    """
    Executed order fill report containing execution price, slippage, and commission.
    """

    model_config = ConfigDict(frozen=True)

    fill_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    timestamp: datetime
    symbol: Annotated[str, Field(min_length=1, max_length=50)]
    side: OrderSide
    quantity: Annotated[float, Field(gt=0.0)]
    price: Annotated[float, Field(gt=0.0, description="Settled execution price post-slippage")]
    commission: Annotated[float, Field(ge=0.0)] = 0.0
    slippage: Annotated[float, Field(ge=0.0)] = 0.0
    event_type: EventType = EventType.FILL

    @field_validator("timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "timestamp")
        assert res is not None
        return res

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity", "price", "commission", "slippage")
    @classmethod
    def check_finite_metrics(cls, v: float) -> float:
        return _validate_finite(v, "fill metric")


# =============================================================================
# Portfolio & Accounting Models
# =============================================================================


class Position(BaseModel):
    """
    Marked-to-market position tracking holding size, average entry price, and PnL.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    quantity: Annotated[float, Field(ge=0.0)] = 0.0
    average_entry_price: Annotated[float, Field(ge=0.0)] = 0.0
    market_price: Annotated[float, Field(ge=0.0)] = 0.0
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        """Current marked-to-market valuation."""
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        """Marked-to-market unrealized profit or loss."""
        if self.quantity <= 0.0:
            return 0.0
        return (self.market_price - self.average_entry_price) * self.quantity

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity", "average_entry_price", "market_price", "realized_pnl")
    @classmethod
    def check_finite_position(cls, v: float) -> float:
        return _validate_finite(v, "position metric")


class EquitySnapshot(BaseModel):
    """
    Point-in-time snapshot of the portfolio's total wealth and accounting components.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    cash: float
    market_value: float
    equity: float
    fees: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @field_validator("timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "timestamp")
        assert res is not None
        return res

    @field_validator("cash", "market_value", "equity", "fees", "realized_pnl", "unrealized_pnl")
    @classmethod
    def check_finite_snapshot(cls, v: float) -> float:
        return _validate_finite(v, "equity snapshot metric")

    @model_validator(mode="after")
    def validate_accounting_equation(self) -> EquitySnapshot:
        # equity == cash + market_value
        if abs((self.cash + self.market_value) - self.equity) > 1e-6:
            raise ValueError(
                f"Equity equation violated: equity ({self.equity:.4f}) != "
                f"cash ({self.cash:.4f}) + market_value ({self.market_value:.4f})."
            )
        return self


class BacktestConfig(BaseModel):
    """
    Configuration parameters for backtesting execution.
    """

    model_config = ConfigDict(frozen=True)

    initial_cash: Annotated[float, Field(gt=0.0)] = 100_000.0
    commission_rate: Annotated[float, Field(ge=0.0)] = 0.0
    slippage_rate: Annotated[float, Field(ge=0.0)] = 0.0
    execution_convention: ExecutionPriceConvention = ExecutionPriceConvention.CURRENT_CLOSE
    allow_short: bool = False

    @field_validator("initial_cash", "commission_rate", "slippage_rate")
    @classmethod
    def check_finite_config(cls, v: float) -> float:
        return _validate_finite(v, "config metric")


# =============================================================================
# Result Container
# =============================================================================


class BacktestResult(BaseModel):
    """
    Strongly-typed, immutable result of an event-driven backtest simulation.
    """

    model_config = ConfigDict(frozen=True)

    start_timestamp: datetime
    end_timestamp: datetime
    initial_cash: float
    final_cash: float
    final_equity: float
    orders: tuple[OrderRequest, ...]
    fills: tuple[FillEvent, ...]
    positions: dict[str, Position]
    equity_curve: tuple[EquitySnapshot, ...]
    total_fees: float
    trade_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_timestamp", "end_timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "result timestamp")
        assert res is not None
        return res

    def to_price_series(self) -> PriceSeries:
        """
        Convert the portfolio equity curve into a canonical V13 PriceSeries.
        """
        timestamps = tuple(snapshot.timestamp for snapshot in self.equity_curve)
        prices = tuple(snapshot.equity for snapshot in self.equity_curve)
        return PriceSeries(
            timestamps=timestamps,
            prices=prices,
            symbol="PORTFOLIO_EQUITY",
        )

    def to_return_series(self, return_type: ReturnType = ReturnType.ARITHMETIC) -> ReturnSeries:
        """
        Derive a canonical V13 ReturnSeries from the backtest equity curve.
        """
        from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine

        engine = PortfolioRiskEngine()
        price_series = self.to_price_series()
        if return_type == ReturnType.LOG:
            return engine.compute_log_returns(
                prices=price_series.prices,
                timestamps=price_series.timestamps,
                symbol="PORTFOLIO_RETURNS",
            )
        return engine.compute_arithmetic_returns(
            prices=price_series.prices,
            timestamps=price_series.timestamps,
            symbol="PORTFOLIO_RETURNS",
        )

    def compute_risk_metrics(
        self,
        risk_engine: PortfolioRiskEngineProtocol | None = None,
    ) -> PortfolioRiskResult:
        """
        Evaluate full portfolio risk analytics on the backtest equity curve
        using the V13 PortfolioRiskEngine.
        """
        from app.modules.portfolio_risk.infrastructure.engine import PortfolioRiskEngine

        engine = risk_engine or PortfolioRiskEngine()
        price_series = self.to_price_series()
        return engine.analyze_risk(
            data=price_series,
            series_id="backtest_portfolio",
        )
