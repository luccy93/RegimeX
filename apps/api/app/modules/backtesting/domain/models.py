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
from datetime import UTC, datetime, timedelta
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
        periods_per_year: float | None = None,
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
            periods_per_year=periods_per_year,
            series_id="backtest_portfolio",
        )


# =============================================================================
# Strategy Comparison Models
# =============================================================================


class StrategyComparisonInput(BaseModel):
    """
    Typed input wrapper binding a unique strategy identifier to a completed BacktestResult.
    """

    model_config = ConfigDict(frozen=True)

    strategy_id: Annotated[
        str, Field(min_length=1, description="Unique, non-empty strategy identifier")
    ]
    display_name: str = ""
    backtest_result: BacktestResult

    @field_validator("strategy_id", mode="before")
    @classmethod
    def validate_strategy_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("strategy_id must be a non-empty, non-whitespace string.")
        return v.strip()

    @field_validator("display_name", mode="before")
    @classmethod
    def default_display_name(cls, v: str | None) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @model_validator(mode="after")
    def resolve_display_name_and_validate(self) -> StrategyComparisonInput:
        if not self.display_name:
            object.__setattr__(self, "display_name", self.strategy_id)
        if (
            self.backtest_result.initial_cash <= 0.0
            or math.isnan(self.backtest_result.initial_cash)
            or math.isinf(self.backtest_result.initial_cash)
        ):
            raise ValueError("backtest_result initial_cash must be strictly positive and finite.")
        return self


class ComparisonPeriod(BaseModel):
    """
    Validated time window for strategy evaluation.
    """

    model_config = ConfigDict(frozen=True)

    start_timestamp: datetime
    end_timestamp: datetime
    is_truncated: bool = False

    @field_validator("start_timestamp", "end_timestamp", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "comparison period timestamp")
        assert res is not None
        return res

    @model_validator(mode="after")
    def validate_temporal_order(self) -> ComparisonPeriod:
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError(
                f"end_timestamp ({self.end_timestamp.isoformat()}) must be strictly after "
                f"start_timestamp ({self.start_timestamp.isoformat()})."
            )
        return self

    @property
    def duration(self) -> timedelta:
        """Total time duration of the evaluation period."""
        return self.end_timestamp - self.start_timestamp


class TradeStatistics(BaseModel):
    """
    Descriptive trading execution statistics extracted from backtest fills.

    Definitions:
    - order_count: Total orders requested during the evaluation period.
    - fill_count: Total execution fills processed during the evaluation period.
    - completed_trade_count: Total position exit fills that realized profit or loss.
    - winning_trades: Count of completed trades with positive realized PnL (> 0).
    - losing_trades: Count of completed trades with negative realized PnL (< 0).
    - win_rate: Ratio of winning trades to completed trades (None if 0 completed trades).
    - total_realized_pnl: Sum of gross realized profit or loss from completed exit trades.
    - average_trade_pnl: Mean realized profit/loss per completed trade (None if 0 completed trades).
    - largest_winning_trade: Maximum positive trade PnL (None if no winning trades).
    - largest_losing_trade: Minimum negative trade PnL (None if no losing trades).
    """

    model_config = ConfigDict(frozen=True)

    order_count: Annotated[int, Field(ge=0, description="Total order requests")]
    fill_count: Annotated[int, Field(ge=0, description="Total order fills")]
    completed_trade_count: Annotated[int, Field(ge=0, description="Total exit fills realizing PnL")]
    winning_trades: Annotated[int, Field(ge=0, description="Number of profitable exit trades")]
    losing_trades: Annotated[int, Field(ge=0, description="Number of loss-making exit trades")]
    win_rate: float | None = Field(default=None, description="Winning trades / completed trades")
    total_realized_pnl: float = Field(default=0.0, description="Cumulative gross realized PnL")
    average_trade_pnl: float | None = Field(
        default=None, description="Average PnL per completed trade"
    )
    largest_winning_trade: float | None = Field(
        default=None, description="Largest single winning trade PnL"
    )
    largest_losing_trade: float | None = Field(
        default=None, description="Largest single losing trade PnL"
    )

    @model_validator(mode="after")
    def validate_trade_counts(self) -> TradeStatistics:
        if self.winning_trades + self.losing_trades > self.completed_trade_count:
            raise ValueError(
                f"winning ({self.winning_trades}) + losing ({self.losing_trades}) trades "
                f"cannot exceed completed_trade_count ({self.completed_trade_count})."
            )
        if self.completed_trade_count > 0 and self.win_rate is not None:
            if not (0.0 <= self.win_rate <= 1.0):
                raise ValueError(f"win_rate must be between 0.0 and 1.0 (got {self.win_rate}).")
        return self


