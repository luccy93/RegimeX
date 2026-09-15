"""
Unit Tests — V08 to V09 Integration
====================================
Validates end-to-end data flow from V08 regime detection outputs into V09
historical regime intelligence summaries and profiles.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.regime_detection import (
    FeatureMatrix,
    KMeansRegimeDetector,
    RegimeDetectionService,
    RegimeModelConfig,
)
from app.modules.regime_intelligence.application.service import (
    RegimeIntelligenceService,
)


def _ts(offset_hours: int = 0) -> datetime:
    return datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


class TestV08V09Integration:
    """End-to-end integration between V08 detection outputs and V09 intelligence."""

    def test_full_pipeline_v08_to_v09_summary(self) -> None:
        """
        Flow:
        1. Build a valid V08 FeatureMatrix with 20 observations.
        2. Fit a V08 KMeansRegimeDetector.
        3. Predict RegimeDetectionResult.
        4. Ingest into RegimeIntelligenceService via from_v08_result.
        5. Generate complete RegimeHistorySummary and verify descriptive metrics.
        """
        n_samples = 20
        timestamps = tuple(_ts(i) for i in range(n_samples))
        feature_names = ("return_1", "volatility_20")

        # Two distinct clusters: first 10 low vol / positive return,
        # second 10 high vol / negative return
        values: list[tuple[float, ...]] = []
        for i in range(10):
            values.append((0.01 + i * 0.001, 0.10 + i * 0.001))
        for i in range(10):
            values.append((-0.02 - i * 0.001, 0.30 + i * 0.001))

        matrix = FeatureMatrix(
            timestamps=timestamps,
            feature_names=feature_names,
            values=tuple(values),
        )

        # 1. Fit V08 detector
        config = RegimeModelConfig(n_clusters=2, random_state=42)
        detector = KMeansRegimeDetector(config)
        detector.fit(matrix)
        detection_service = RegimeDetectionService(detector=detector)

        # 2. Predict regimes
        detection_result = detection_service.detect_from_matrix(matrix)
        assert len(detection_result.records) == 20

        # 3. Transform to V09 domain assignments
        intel_service = RegimeIntelligenceService()
        assignments = RegimeIntelligenceService.from_v08_result(
            detection_result=detection_result,
            feature_matrix=matrix,
        )
        assert len(assignments) == 20
        assert assignments[0].features["return_1"] == matrix.values[0][0]

        # 4. Summarize history
        summary = intel_service.summarize_history(
            assignments=assignments,
            model_name="kmeans-baseline",
            model_version=detection_result.model_version,
            algorithm=detection_result.algorithm,
            feature_names=feature_names,
        )

        assert summary.total_observations == 20
        assert len(summary.regimes_observed) == 2
        assert summary.current_regime is not None
        assert summary.current_regime.observations_in_current_run >= 1

        # Check that profiles contain valid statistics for both features
        for r_id in summary.regimes_observed:
            profile = summary.regime_profiles[r_id]
            assert 0.0 < profile.frequency < 1.0
            assert "return_1" in profile.feature_statistics
            assert "volatility_20" in profile.feature_statistics
            ret_stat = profile.feature_statistics["return_1"]
            assert ret_stat.mean is not None
            assert ret_stat.observation_count > 0

        # Invariant: frequencies sum to 1.0
        total_freq = sum(p.frequency for p in summary.regime_profiles.values())
        assert abs(total_freq - 1.0) < 1e-6
