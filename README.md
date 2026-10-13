# FairMedAgent

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22165979.svg)](https://doi.org/10.5281/zenodo.22165979)
[![arXiv](https://img.shields.io/badge/arXiv-2609.03221-b31b1b.svg)](https://arxiv.org/abs/2609.03221)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

An evaluation harness for demographic disparity in the **actions** of multi-step clinical
LLM agents, together with the instability-floor protocol that says how large a disparity
estimate has to be before it means anything.

It accompanies the manuscript *FairMedAgent: run-to-run instability sets a floor for fairness audits of clinical large language model agents* ([arXiv:2609.03221](https://arxiv.org/abs/2609.03221), DOI [10.48550/arXiv.2609.03221](https://doi.org/10.48550/arXiv.2609.03221)).

A counterfactual audit holds the clinical content of a case fixed, changes only the patient
descriptor, and reports how often the agent's action changes. Part of that rate is not
demographic: a stochastic agent also changes its own action when nothing changes.
Re-running an identical condition ten times over sixteen vignettes moved the primary hosted
endpoint's action (haiku-4.5, queried through an agent runtime with batched context and
unrecorded decoding, so not independently reproducible) in 6.8 percent of replicate pairs
(245/3600 comparisons) over five clinically defined actions (admission, ICU escalation, high
acuity, referral, any opioid), and the rate differed across actions from 2.2 percent for ICU
escalation to 14.2 percent for admission. Across six models (haiku-4.5 and sonnet-5, hosted;
llama3.1:8b, mistral:7b, qwen3:4b and phi3:mini, served locally) the pooled five-action floor
ranged from 1.7 to 24.5 percent. The controlled-substance caution flag is reported separately
as an exploratory, model-generated flag rather than a clinically defined action. For a binary
action, the flip rate expected under no demographic effect equals the floor, so a
counterfactual flip rate should be reported beside a per-action floor measured on the same
system. All intervals are crossed (vignette by replicate) bootstraps.

The primary endpoint answered sixteen cases per call. Re-running the same model identifier with
one isolated `claude -p` call per prompt (ten replicates, 800 calls, no retries) gave a
five-action floor of 0.091 (95 percent crossed interval 0.041 to 0.149) against 0.068 batched,
with no sign that the shared context inflated the floor; the noisiest action changed from admission to
high acuity.

The floor depends on decoding. In logged reruns of the four local models (Ollama 0.35.1,
attempt-level logs, a retry uses the same decoding configuration as the first attempt),
temperature-0 decoding left no observed disagreement across five replicates for three of the
four models (llama3.1:8b, mistral:7b, qwen3:4b; one-sided 95 percent bound at most 0.015 for
each), but not for phi3:mini. A hosted check (openai/gpt-oss-20b on Groq) did not reach zero at
temperature 0: its five-action floor was 0.028, and the temperature-1 to temperature-0
difference was a descriptive 69 percent reduction that cannot be attributed to temperature
alone, because the serving configuration varied. Majority voting over five draws removed 53
percent of the primary endpoint's floor.

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
`experiments/` and checked against the text. The reported numbers use the logged reruns of the
four local models (`experiments/floor16v3_*`), selected with `FMA_PANEL=v3`; without it the
scripts read the earlier `floor16_*` local arms and write the original, unsuffixed outputs:

```bash
FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/verify_paper_numbers.py
```

`FMA_BOOT=crossed` selects the crossed (vignette by replicate) bootstrap intervals used in the
manuscript.

The script names each claim and recomputes it from its source artifact. It does not parse
LaTeX for numbers and diff them, which would be brittle.

The manuscript source is not part of this release, so in a fresh clone the script recomputes
the floor and panel quantities and skips only the step that asserts each figure appears in the text. To run
that step as well, pass the path to the manuscript:

```bash
FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/verify_paper_numbers.py /path/to/main.tex
```

The check covers the robustness and temperature-0 figures generated by `robustness.py` and
`temperature_compare.py`. The manuscript may be split into section files; `\input{...}` is followed.

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
| `experiments/floor16_sonnet/` | Second hosted model, sonnet-5 (Claude Sonnet 5, identifier `claude-sonnet-5` as reported by the calling layer; six replicates). The directory name is unchanged |
| `experiments/floor16v3_llama/`, `floor16v3_mistral/`, `floor16v3_qwen3/`, `floor16v3_phi3/` | Logged reruns of the four local models (Ollama 0.35.1; ten replicates each, default sampling). Each `rep*/answers/s*.json` carries per-attempt logs (timestamps, durations, parse status); `attempt_summary.json` totals them. A retry uses the same decoding configuration as the first attempt (`FMA_RETRY_POLICY=same`) |
| `experiments/floor16v3_*_t0/` | The same four models at temperature 0 (five replicates each; `FMA_TEMPERATURE=0`) |
| `experiments/floor16v3_provenance.txt`, `run_v3_all.sh` | Ollama version, model tags and digests, environment, and the driver that produced the v3 runs |
| `experiments/floor16_ollama/`, `floor16_mistral/`, `floor16_qwen3/`, `floor16_phi3/`, `floor16_*_t0/` | The earlier local-model runs, kept for comparison; the reported numbers use the v3 reruns |
| `experiments/floor16_groq_t0/`, `floor16_groq_t1/` | Hosted check: openai/gpt-oss-20b on Groq at temperature 0 and 1.0 (five replicates each; `groq_answerer.py`) |
| `experiments/robustness_v3.json`, `temperature_compare_v3.json`, `five_action_extras_v3.json`, `first_attempt_v3.json`, `panel_summary_v3.txt`, `rank_tests_v3.txt` | Reported analysis outputs (`FMA_PANEL=v3`): paired-bootstrap, leave-one-out, signed-test simulation, five-action analyses, first-attempt sensitivity and temperature-0 results |
| `experiments/robustness_v3_crossed.json`, `CROSSED_BOOT.md` | Crossed (vignette by replicate) bootstrap intervals used in the manuscript, with a comparison against the earlier intervals |
| `experiments/COVERAGE_SIM.json`, `COVERAGE_SIM.md` | Simulated coverage of the crossed-bootstrap interval, and the zero-observed bound comparison |
| `experiments/floor16_haiku_iso/`, `run_haiku_iso.sh`, `haiku_iso_floor.json` | Isolated-call sensitivity arm for endpoint A (claude-haiku-4-5, one `claude -p` call per prompt via `claude_cli_answerer.py`, R=10) and its floor comparison (`haiku_iso_floor.py`) |
| `experiments/fixed_case_bounds_v3.json` | One-sided upper bounds for zero-observed floors, replicate-only intervals, and achieved shifts |
| `experiments/robustness.json`, `temperature_compare.json` | The same analyses on the earlier local-model runs |
| `docs/ADJUDICATION_PROTOCOL.md` | How a band is adjudicated and what makes one load-bearing |
| `docs/BAND_ADJUDICATION_RECORD.md` | The adjudicator's reasoning, in full, per band |
| `docs/DATASHEET.md` | Datasheet for the synthetic cohort |
| `docs/COUNTERFACTUAL_DESIGN.md` | Condition construction and the descriptor grammar |
| `docs/ANALYSIS_PLAN.md` | Pre-specified analysis, frozen before sealed-split unblinding |

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

**Cite the paper, not the archive.** The citable reference is the preprint
[arXiv:2609.03221](https://arxiv.org/abs/2609.03221) (DOI [10.48550/arXiv.2609.03221](https://doi.org/10.48550/arXiv.2609.03221)):

```bibtex
@article{bellibatlu2026instability,
  title   = {{FairMedAgent}: run-to-run instability sets a floor for fairness audits of clinical large language model agents},
  author  = {Bellibatlu, Rohith Reddy and Singh, Manpreet and Parashar, Deepak and Joshi, Rahul},
  journal = {arXiv preprint arXiv:2609.03221},
  year    = {2026},
  doi     = {10.48550/arXiv.2609.03221},
  url     = {https://arxiv.org/abs/2609.03221}
}
```

Zenodo indexes software records but Google Scholar does not, so a Zenodo-only citation does not accrue anywhere a
reader or a bibliometric tool will look for it.

`10.5281/zenodo.22165979` is the archival identifier for the software itself. It belongs in a data or
code availability statement, which is where journals ask for it, and it is what makes a
specific version of this harness retrievable years from now. It is not the reference to put
in a bibliography.

See `CITATION.cff` for the machine-readable form.

## License

Apache 2.0. See `LICENSE`.

## Reproduction map

Set `FMA_PANEL=v3` to compute the reported numbers from the logged reruns (`floor16v3_*`).

| Result | Script | Command |
|---|---|---|
| Every number in the manuscript | `verify_paper_numbers.py` | `FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/verify_paper_numbers.py [main.tex]` |
| Crossed (vignette by replicate) bootstrap intervals | `crossed_boot.py` (used by `robustness.py`) | `FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/robustness.py` |
| Isolated-call versus batched floor for endpoint A | `haiku_iso_floor.py` | `FMA_PANEL=v3 python harness/scripts/haiku_iso_floor.py` |
| Coverage of the crossed-bootstrap interval (simulation) | `coverage_sim.py` | `python harness/scripts/coverage_sim.py` |
| Zero-observed floor bounds, replicate-only intervals, achieved shifts | `fixed_case_bounds.py` | `FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/fixed_case_bounds.py` |
| Floors and panel intervals (B=5000) | `panel_summary.py` | `FMA_PANEL=v3 python harness/scripts/panel_summary.py` |
| Paired differences, leave-one-out, excluding caution, voting reduction, null sensitivity, signed-test simulation, five-action analysis | `robustness.py` | `FMA_PANEL=v3 python harness/scripts/robustness.py` |
| Five-action extras (paired leave-one-out, voting, per-cell structure, temperature) | `five_action_extras.py` | `FMA_PANEL=v3 python harness/scripts/five_action_extras.py` |
| Default versus temperature-0 floors | `temperature_compare.py` | `FMA_PANEL=v3 python harness/scripts/temperature_compare.py` |
| Attempt totals (first-attempt failures, retries) per run directory | `attempt_summary.py` | `python harness/scripts/attempt_summary.py experiments/floor16v3_llama` |
| Floors from first attempts only | `first_attempt_sensitivity.py` | `FMA_PANEL=v3 python harness/scripts/first_attempt_sensitivity.py` |
| Per-action and per-model figures | `gen_fig_per_action.py`, `gen_fig_floor_by_model.py` | `FMA_PANEL=v3 python harness/scripts/gen_fig_per_action.py` |
| Rank correlations | `rank_tests.py` | `FMA_PANEL=v3 python harness/scripts/rank_tests.py` |
| Majority-vote curve and null simulation | `aggregation_curve.py`, `plateau_null.py` | `FMA_PANEL=v3 python harness/scripts/aggregation_curve.py` |
| Local and hosted runs | `run_ollama_floor.py` with `ollama_answerer.py` or `groq_answerer.py` (`FMA_ANSWERER`) | `python harness/scripts/run_ollama_floor.py <dir> <model> 1 10` (set `FMA_TEMPERATURE=0` for greedy; `FMA_RETRY_POLICY=same`) |
| The full v3 local rerun (requires Ollama and the model tags in `floor16v3_provenance.txt`) | `experiments/run_v3_all.sh` | `bash experiments/run_v3_all.sh` |

The supplementary material is attached to each GitHub release.
