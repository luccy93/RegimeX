"""
RegimeX Feature Engineering — Application Services
==================================================
Application services providing unified interfaces for feature calculation and catalogue queries.

Architectural position: ``application/services.py``
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.feature_engineering.application.config import FeaturePipelineConfig
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.feature_engineering.application.feature_registry import (
    FeatureRegistry,
    get_default_registry,
)
from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.market_data.domain.models import DataInterval, MarketDataResult, OHLCVRecord


class FeatureService:
    """
    High-level application service for quantitative feature generation and discovery.
    """

    def __init__(self, registry: FeatureRegistry | None = None) -> None:
        self._registry = registry or get_default_registry()

    @property
    def registry(self) -> FeatureRegistry:
        return self._registry

    def list_available_features(self) -> list[FeatureDefinition]:
        """Return metadata definitions of all registered features."""
        return self._registry.list()

    def get_feature_definition(self, name: str) -> FeatureDefinition:
        """Retrieve definition for a specific feature."""
        return self._registry.get(name).definition

    def compute_features(
        self,
        data: Sequence[OHLCVRecord] | MarketDataResult,
        config: FeaturePipelineConfig | None = None,
        symbol: str | None = None,
        interval: DataInterval | None = None,
    ) -> FeatureSet:
        """
        Execute feature computation pipeline over the provided market data.
        """
        pipeline = FeaturePipeline(config=config, registry=self._registry)
        return pipeline.compute(data, symbol=symbol, interval=interval)
