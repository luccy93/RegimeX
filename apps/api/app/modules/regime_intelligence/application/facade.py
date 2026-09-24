"""
RegimeX Regime Intelligence — Application Facade
================================================
Coordinates market data retrieval, feature engineering, regime detection,
regime intelligence profiling, and transition analytics across domain modules.

Architectural Position: ``modules/regime_intelligence/application/facade.py``
- Pure application facade orchestrating domain services.
- Zero dependencies on HTTP, FastAPI, Starlette, or presentation schemas.
- Injected into API endpoints via FastAPI dependency injection.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.market_data.application.service import MarketDataService
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import RegimeModelConfig
from app.modules.regime_detection.infrastructure.ensemble.registry import (
    RegimeModelRegistry,
)
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)
from app.modules.regime_intelligence.domain.errors import (
    InsufficientRegimeDataError,
)
from app.modules.regime_intelligence.domain.models import (
    RegimeAssignment,
    RegimeHistorySummary,
)
from app.modules.regime_transition.domain.errors import (
    InsufficientTransitionDataError,
)
from app.modules.regime_transition.domain.models import (
    TransitionAnalyticsResult,
)
from app.modules.regime_transition.infrastructure.analytics import (
    RegimeTransitionAnalytics,
)

logger = logging.getLogger(__name__)


class MarketIntelligenceFacade:
    """
    Application facade coordinating market data, feature calculation,
    regime detection, intelligence profiling, and transition analytics.
    """

    def __init__(
        self,
        market_service: MarketDataService,
        regime_intelligence_service: RegimeIntelligenceService | None = None,
        transition_analytics: RegimeTransitionAnalytics | None = None,
        detector: RegimeDetector | None = None,
        detector_model_id: str = "kmeans",
        feature_pipeline: FeaturePipeline | None = None,
    ) -> None:
        self._market_service = market_service
        self._regime_intel_service = regime_intelligence_service or RegimeIntelligenceService()
        self._transition_analytics = transition_analytics or RegimeTransitionAnalytics()
        self._detector = detector
        self._detector_model_id = detector_model_id
        self._feature_pipeline = feature_pipeline or FeaturePipeline()

    async def _compute_assignments(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
    ) -> tuple[list[RegimeAssignment], str | None, str | None, str | None, tuple[str, ...]]:
        """
        Execute market data retrieval, feature pipeline, and regime detection.

        Returns:
            tuple of (assignments, model_name, model_version, algorithm, feature_names).
        """
        records, _ = await self._market_service.get_market_data(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            limit=limit,
            offset=0,
        )
        if not records:
            raise InsufficientRegimeDataError(
                required_samples=2,
                available_samples=0,
                details={
                    "symbol": symbol,
                    "message": f"No market data returned for symbol {symbol!r}.",
                },
            )

        feature_set = self._feature_pipeline.compute(records, symbol=symbol, interval=interval)
        matrix = FeatureMatrixBuilder.build(feature_set)

        if matrix.sample_count < 2:
            raise InsufficientRegimeDataError(
                required_samples=2,
                available_samples=matrix.sample_count,
                details={
                    "symbol": symbol,
                    "message": "Insufficient feature observations to detect regimes.",
                },
            )

        n_clusters = min(3, matrix.sample_count)
        if self._detector is not None:
            detector = self._detector
        else:
            detector = RegimeModelRegistry.create(
                self._detector_model_id,
                config=RegimeModelConfig(n_clusters=n_clusters, random_state=42),
            )

        detector.fit(matrix)
        det_service = RegimeDetectionService(detector=detector)
        detection_result = det_service.detect_from_matrix(matrix)

        assignments = RegimeIntelligenceService.from_v08_result(
            detection_result=detection_result,
            feature_matrix=matrix,
        )

        model_name = f"{self._detector_model_id}-baseline"
        model_version = detection_result.model_version
        algorithm = detection_result.algorithm

        return assignments, model_name, model_version, algorithm, matrix.feature_names

    async def get_market_regime(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
    ) -> tuple[RegimeHistorySummary, float | None]:
        """
        Retrieve complete regime intelligence summary for a market instrument.

        Returns:
            tuple of (RegimeHistorySummary, latest_confidence).
        """
        (
            assignments,
            model_name,
            model_version,
            algorithm,
            feature_names,
        ) = await self._compute_assignments(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            limit=limit,
        )

        summary = self._regime_intel_service.summarize_history(
            assignments=assignments,
            model_name=model_name,
            model_version=model_version,
            algorithm=algorithm,
            feature_names=feature_names,
        )

        confidence = assignments[-1].confidence if assignments else None
        return summary, confidence

    async def get_transition_analytics(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: DataInterval = DataInterval.ONE_DAY,
        limit: int = 1000,
    ) -> TransitionAnalyticsResult:
        """
        Retrieve empirical transition analytics for a market instrument.

        Returns:
            TransitionAnalyticsResult container.
        """
        assignments, _, _, _, _ = await self._compute_assignments(
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            limit=limit,
        )

        if len(assignments) < 2:
            raise InsufficientTransitionDataError(
                required_samples=2,
                available_samples=len(assignments),
            )

        return self._transition_analytics.analyze_from_assignments(assignments)
