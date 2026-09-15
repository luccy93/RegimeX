"""
RegimeX Regime Detection — Feature Matrix Validation Hardening Tests
====================================================================
Extended validation tests for FeatureMatrix domain model and FeatureMatrixBuilder.

Tests beyond Commit 01 coverage:
1. Duplicate timestamps in FeatureMatrix.
2. FeatureMatrix with exactly one row.
3. Fewer rows than clusters — domain model vs builder behavior.
4. Duplicate feature names in FeatureMatrix (domain model-level rejection).
5. Feature name with internal whitespace.
6. Extra feature columns not in model config.
7. Feature ordering test: alphabetical normalization vs custom ordering.
8. FeatureMatrixBuilder deduplication of requested features.
9. Non-UTC timezone-aware timestamps.
10. Malformed timestamps (naive).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.models import FeatureRecord
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.domain.errors import InvalidFeatureMatrixError
from app.modules.regime_detection.domain.models import (
    FeatureMatrix,
    RegimeModelConfig,
)
from app.modules.regime_detection.infrastructure.models.kmeans import (
    KMeansRegimeDetector,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _ts(i: int) -> datetime:
    return _BASE_TIME + timedelta(days=i)


# ---------------------------------------------------------------------------
# Class 1: FeatureMatrix domain model hardening
# ---------------------------------------------------------------------------


class TestFeatureMatrixDomainModelHardening:
    """Extended validation tests for the FeatureMatrix domain model."""

    def test_single_row_matrix_is_valid(self) -> None:
        """A FeatureMatrix with exactly one row must be constructible."""
        matrix = FeatureMatrix(
            timestamps=(_ts(0),),
            feature_names=("feat_a", "feat_b"),
            values=((1.0, 2.0),),
        )
        assert matrix.sample_count == 1
        assert not matrix.is_empty

    def test_empty_matrix_is_valid(self) -> None:
        """A FeatureMatrix with zero rows must be constructible (is_empty == True)."""
        matrix = FeatureMatrix(
            timestamps=(),
            feature_names=("feat_a", "feat_b"),
            values=(),
        )
        assert matrix.is_empty
        assert matrix.sample_count == 0

    def test_duplicate_timestamps_rejected(self) -> None:
        """Duplicate timestamps must be rejected (timestamps must be strictly increasing)."""
        t = _ts(0)
        with pytest.raises(ValidationError, match="strictly increasing"):
            FeatureMatrix(
                timestamps=(t, t),  # identical timestamps
                feature_names=("feat_a",),
                values=((1.0,), (2.0,)),
            )

    def test_out_of_order_timestamps_rejected(self) -> None:
        """Timestamps that decrease must be rejected."""
        t1 = _ts(5)
        t2 = _ts(3)  # before t1
        with pytest.raises(ValidationError, match="strictly increasing"):
            FeatureMatrix(
                timestamps=(t1, t2),
                feature_names=("feat_a",),
                values=((1.0,), (2.0,)),
            )

    def test_naive_timestamps_rejected(self) -> None:
        """Naive (timezone-unaware) timestamps must be rejected."""
        naive_ts = datetime(2026, 6, 1, 0, 0)  # no tzinfo
        with pytest.raises(ValidationError, match="naive"):
            FeatureMatrix(
                timestamps=(naive_ts,),
                feature_names=("feat_a",),
                values=((1.0,),),
            )

    def test_non_utc_timezone_aware_timestamps_accepted(self) -> None:
        """Non-UTC timezone-aware timestamps must be accepted (they have tzinfo)."""
        eastern = timezone(timedelta(hours=-5))
        ts = datetime(2026, 6, 1, 10, 0, tzinfo=eastern)
        matrix = FeatureMatrix(
            timestamps=(ts,),
            feature_names=("feat_a",),
            values=((1.5,),),
        )
        assert matrix.sample_count == 1

    def test_duplicate_feature_names_in_matrix_rejected(self) -> None:
        """Duplicate feature names in FeatureMatrix must be rejected."""
        with pytest.raises(ValidationError, match="Duplicate feature name"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("feat_a", "feat_a"),
                values=((1.0, 2.0),),
            )

    def test_whitespace_only_feature_name_rejected(self) -> None:
        """A feature name that is only whitespace must be rejected."""
        with pytest.raises(ValidationError, match="non-empty string"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("   ",),
                values=((1.0,),),
            )

    def test_row_column_dimension_mismatch_rejected(self) -> None:
        """Providing N rows in values but M ≠ N timestamps must be rejected."""
        with pytest.raises(ValidationError, match="Row dimension mismatch"):
            FeatureMatrix(
                timestamps=(_ts(0), _ts(1)),  # 2 timestamps
                feature_names=("feat_a",),
                values=((1.0,), (2.0,), (3.0,)),  # 3 rows
            )

    def test_column_count_mismatch_rejected(self) -> None:
        """A row with wrong number of columns must be rejected."""
        with pytest.raises(ValidationError, match="Column dimension mismatch"):
            FeatureMatrix(
                timestamps=(_ts(0),),
                feature_names=("feat_a", "feat_b"),  # 2 features
                values=((1.0,),),  # 1 column
            )

    def test_get_column_returns_correct_values(self) -> None:
        """get_column() must return the correct ordered series for a feature."""
        matrix = FeatureMatrix(
            timestamps=(_ts(0), _ts(1), _ts(2)),
            feature_names=("return_1", "volatility_20"),
            values=((0.01, 0.10), (0.02, 0.12), (0.03, 0.11)),
        )
        assert matrix.get_column("return_1") == (0.01, 0.02, 0.03)
        assert matrix.get_column("volatility_20") == (0.10, 0.12, 0.11)

    def test_get_column_unknown_feature_raises_key_error(self) -> None:
        """get_column() with an unknown feature name must raise KeyError."""
        matrix = FeatureMatrix(
            timestamps=(_ts(0),),
            feature_names=("feat_a",),
            values=((1.0,),),
        )
        with pytest.raises(KeyError, match="not in matrix features"):
            matrix.get_column("non_existent")


# ---------------------------------------------------------------------------
# Class 2: FeatureMatrixBuilder hardening
# ---------------------------------------------------------------------------


class TestFeatureMatrixBuilderHardening:
    """Extended FeatureMatrixBuilder validation beyond Commit 01 coverage."""

    def _make_fset(
        self,
        records_data: list[tuple[datetime, dict[str, float | None]]],
        feature_names: tuple[str, ...],
    ) -> FeatureSet:
        records = tuple(FeatureRecord(timestamp=ts, values=vals) for ts, vals in records_data)
        return FeatureSet(
            symbol="TEST",
            interval=DataInterval.ONE_DAY,
            feature_names=feature_names,
            records=records,
        )

    def test_alphabetical_ordering_when_feature_names_not_specified(self) -> None:
        """Without feature_names argument, FeatureMatrixBuilder sorts alphabetically."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"volatility_20": 0.12, "return_1": 0.01, "momentum_10": 0.03}),
            (_ts(1), {"volatility_20": 0.13, "return_1": 0.02, "momentum_10": 0.04}),
        ]
        fset = self._make_fset(records_data, ("volatility_20", "return_1", "momentum_10"))
        matrix = FeatureMatrixBuilder.build(fset)
        assert matrix.feature_names == ("momentum_10", "return_1", "volatility_20")

    def test_custom_feature_order_preserved(self) -> None:
        """With feature_names argument, the specified order must be preserved."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"volatility_20": 0.12, "return_1": 0.01}),
            (_ts(1), {"volatility_20": 0.13, "return_1": 0.02}),
        ]
        fset = self._make_fset(records_data, ("volatility_20", "return_1"))
        matrix = FeatureMatrixBuilder.build(fset, feature_names=["volatility_20", "return_1"])
        assert matrix.feature_names == ("volatility_20", "return_1")
        assert matrix.values[0] == (0.12, 0.01)

    def test_duplicate_feature_names_in_request_deduplicated(self) -> None:
        """Duplicate feature names in the request list must be deduplicated
        (first occurrence wins)."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": 0.01, "volatility_20": 0.10}),
        ]
        fset = self._make_fset(records_data, ("return_1", "volatility_20"))
        # Request ["return_1", "volatility_20", "return_1"] — duplicate
        matrix = FeatureMatrixBuilder.build(
            fset, feature_names=["return_1", "volatility_20", "return_1"]
        )
        # Deduplicated to ("return_1", "volatility_20")
        assert matrix.feature_names == ("return_1", "volatility_20")

    def test_extra_feature_in_matrix_not_requested(self) -> None:
        """
        If the FeatureSet has extra features not in the request, they must be excluded.
        """
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": 0.01, "volatility_20": 0.10, "momentum_10": 0.03}),
            (_ts(1), {"return_1": 0.02, "volatility_20": 0.11, "momentum_10": 0.04}),
        ]
        fset = self._make_fset(records_data, ("return_1", "volatility_20", "momentum_10"))
        matrix = FeatureMatrixBuilder.build(fset, feature_names=["return_1", "volatility_20"])
        assert matrix.feature_names == ("return_1", "volatility_20")
        assert matrix.feature_count == 2

    def test_missing_requested_feature_raises_typed_error(self) -> None:
        """Requesting a feature not in FeatureSet must raise InvalidFeatureMatrixError."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": 0.01}),
        ]
        fset = self._make_fset(records_data, ("return_1",))
        with pytest.raises(InvalidFeatureMatrixError, match="Requested features not present"):
            FeatureMatrixBuilder.build(fset, feature_names=["return_1", "non_existent"])

    def test_empty_feature_name_in_request_raises_typed_error(self) -> None:
        """An empty string in feature_names request must raise InvalidFeatureMatrixError."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": 0.01}),
        ]
        fset = self._make_fset(records_data, ("return_1",))
        with pytest.raises(InvalidFeatureMatrixError, match="non-empty strings"):
            FeatureMatrixBuilder.build(fset, feature_names=["  "])

    def test_warm_up_none_rows_excluded_not_zero_filled(self) -> None:
        """
        Rows where any requested feature is None must be dropped.
        The builder must NEVER substitute 0.0 for None.

        This guards against the 'fillna(0)' anti-pattern.
        """
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": None, "volatility_20": None}),  # warm-up row
            (_ts(1), {"return_1": None, "volatility_20": 0.10}),  # partial warm-up
            (_ts(2), {"return_1": 0.01, "volatility_20": 0.11}),  # complete
            (_ts(3), {"return_1": 0.02, "volatility_20": 0.12}),  # complete
        ]
        fset = self._make_fset(records_data, ("return_1", "volatility_20"))
        matrix = FeatureMatrixBuilder.build(fset)

        # Only rows 2 and 3 are complete
        assert matrix.sample_count == 2
        # Row 0 must NOT be (0.0, 0.0) — it must have been dropped entirely
        assert matrix.values[0] == (0.01, 0.11)
        assert matrix.values[1] == (0.02, 0.12)

    def test_all_none_rows_raises_typed_error(self) -> None:
        """If all rows have None values, build must raise InvalidFeatureMatrixError."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": None, "volatility_20": None}),
            (_ts(1), {"return_1": None, "volatility_20": None}),
        ]
        fset = self._make_fset(records_data, ("return_1", "volatility_20"))
        with pytest.raises(InvalidFeatureMatrixError, match="No complete feature observations"):
            FeatureMatrixBuilder.build(fset)

    def test_timestamp_alignment_after_warmup_exclusion(self) -> None:
        """After dropping warm-up rows, remaining timestamps must align with data rows."""
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (_ts(0), {"return_1": None}),  # dropped
            (_ts(1), {"return_1": 0.01}),  # kept
            (_ts(2), {"return_1": 0.02}),  # kept
        ]
        fset = self._make_fset(records_data, ("return_1",))
        matrix = FeatureMatrixBuilder.build(fset)

        assert matrix.timestamps == (_ts(1), _ts(2))
        assert matrix.values == ((0.01,), (0.02,))


# ---------------------------------------------------------------------------
# Class 3: Feature ordering and model inference
# ---------------------------------------------------------------------------


class TestFeatureOrderingAndModelInference:
    """
    Tests that feature ordering is handled deterministically through the pipeline.

    Specification (from FeatureMatrixBuilder):
    - When feature_names is None: alphabetical ordering is applied.
    - When feature_names is provided: the requested order is preserved.
    - The model must be fitted and predicted on consistently ordered matrices.
    """

    def _make_matrix_with_features(
        self,
        feature_names: tuple[str, ...],
        n_rows: int = 30,
    ) -> FeatureMatrix:
        """Creates a separable matrix using the specified feature column order."""
        import numpy as np

        rng = np.random.default_rng(42)
        n_feat = len(feature_names)
        # Half rows: group A, half: group B (clearly separated per-feature)
        rows_a = [
            tuple(float(1.0 + rng.normal(0, 0.01)) for _ in range(n_feat))
            for _ in range(n_rows // 2)
        ]
        rows_b = [
            tuple(float(-1.0 + rng.normal(0, 0.01)) for _ in range(n_feat))
            for _ in range(n_rows // 2)
        ]
        rows = rows_a + rows_b
        return FeatureMatrix(
            timestamps=tuple(_ts(i) for i in range(len(rows))),
            feature_names=feature_names,
            values=tuple(rows),
        )

    def test_model_rejects_inference_with_different_feature_order(self) -> None:
        """
        If a model is trained with feature order (A, B) and inference is attempted
        with (B, A), the model must raise InvalidFeatureMatrixError.
        """
        matrix_ab = self._make_matrix_with_features(("return_1", "volatility_20"))
        detector = KMeansRegimeDetector(RegimeModelConfig(n_clusters=2, random_state=42))
        detector.fit(matrix_ab)

        # Swap feature order for inference
        matrix_ba = self._make_matrix_with_features(("volatility_20", "return_1"))
        from app.modules.regime_detection.domain.errors import InvalidFeatureMatrixError

        with pytest.raises(InvalidFeatureMatrixError, match="Feature mismatch"):
            detector.predict(matrix_ba)

    def test_alphabetical_normalization_produces_consistent_results(self) -> None:
        """
        Two detectors trained via FeatureMatrixBuilder (alphabetical) on the same
        FeatureSet must produce identical predictions regardless of FeatureSet order.
        """
        from app.modules.feature_engineering.domain.models import FeatureRecord

        records = (
            FeatureRecord(timestamp=_ts(0), values={"return_1": 0.02, "volatility_20": 0.10}),
            FeatureRecord(timestamp=_ts(1), values={"return_1": 0.021, "volatility_20": 0.11}),
            FeatureRecord(timestamp=_ts(2), values={"return_1": -0.02, "volatility_20": 0.30}),
            FeatureRecord(timestamp=_ts(3), values={"return_1": -0.021, "volatility_20": 0.31}),
        )

        # FeatureSet with order A
        fset_a = FeatureSet(
            symbol="X",
            interval=DataInterval.ONE_DAY,
            feature_names=("return_1", "volatility_20"),
            records=records,
        )
        # FeatureSet with order B (swapped)
        fset_b = FeatureSet(
            symbol="X",
            interval=DataInterval.ONE_DAY,
            feature_names=("volatility_20", "return_1"),
            records=records,
        )

        matrix_a = FeatureMatrixBuilder.build(fset_a)
        matrix_b = FeatureMatrixBuilder.build(fset_b)

        # Both must produce alphabetically sorted features
        assert matrix_a.feature_names == ("return_1", "volatility_20")
        assert matrix_b.feature_names == ("return_1", "volatility_20")
        assert matrix_a.values == matrix_b.values

        # Fitting on either must produce identical predictions
        config = RegimeModelConfig(n_clusters=2, random_state=42)
        det_a = KMeansRegimeDetector(config=config)
        det_a.fit(matrix_a)
        preds_a = det_a.predict(matrix_a)

        det_b = KMeansRegimeDetector(config=config)
        det_b.fit(matrix_b)
        preds_b = det_b.predict(matrix_b)

        assert preds_a == preds_b
