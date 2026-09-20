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


class HMMModelConfig(BaseModel):
    """
    Hyperparameter and execution configuration for a Hidden Markov Model (HMM).

    Guarantees:
    - Immutable (frozen).
    - Validates state counts, covariance type, iterations, tolerance, regularization,
      and decoding algorithm.
    - Zero vendor dependencies in domain contracts.
    """

    model_config = {"frozen": True}

    model_name: Annotated[
        str,
        Field(min_length=1, max_length=100, description="Model identifier name"),
    ] = "hmm"
    model_version: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Semantic model version"),
    ] = "1.0.0"
    n_components: Annotated[
        int,
        Field(ge=1, le=50, description="Number of hidden states / regimes"),
    ] = 4
    covariance_type: Annotated[
        str,
        Field(description="Type of covariance parameters: 'full', 'tied', 'diag', 'spherical'"),
    ] = "full"
    random_state: Annotated[
        int,
        Field(ge=0, description="Deterministic random seed for reproducibility"),
    ] = 42
    n_iter: Annotated[
        int,
        Field(ge=1, le=10000, description="Maximum iterations for Baum-Welch EM convergence"),
    ] = 100
    tol: Annotated[
        float,
        Field(gt=0.0, description="Convergence threshold for EM log-likelihood change"),
    ] = 1e-3
    min_covar: Annotated[
        float,
        Field(
            gt=0.0,
            description="Floor added to covariance diagonal to prevent collapse",
        ),
    ] = 1e-3
    algorithm: Annotated[
        str,
        Field(description="Decoding algorithm for predict(): 'viterbi' or 'map'"),
    ] = "viterbi"
    init_params: Annotated[
        str,
        Field(
            description=(
                "Parameters to initialize: subset of 'stmc' (startprob, transmat, means, covars)"
            )
        ),
    ] = "stmc"
    params: Annotated[
        str,
        Field(description="Parameters to update during M-step: subset of 'stmc'"),
    ] = "stmc"
    implementation: Annotated[
        str,
        Field(description="Implementation engine: 'log' or 'scaling'"),
    ] = "log"
    feature_names: tuple[str, ...] = Field(
        default=(),
        description="Explicit subset of feature names to use in model training and inference",
    )

    @field_validator("covariance_type")
    @classmethod
    def validate_covariance_type(cls, v: str) -> str:
        """Ensure covariance_type is recognized by standard."""
        allowed = {"full", "tied", "diag", "spherical"}
        if v not in allowed:
            raise ValueError(f"covariance_type '{v}' must be one of {allowed}.")
        return v

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Ensure decoding algorithm is recognized."""
        allowed = {"viterbi", "map"}
        if v not in allowed:
            raise ValueError(f"algorithm '{v}' must be one of {allowed}.")
        return v

    @field_validator("init_params")
    @classmethod
    def validate_init_params(cls, v: str) -> str:
        """Ensure init_params contains only valid parameter characters ('s', 't', 'm', 'c')."""
        allowed = {"s", "t", "m", "c"}
        if not v:
            return v
        for char in v:
            if char not in allowed:
                raise ValueError(
                    f"init_params character '{char}' is invalid; must be subset of 'stmc'."
                )
        return v

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: str) -> str:
        """Ensure params contains only valid parameter characters ('s', 't', 'm', 'c')."""
        allowed = {"s", "t", "m", "c"}
        if not v:
            return v
        for char in v:
            if char not in allowed:
                raise ValueError(f"params character '{char}' is invalid; must be subset of 'stmc'.")
        return v

    @field_validator("implementation")
    @classmethod
    def validate_implementation(cls, v: str) -> str:
        """Ensure implementation is recognized."""
        allowed = {"log", "scaling"}
        if v not in allowed:
            raise ValueError(f"implementation '{v}' must be one of {allowed}.")
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
        description=(
            "Log-likelihood lower bound computed by EM (for GMM) or log-likelihood score (for HMM)"
        ),
    )
    converged: bool | None = Field(
        default=None,
        description="Convergence status flag from EM algorithm (for GMM/HMM)",
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


class AlignmentPolicy(StrEnum):
    """Strategy for aligning heterogeneous model regime identities into canonical space."""

    CANONICAL_LABEL = "canonical_label"
    FEATURE_SIMILARITY = "feature_similarity"
    EXPLICIT_MAPPING = "explicit_mapping"


class AggregationStrategy(StrEnum):
    """Consensus voting strategy for combining component regime predictions."""

    WEIGHTED_VOTING = "weighted_voting"
    MAJORITY_VOTING = "majority_voting"
    PLURALITY_VOTING = "plurality_voting"


class FailurePolicy(StrEnum):
    """Behavior when a component model is unavailable or encounters an error."""

    FAIL_FAST = "fail_fast"
    SKIP_UNAVAILABLE = "skip_unavailable"
    BEST_EFFORT = "best_effort"


class EnsembleTieBreaker(StrEnum):
    """Deterministic tie-breaking mechanism for ensemble consensus voting."""

    LOWEST_REGIME_ID = "lowest_regime_id"
    MODEL_PRECEDENCE = "model_precedence"


class EnsembleModelConfig(BaseModel):
    """
    Hyperparameter and execution configuration for a Regime Model Ensemble.

    Guarantees:
    - Immutable (frozen).
    - Validates enabled models, weights, minimum required models, and policies.
    - Zero vendor/ML dependencies in domain layer.
    """

    model_config = {"frozen": True}

    model_name: Annotated[
        str,
        Field(min_length=1, max_length=100, description="Ensemble model identifier name"),
    ] = "regime-ensemble"
    model_version: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Semantic model version"),
    ] = "1.0.0"
    enabled_models: tuple[str, ...] = Field(
        default=("kmeans", "gmm", "hmm"),
        description="Identifiers of component models participating in the ensemble",
    )
    model_weights: dict[str, float] = Field(
        default_factory=lambda: {"kmeans": 1.0, "gmm": 1.0, "hmm": 1.0},
        description="Relative voting weights assigned to each component model",
    )
    aggregation_strategy: AggregationStrategy = Field(
        default=AggregationStrategy.WEIGHTED_VOTING,
        description="Mechanism used to aggregate aligned model predictions into consensus",
    )
    minimum_required_models: Annotated[
        int,
        Field(
            ge=1,
            description="Minimum number of successful models required to produce a consensus",
        ),
    ] = 2
    failure_policy: FailurePolicy = Field(
        default=FailurePolicy.SKIP_UNAVAILABLE,
        description="Policy governing execution when one or more models fail or are unavailable",
    )
    alignment_policy: AlignmentPolicy = Field(
        default=AlignmentPolicy.FEATURE_SIMILARITY,
        description="Policy for aligning model labels into canonical regime space",
    )
    tie_breaker: EnsembleTieBreaker = Field(
        default=EnsembleTieBreaker.LOWEST_REGIME_ID,
        description="Deterministic tie-breaking rule when regimes receive equal votes",
    )
    reference_model: str | None = Field(
        default=None,
        description="Model ID for canonical reference (defaults to first enabled model)",
    )
    explicit_mapping: dict[str, dict[int, int]] | None = Field(
        default=None,
        description="Manual mapping {model_id: {source_id: canonical_id}} for explicit policy",
    )
    feature_names: tuple[str, ...] = Field(
        default=(),
        description="Explicit subset of feature names to use in model training and inference",
    )

    @model_validator(mode="before")
    @classmethod
    def populate_default_weights(cls, data: object) -> object:
        if isinstance(data, dict):
            if "model_weights" not in data or data["model_weights"] is None:
                enabled = data.get("enabled_models", ("kmeans", "gmm", "hmm"))
                data["model_weights"] = dict.fromkeys(enabled, 1.0)
        return data

    @field_validator("enabled_models")
    @classmethod
    def validate_enabled_models(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("Ensemble configuration must enable at least one model.")
        seen: set[str] = set()
        for m in v:
            if not isinstance(m, str) or not m.strip():
                raise ValueError("Model identifier must be a non-empty string.")
            if m in seen:
                raise ValueError(f"Duplicate model identifier in enabled_models: '{m}'.")
            seen.add(m)
        return v

    @field_validator("model_weights")
    @classmethod
    def validate_weights(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("model_weights dictionary cannot be empty.")
        total_weight = 0.0
        for model_id, weight in v.items():
            if not isinstance(model_id, str) or not model_id.strip():
                raise ValueError("Model identifier in weights must be a non-empty string.")
            if weight < 0.0:
                raise ValueError(f"Model weight for '{model_id}' cannot be negative: {weight}.")
            total_weight += weight
        if total_weight <= 0.0:
            raise ValueError("Total ensemble weight must be strictly greater than 0.0.")
        return v

    @field_validator("feature_names")
    @classmethod
    def validate_feature_names(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        for name in v:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature names must be non-empty strings.")
            if name in seen:
                raise ValueError(f"Duplicate feature name detected in config: '{name}'.")
            seen.add(name)
        return v

    @model_validator(mode="after")
    def validate_ensemble_consistency(self) -> EnsembleModelConfig:
        n_enabled = len(self.enabled_models)
        if self.minimum_required_models > n_enabled:
            raise ValueError(
                f"minimum_required_models ({self.minimum_required_models}) cannot exceed "
                f"the number of enabled models ({n_enabled})."
            )
        unknown_keys = set(self.model_weights.keys()) - set(self.enabled_models)
        if unknown_keys:
            sorted_unknown = sorted(unknown_keys)
            raise ValueError(
                f"model_weights contains keys not present in enabled_models: {sorted_unknown}."
            )
        if self.reference_model is not None and self.reference_model not in self.enabled_models:
            raise ValueError(
                f"reference_model '{self.reference_model}' is not in "
                f"enabled_models {self.enabled_models}."
            )
        if self.alignment_policy == AlignmentPolicy.EXPLICIT_MAPPING and not self.explicit_mapping:
            raise ValueError(
                "explicit_mapping must be provided when alignment_policy is EXPLICIT_MAPPING."
            )
        return self


class EnsembleRecord(BaseModel):
    """
    Point-in-time consensus regime assignment and component model predictions for an observation.

    Guarantees:
    - Zero fake confidence metrics in Commit 01.
    - Explicit tracking of component predictions, canonical alignment, and model agreement.
    """

    model_config = {"frozen": True}

    timestamp: datetime = Field(description="Observation timestamp (UTC)")
    ensemble_regime_id: int = Field(
        ge=0, description="Consensus canonical regime integer identifier (0..K-1)"
    )
    ensemble_regime_label: str = Field(
        min_length=1, description="Canonical regime label (e.g. 'REGIME_0')"
    )
    model_predictions: dict[str, int] = Field(
        description="Raw/model-level predictions per component model {model_id: source_regime_id}"
    )
    aligned_predictions: dict[str, int] = Field(
        description="Aligned canonical regime predictions {model_id: canonical_regime_id}"
    )

    agreement_count: int = Field(
        ge=1, description="Count of usable models agreeing with the consensus regime"
    )
    total_models: int = Field(
        ge=1, description="Total count of usable models participating in this observation"
    )
    disagreeing_models: tuple[str, ...] = Field(
        default=(), description="Identifiers of models that voted for a different regime"
    )
    is_unanimous: bool = Field(
        description="True if all participating models agreed on the consensus regime"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"timestamp must be timezone-aware (got naive: {v!r}).")
        return v


class RegimeEnsembleResult(BaseModel):
    """
    Complete, deterministic output of the Regime Model Ensemble.

    Guarantees:
    - Immutable (frozen).
    - Preserves individual model outputs and aligned predictions for explainability.
    - Captures configuration snapshot, weights used, unavailable models, and execution metadata.
    - Zero confidence fields (reserved for V11 Commit 02).
    """

    model_config = {"frozen": True}

    model_version: str = Field(description="Ensemble implementation version")
    algorithm: str = Field(description="Ensemble algorithm name")
    feature_names: tuple[str, ...] = Field(description="Names of input features in column order")
    records: tuple[EnsembleRecord, ...] = Field(
        default=(), description="Chronologically ordered ensemble regime records"
    )
    models_used: tuple[str, ...] = Field(
        description="Component models that successfully participated"
    )
    models_unavailable: tuple[str, ...] = Field(
        default=(), description="Configured models that were unavailable or failed"
    )
    component_predictions: dict[str, tuple[int, ...]] = Field(
        description="Full observation series of predictions per model {model_id: (p0, p1, ...)}"
    )
    aligned_predictions: dict[str, tuple[int, ...]] = Field(
        description="Full observation series of aligned canonical predictions per model"
    )
    ensemble_regimes: tuple[int, ...] = Field(
        description="Ordered sequence of consensus canonical regime identifiers"
    )
    weights_used: dict[str, float] = Field(
        description="Normalized or active weights applied during aggregation"
    )
    aggregation_strategy: str = Field(description="Name of the aggregation strategy used")
    alignment_policy: str = Field(description="Name of the alignment policy used")
    failure_policy: str = Field(description="Name of the failure policy used")
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when ensemble inference was computed",
    )

    @field_validator("computed_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"computed_at must be timezone-aware (got naive: {v!r}).")
        return v

    @property
    def is_empty(self) -> bool:
        return len(self.records) == 0

    @property
    def record_count(self) -> int:
        return len(self.records)

    def get_timestamps(self) -> tuple[datetime, ...]:
        return tuple(r.timestamp for r in self.records)

    def get_regime_series(self) -> tuple[int, ...]:
        return tuple(r.ensemble_regime_id for r in self.records)

    def get_labels_series(self) -> tuple[str, ...]:
        return tuple(r.ensemble_regime_label for r in self.records)

    def get_agreement_rate(self) -> float:
        """Overall proportion of component model votes matching the consensus across all records."""
        if not self.records:
            return 0.0
        total_votes = sum(r.total_models for r in self.records)
        agreeing_votes = sum(r.agreement_count for r in self.records)
        return float(agreeing_votes / total_votes) if total_votes > 0 else 0.0
