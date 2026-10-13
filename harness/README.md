# FairMedAgent evaluation harness

A harness that measures **demographic disparities in the *actions*** of
clinical LLM decision-support agents using counterfactual synthetic patient profiles.

The core fairness metrics are implemented, tested and dependency-free. The runner, the
scenario and condition modules and the scripts that reproduce the reported numbers are in
this repository. The design documents are in `../docs/`.

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
Models in the reported runs use their default decoding; temperature 0 is run as a comparison
arm (`FMA_TEMPERATURE=0`) and is reported separately. Model identifiers and, for local models,
Ollama tags and digests are recorded with each run (`experiments/floor16v3_provenance.txt`).
Analysis seeds are fixed in the scripts. All vignettes are synthetic. The held-out test split
is not in this repository.
