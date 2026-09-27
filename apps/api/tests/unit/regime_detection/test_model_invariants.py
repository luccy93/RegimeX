"""
RegimeX Regime Detection — Model Invariants & Numerical Stability Tests
======================================================================
Verifies:
- GMM posterior probabilities sum to 1.0 within numerical tolerance
- HMM temporal order preservation and posterior probability normalization
- KMeans deterministic cluster canonicalization
- Ensemble failure policies and deterministic consensus aggregation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.modules.regime_detection.domain.errors import (
    EnsembleModelUnavailableError,
    InsufficientUsableModelsError,
)
from app.modules.regime_detection.domain.models import (
    AggregationStrategy,
    EnsembleModelConfig,
    FailurePolicy,
    FeatureMatrix,
    GMMModelConfig,
    HMMModelConfig,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.ensemble import (
    RegimeModelEnsemble,
)
from app.modules.regime_detection.infrastructure.models.gmm import (
    GaussianMixtureRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.hmm import (
    GaussianHMMRegimeDetector,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)


@pytest.fixture
def synthetic_features() -> FeatureMatrix:
    rng = np.random.default_rng(42)
    n_samples = 100
    dates = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(n_samples)]
    # 2 features: return and volatility
    data = rng.standard_normal((n_samples, 2))
    values = tuple(tuple(float(v) for v in row) for row in data)
    return FeatureMatrix(
        timestamps=tuple(dates),
        feature_names=("return_1d", "volatility_20d"),
        values=values,
    )


class TestGMMInvariants:
    def test_posterior_probabilities_sum_to_one(self, synthetic_features: FeatureMatrix) -> None:
        detector = GaussianMixtureRegimeDetector(GMMModelConfig(n_regimes=3, random_state=42))
        detector.fit(synthetic_features)
        probs = detector.predict_proba(synthetic_features)

        assert len(probs) == synthetic_features.sample_count
        for row in probs:
            assert abs(sum(row) - 1.0) < 1e-5


class TestHMMInvariants:
    def test_hmm_posterior_probabilities_sum_to_one(
        self, synthetic_features: FeatureMatrix
    ) -> None:
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_regimes=3, random_state=42))
        detector.fit(synthetic_features)
        probs = detector.predict_proba(synthetic_features)

        assert len(probs) == synthetic_features.sample_count
        for row in probs:
            assert abs(sum(row) - 1.0) < 1e-4

    def test_hmm_preserves_temporal_length(self, synthetic_features: FeatureMatrix) -> None:
        detector = GaussianHMMRegimeDetector(HMMModelConfig(n_regimes=2, random_state=42))
        detector.fit(synthetic_features)
        pred = detector.predict(synthetic_features)
        assert len(pred) == synthetic_features.sample_count


class TestKMeansInvariants:
    def test_kmeans_deterministic_canonicalization(self, synthetic_features: FeatureMatrix) -> None:
        d1 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=123))
        d2 = KMeansRegimeDetector(RegimeModelConfig(n_clusters=3, random_state=123))

        p1 = d1.fit(synthetic_features).predict(synthetic_features)
        p2 = d2.fit(synthetic_features).predict(synthetic_features)

        assert p1 == p2
        assert len(d1.cluster_profiles) == 3
        assert len(d2.cluster_profiles) == 3
        for c1, c2 in zip(d1.cluster_profiles, d2.cluster_profiles, strict=True):
            assert c1.canonical_regime_id == c2.canonical_regime_id
            assert c1.canonical_regime_label == c2.canonical_regime_label


class TestEnsembleInvariants:
    def test_ensemble_fail_fast_on_unregistered_model(
        self, synthetic_features: FeatureMatrix
    ) -> None:
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "non_existent_model"),
            failure_policy=FailurePolicy.FAIL_FAST,
        )
        ensemble = RegimeModelEnsemble(config=config, models={"kmeans": KMeansRegimeDetector()})

        with pytest.raises(EnsembleModelUnavailableError):
            ensemble.fit(synthetic_features)

    def test_ensemble_insufficient_usable_models(self, synthetic_features: FeatureMatrix) -> None:
        # Require 2 models, but only 1 is registered / usable
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm"),
            minimum_required_models=2,
            failure_policy=FailurePolicy.SKIP_UNAVAILABLE,
        )
        # Only provide kmeans, missing gmm
        ensemble = RegimeModelEnsemble(
            config=config,
            models={"kmeans": KMeansRegimeDetector()},
        )

        with pytest.raises(InsufficientUsableModelsError):
            ensemble.fit(synthetic_features)

    def test_ensemble_fit_and_predict_determinism(self, synthetic_features: FeatureMatrix) -> None:
        config = EnsembleModelConfig(
            enabled_models=("kmeans", "gmm"),
            aggregation_strategy=AggregationStrategy.WEIGHTED_VOTING,
        )
        e1 = RegimeModelEnsemble(config=config)
        e2 = RegimeModelEnsemble(config=config)

        res1 = e1.fit(synthetic_features).predict_ensemble(synthetic_features)
        res2 = e2.fit(synthetic_features).predict_ensemble(synthetic_features)

        assert res1.ensemble_regimes == res2.ensemble_regimes
        assert res1.confidence_scores == res2.confidence_scores