class StrategySummary(BaseModel):
    """
    Standardized, descriptive performance and risk summary for an individual strategy
    over the evaluated comparison period.
    """

    model_config = ConfigDict(frozen=True)

    strategy_id: str
    display_name: str
    evaluation_period: ComparisonPeriod
    initial_equity: Annotated[
        float, Field(gt=0.0, description="Starting capital for evaluation period")
    ]
    final_equity: Annotated[
        float, Field(ge=0.0, description="Ending capital at conclusion of period")
    ]
    absolute_pnl: float = Field(description="Net wealth change: final_equity - initial_equity")
    total_return: float = Field(
        description="Cumulative return: (final_equity / initial_equity) - 1"
    )
    annualized_return: float | None = Field(
        default=None, description="Compound annualized return if applicable"
    )
    realized_pnl: float = Field(description="Gross realized PnL during evaluation period")
    unrealized_pnl: float = Field(description="Marked-to-market unrealized PnL at period close")
    total_fees: float = Field(
        ge=0.0, description="Total transaction costs and commissions incurred"
    )
    trades: TradeStatistics
    volatility: float = Field(ge=0.0, description="Sample standard deviation of period returns")
    annualized_volatility: float | None = Field(
        default=None, ge=0.0, description="Annualized volatility"
    )
    maximum_drawdown: float = Field(
        le=0.0, description="Maximum peak-to-trough decline (signed <= 0)"
    )
    drawdown_magnitude: float = Field(
        ge=0.0, description="Absolute magnitude of max drawdown (|max_drawdown|)"
    )
    peak_timestamp: datetime | None = None
    trough_timestamp: datetime | None = None
    recovery_timestamp: datetime | None = None
    is_recovered: bool = False
    var_95: float | None = Field(
        default=None, description="Historical VaR at 95% confidence (loss-oriented)"
    )
    expected_shortfall_95: float | None = Field(
        default=None, description="Expected Shortfall at 95% confidence (loss-oriented)"
    )
    return_mean: float | None = Field(default=None, description="Mean discrete return")
    return_median: float | None = Field(default=None, description="Median discrete return")
    return_min: float | None = Field(default=None, description="Minimum observed return")
    return_max: float | None = Field(default=None, description="Maximum observed return")

    @field_validator(
        "initial_equity",
        "final_equity",
        "absolute_pnl",
        "total_return",
        "realized_pnl",
        "unrealized_pnl",
        "total_fees",
        "volatility",
        "maximum_drawdown",
        "drawdown_magnitude",
    )
    @classmethod
    def check_finite_metrics(cls, v: float) -> float:
        return _validate_finite(v, "summary metric")


