# FairMedAgent. evaluation harness

A pip-installable harness that measures **demographic disparities in the *actions*** of
clinical LLM decision-support agents using counterfactual synthetic patient profiles.

> Status: **early build.** The core fairness metrics are implemented, tested, and
> dependency-free. Scenario data, model adapters, the runner, and the leaderboard are
> being built to the design in `../docs/` (TECHNICAL_ARCHITECTURE, ANALYSIS_PLAN,
> SCENARIO_DESIGN, COUNTERFACTUAL_DESIGN). No fabricated results: metrics ship only
> against real or clearly-labeled pilot runs.

## Install (dev)
```bash
cd harness
pip install -e .          # core (stdlib-only metrics)
pip install -e ".[full]"  # + numpy/scipy/datasets for scale
pip install -e ".[dev]"   # + pytest
```

## Core metrics (implemented + tested)
```python
from fairmedagent.metrics import (
    Pair, counterfactual_flip_rate, mean_absolute_score_difference,
    action_level_disparity, positive_rate, cluster_bootstrap_ci,
    mcnemar_exact, benjamini_hochberg,
)

pairs = [Pair("v1", action_ref=True, action_cf=False, score_ref=82, score_cf=61), ...]
cfr  = counterfactual_flip_rate(pairs)                    # flip rate across the swap
masd = mean_absolute_score_difference(pairs)             # mean |Δ urgency|
ci   = cluster_bootstrap_ci(pairs, counterfactual_flip_rate)   # 95% CI (cluster bootstrap)
mc   = mcnemar_exact(pairs)                              # paired-binary discordance test
fdr  = benjamini_hochberg([...p-values...])             # BH-FDR across the grid
```

## Test
```bash
python tests/test_metrics.py     # stdlib runner (prints PASS lines)
pytest tests/                    # or via pytest
```

## Metric definitions
See `../docs/ANALYSIS_PLAN.md` for the formal estimators, CI method, multiple-comparison
correction, and the mixed-effects model used for the repeated-measures-by-vignette design.

## Reproducibility
Seeds fixed, temperature 0, model IDs + dates pinned, dataset versioned on HuggingFace,
harness semantically versioned on PyPI. A public dev split ships; the held-out test split
is sealed and scored server-side via the submission protocol (anti-gaming).
