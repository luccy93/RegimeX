"""
RegimeX Regime Detection — Application Service Integration Tests
================================================================
Tests end-to-end orchestration connecting V07 FeaturePipeline output
with the RegimeDetectionService and KMeansRegimeDetector.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.feature_engineering.application.feature_pipeline import FeaturePipeline
from app.modules.market_data.domain.models import (
    AdjustmentPolicy,
    DataInterval,
    OHLCVRecord,
)
from app.modules.regime_detection.application.services import RegimeDetectionService
from app.modules.regime_detection.domain.errors import ModelNotFittedError
from app.modules.regime_detection.domain.models import (
    ModelState,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


def _generate_synthetic_market_data(n_bars: int = 60) -> list[OHLCVRecord]:
    """Generates 60 realistic chronological daily bars."""
    base_time = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    bars = []
    price = 100.0

    for i in range(n_bars):
        ret = 0.01 * math.sin(i * 0.2)
        close = price * (1.0 + ret)
        high = max(price, close) + 0.5
        low = min(price, close) - 0.5
        volume = 10000.0 + 500.0 * (i % 7)

        bar = OHLCVRecord(
            symbol="SPY",
            timestamp=base_time + timedelta(days=i),
            open=price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            interval=DataInterval.ONE_DAY,
            adjustment_policy=AdjustmentPolicy.RAW,
            source_provider_id="test",
            ingested_at=datetime.now(tz=UTC),
        )
        bars.append(bar)
        price = close

    return bars


class TestRegimeDetectionServiceIntegration:
    def test_end_to_end_v07_feature_pipeline_integration(self) -> None:
        """
        Generates bars, computes all V07 baseline features, fits the KMeans detector,
        and generates canonical regime detection records.
        """
        bars = _generate_synthetic_market_data(n_bars=60)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        assert feature_set.record_count == 60
        assert len(feature_set.feature_names) >= 15

        config = RegimeModelConfig(n_clusters=3, random_state=42)
        detector = KMeansRegimeDetector(config=config)
        service = RegimeDetectionService(detector=detector)

        assert service.detector.state == ModelState.UNFITTED

        # Execute full fit and detection workflow
        fitted_detector, result = service.fit_and_detect(feature_set)

        assert fitted_detector is detector
        assert detector.state == ModelState.FITTED
        assert not result.is_empty

        # 60 total bars minus 20 warm-up bars for 20-period indicators = 40 complete observations
        assert result.record_count == 40
        assert len(result.records) == 40

        # Verify record structure
        for record in result.records:
            assert 0 <= record.canonical_regime_id < 3
            assert record.canonical_regime_label in {"REGIME_0", "REGIME_1", "REGIME_2"}
            assert record.probabilities is not None
            assert len(record.probabilities) == 3
            assert math.isclose(sum(record.probabilities), 1.0, rel_tol=1e-6)

        # Subsequent inference on same feature set
        result_subsequent = service.detect_from_feature_set(feature_set)
        assert result_subsequent.get_regime_series() == result.get_regime_series()

    def test_fit_and_detect_with_feature_subset(self) -> None:
        bars = _generate_synthetic_market_data(n_bars=40)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        _, result = service.fit_and_detect(
            feature_set,
            feature_names=["return_1", "volatility_10"],
        )

        assert result.feature_names == ("return_1", "volatility_10")
        assert not result.is_empty

    def test_detect_before_fit_raises_typed_error(self) -> None:
        bars = _generate_synthetic_market_data(n_bars=30)
        pipeline = FeaturePipeline()
        feature_set = pipeline.compute(bars)

        service = RegimeDetectionService()
        with pytest.raises(ModelNotFittedError):
            service.detect_from_feature_set(feature_set)
