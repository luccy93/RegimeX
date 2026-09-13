"""
RegimeX Regime Detection — Feature Matrix Builder Unit Tests
============================================================
Verifies FeatureMatrix extraction from V07 FeatureSet, including warm-up
missing-value exclusion, zero-fabrication rejection, and timestamp alignment.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.feature_engineering.domain.models import FeatureRecord
from app.modules.market_data.domain.models import DataInterval
from app.modules.regime_detection.application.feature_matrix_builder import (
    FeatureMatrixBuilder,
)
from app.modules.regime_detection.domain.errors import InvalidFeatureMatrixError


def _make_sample_feature_set(
    symbol: str = "AAPL",
    records_data: Sequence[tuple[datetime, dict[str, float | None]]] | None = None,
) -> FeatureSet:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    if records_data is None:
        records_data = [
            (base_time, {"return_1": None, "volatility_20": None}),
            (base_time + timedelta(days=1), {"return_1": 0.01, "volatility_20": None}),
            (base_time + timedelta(days=2), {"return_1": 0.02, "volatility_20": 0.15}),
            (base_time + timedelta(days=3), {"return_1": -0.01, "volatility_20": 0.18}),
            (base_time + timedelta(days=4), {"return_1": 0.03, "volatility_20": 0.14}),
        ]

    records = tuple(FeatureRecord(timestamp=ts, values=vals) for ts, vals in records_data)
    return FeatureSet(
        symbol=symbol,
        interval=DataInterval.ONE_DAY,
        feature_names=("return_1", "volatility_20"),
        records=records,
    )


class TestFeatureMatrixBuilder:
    def test_build_excludes_warmup_incomplete_rows(self) -> None:
        fset = _make_sample_feature_set()
        matrix = FeatureMatrixBuilder.build(fset)

        # First 2 rows had None values and must be dropped; remaining 3 rows kept
        assert matrix.sample_count == 3
        assert matrix.feature_count == 2
        # Alphabetical column order by default: return_1, volatility_20
        assert matrix.feature_names == ("return_1", "volatility_20")

        # Verify exact numerical values in rows
        assert matrix.values[0] == (0.02, 0.15)
        assert matrix.values[1] == (-0.01, 0.18)
        assert matrix.values[2] == (0.03, 0.14)

    def test_build_preserves_timestamp_alignment(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        fset = _make_sample_feature_set()
        matrix = FeatureMatrixBuilder.build(fset)

        expected_timestamps = (
            base_time + timedelta(days=2),
            base_time + timedelta(days=3),
            base_time + timedelta(days=4),
        )
        assert matrix.timestamps == expected_timestamps

    def test_no_synthetic_zero_fabrication(self) -> None:
        """Confirms that warm-up None values are NEVER replaced with 0.0."""
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (base_time, {"return_1": None, "volatility_20": 0.20}),
            (base_time + timedelta(days=1), {"return_1": 0.05, "volatility_20": 0.22}),
        ]
        fset = _make_sample_feature_set(records_data=records_data)
        matrix = FeatureMatrixBuilder.build(fset)

        # Row 0 must NOT become (0.0, 0.20) — it must be dropped
        assert matrix.sample_count == 1
        assert matrix.timestamps == (base_time + timedelta(days=1),)
        assert matrix.values == ((0.05, 0.22),)

    def test_custom_feature_subset_and_order(self) -> None:
        fset = _make_sample_feature_set()
        matrix = FeatureMatrixBuilder.build(
            fset,
            feature_names=["volatility_20", "return_1"],
        )
        assert matrix.feature_names == ("volatility_20", "return_1")
        assert matrix.values[0] == (0.15, 0.02)

    def test_rejects_empty_feature_set(self) -> None:
        empty_fset = FeatureSet(
            symbol="MSFT",
            interval=DataInterval.ONE_DAY,
            feature_names=("return_1",),
            records=(),
        )
        with pytest.raises(InvalidFeatureMatrixError, match="empty FeatureSet"):
            FeatureMatrixBuilder.build(empty_fset)

    def test_rejects_missing_requested_features(self) -> None:
        fset = _make_sample_feature_set()
        with pytest.raises(InvalidFeatureMatrixError, match="Requested features not present"):
            FeatureMatrixBuilder.build(fset, feature_names=["non_existent_feature"])

    def test_rejects_all_incomplete_observations(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (base_time, {"return_1": None, "volatility_20": None}),
            (base_time + timedelta(days=1), {"return_1": None, "volatility_20": 0.1}),
        ]
        fset = _make_sample_feature_set(records_data=records_data)
        with pytest.raises(InvalidFeatureMatrixError, match="No complete feature observations"):
            FeatureMatrixBuilder.build(fset)

    def test_rejects_non_finite_values(self) -> None:
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        records_data: list[tuple[datetime, dict[str, float | None]]] = [
            (base_time, {"return_1": float("inf"), "volatility_20": 0.15}),
        ]
        fset = _make_sample_feature_set(records_data=records_data)
        with pytest.raises(InvalidFeatureMatrixError, match="Non-finite feature value"):
            FeatureMatrixBuilder.build(fset)
