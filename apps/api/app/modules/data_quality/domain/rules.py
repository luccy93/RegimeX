"""
RegimeX Data Quality — Rule Abstraction
=======================================
Defines the base interface and context for individual data quality rules.

Design Goals:
- Composable, single-responsibility rules.
- Deterministic execution: rules accept an explicit RuleContext containing
  the dataset, calendar, and reference clock.
- Non-mutating: rules only evaluate and emit QualityIssue objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.data_quality.domain.calendar import TradingCalendar
from app.modules.data_quality.domain.models import (
    QualityCategory,
    QualityIssue,
    QualitySeverity,
)
from app.modules.market_data.domain.models import MarketDataQuery, OHLCVRecord


class RuleContext(BaseModel):
    """
    Execution context provided to data quality rules.

    Holds the query, records, exchange calendar, reference clock, and configuration.
    """

    model_config = {"arbitrary_types_allowed": True, "frozen": True}

    query: MarketDataQuery
    records: tuple[OHLCVRecord, ...]
    calendar: TradingCalendar
    reference_time: datetime = Field(
        description="Deterministic reference time for freshness/future checks."
    )
    options: dict[str, Any] = Field(
        default_factory=dict, description="Rule-specific tuning options."
    )

    @field_validator("records", mode="plain")
    @classmethod
    def _validate_records(cls, v: object) -> tuple[OHLCVRecord, ...]:
        if isinstance(v, tuple):
            return v
        if isinstance(v, (list, set)):
            return tuple(v)
        raise ValueError(f"Expected sequence of OHLCVRecord, got {type(v)}")

    @property
    def symbol(self) -> str:
        return self.query.instrument.symbol

    @property
    def is_empty(self) -> bool:
        return len(self.records) == 0


class DataQualityRule(ABC):
    """
    Abstract base class for all data quality rules.

    Contributors implement new rules by subclassing this and implementing validate().
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Stable rule identifier, e.g. 'DQ-OHLC-001'."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Brief descriptive name of the rule."""
        ...

    @property
    @abstractmethod
    def category(self) -> QualityCategory:
        """The primary category of data quality checked by this rule."""
        ...

    @property
    @abstractmethod
    def default_severity(self) -> QualitySeverity:
        """Default severity level when a violation is triggered."""
        ...

    @abstractmethod
    def validate(self, context: RuleContext) -> list[QualityIssue]:
        """
        Evaluate records in context and return any detected quality issues.

        Must not mutate context.records or any domain state.
        """
        ...
