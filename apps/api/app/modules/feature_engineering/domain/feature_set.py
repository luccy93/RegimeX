"""
RegimeX Feature Engineering — Feature Set Domain Model
======================================================
Defines the reproducible, point-in-time feature output structure for an instrument.

Architectural position: ``domain/feature_set.py`` — pure Python and Pydantic v2 only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.models import FeatureRecord
from app.modules.market_data.domain.models import DataInterval


class FeatureSet(BaseModel):
    """
    Complete, deterministic feature collection for an instrument over an observation window.

    Guarantees:
    - Immutable (frozen).
    - Preserves chronological ordering.
    - Captures full metadata and provenance needed for reproducibility.
    """

    model_config = {"frozen": True}

    symbol: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Canonical ticker/symbol"),
    ]
    interval: DataInterval = Field(description="Bar interval of the underlying data")
    feature_names: tuple[str, ...] = Field(description="Names of all computed features in this set")
    records: tuple[FeatureRecord, ...] = Field(
        default=(),
        description="Chronologically ordered feature records",
    )
    definitions: dict[str, FeatureDefinition] = Field(
        default_factory=dict,
        description="Definitions of all features included in this set",
    )
    version: str = Field(
        default="1.0.0",
        description="Feature pipeline version used to generate this set",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when this feature set was computed",
    )

    @field_validator("computed_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"computed_at must be timezone-aware (got naive: {v!r}).")
        return v

    @property
    def is_empty(self) -> bool:
        """True if the feature set contains zero records."""
        return len(self.records) == 0

    @property
    def record_count(self) -> int:
        """Number of observation records in this feature set."""
        return len(self.records)

    def get_timestamps(self) -> tuple[datetime, ...]:
        """Return all observation timestamps in chronological order."""
        return tuple(r.timestamp for r in self.records)

    def get_series(self, feature_name: str) -> tuple[float | None, ...]:
        """
        Extract the ordered series for a specific feature.

        Raises:
            KeyError: if the feature is not present in feature_names.
        """
        if feature_name not in self.feature_names:
            raise KeyError(f"Feature '{feature_name}' not present in this FeatureSet.")
        return tuple(r.values.get(feature_name) for r in self.records)

    def to_matrix(self) -> list[list[float | None]]:
        """
        Export feature values as a 2D matrix (rows = observations, columns = features).

        Column order strictly matches ``feature_names``.
        """
        return [[record.values.get(name) for name in self.feature_names] for record in self.records]
