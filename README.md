# FairMedAgent

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22165979.svg)](https://doi.org/10.5281/zenodo.22165979)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

An evaluation harness for demographic disparity in the **actions** of multi-step clinical
LLM agents, together with the instability-floor protocol that says how large a disparity
estimate has to be before it means anything.

A counterfactual audit holds the clinical content of a case fixed, changes only the patient
descriptor, and reports how often the agent's action changes. That number is not
interpretable on its own. Re-running an identical condition ten times over sixteen vignettes,
with nothing varied at all, moved the agent's action in 8.7 percent of outcome-vignette cells,
and the rate differed across actions by a factor of eight. A second model reproduces the
pattern. Any counterfactual flip rate reported without a per-action floor beside it therefore
cannot be read as evidence of disparity.

The estimand this harness targets is the within-range counterfactual flip rate, which counts
only flips between actions that a published decision rule admits and a clinician has
adjudicated as defensible. That adjudication is under way. **No disparity result is claimed
here, and none should be quoted from this repository.**

## Install

```bash
pip install -e harness
```

Core metrics are standard library only, so they run anywhere. `pip install -e "harness[full]"`
adds numpy, scipy, datasets and pandas for scale; `harness[dev]` adds pytest.

## Reproducing the reported numbers

Every quantity in the manuscript is recomputed from the raw trajectory files in
`experiments/` and checked against the text:

```bash
python harness/scripts/verify_paper_numbers.py
```

The script names each claim and recomputes it from its source artifact. It does not parse
LaTeX for numbers and diff them, which would be brittle.

The manuscript source is not part of this release, so in a fresh clone the script recomputes
all 21 quantities and skips only the step that asserts each figure appears in the text. To run
that step as well, pass the path to the manuscript:

```bash
python harness/scripts/verify_paper_numbers.py /path/to/main.tex
```

Against the submitted manuscript it reports 21 of 21 claims matching.

```bash
python -m pytest harness/tests/ -q
```

## What is here

| Path | Contents |
|---|---|
| `harness/fairmedagent/` | Metrics, bands, conditions, scenarios, runner, adjudicator registry |
| `harness/scripts/` | Analysis and verification scripts, one per reported quantity |
| `harness/tests/` | Unit tests for the metric and band logic |
| `experiments/floor16/` | Raw trajectories for the sixteen-vignette instability floor |
| `experiments/floor16_sonnet/` | The second-model replication |
| `docs/ADJUDICATION_PROTOCOL.md` | How a band is adjudicated and what makes one load-bearing |
| `docs/BAND_ADJUDICATION_RECORD.md` | The adjudicator's reasoning, in full, per band |
| `docs/DATASHEET.md` | Datasheet for the synthetic cohort |
| `docs/COUNTERFACTUAL_DESIGN.md` | Condition construction and the descriptor grammar |
| `docs/ANALYSIS_PLAN.md` | Pre-specified analysis |

## On the adjudicator

Acceptable-action bands are reviewed by a licensed clinician who is deliberately not an
author, because the labeling protocol requires the adjudicator to be independent of the
authorship. The published record carries a stable pseudonym and a credential. The signed
attestation carrying the real name, registration number and institution is held by the
corresponding author and produced to a journal editor on request; it is never committed here.

`harness/fairmedagent/adjudicators.py` enforces this. A band cannot be marked
`clinician-adjudicated` under a pseudonym that is not registered, or that is registered
without an attestation on file. Refusing is the point: a provenance level that reports green
while resting on nothing is the failure this guards against.

At the current commit no attestation is on file, so `within_range_flip_rate` reports
`ground_truth: false`.

## Data

All patient vignettes are synthetic. No real patient data, no protected health information,
no human subjects. Cohort provenance, including the generator version, seed and command, is
recorded in `cohort/PROVENANCE.md`, so the cohort is regenerable rather than stored.

The held-out test split is sealed and is not in this repository. It is scored under the
submission protocol.

## Citing

See `CITATION.cff`. Cite the archived release by its concept DOI, which always resolves to the
latest version:

> Bellibaltu, R. R., and Singh, M. FairMedAgent: a counterfactual benchmark for demographic
> fairness in the actions of multi-step clinical LLM agents. Zenodo. https://doi.org/10.5281/zenodo.22165979

The manuscript reference is added on publication.

## License

Apache 2.0. See `LICENSE`.
