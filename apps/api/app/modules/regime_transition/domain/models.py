"""
RegimeX Regime Transition — Domain Models
=========================================
Canonical domain models for historical regime transition analysis, count matrices,
empirical transition probability matrices, and individual transition records.

Guarantees:
- Pure Python and Pydantic v2 only (zero NumPy, SciPy, Pandas, or scikit-learn dependencies).
- Immutable, frozen domain models with strict invariant validation.
- Row-normalized transition probability simplex verification (sums to 1.0 within tolerance).
- Sample-size awareness: preserves transition observation counts alongside probabilities.
- Deterministic canonical ordering on regime identifiers.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class TransitionRecord(BaseModel):
    """
    Explicit point-in-time record of a regime transition between two consecutive observations.

    Captures source regime, target regime, target observation timestamp, and labels.
    """

    model_config = {"frozen": True}

    source_regime: Annotated[
        int,
        Field(ge=0, description="Canonical identifier of origin regime (0..K-1)"),
    ]
    target_regime: Annotated[
        int,
        Field(ge=0, description="Canonical identifier of destination regime (0..K-1)"),
    ]
    timestamp: datetime = Field(
        description="Timezone-aware UTC timestamp when target regime took effect",
    )
    source_label: str = Field(
        default="",
        description="Canonical label of source regime (e.g., 'REGIME_0')",
    )
    target_label: str = Field(
        default="",
        description="Canonical label of target regime (e.g., 'REGIME_1')",
    )
    is_self_transition: bool = Field(
        default=False,
        description="True if transition is persistence (source_regime == target_regime)",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"timestamp must be timezone-aware (got naive: {v!r}).")
        return v

    @model_validator(mode="after")
    def validate_self_transition_consistency(self) -> TransitionRecord:
        """Ensure default labels and self-transition consistency."""
        expected_self = self.source_regime == self.target_regime
        if self.is_self_transition != expected_self:
            object.__setattr__(self, "is_self_transition", expected_self)

        if not self.source_label:
            object.__setattr__(self, "source_label", f"REGIME_{self.source_regime}")
        if not self.target_label:
            object.__setattr__(self, "target_label", f"REGIME_{self.target_regime}")
        return self


class TransitionProbability(BaseModel):
    """
    Empirical transition probability and supporting sample size for a specific regime pair.

    Guarantees:
    - Probability bounded in [0.0, 1.0].
    - Preserves count and total_transitions_from_source to avoid sample-size illusion.
    """

    model_config = {"frozen": True}

    source_regime: Annotated[int, Field(ge=0, description="Source regime identifier")]
    target_regime: Annotated[int, Field(ge=0, description="Target regime identifier")]
    count: Annotated[
        int,
        Field(ge=0, description="Number of observed transitions from source to target"),
    ]
    total_transitions_from_source: Annotated[
        int,
        Field(ge=0, description="Total observed transitions originating from source regime"),
    ]
    probability: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Empirical transition probability P(source -> target)"),
    ]

    @property
    def sample_size(self) -> int:
        """Alias for total_transitions_from_source."""
        return self.total_transitions_from_source

    @field_validator("probability")
    @classmethod
    def validate_finite_probability(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Probability must be a finite float, got {v}.")
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Probability must be in [0.0, 1.0], got {v}.")
        return v

    @model_validator(mode="after")
    def validate_probability_invariants(self) -> TransitionProbability:
        if self.count > self.total_transitions_from_source:
            raise ValueError(
                f"Transition count ({self.count}) cannot exceed total transitions from source "
                f"({self.total_transitions_from_source})."
            )
        if self.total_transitions_from_source == 0:
            if self.probability != 0.0:
                raise ValueError(
                    f"Probability must be 0.0 when total_transitions_from_source is 0, "
                    f"got {self.probability}."
                )
        else:
            expected = float(self.count / self.total_transitions_from_source)
            if abs(self.probability - expected) > 1e-6:
                raise ValueError(
                    f"Probability ({self.probability}) does not match empirical ratio "
                    f"count / total ({expected:.6f})."
                )
        return self


class TransitionCountMatrix(BaseModel):
    """
    Immutable square matrix of empirical transition counts between regimes.

    Rows represent origin regimes (From), columns represent destination regimes (To).
    """

    model_config = {"frozen": True}

    regimes: tuple[int, ...] = Field(
        description="Deterministically sorted canonical regime identifiers",
    )
    matrix: tuple[tuple[int, ...], ...] = Field(
        description="Square 2D count matrix where matrix[i][j] is count(regimes[i] -> regimes[j])",
    )
    total_transitions: Annotated[
        int,
        Field(ge=0, description="Sum of all transitions across the matrix"),
    ]
    row_totals: dict[int, int] = Field(
        description="Total transitions originating from each regime {regime_id: count}",
    )

    @field_validator("regimes")
    @classmethod
    def validate_regimes(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if not v:
            raise ValueError("TransitionCountMatrix must have at least one regime.")
        seen: set[int] = set()
        for r in v:
            if not isinstance(r, int) or r < 0:
                raise ValueError(f"Regime identifier must be a non-negative integer, got {r!r}.")
            if r in seen:
                raise ValueError(f"Duplicate regime identifier detected: {r}.")
            seen.add(r)
        if list(v) != sorted(v):
            raise ValueError(f"Regimes must be sorted deterministically in ascending order: {v}.")
        return v

    @model_validator(mode="after")
    def validate_matrix_shape_and_totals(self) -> TransitionCountMatrix:
        k = len(self.regimes)
        if len(self.matrix) != k:
            raise ValueError(
                f"Matrix row dimension mismatch: expected {k} rows for regimes {self.regimes}, "
                f"got {len(self.matrix)}."
            )
        computed_total = 0
        computed_row_totals: dict[int, int] = {}

        for i, row in enumerate(self.matrix):
            if len(row) != k:
                raise ValueError(
                    f"Matrix column dimension mismatch at row {i} (regime {self.regimes[i]}): "
                    f"expected {k} columns, got {len(row)}."
                )
            row_sum = 0
            for j, count in enumerate(row):
                if not isinstance(count, int) or count < 0:
                    raise ValueError(
                        f"Count at ({i}, {j}) must be a non-negative integer, got {count!r}."
                    )
                row_sum += count
            computed_row_totals[self.regimes[i]] = row_sum
            computed_total += row_sum

        if self.total_transitions != computed_total:
            raise ValueError(
                f"total_transitions ({self.total_transitions}) does not match sum of matrix "
                f"elements ({computed_total})."
            )

        for r in self.regimes:
            declared = self.row_totals.get(r)
            expected = computed_row_totals[r]
            if declared != expected:
                raise ValueError(
                    f"row_totals for regime {r} ({declared}) does not match "
                    f"computed row sum ({expected})."
                )

        return self

    @property
    def cardinality(self) -> int:
        """Number of regimes (K)."""
        return len(self.regimes)

    def get_count(self, source_regime: int, target_regime: int) -> int:
        """Return transition count from source_regime to target_regime."""
        if source_regime not in self.regimes:
            raise KeyError(f"Source regime {source_regime} not in matrix regimes {self.regimes}.")
        if target_regime not in self.regimes:
            raise KeyError(f"Target regime {target_regime} not in matrix regimes {self.regimes}.")
        i = self.regimes.index(source_regime)
        j = self.regimes.index(target_regime)
        return self.matrix[i][j]

    def get_row(self, source_regime: int) -> tuple[int, ...]:
        """Return all destination counts originating from source_regime."""
        if source_regime not in self.regimes:
            raise KeyError(f"Source regime {source_regime} not in matrix regimes {self.regimes}.")
        i = self.regimes.index(source_regime)
        return self.matrix[i]

    def get_column(self, target_regime: int) -> tuple[int, ...]:
        """Return all origin counts arriving into target_regime."""
        if target_regime not in self.regimes:
            raise KeyError(f"Target regime {target_regime} not in matrix regimes {self.regimes}.")
        j = self.regimes.index(target_regime)
        return tuple(self.matrix[i][j] for i in range(len(self.regimes)))

    def to_dict(self) -> dict[int, dict[int, int]]:
        """Return nested dictionary {source_regime: {target_regime: count}}."""
        return {
            src: {tgt: self.get_count(src, tgt) for tgt in self.regimes} for src in self.regimes
        }


class TransitionProbabilityMatrix(BaseModel):
    """
    Immutable square matrix of row-normalized empirical transition probabilities.

    Row i, col j represents P(regimes[i] -> regimes[j]).
    Each non-empty row sums to 1.0 within numerical tolerance (1e-6).
    """

    model_config = {"frozen": True}

    regimes: tuple[int, ...] = Field(
        description="Deterministically sorted canonical regime identifiers",
    )
    matrix: tuple[tuple[float, ...], ...] = Field(
        description="Square 2D probability matrix where matrix[i][j] = P(regimes[i] -> regimes[j])",
    )
    counts: TransitionCountMatrix = Field(
        description="Underlying transition count matrix providing statistical sample sizes",
    )

    @field_validator("regimes")
    @classmethod
    def validate_regimes(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if not v:
            raise ValueError("TransitionProbabilityMatrix must have at least one regime.")
        if list(v) != sorted(v):
            raise ValueError(f"Regimes must be sorted deterministically: {v}.")
        return v

    @model_validator(mode="after")
    def validate_matrix_shape_and_probabilities(self) -> TransitionProbabilityMatrix:
        k = len(self.regimes)
        if len(self.matrix) != k:
            raise ValueError(
                f"Matrix row dimension mismatch: expected {k} rows, got {len(self.matrix)}."
            )
        if self.counts.regimes != self.regimes:
            raise ValueError(
                f"Counts regimes {self.counts.regimes} must match "
                f"probability matrix regimes {self.regimes}."
            )

        for i, row in enumerate(self.matrix):
            if len(row) != k:
                raise ValueError(
                    f"Matrix column dimension mismatch at row {i}: expected {k}, got {len(row)}."
                )
            row_sum = 0.0
            r_id = self.regimes[i]
            row_count_total = self.counts.row_totals.get(r_id, 0)

            for j, p in enumerate(row):
                if not isinstance(p, (int, float)):
                    raise ValueError(f"Probability at ({i}, {j}) must be numeric, got {p!r}.")
                if math.isnan(p) or math.isinf(p):
                    raise ValueError(f"Probability at ({i}, {j}) cannot be NaN or infinite.")
                if not (0.0 <= p <= 1.0):
                    raise ValueError(f"Probability at ({i}, {j}) must be in [0.0, 1.0], got {p}.")
                row_sum += float(p)

            if row_count_total > 0:
                if abs(row_sum - 1.0) > 1e-5:
                    raise ValueError(
                        f"Row {i} (regime {r_id}) probability sum ({row_sum:.6f}) violates "
                        f"simplex invariant (must sum to 1.0 within tolerance)."
                    )
            else:
                # Absorbing or unobserved row: probabilities are 0.0
                if row_sum != 0.0:
                    raise ValueError(
                        f"Row {i} (regime {r_id}) has 0 observations; "
                        f"all probabilities must be 0.0."
                    )

        return self

    @property
    def cardinality(self) -> int:
        """Number of regimes (K)."""
        return len(self.regimes)

    def get_probability(self, source_regime: int, target_regime: int) -> float:
        """Return transition probability P(source_regime -> target_regime)."""
        if source_regime not in self.regimes:
            raise KeyError(f"Source regime {source_regime} not in matrix regimes {self.regimes}.")
        if target_regime not in self.regimes:
            raise KeyError(f"Target regime {target_regime} not in matrix regimes {self.regimes}.")
        i = self.regimes.index(source_regime)
        j = self.regimes.index(target_regime)
        return self.matrix[i][j]

    def get_row(self, source_regime: int) -> tuple[float, ...]:
        """Return destination probability distribution originating from source_regime."""
        if source_regime not in self.regimes:
            raise KeyError(f"Source regime {source_regime} not in matrix regimes {self.regimes}.")
        i = self.regimes.index(source_regime)
        return self.matrix[i]

    def get_column(self, target_regime: int) -> tuple[float, ...]:
        """Return origin probability column arriving into target_regime."""
        if target_regime not in self.regimes:
            raise KeyError(f"Target regime {target_regime} not in matrix regimes {self.regimes}.")
        j = self.regimes.index(target_regime)
        return tuple(self.matrix[i][j] for i in range(len(self.regimes)))

    def to_dict(self) -> dict[int, dict[int, float]]:
        """Return nested dictionary {source_regime: {target_regime: probability}}."""
        return {
            src: {tgt: self.get_probability(src, tgt) for tgt in self.regimes}
            for src in self.regimes
        }


class RegimeTransitionResult(BaseModel):
    """
    Complete, deterministic output of the Regime Transition Probability Engine.

    Guarantees:
    - Immutable (frozen).
    - Preserves count matrix alongside probability matrix for sample-size transparency.
    - Exposes query methods for arbitrary regime pairs (P(i -> j)).
    - Provides explicit list of discrete state-change transition events.
    """

    model_config = {"frozen": True}

    count_matrix: TransitionCountMatrix = Field(
        description="Matrix of empirical observation counts between regimes",
    )
    probability_matrix: TransitionProbabilityMatrix = Field(
        description="Matrix of row-normalized transition probabilities",
    )
    transitions: tuple[TransitionRecord, ...] = Field(
        default=(),
        description="Chronologically ordered sequence of explicit regime change events",
    )
    regimes_observed: tuple[int, ...] = Field(
        description="Unique canonical regime identifiers observed in the sequence",
    )
    total_observations: Annotated[
        int,
        Field(ge=0, description="Total number of consecutive observations evaluated"),
    ]
    total_transitions: Annotated[
        int,
        Field(ge=0, description="Total count of transitions evaluated"),
    ]
    analysis_start: datetime | None = Field(
        default=None,
        description="Earliest observation timestamp in the analyzed history",
    )
    analysis_end: datetime | None = Field(
        default=None,
        description="Latest observation timestamp in the analyzed history",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when transition analysis was computed",
    )

    @field_validator("analysis_start", "analysis_end", "computed_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware (got naive: {v!r}).")
        return v

    def get_transition_probability(
        self,
        source_regime: int,
        target_regime: int,
    ) -> TransitionProbability:
        """
        Query the empirical transition probability and supporting sample size for a regime pair.

        Raises:
            KeyError: If either regime is not present in the transition matrix.
        """
        prob = self.probability_matrix.get_probability(source_regime, target_regime)
        count = self.count_matrix.get_count(source_regime, target_regime)
        total_from_src = self.count_matrix.row_totals.get(source_regime, 0)
        return TransitionProbability(
            source_regime=source_regime,
            target_regime=target_regime,
            count=count,
            total_transitions_from_source=total_from_src,
            probability=prob,
        )

    def get_transitions_from(self, source_regime: int) -> tuple[TransitionRecord, ...]:
        """Return all discrete regime change events originating from source_regime."""
        return tuple(t for t in self.transitions if t.source_regime == source_regime)

    def get_transitions_to(self, target_regime: int) -> tuple[TransitionRecord, ...]:
        """Return all discrete regime change events transitioning into target_regime."""
        return tuple(t for t in self.transitions if t.target_regime == target_regime)

    def get_transition_records(self) -> tuple[TransitionRecord, ...]:
        """Return all discrete regime change records in chronological order."""
        return self.transitions

    def get_matrix(self) -> tuple[tuple[float, ...], ...]:
        """Return the 2D tuple of transition probabilities."""
        return self.probability_matrix.matrix

    def get_count_matrix(self) -> tuple[tuple[int, ...], ...]:
        """Return the 2D tuple of transition counts."""
        return self.count_matrix.matrix

    def get_probabilities_from(self, source_regime: int) -> dict[int, float]:
        """Return dictionary mapping target regimes to their transition probability from source."""
        return {
            tgt: self.probability_matrix.get_probability(source_regime, tgt)
            for tgt in self.probability_matrix.regimes
        }

    def get_probabilities_to(self, target_regime: int) -> dict[int, float]:
        """Return dictionary mapping source regimes to their transition probability to target."""
        return {
            src: self.probability_matrix.get_probability(src, target_regime)
            for src in self.probability_matrix.regimes
        }

    def get_self_transition_probability(self, regime_id: int) -> float:
        """Return the persistence / self-transition probability P(regime_id -> regime_id)."""
        return self.probability_matrix.get_probability(regime_id, regime_id)


class RankedDestination(BaseModel):
    """
    Ranked destination regime with transition count, probability, and deterministic rank.
    """

    model_config = {"frozen": True}

    target_regime: Annotated[
        int,
        Field(ge=0, description="Destination canonical regime ID"),
    ]
    target_label: str = Field(description="Destination canonical regime label")
    probability: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Empirical transition probability P(source -> target)"),
    ]
    count: Annotated[
        int,
        Field(ge=0, description="Empirical transition count from source to target"),
    ]
    rank: Annotated[
        int,
        Field(ge=1, description="1-indexed rank among destinations for this source"),
    ]


class TransitionRegimeAnalytics(BaseModel):
    """
    Detailed transition analytics and behavioral statistics for a single market regime.
    """

    model_config = {"frozen": True}

    regime_id: Annotated[int, Field(ge=0, description="Canonical regime ID")]
    regime_label: str = Field(description="Canonical regime label")
    outgoing_transition_count: Annotated[
        int,
        Field(ge=0, description="Total outgoing transitions originating from this regime"),
    ]
    incoming_transition_count: Annotated[
        int,
        Field(ge=0, description="Total incoming transitions arriving into this regime"),
    ]
    self_transition_count: Annotated[
        int,
        Field(ge=0, description="Count of persistence self-transitions (i -> i)"),
    ]
    regime_change_count: Annotated[
        int,
        Field(ge=0, description="Count of transitions out to different regimes (i -> j, j != i)"),
    ]
    persistence_probability: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Empirical persistence probability P(i -> i)"),
    ]
    change_rate: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Proportion of outgoing transitions that are changes to other regimes",
        ),
    ]
    most_likely_destination: int | None = Field(
        default=None,
        description="Highest probability destination regime ID, or None if unobserved",
    )
    most_likely_destination_probability: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Empirical transition probability of the most likely destination",
        ),
    ]
    destination_count: Annotated[
        int,
        Field(ge=0, description="Count of distinct destination regimes with count > 0"),
    ]
    source_count: Annotated[
        int,
        Field(ge=0, description="Count of distinct origin regimes transitioning into this regime"),
    ]
    transition_entropy: Annotated[
        float,
        Field(ge=0.0, description="Shannon transition entropy H(i) = -sum P ln P (nats)"),
    ]
    rankings: tuple[RankedDestination, ...] = Field(
        default=(),
        description="Deterministically ordered destination rankings (prob desc, target_id asc)",
    )


# Backward-compatible alias
RegimeTransitionAnalytics = TransitionRegimeAnalytics


class GlobalTransitionAnalytics(BaseModel):
    """
    Aggregate global transition summary across the entire observed regime sequence.
    """

    model_config = {"frozen": True}

    total_observations: Annotated[
        int,
        Field(ge=0, description="Total observations in the analyzed sequence"),
    ]
    total_consecutive_transitions: Annotated[
        int,
        Field(ge=0, description="Total consecutive step transitions evaluated"),
    ]
    total_regime_changes: Annotated[
        int,
        Field(ge=0, description="Total regime shift transitions (source != target)"),
    ]
    total_self_transitions: Annotated[
        int,
        Field(ge=0, description="Total regime persistence transitions (source == target)"),
    ]
    global_change_rate: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Proportion of transitions that are regime shifts",
        ),
    ]
    global_persistence_rate: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Proportion of transitions that are regime persistence",
        ),
    ]
    number_of_regimes: Annotated[
        int,
        Field(ge=1, description="Number of canonical regimes in the universe"),
    ]
    number_of_observed_transition_edges: Annotated[
        int,
        Field(ge=0, description="Count of distinct directed edges (i, j) with count > 0"),
    ]

    @model_validator(mode="after")
    def validate_global_invariants(self) -> GlobalTransitionAnalytics:
        expected_transitions = self.total_self_transitions + self.total_regime_changes
        if expected_transitions != self.total_consecutive_transitions:
            raise ValueError(
                f"Count invariant violated: self_transitions ({self.total_self_transitions}) + "
                f"regime_changes ({self.total_regime_changes}) != "
                f"total_consecutive_transitions ({self.total_consecutive_transitions})."
            )
        if self.total_consecutive_transitions > 0:
            rate_sum = self.global_change_rate + self.global_persistence_rate
            if abs(rate_sum - 1.0) > 1e-5:
                raise ValueError(
                    f"Rate invariant violated: change_rate ({self.global_change_rate}) + "
                    f"persistence_rate ({self.global_persistence_rate}) must sum to 1.0."
                )
        return self


class TransitionAnalyticsResult(BaseModel):
    """
    Comprehensive transition analytics container combining the underlying transition result,
    per-regime analytics, global statistics, and regime change matrices.
    """

    model_config = {"frozen": True}

    transition_result: RegimeTransitionResult = Field(
        description="Underlying transition result from V12 Commit 01",
    )
    regime_analytics: dict[int, TransitionRegimeAnalytics] = Field(
        description="Per-regime transition metrics {regime_id: analytics}",
    )
    global_analytics: GlobalTransitionAnalytics = Field(
        description="Sequence-wide global transition statistics",
    )
    regime_change_counts: tuple[tuple[int, ...], ...] = Field(
        description="Transition count matrix with diagonal zeroed out (shifts only)",
    )
    regime_change_probabilities: tuple[tuple[float, ...], ...] = Field(
        description="Conditional shift probabilities excluding self-transitions",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="UTC timestamp when transition analytics was computed",
    )

    @field_validator("computed_at", mode="before")
    @classmethod
    def require_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(f"computed_at must be timezone-aware (got naive: {v!r}).")
        return v

    def get_regime_analytics(self, regime_id: int) -> TransitionRegimeAnalytics:
        """Retrieve analytics for a specific canonical regime."""
        if regime_id not in self.regime_analytics:
            raise KeyError(
                f"Regime {regime_id} not in analyzed regimes: "
                f"{sorted(self.regime_analytics.keys())}."
            )
        return self.regime_analytics[regime_id]

    def get_persistence(self, regime_id: int) -> float:
        """Shortcut for empirical persistence probability P(regime_id -> regime_id)."""
        return self.get_regime_analytics(regime_id).persistence_probability

    def get_most_likely_destination(self, regime_id: int) -> int | None:
        """Shortcut for the most likely destination regime ID."""
        return self.get_regime_analytics(regime_id).most_likely_destination

    def get_rankings(self, regime_id: int) -> tuple[RankedDestination, ...]:
        """Shortcut for destination rankings originating from regime_id."""
        return self.get_regime_analytics(regime_id).rankings

    def get_change_rate(self) -> float:
        """Shortcut for sequence-wide global change rate."""
        return self.global_analytics.global_change_rate

    def get_persistence_rate(self) -> float:
        """Shortcut for sequence-wide global persistence rate."""
        return self.global_analytics.global_persistence_rate
