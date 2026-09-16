"""
RegimeX Regime Detection — Domain Models
========================================
Canonical domain models for market regime detection, configuration,
cluster profiles, feature matrices, and inference results.

Guarantees:
- Pure Python and Pydantic v2 only (zero scikit-learn, numpy, or pandas dependencies).
- Immutable, frozen domain models with strict validation.
- Complete auditability and provenance metadata for research reproducibility.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ModelState(StrEnum):
    """Lifecycle state of a regime detection model."""

    UNFITTED = "UNFITTED"
    FITTED = "FITTED"


class RegimeModelConfig(BaseModel):
    """
    Hyperparameter and execution configuration for a regime detection model.

    Guarantees:
    - Immutable (frozen).
    - Validates cluster counts, iterations, tolerance, and feature specifications.
    """

    model_config = {"frozen": True}

    model_name: Annotated[
        str,
        Field(min_length=1, max_length=100, description="Model identifier name"),
    ] = "kmeans-baseline"
    model_version: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Semantic model version"),
    ] = "1.0.0"
    n_clusters: Annotated[
        int,
        Field(ge=2, le=50, description="Number of regimes/clusters to discover"),
    ] = 4
    random_state: Annotated[
        int,
        Field(ge=0, description="Deterministic random seed for reproducibility"),
    ] = 42
    max_iter: Annotated[
        int,
        Field(gt=0, le=10000, description="Maximum iterations for algorithm convergence"),
    ] = 300
    init: Annotated[
        str,
        Field(description="Initialization method: 'k-means++' or 'random'"),
    ] = "k-means++"
    tol: Annotated[
        float,
        Field(gt=0.0, description="Relative tolerance with respect to Frobenius norm"),
    ] = 1e-4
    feature_names: tuple[str, ...] = Field(
        default=(),
        description="Explicit subset of feature names to use in model training and inference",
    )

    @field_validator("init")
    @classmethod
    def validate_init_strategy(cls, v: str) -> str:
        """Ensure initialization strategy is recognized."""
        allowed = {"k-means++", "random"}
        if v not in allowed:
            raise ValueError(f"init strategy '{v}' must be one of {allowed}.")
        return v

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        """Ensure feature names are non-empty and distinct."""
        seen: set[str] = set()
        for name in v:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature names must be non-empty strings.")
            if name in seen:
                raise ValueError(f"Duplicate feature name detected in config: '{name}'.")
            seen.add(name)
        return v


class GMMModelConfig(BaseModel):
    """
    Hyperparameter and execution configuration for a Gaussian Mixture Model (GMM).

    Guarantees:
    - Immutable (frozen).
    - Validates component counts, covariance type, iterations, tolerance, and regularization.
    - Zero vendor/scikit-learn dependencies in domain contracts.
    """

    model_config = {"frozen": True}

    model_name: Annotated[
        str,
        Field(min_length=1, max_length=100, description="Model identifier name"),
    ] = "gmm"
    model_version: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Semantic model version"),
    ] = "1.0.0"
    n_components: Annotated[
        int,
        Field(ge=1, le=50, description="Number of mixture components / regimes"),
    ] = 4
    covariance_type: Annotated[
        str,
        Field(description="Type of covariance parameters: 'full', 'tied', 'diag', 'spherical'"),
    ] = "full"
    random_state: Annotated[
        int,
        Field(ge=0, description="Deterministic random seed for reproducibility"),
    ] = 42
    max_iter: Annotated[
        int,
        Field(ge=1, le=10000, description="Maximum iterations for EM algorithm convergence"),
    ] = 100
    tol: Annotated[
        float,
        Field(gt=0.0, description="Convergence threshold for EM log-likelihood lower bound"),
    ] = 1e-3
    reg_covar: Annotated[
        float,
        Field(
            gt=0.0,
            description="Non-negative regularization added to covariance diagonal",
        ),
    ] = 1e-6
    init_params: Annotated[
        str,
        Field(
            description="Initialization method: 'kmeans', 'k-means++', 'random', 'random_from_data'"
        ),
    ] = "kmeans"
    feature_names: tuple[str, ...] = Field(
        default=(),
        description="Explicit subset of feature names to use in model training and inference",
    )

    @field_validator("covariance_type")
    @classmethod
    def validate_covariance_type(cls, v: str) -> str:
        """Ensure covariance_type is recognized by scikit-learn standard."""
        allowed = {"full", "tied", "diag", "spherical"}
        if v not in allowed:
            raise ValueError(f"covariance_type '{v}' must be one of {allowed}.")
        return v

    @field_validator("init_params")
    @classmethod
    def validate_init_params(cls, v: str) -> str:
        """Ensure initialization method is recognized."""
        allowed = {"kmeans", "k-means++", "random", "random_from_data"}
        if v not in allowed:
            raise ValueError(f"init_params '{v}' must be one of {allowed}.")
        return v

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        """Ensure feature names are non-empty and distinct."""
        seen: set[str] = set()
        for name in v:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature names must be non-empty strings.")
            if name in seen:
                raise ValueError(f"Duplicate feature name detected in config: '{name}'.")
            seen.add(name)
        return v


class ClusterProfile(BaseModel):
    """
    Statistical profile of an identified cluster in feature space.

    Guarantees:
    - Decouples arbitrary raw cluster IDs from canonical, deterministically sorted regime IDs.
    - Captures centroid coordinates, sample counts, and feature summary statistics.
    """

    model_config = {"frozen": True}

    cluster_id: int = Field(ge=0, description="Raw algorithmic cluster ID from ML model")
    canonical_regime_id: int = Field(
        ge=0, description="Deterministically sorted canonical regime index (0..K-1)"
    )
    canonical_regime_label: str = Field(
        min_length=1, description="Standard canonical label (e.g., 'REGIME_0')"
    )
    center: tuple[float, ...] = Field(description="Centroid coordinates in unscaled feature space")
    sample_count: int = Field(
        ge=0, description="Number of training samples assigned to this cluster"
    )
    feature_means: dict[str, float] = Field(
        description="Mean value for each feature in this cluster (unscaled)"
    )
    feature_stds: dict[str, float] = Field(
        description="Standard deviation for each feature in this cluster (unscaled)"
    )


class DetectorMetadata(BaseModel):
    """
    Self-describing documentation and scientific assumptions for a regime detector.

    Conforms to the V03 RegimeDetector contract requirement.
    """

    model_config = {"frozen": True}

    algorithm_id: str = Field(min_length=1, description="Unique algorithm identifier")
    algorithm_version: str = Field(min_length=1, description="Model implementation version")
    algorithm_family: str = Field(min_length=1, description="Mathematical model family")
    description: str = Field(description="Human-readable overview of the model mechanics")
    assumptions: tuple[str, ...] = Field(
        default=(), description="Mathematical and financial assumptions"
    )
    known_limitations: tuple[str, ...] = Field(
        default=(), description="Disclosed scientific and practical limitations"
    )
    hyperparameters: dict[str, Any] = Field(
        default_factory=dict, description="Active hyperparameter configuration"
    )


class FitResult(BaseModel):
    """
    Provenance and summary diagnostics returned upon successful model fitting.
    """

    model_config = {"frozen": True}

    model_name: str = Field(description="Name of the fitted model")
    model_version: str = Field(description="Version of the fitted model")
    algorithm: str = Field(description="Algorithm type")
    n_clusters: int = Field(ge=1, description="Number of regimes/clusters")
    random_state: int = Field(description="Random seed used during fitting")
    feature_names: tuple[str, ...] = Field(description="Ordered features used for fitting")
    training_sample_count: int = Field(ge=1, description="Number of observations used in training")
    training_start: datetime = Field(
        description="UTC timestamp of the earliest training observation"
    )
    training_end: datetime = Field(description="UTC timestamp of the latest training observation")
    inertia: float = Field(
        default=0.0,
        ge=0.0,
        description="Sum of squared distances to closest center (0.0 for non-inertia models)",
    )
    iterations: int = Field(ge=1, description="Number of iterations run to reach convergence")
    cluster_profiles: tuple[ClusterProfile, ...] = Field(
        description="Statistical summary of each identified cluster"
    )
    lower_bound: float | None = Field(
        default=None,
        description="Log-likelihood lower bound computed by EM (for GMM)",
    )
    converged: bool | None = Field(
        default=None,
        description="Convergence status flag from EM algorithm (for GMM)",
    )
    fitted_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when model was fitted",
    )

    @field_validator("training_start", "training_end", "fitted_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware (got naive: {v!r}).")
        return v


class RegimeRecord(BaseModel):
    """
    Point-in-time regime assignment for a single observation timestamp.
    """

    model_config = {"frozen": True}

    timestamp: datetime = Field(description="Observation timestamp (UTC)")
    cluster_id: int = Field(ge=0, description="Raw algorithmic cluster ID")
    canonical_regime_id: int = Field(ge=0, description="Canonical regime index (0..K-1)")
    canonical_regime_label: str = Field(
        min_length=1, description="Canonical label (e.g., 'REGIME_0')"
    )
    probabilities: tuple[float, ...] | None = Field(
        default=None,
        description="Optional continuous confidence vector across all K regimes",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"timestamp must be timezone-aware (got naive: {v!r}).")
        return v


class RegimeDetectionResult(BaseModel):
    """
    Complete, deterministic regime detection output for a series of observations.

    Guarantees:
    - Immutable (frozen).
    - Preserves chronological ordering.
    - Captures model provenance and execution timestamp.
    """

    model_config = {"frozen": True}

    model_version: str = Field(description="Model version used for inference")
    algorithm: str = Field(description="Algorithm name")
    feature_names: tuple[str, ...] = Field(description="Names of input features in column order")
    records: tuple[RegimeRecord, ...] = Field(
        default=(), description="Chronologically ordered regime assignment records"
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when inference was computed",
    )

    @field_validator("computed_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"computed_at must be timezone-aware (got naive: {v!r}).")
        return v

    @property
    def is_empty(self) -> bool:
        """True if the result contains zero records."""
        return len(self.records) == 0

    @property
    def record_count(self) -> int:
        """Total number of inference records."""
        return len(self.records)

    def get_timestamps(self) -> tuple[datetime, ...]:
        """Return all observation timestamps in chronological order."""
        return tuple(r.timestamp for r in self.records)

    def get_regime_series(self) -> tuple[int, ...]:
        """Extract ordered sequence of canonical regime integer identifiers (0..K-1)."""
        return tuple(r.canonical_regime_id for r in self.records)

    def get_labels_series(self) -> tuple[str, ...]:
        """Extract ordered sequence of canonical regime string labels ('REGIME_0', etc.)."""
        return tuple(r.canonical_regime_label for r in self.records)

    def get_raw_cluster_series(self) -> tuple[int, ...]:
        """Extract ordered sequence of raw algorithmic cluster identifiers."""
        return tuple(r.cluster_id for r in self.records)


class FeatureMatrix(BaseModel):
    """
    Pure domain representation of a prepared numerical feature matrix.

    Guarantees:
    - Zero scikit-learn, numpy, or pandas dependencies.
    - Strict row-column dimensional consistency: len(values) == len(timestamps),
      len(row) == len(feature_names).
    - Every numerical value is finite (no NaN, +inf, -inf).
    - Chronologically sorted timezone-aware timestamps.
    - Deterministic column ordering.
    """

    model_config = {"frozen": True}

    timestamps: tuple[datetime, ...] = Field(
        description="Ordered observation timestamps (timezone-aware)"
    )
    feature_names: tuple[str, ...] = Field(
        description="Deterministic column names for the numerical features"
    )
    values: tuple[tuple[float, ...], ...] = Field(
        description="2D numerical values matrix: rows = observations, columns = features"
    )

    @field_validator("timestamps", mode="before")
    @classmethod
    def validate_timestamps(cls, v: tuple[datetime, ...]) -> tuple[datetime, ...]:
        """Ensure all timestamps are timezone-aware and strictly increasing."""
        if not v:
            return v
        for i, ts in enumerate(v):
            if ts.tzinfo is None:
                raise ValueError(f"Timestamp at index {i} is naive: {ts!r}. UTC required.")
            if i > 0 and ts <= v[i - 1]:
                raise ValueError(
                    f"Timestamps must be strictly increasing: index {i} ({ts}) "
                    f"<= index {i - 1} ({v[i - 1]})."
                )
        return v

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        """Ensure feature names are non-empty and unique."""
        if not v:
            raise ValueError("FeatureMatrix must specify at least one feature name.")
        seen: set[str] = set()
        for name in v:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature name must be a non-empty string.")
            if name in seen:
                raise ValueError(f"Duplicate feature name in FeatureMatrix: '{name}'.")
            seen.add(name)
        return v

    @model_validator(mode="after")
    def validate_matrix_shape_and_values(self) -> FeatureMatrix:
        """Validate dimensional consistency and ensure all values are finite."""
        n_rows = len(self.timestamps)
        n_cols = len(self.feature_names)

        if len(self.values) != n_rows:
            raise ValueError(
                f"Row dimension mismatch: {len(self.values)} rows in values, "
                f"but {n_rows} timestamps provided."
            )

        for row_idx, row in enumerate(self.values):
            if len(row) != n_cols:
                raise ValueError(
                    f"Column dimension mismatch at row {row_idx}: "
                    f"expected {n_cols} columns ({self.feature_names}), got {len(row)}."
                )
            for col_idx, val in enumerate(row):
                if not isinstance(val, (int, float)):
                    raise ValueError(
                        f"Non-numeric value at row {row_idx}, column {col_idx}: {val!r}"
                    )
                if math.isnan(val):
                    raise ValueError(
                        f"NaN detected at row {row_idx}, feature '{self.feature_names[col_idx]}'."
                    )
                if math.isinf(val):
                    raise ValueError(
                        f"Infinite value ({val}) detected at row {row_idx}, "
                        f"feature '{self.feature_names[col_idx]}'."
                    )

        return self

    @property
    def sample_count(self) -> int:
        """Number of observation rows in the matrix."""
        return len(self.timestamps)

    @property
    def feature_count(self) -> int:
        """Number of feature columns in the matrix."""
        return len(self.feature_names)

    @property
    def is_empty(self) -> bool:
        """True if the matrix has zero samples."""
        return self.sample_count == 0

    def get_column(self, feature_name: str) -> tuple[float, ...]:
        """
        Extract the ordered series for a specific feature column.

        Raises:
            KeyError: if feature_name is not present.
        """
        if feature_name not in self.feature_names:
            raise KeyError(f"Feature '{feature_name}' not in matrix features: {self.feature_names}")
        col_idx = self.feature_names.index(feature_name)
        return tuple(row[col_idx] for row in self.values)
