# Datasheet — FairMedAgent synthetic vignette dataset

*Following Gebru et al., "Datasheets for Datasets" (CACM 2021). Ships with the HuggingFace dataset card. `\final{}` marks values set at release / after clinician validation.*

## Motivation
- **Purpose.** To benchmark demographic fairness in the *actions* of multi-step clinical LLM agents via counterfactual synthetic patient profiles. Created because no existing dataset supports action-level, within-range, counterfactual fairness evaluation of clinical agents.
- **Created by / funded by.** Rohith Reddy and collaborators (incl. clinician co-authors); [funding: none / …].

## Composition
- **Instances.** Synthetic clinical vignettes, each a frozen clinical narrative (`clinical_core`), a condition-independent tool-result fixture (`ρ(v)`), a clinician-labeled set of acceptable actions per task (`A(v)`), and a canary string; rendered under a set of fixed-form counterfactual demographic conditions.
- **Count.** \final{N} base vignettes across 4 domains (triage/escalation, diagnostic & lab ordering, medication management, documentation/disposition); \final{|C|} demographic conditions per vignette (race/ethnicity, sex, age, insurance, LEP, + intersections).
- **No PHI / no real patients.** All content is synthetic; the dataset contains no protected health information and is not derived from patient records.
- **Labels.** Clinician-defined acceptable-action ranges per task (≥2 independent blinded labelers; Krippendorff α = \final{α}).
- **Splits.** Public **development** split (released) + **sealed** held-out test split (withheld; scored server-side via the submission protocol).
- **Confounded pairs.** A registry flags attribute×domain pairs carrying legitimate clinical signal (e.g., LEP×documentation); these are reported descriptively, not as bias.

## Collection / Generation process
- **How.** Vignettes authored + parameterized from templates (synthetic), then validated for clinical realism by ≥2 clinicians; demographic descriptors rendered in fixed grammatical form (only slot fillers vary).
- **Human subjects.** No patient subjects. **Synthetic, zero-PHI data does NOT by itself remove human-research-protection obligations.** A **written** HRPP/IRB determination (even a "not human subjects research" determination must be *determined in writing, not assumed*) is obtained **before** any clinician annotation begins. ⚠️ Prerequisite gate — annotation may not start without it.

## Uses
- **Intended.** Fairness/robustness auditing of clinical LLM agents; leaderboard evaluation; methods research.
- **Out of scope / discouraged.** Training clinical decision models; any real-world clinical deployment decision; inferring patient-outcome effects (this is in-silico). Coarse demographic descriptors; axes excluded (nonbinary gender, disability, religion) are limitations, not coverage.
- **Dual use.** A disparity-elicitation resource could be misused; exploit-specific details are gated and safety-relevant findings follow responsible disclosure (`DISCLOSURE_SOP.md`).

## Distribution
- **Where.** HuggingFace (dev split) + archival Zenodo DOI \final{DOI}; sealed test split not distributed.
- **License.** \final{license, e.g., CC BY 4.0 for dev split}. Canary strings must not be removed.

## Maintenance
- **Maintainer.** Rohith Reddy. Versioned (semver) alongside the pip harness; leaderboard logs submissions (name/affiliation/country) for adoption transparency; stated sunset plan if unmaintained.
