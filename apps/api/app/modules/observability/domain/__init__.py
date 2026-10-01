"""
RegimeX Observability — Domain Package
======================================
Canonical domain models, health statuses, and drift algorithms.
"""

from app.modules.observability.domain.drift import (
    compute_jensen_shannon_divergence,
    compute_population_stability_index,
    compute_total_variation_distance,
    evaluate_feature_drift,
    evaluate_regime_distribution_drift,
)
from app.modules.observability.domain.enums import (
    DriftMethod,
    HealthStatus,
    PipelineStage,
    ProviderStatus,
)
from app.modules.observability.domain.models import (
    DataCompletenessSnapshot,
    DataFreshnessSnapshot,
    DataHealthSnapshot,
    DataValiditySnapshot,
    DistributionDriftSnapshot,
    ModelConfidenceSnapshot,
    ModelExecutionSnapshot,
    ModelHealthSnapshot,
    ModelStabilitySnapshot,
    PipelineHealthSnapshot,
    PipelineStageHealth,
    PredictionValiditySnapshot,
    ProviderHealthSnapshot,
    RegimeDistributionSnapshot,
    SystemHealthSummarySnapshot,
)

__all__ = [
    "DataCompletenessSnapshot",
    "DataFreshnessSnapshot",
    "DataHealthSnapshot",
    "DataValiditySnapshot",
    "DistributionDriftSnapshot",
    "DriftMethod",
    "HealthStatus",
    "ModelConfidenceSnapshot",
    "ModelExecutionSnapshot",
    "ModelHealthSnapshot",
    "ModelStabilitySnapshot",
    "PipelineHealthSnapshot",
    "PipelineStageHealth",
    "PipelineStage",
    "PredictionValiditySnapshot",
    "ProviderHealthSnapshot",
    "ProviderStatus",
    "RegimeDistributionSnapshot",
    "SystemHealthSummarySnapshot",
    "compute_jensen_shannon_divergence",
    "compute_population_stability_index",
    "compute_total_variation_distance",
    "evaluate_feature_drift",
    "evaluate_regime_distribution_drift",
]
