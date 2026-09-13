"""
RegimeX Regime Detection — Feature Matrix Builder
=================================================
Builds validated, aligned, and leakage-safe FeatureMatrix objects from
V07 FeatureSet outputs.

Guarantees:
- Strictly point-in-time: respects chronological order.
- Explicit missing-value policy: drops warm-up rows with incomplete feature vectors.
  No synthetic zero values or forward fills are ever fabricated.
- Deterministic column ordering: features are arranged in a repeatable, canonical sequence.
- Full numerical validation: rejects NaN, +Inf, -Inf, and dimension mismatches with typed errors.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.modules.feature_engineering.domain.feature_set import FeatureSet
from app.modules.regime_detection.domain.errors import InvalidFeatureMatrixError
from app.modules.regime_detection.domain.models import FeatureMatrix


class FeatureMatrixBuilder:
    """
    Transforms V07 FeatureSet domain objects into model-ready FeatureMatrix representations.
    """

    @classmethod
    def build(
        cls,
        feature_set: FeatureSet,
        feature_names: Sequence[str] | None = None,
    ) -> FeatureMatrix:
        """
        Extract and validate a numerical FeatureMatrix from a FeatureSet.

        Args:
            feature_set: Complete V07 feature engineering output collection.
            feature_names: Optional ordered subset of features to include.
                If None, all features in the FeatureSet are included in deterministic
                (alphabetical) order.

        Returns:
            Validated, immutable FeatureMatrix with complete observations only.

        Raises:
            InvalidFeatureMatrixError: If input is empty, requested features are missing,
                or no complete observations remain after warm-up filtering.
        """
        if feature_set.is_empty:
            raise InvalidFeatureMatrixError("Cannot build FeatureMatrix from an empty FeatureSet.")

        # Determine target feature names and order
        if feature_names is None:
            # Deterministic alphabetical ordering of all available features
            target_features: tuple[str, ...] = tuple(sorted(feature_set.feature_names))
        else:
            # Validate requested features and remove duplicates while preserving specified order
            seen: set[str] = set()
            ordered: list[str] = []
            for name in feature_names:
                if not isinstance(name, str) or not name.strip():
                    raise InvalidFeatureMatrixError("Feature names must be non-empty strings.")
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            target_features = tuple(ordered)

        if not target_features:
            raise InvalidFeatureMatrixError(
                "Target feature list must contain at least one feature."
            )

        # Verify all target features exist in the FeatureSet
        missing = [f for f in target_features if f not in feature_set.feature_names]
        if missing:
            raise InvalidFeatureMatrixError(
                f"Requested features not present in FeatureSet: {missing}. "
                f"Available features: {sorted(feature_set.feature_names)}"
            )

        # Filter complete rows and build values matrix
        valid_timestamps = []
        valid_rows = []

        for record in feature_set.records:
            # Check if all target features are available (not None) for this observation
            row_vals: list[float] = []
            row_is_complete = True

            for feat_name in target_features:
                val = record.values.get(feat_name)
                if val is None:
                    row_is_complete = False
                    break
                if not isinstance(val, (int, float)) or not math.isfinite(val):
                    raise InvalidFeatureMatrixError(
                        f"Non-finite feature value ({val!r}) encountered at timestamp "
                        f"{record.timestamp} for feature '{feat_name}'."
                    )
                row_vals.append(float(val))

            if row_is_complete:
                valid_timestamps.append(record.timestamp)
                valid_rows.append(tuple(row_vals))

        if not valid_rows:
            raise InvalidFeatureMatrixError(
                "No complete feature observations available after excluding warm-up periods. "
                "Feature engineering produces initial unavailable periods; ensure the dataset "
                "spans sufficient historical bars."
            )

        try:
            return FeatureMatrix(
                timestamps=tuple(valid_timestamps),
                feature_names=target_features,
                values=tuple(valid_rows),
            )
        except ValueError as exc:
            raise InvalidFeatureMatrixError(f"FeatureMatrix validation failed: {exc}") from exc