class PairwiseComparison(BaseModel):
    """
    Deterministic pairwise comparison between two strategies: Base (A) vs Target (B).

    Convention:
    - Delta = Metric_A - Metric_B.
    - Relative Difference = (Metric_A - Metric_B) / |Metric_B| (None if Metric_B == 0).
    - No scores, ranks, or 'winner' classifications are generated.
    """

    model_config = ConfigDict(frozen=True)

    base_strategy_id: str
    target_strategy_id: str

    # Absolute Deltas: (A - B)
    final_equity_delta: float = Field(description="A.final_equity - B.final_equity")
    pnl_delta: float = Field(description="A.absolute_pnl - B.absolute_pnl")
    return_delta: float = Field(description="A.total_return - B.total_return (percentage points)")
    annualized_return_delta: float | None = Field(
        default=None, description="A.annualized_return - B.annualized_return"
    )
    volatility_delta: float = Field(description="A.volatility - B.volatility")
    annualized_volatility_delta: float | None = Field(
        default=None, description="A.annualized_volatility - B.annualized_volatility"
    )
    drawdown_delta: float = Field(
        description="A.maximum_drawdown - B.maximum_drawdown (signed delta)"
    )
    drawdown_magnitude_delta: float = Field(
        description="A.drawdown_magnitude - B.drawdown_magnitude"
    )
    var_delta: float | None = Field(default=None, description="A.var_95 - B.var_95")
    es_delta: float | None = Field(
        default=None, description="A.expected_shortfall_95 - B.expected_shortfall_95"
    )
    fees_delta: float = Field(description="A.total_fees - B.total_fees")
    trade_count_delta: int = Field(description="A.completed_trade_count - B.completed_trade_count")
    win_rate_delta: float | None = Field(default=None, description="A.win_rate - B.win_rate")

    # Safe Relative Differences: (A - B) / |B| (None if denominator is zero)
    relative_return_difference: float | None = Field(
        default=None, description="(A.total_return - B.total_return) / |B.total_return|"
    )
    relative_fee_difference: float | None = Field(
        default=None, description="(A.total_fees - B.total_fees) / |B.total_fees|"
    )
    relative_drawdown_difference: float | None = Field(
        default=None,
        description="(A.drawdown_magnitude - B.drawdown_magnitude) / |B.drawdown_magnitude|",
    )
    relative_equity_difference: float | None = Field(
        default=None, description="(A.final_equity - B.final_equity) / |B.final_equity|"
    )

    @field_validator(
        "final_equity_delta",
        "pnl_delta",
        "return_delta",
        "volatility_delta",
        "drawdown_delta",
        "drawdown_magnitude_delta",
        "fees_delta",
    )
    @classmethod
    def check_finite_deltas(cls, v: float) -> float:
        return _validate_finite(v, "pairwise delta")


class MetricDirectionSemantics(BaseModel):
    """
    Descriptive dictionary of metric interpretation semantics without value judgments or ranking.
    """

    model_config = ConfigDict(frozen=True)

    semantics: dict[str, str] = Field(
        default_factory=lambda: {
            "total_return": "Higher value denotes greater realized cumulative return.",
            "annualized_return": "Higher value denotes greater annualized compound return.",
            "volatility": (
                "Higher value denotes greater variability/dispersion of periodic returns."
            ),
            "maximum_drawdown": (
                "More negative value denotes deeper peak-to-trough capital decline."
            ),
            "drawdown_magnitude": "Higher value denotes greater peak-to-trough decline magnitude.",
            "var_95": "Higher value denotes larger estimated downside tail loss at 95% confidence.",
            "expected_shortfall_95": (
                "Higher value denotes larger expected tail loss conditional on exceeding VaR."
            ),
            "total_fees": (
                "Higher value denotes greater cumulative execution commissions and "
                "transaction costs."
            ),
            "win_rate": (
                "Higher value denotes higher proportion of profitable completed exit trades."
            ),
        }
    )


class StrategyComparisonResult(BaseModel):
    """
    Immutable, strongly-typed result of a strategy comparison analysis.
    """

    model_config = ConfigDict(frozen=True)

    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    computed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    common_evaluation_period: ComparisonPeriod
    strategies: tuple[StrategySummary, ...]
    pairwise_comparisons: tuple[PairwiseComparison, ...]
    metric_semantics: dict[str, str] = Field(
        default_factory=lambda: MetricDirectionSemantics().semantics
    )
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("computed_at", mode="before")
    @classmethod
    def check_utc(cls, v: datetime) -> datetime:
        res = _validate_utc(v, "computed_at")
        assert res is not None
        return res

    def get_strategy_summary(self, strategy_id: str) -> StrategySummary:
        """Lookup strategy summary by strategy_id."""
        for s in self.strategies:
            if s.strategy_id == strategy_id:
                return s
        raise KeyError(f"Strategy {strategy_id!r} not found in comparison result.")

    def get_pairwise_comparison(self, base_id: str, target_id: str) -> PairwiseComparison:
        """Lookup pairwise comparison for ordered pair (base_id, target_id)."""
        for p in self.pairwise_comparisons:
            if p.base_strategy_id == base_id and p.target_strategy_id == target_id:
                return p
        raise KeyError(
            f"Pairwise comparison for ({base_id!r}, {target_id!r}) not found in comparison result."
        )
