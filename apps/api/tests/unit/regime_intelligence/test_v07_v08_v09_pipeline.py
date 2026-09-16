"""
Integration Tests — Full Pipeline: V07 Features -> V08 Regime Detection -> V09 Regime Intelligence
===================================================================================================
Validates the complete end-to-end data pipeline from raw OHLCV market bars
through feature engineering, baseline KMeans clustering, and historical regime
intelligence profiling.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    OHLCVRecord,
)
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.models import RegimeModelConfig
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)


def _generate_synthetic_bars(n_bars: int = 80) -> list[OHLCVRecord]:
    """Generates synthetic daily OHLCV bars with predictable cyclic patterns."""
    base_time = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    bars: list[OHLCVRecord] = []
    price = 100.0

    for i in range(n_bars):
        ret = 0.015 * math.sin(i * 0.25)
        close = price * (1.0 + ret)
        high = max(price, close) + 0.50
        low = min(price, close) - 0.50
        volume = 10_000.0 + 1000.0 * (i % 5)

        bars.append(
            OHLCVRecord(
                symbol="SPY",
                timestamp=base_time + timedelta(days=i),
                open=price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                interval=DataInterval.ONE_DAY,
                adjustment_policy=AdjustmentPolicy.RAW,
                source_provider_id="test_provider",
                ingested_at=datetime.now(tz=UTC),
            )
        )
        price = close

    return bars


class TestFullV07V08V09Pipeline:
    """End-to-end integration across V07, V08, and V09."""

    def test_full_pipeline_produces_deterministic_summary(self) -> None:
        """
        Flow:
        1. V07: Compute features from 80 OHLCV bars (FeatureSet).
        2. V08: Build FeatureMatrix (excluding warmup None rows) and detect regimes with KMeans.
        3. V09: Bridge detection result to V09 domain assignments and compute RegimeHistorySummary.
        4. Invariant checks: frequency sum, duration invariants, feature distributions.
        """
        # Step 1: V07 Feature Pipeline
        bars = _generate_synthetic_bars(n_bars=80)
        feat_pipeline = FeaturePipeline()
        feature_set = feat_pipeline.compute(bars)
        assert feature_set.record_count == 80

        # Step 2: V08 Matrix Builder and Detection
        matrix = FeatureMatrixBuilder.build(feature_set)
        assert matrix.sample_count >= 55  # Warm-up rows cleanly excluded

        config = RegimeModelConfig(n_clusters=3, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        detector.fit(matrix)
        det_service = RegimeDetectionService(detector=detector)

        detection_result = det_service.detect_from_matrix(matrix)
        assert detection_result.record_count == matrix.sample_count

        # Step 3: V09 Regime Intelligence Service Ingestion
        intel_service = RegimeIntelligenceService()
        assignments = RegimeIntelligenceService.from_v08_result(
            detection_result=detection_result,
            feature_matrix=matrix,
        )
        assert len(assignments) == matrix.sample_count

        # Step 4: Summarize History
        summary = intel_service.summarize_history(
            assignments=assignments,
            model_name="kmeans-baseline",
            model_version=detection_result.model_version,
            algorithm=detection_result.algorithm,
            feature_names=matrix.feature_names,
        )

        assert summary.total_observations == matrix.sample_count
        assert len(summary.regimes_observed) <= 3
        assert summary.current_regime is not None
        assert summary.current_regime.observations_in_current_run >= 1

        # Check frequency sum invariant
        total_freq = sum(p.frequency for p in summary.regime_profiles.values())
        assert math.isclose(total_freq, 1.0, abs_tol=1e-6)

        # Check duration property invariants for each regime
        for p in summary.regime_profiles.values():
            assert p.min_duration <= p.median_duration <= p.max_duration
            assert p.min_duration <= p.average_duration <= p.max_duration
            assert 0.0 <= p.frequency <= 1.0

        # Provenance metadata preservation
        assert summary.algorithm == "kmeans_baseline"
        assert summary.model_name == "kmeans-baseline"
        assert summary.feature_names == matrix.feature_names
