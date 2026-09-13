"""
RegimeX Regime Detection — Domain Models Unit Tests
===================================================
Tests validation, immutability, and invariants of domain models.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeDetectionResult,
    RegimeModelConfig,
    RegimeRecord,
)
from pydantic import ValidationError


class TestRegimeModelConfig:
    def test_default_configuration(self) -> None:
        cfg = RegimeModelConfig()
        assert cfg.model_name == "kmeans-baseline"
        assert cfg.model_version == "1.0.0"
        assert cfg.n_clusters == 4
        assert cfg.random_state == 42
        assert cfg.max_iter == 300
        assert cfg.init == "k-means++"
        assert cfg.tol == 1e-4
        assert cfg.feature_names == ()

    def test_custom_valid_configuration(self) -> None:
        cfg = RegimeModelConfig(
            model_name="custom-kmeans",
            model_version="2.1.0",
            n_clusters=3,
            random_state=123,
            max_iter=500,
            init="random",
            tol=1e-5,
            feature_names=("return_1", "volatility_20"),
        )
        assert cfg.n_clusters == 3
        assert cfg.init == "random"
        assert cfg.feature_names == ("return_1", "volatility_20")

    def test_rejects_n_clusters_less_than_two(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 2"):
            RegimeModelConfig(n_clusters=1)
        with pytest.raises(ValidationError, match="greater than or equal to 2"):
            RegimeModelConfig(n_clusters=0)

    def test_rejects_invalid_max_iter(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            RegimeModelConfig(max_iter=0)

    def test_rejects_invalid_tol(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            RegimeModelConfig(tol=0.0)

    def test_rejects_invalid_init_strategy(self) -> None:
        with pytest.raises(ValidationError, match="init strategy 'spectral' must be one of"):
            RegimeModelConfig(init="spectral")

    def test_rejects_duplicate_feature_names(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate feature name detected in config"):
            RegimeModelConfig(feature_names=("return_1", "return_1"))

    def test_rejects_empty_feature_name_string(self) -> None:
        with pytest.raises(ValidationError, match="Feature names must be non-empty strings"):
            RegimeModelConfig(feature_names=("return_1", "   "))

    def test_config_is_frozen(self) -> None:
        cfg = RegimeModelConfig()
        with pytest.raises(ValidationError):
            cfg.n_clusters = 5  # type: ignore[misc]


class TestFeatureMatrix:
    def _make_valid_matrix(self) -> FeatureMatrix:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        timestamps = tuple(base_time + timedelta(days=i) for i in range(5))
        feature_names = ("feat_a", "feat_b")
        values = (
            (1.0, 2.0),
            (1.5, 2.5),
            (2.0, 3.0),
            (2.5, 3.5),
            (3.0, 4.0),
        )
        return FeatureMatrix(
            timestamps=timestamps,
            feature_names=feature_names,
            values=values,
        )

    def test_valid_feature_matrix_properties(self) -> None:
        fm = self._make_valid_matrix()
        assert fm.sample_count == 5
        assert fm.feature_count == 2
        assert not fm.is_empty
        assert fm.get_column("feat_a") == (1.0, 1.5, 2.0, 2.5, 3.0)
        assert fm.get_column("feat_b") == (2.0, 2.5, 3.0, 3.5, 4.0)

    def test_get_column_unknown_feature_raises_key_error(self) -> None:
        fm = self._make_valid_matrix()
        with pytest.raises(KeyError, match="Feature 'non_existent' not in matrix features"):
            fm.get_column("non_existent")

    def test_rejects_row_count_mismatch(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        timestamps = (base_time, base_time + timedelta(days=1))
        # 3 rows of values, but only 2 timestamps
        values = ((1.0, 2.0), (1.5, 2.5), (2.0, 3.0))
        with pytest.raises(ValidationError, match="Row dimension mismatch"):
            FeatureMatrix(timestamps=timestamps, feature_names=("a", "b"), values=values)

    def test_rejects_column_count_mismatch(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        timestamps = (base_time,)
        # 1 column of values, but 2 feature names
        values = ((1.0,),)
        with pytest.raises(ValidationError, match="Column dimension mismatch at row 0"):
            FeatureMatrix(timestamps=timestamps, feature_names=("a", "b"), values=values)

    def test_rejects_naive_timestamps(self) -> None:
        timestamps = (datetime(2026, 1, 1, 0, 0),)  # naive
        values = ((1.0,),)
        with pytest.raises(ValidationError, match="naive"):
            FeatureMatrix(timestamps=timestamps, feature_names=("a",), values=values)

    def test_rejects_non_increasing_timestamps(self) -> None:
        t1 = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)  # inverted
        with pytest.raises(ValidationError, match="strictly increasing"):
            FeatureMatrix(timestamps=(t1, t2), feature_names=("a",), values=((1.0,), (2.0,)))

    def test_rejects_nan_values(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        with pytest.raises(ValidationError, match="NaN detected"):
            FeatureMatrix(
                timestamps=(base_time,),
                feature_names=("a",),
                values=((float("nan"),),),
            )

    def test_rejects_infinite_values(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        with pytest.raises(ValidationError, match="Infinite value"):
            FeatureMatrix(
                timestamps=(base_time,),
                feature_names=("a",),
                values=((float("inf"),),),
            )
        with pytest.raises(ValidationError, match="Infinite value"):
            FeatureMatrix(
                timestamps=(base_time,),
                feature_names=("a",),
                values=((float("-inf"),),),
            )

    def test_rejects_empty_feature_names(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        with pytest.raises(ValidationError, match="at least one feature name"):
            FeatureMatrix(timestamps=(base_time,), feature_names=(), values=((),))


class TestRegimeDetectionResult:
    def test_result_series_extraction(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        records = (
            RegimeRecord(
                timestamp=base_time,
                cluster_id=1,
                canonical_regime_id=0,
                canonical_regime_label="REGIME_0",
                probabilities=(0.8, 0.2),
            ),
            RegimeRecord(
                timestamp=base_time + timedelta(days=1),
                cluster_id=0,
                canonical_regime_id=1,
                canonical_regime_label="REGIME_1",
                probabilities=(0.1, 0.9),
            ),
        )
        res = RegimeDetectionResult(
            model_version="1.0.0",
            algorithm="kmeans_baseline",
            feature_names=("f1", "f2"),
            records=records,
        )
        assert res.record_count == 2
        assert not res.is_empty
        assert res.get_timestamps() == (base_time, base_time + timedelta(days=1))
        assert res.get_regime_series() == (0, 1)
        assert res.get_labels_series() == ("REGIME_0", "REGIME_1")
        assert res.get_raw_cluster_series() == (1, 0)
