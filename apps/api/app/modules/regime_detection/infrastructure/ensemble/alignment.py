"""
RegimeX Regime Detection — Regime Identity Alignment Engine
============================================================
Provides deterministic alignment of heterogeneous regime detection models
(KMeans, GMM, HMM) into a common canonical regime space.

Architectural Position:
- ``infrastructure/ensemble/alignment.py``
- Solves label switching and semantic misalignment across heterogeneous models.
- Mathematical foundation: pairwise centroid Euclidean distance matching,
  optimal transport / linear sum assignment, and deterministic lexicographic tie-breaking.

Guarantees:
- Deterministic reproducibility: same input models and profiles always produce
  the exact same alignment mapping.
- Zero lookahead: alignment uses only fitted cluster profiles from in-sample training.
- Clean decoupling: supports CANONICAL_LABEL, FEATURE_SIMILARITY, and EXPLICIT_MAPPING.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.modules.regime_detection.domain.errors import (
    ModelNotFittedError,
    RegimeAlignmentError,
)
from app.modules.regime_detection.domain.interfaces import RegimeDetector
from app.modules.regime_detection.domain.models import (
    AlignmentPolicy,
    ClusterProfile,
    EnsembleModelConfig,
    ModelState,
)

logger = logging.getLogger(__name__)

# Numerical tolerance for considering two centroid distances identical
DISTANCE_TOLERANCE: float = 1e-12


class RegimeAlignmentEngine:
    """
    Deterministic alignment engine mapping heterogeneous model regime labels
    into a unified canonical regime coordinate space.
    """

    @classmethod
    def build_alignment(
        cls,
        models: dict[str, RegimeDetector],
        config: EnsembleModelConfig,
    ) -> dict[str, dict[int, int]]:
        """
        Construct a deterministic label mapping dictionary for each model.

        Args:
            models: Mapping of model_id -> fitted RegimeDetector instance.
            config: Ensemble configuration specifying alignment policy and reference model.

        Returns:
            Dictionary mapping model_id -> {source_regime_id: canonical_regime_id}.

        Raises:
            ModelNotFittedError: If any model has not been fitted.
            RegimeAlignmentError: If alignment cannot be established deterministically.
        """
        # Ensure all participating models are fitted
        for model_id, model in models.items():
            if model.state != ModelState.FITTED or model.fit_result is None:
                raise ModelNotFittedError(
                    model_name=model_id,
                    details={"reason": f"Cannot align unfitted model '{model_id}'."},
                )

        policy = config.alignment_policy

        if policy == AlignmentPolicy.CANONICAL_LABEL:
            return cls._align_by_canonical_label(models)
        elif policy == AlignmentPolicy.EXPLICIT_MAPPING:
            return cls._align_by_explicit_mapping(models, config)
        elif policy == AlignmentPolicy.FEATURE_SIMILARITY:
            return cls._align_by_feature_similarity(models, config)
        else:
            raise RegimeAlignmentError(
                f"Unsupported alignment policy: '{policy}'.",
                {"policy": str(policy)},
            )

    @classmethod
    def _align_by_canonical_label(
        cls,
        models: dict[str, RegimeDetector],
    ) -> dict[str, dict[int, int]]:
        """
        Direct identity mapping relying on models' internal V08/V10 canonicalization.

        Each model's canonical_regime_id maps directly to the ensemble canonical_regime_id.
        """
        alignment_map: dict[str, dict[int, int]] = {}
        for model_id, model in models.items():
            fit_res = model.fit_result
            if fit_res is None or not fit_res.cluster_profiles:
                n_clusters = fit_res.n_clusters if fit_res else 4
                alignment_map[model_id] = {k: k for k in range(n_clusters)}
            else:
                alignment_map[model_id] = {
                    prof.canonical_regime_id: prof.canonical_regime_id
                    for prof in fit_res.cluster_profiles
                }
        return alignment_map

    @classmethod
    def _align_by_explicit_mapping(
        cls,
        models: dict[str, RegimeDetector],
        config: EnsembleModelConfig,
    ) -> dict[str, dict[int, int]]:
        """Use explicit user-provided mapping."""
        if not config.explicit_mapping:
            raise RegimeAlignmentError(
                "explicit_mapping must be provided in config when policy is EXPLICIT_MAPPING."
            )
        alignment_map: dict[str, dict[int, int]] = {}
        for model_id in models:
            if model_id not in config.explicit_mapping:
                raise RegimeAlignmentError(
                    f"Model '{model_id}' is missing from explicit_mapping in config.",
                    {
                        "model_id": model_id,
                        "available_mappings": list(config.explicit_mapping.keys()),
                    },
                )
            alignment_map[model_id] = dict(config.explicit_mapping[model_id])
        return alignment_map

    @classmethod
    def _align_by_feature_similarity(
        cls,
        models: dict[str, RegimeDetector],
        config: EnsembleModelConfig,
    ) -> dict[str, dict[int, int]]:
        """
        Align each model's cluster profiles to a canonical reference model's profiles
        using optimal transport (linear sum assignment) on Euclidean centroid distances.
        """
        # Determine reference model
        ref_id = config.reference_model
        if ref_id is None or ref_id not in models:
            for enabled_id in config.enabled_models:
                if enabled_id in models:
                    ref_id = enabled_id
                    break
        if ref_id is None or ref_id not in models:
            raise RegimeAlignmentError(
                "Could not establish a reference model for feature similarity alignment.",
                {"enabled_models": config.enabled_models, "models": list(models.keys())},
            )

        ref_model = models[ref_id]
        ref_fit = ref_model.fit_result
        if ref_fit is None or not ref_fit.cluster_profiles:
            logger.warning(
                "Reference model '%s' has no cluster profiles; "
                "falling back to canonical label alignment.",
                ref_id,
            )

            return cls._align_by_canonical_label(models)

        ref_profiles: tuple[ClusterProfile, ...] = ref_fit.cluster_profiles
        ref_feature_names: tuple[str, ...] = ref_fit.feature_names

        # Reference model maps identity: canonical_id -> canonical_id
        alignment_map: dict[str, dict[int, int]] = {
            ref_id: {p.canonical_regime_id: p.canonical_regime_id for p in ref_profiles}
        }

        # Align all other models to reference profiles
        for model_id, model in models.items():
            if model_id == ref_id:
                continue

            model_fit = model.fit_result
            if model_fit is None or not model_fit.cluster_profiles:
                logger.warning(
                    "Model '%s' has no cluster profiles; using identity mapping.",
                    model_id,
                )
                n_clust = ref_fit.n_clusters if ref_fit else 4
                alignment_map[model_id] = {k: k for k in range(n_clust)}
                continue

            src_profiles = model_fit.cluster_profiles
            mapping = cls._match_profiles_to_reference(
                source_profiles=src_profiles,
                ref_profiles=ref_profiles,
                feature_names=ref_feature_names,
                model_id=model_id,
                ref_id=ref_id,
            )
            alignment_map[model_id] = mapping

        return alignment_map

    @classmethod
    def _match_profiles_to_reference(
        cls,
        source_profiles: tuple[ClusterProfile, ...],
        ref_profiles: tuple[ClusterProfile, ...],
        feature_names: tuple[str, ...],
        model_id: str,
        ref_id: str,
    ) -> dict[int, int]:
        """
        Compute optimal 1-to-1 matching from source clusters to reference canonical regimes.

        Methodology:
        1. Construct cost matrix C[i, j] = Euclidean distance between source profile i
           and reference canonical profile j in feature mean space.
        2. Features are strictly matched in sorted alphabetical feature name order.
        3. Solve minimum weight bipartite matching via Hungarian algorithm (linear_sum_assignment).
        4. If dimensions differ or non-square, solve via deterministic nearest-neighbor assignment
           with lexicographic tie-breaking on (distance, target_canonical_id, source_regime_id).
        """
        sorted_feats = sorted(feature_names)
        n_src = len(source_profiles)
        n_ref = len(ref_profiles)

        cost_matrix = np.zeros((n_src, n_ref), dtype=np.float64)

        for i, s_prof in enumerate(source_profiles):
            s_vec = np.array(
                [s_prof.feature_means.get(f, 0.0) for f in sorted_feats], dtype=np.float64
            )
            for j, r_prof in enumerate(ref_profiles):
                r_vec = np.array(
                    [r_prof.feature_means.get(f, 0.0) for f in sorted_feats], dtype=np.float64
                )
                dist = float(np.linalg.norm(s_vec - r_vec))
                cost_matrix[i, j] = dist

        mapping: dict[int, int] = {}

        if n_src == n_ref:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            for r, c in zip(row_ind, col_ind, strict=True):
                src_canonical_id = source_profiles[r].canonical_regime_id
                target_canonical_id = ref_profiles[c].canonical_regime_id
                mapping[src_canonical_id] = target_canonical_id
        else:
            for i, s_prof in enumerate(source_profiles):
                dists = cost_matrix[i, :]
                min_dist = float(np.min(dists))
                close_targets = [
                    (ref_profiles[j].canonical_regime_id, float(dists[j]))
                    for j in range(n_ref)
                    if abs(dists[j] - min_dist) <= DISTANCE_TOLERANCE
                ]
                best_target = min(close_targets, key=lambda x: x[0])[0]
                mapping[s_prof.canonical_regime_id] = best_target

        return mapping

    @classmethod
    def align_predictions(
        cls,
        predictions: Mapping[str, Sequence[int]],
        alignment_maps: Mapping[str, Mapping[int, int]],
    ) -> dict[str, tuple[int, ...]]:
        """
        Translate model-level predictions into canonical regime IDs using alignment maps.

        Args:
            predictions: Mapping {model_id: (p0, p1, ...)}
            alignment_maps: Mapping {model_id: {source_id: canonical_id}}

        Returns:
            Mapping {model_id: (aligned_p0, aligned_p1, ...)}
        """
        aligned: dict[str, tuple[int, ...]] = {}
        for model_id, preds in predictions.items():
            model_map = alignment_maps.get(model_id, {})
            aligned[model_id] = tuple(model_map.get(p, p) for p in preds)
        return aligned

    @classmethod
    def get_alignment_diagnostics(
        cls,
        models: dict[str, RegimeDetector],
        alignment_maps: dict[str, dict[int, int]],
    ) -> dict[str, Any]:
        """Expose explainability diagnostics regarding how each model was aligned."""
        diagnostics: dict[str, Any] = {}
        for model_id, mapping in alignment_maps.items():
            diagnostics[model_id] = {
                "source_to_canonical": mapping,
                "regimes_aligned_count": len(mapping),
            }
        return diagnostics
