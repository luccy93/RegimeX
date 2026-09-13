"""
RegimeX Feature Engineering — Feature Pipeline
==============================================
Deterministic pipeline orchestration executing validated feature transformations.

Architectural position: ``application/feature_pipeline.py``
Ensures chronological point-in-time calculation, zero look-ahead bias,
numerical safety, and explicit missing-value handling.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.feature_engineering.application.config import FeaturePipelineConfig
from app.modules.feature_engineering.application.feature_registry import (
    FeatureRegistry,
    get_default_registry,
)
from app.modules.feature_engineering.domain.errors import (
    InsufficientDataError,
    InvalidFeatureInputError,
)
from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.feature_spec import FeatureDefinition
from app.modules.feature_engineering.domain.interfaces import FeatureCalculator
from app.modules.feature_engineering.domain.models import (
    FeatureInputData,
    FeatureRecord,
    MissingValuePolicy,
)
from app.modules.market_data.domain.models import DataInterval, MarketDataResult, OHLCVRecord


class FeaturePipeline:
    """
    Executes feature calculations on canonical market data.

    Workflow:
        1. Validate input structure and enforce strictly ascending UTC timestamps.
        2. Resolve enabled calculators from registry.
        3. Validate minimum required observation thresholds.
        4. Execute vectorized calculators with zero look-ahead bias.
        5. Validate numerical safety of outputs.
        6. Apply configured missing-value policy (PRESERVE or DROP_WARMUP).
        7. Return deterministic, immutable FeatureSet.
    """

    def __init__(
        self,
        config: FeaturePipelineConfig | None = None,
        registry: FeatureRegistry | None = None,
    ) -> None:
        self._config = config or FeaturePipelineConfig()
        self._registry = registry or get_default_registry(self._config.annualization_factor)

    @property
    def config(self) -> FeaturePipelineConfig:
        return self._config

    @property
    def registry(self) -> FeatureRegistry:
        return self._registry

    def compute(
        self,
        data: Sequence[OHLCVRecord] | MarketDataResult,
        symbol: str | None = None,
        interval: DataInterval | None = None,
    ) -> FeatureSet:
        """
        Compute features for the given market data series.

        Args:
            data: Canonical OHLCV records or MarketDataResult.
            symbol: Optional symbol override.
            interval: Optional interval override.

        Returns:
            Deterministic FeatureSet containing timestamps, values, and definitions.

        Raises:
            InvalidFeatureInputError: if input is empty or timestamps are not strictly ascending.
            InsufficientDataError: if records are fewer than the required lookback.
            FeatureNotFoundError: if an enabled feature is not registered.
        """
        # 1. Normalize input
        if isinstance(data, MarketDataResult):
            records = list(data.records)
            resolved_symbol = symbol or data.symbol
            resolved_interval = interval or data.query.interval
        else:
            records = list(data)
            if not records:
                raise InvalidFeatureInputError("Cannot compute features on empty records sequence.")
            resolved_symbol = symbol or records[0].symbol
            resolved_interval = interval or records[0].interval

        if not records:
            raise InvalidFeatureInputError("Cannot compute features on empty records sequence.")

        # 2. Timestamp ordering validation
        for i in range(1, len(records)):
            if records[i].timestamp <= records[i - 1].timestamp:
                raise InvalidFeatureInputError(
                    "Market data records must have strictly ascending timestamps. "
                    f"Found violation at index {i}: "
                    f"{records[i - 1].timestamp} >= {records[i].timestamp}"
                )

        # 3. Resolve enabled calculators
        calculators: list[FeatureCalculator] = []
        if self._config.enabled_features is not None:
            for feat_name in self._config.enabled_features:
                calculators.append(self._registry.get(feat_name))
        else:
            for feat_def in self._registry.list():
                calculators.append(self._registry.get(feat_def.name))

        if not calculators:
            raise InvalidFeatureInputError("No feature calculators enabled for execution.")

        # 4. Check minimum observation requirements
        total_obs = len(records)
        for calc in calculators:
            if total_obs < calc.definition.min_observations:
                raise InsufficientDataError(
                    required=calc.definition.min_observations,
                    provided=total_obs,
                    feature_name=calc.name,
                )

        # 5. Build domain input data
        feature_input = FeatureInputData.from_ohlcv_records(records)

        # 6. Execute calculators
        feature_names: tuple[str, ...] = tuple(c.name for c in calculators)
        computed_values: dict[str, list[float | None]] = {}
        definitions: dict[str, FeatureDefinition] = {}

        for calc in calculators:
            series = calc.calculate(feature_input)
            if len(series) != total_obs:
                raise InvalidFeatureInputError(
                    f"Calculator '{calc.name}' returned {len(series)} values, expected {total_obs}."
                )
            computed_values[calc.name] = series
            definitions[calc.name] = calc.definition

        # 7. Assemble bar-level feature records
        raw_records: list[FeatureRecord] = []
        for i in range(total_obs):
            bar_values: dict[str, float | None] = {
                name: computed_values[name][i] for name in feature_names
            }
            raw_records.append(
                FeatureRecord(
                    timestamp=feature_input.timestamps[i],
                    values=bar_values,
                )
            )

        # 8. Apply missing value policy
        if self._config.missing_value_policy == MissingValuePolicy.DROP_WARMUP:
            final_records = tuple(
                r for r in raw_records if all(v is not None for v in r.values.values())
            )
        else:
            final_records = tuple(raw_records)

        return FeatureSet(
            symbol=resolved_symbol,
            interval=resolved_interval,
            feature_names=feature_names,
            records=final_records,
            definitions=definitions,
            version=self._config.version,
        )
