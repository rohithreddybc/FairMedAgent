"""FairMedAgent: benchmark for demographic disparities in the *actions* of clinical LLM agents.

Core fairness metrics are stdlib-only (see ``fairmedagent.metrics``) so the harness is
runnable with zero dependencies; install ``fairmedagent[full]`` for numpy/scipy/datasets
acceleration at scale. Public API is intentionally small and stable.
"""
from .metrics import (
    Pair,
    counterfactual_flip_rate,
    within_range_flip_rate,
    wcfr_statistic,
    in_band,
    band_straddles,
    disparity_propagation,
    mean_absolute_score_difference,
    action_level_disparity,
    positive_rate,
    cluster_bootstrap_ci,
    mcnemar_exact,
    benjamini_hochberg,
    benjamini_yekutieli,
    paired_permutation_test,
    signed_ordinal_disparity,
    interventional_propagation,
    capability_floor_gate,
    trajectory_accumulation,
)
from .runner import run_vignette, run_replicates, collapse_replicates, resolve_orderables
from .bands import Band, PROVENANCE, unadjudicated, rater_counts, as_acceptable_map, draft_bands_for
from .conditions import (
    standard_conditions,
    control_conditions,
    is_confounded,
    confounded_direction,
    classify_contrast,
    descriptor_surface_stats,
)

__version__ = "0.0.1"

__all__ = [
    "Pair",
    "counterfactual_flip_rate",
    "within_range_flip_rate",
    "wcfr_statistic",
    "in_band",
    "band_straddles",
    "disparity_propagation",
    "mean_absolute_score_difference",
    "action_level_disparity",
    "positive_rate",
    "cluster_bootstrap_ci",
    "mcnemar_exact",
    "benjamini_hochberg",
    "benjamini_yekutieli",
    "paired_permutation_test",
    "signed_ordinal_disparity",
    "interventional_propagation",
    "capability_floor_gate",
    "trajectory_accumulation",
    "run_vignette",
    "run_replicates",
    "collapse_replicates",
    "resolve_orderables",
    "standard_conditions",
    "is_confounded",
    "control_conditions",
    "confounded_direction",
    "classify_contrast",
    "Band",
    "PROVENANCE",
    "unadjudicated",
    "rater_counts",
    "as_acceptable_map",
    "draft_bands_for",
    "descriptor_surface_stats",
    "__version__",
]
