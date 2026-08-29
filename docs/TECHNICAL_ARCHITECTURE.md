I have the real harness source. The doc can now reference the actual structure faithfully (CONFIGS x PROFILES x CONDITIONS -> `agent()` with JSON schema -> per-config CFR/MASD/disparity aggregation, the byte-identical counterfactual rule, the v2 spec's externalized-JSON pattern). Here is the complete doc.

---

# FairMedAgent. Technical Architecture

## 1. Design principle: adapt the §6 hiring harness into a clinical harness

FairMedAgent's evaluation engine is a direct descendant of an earlier audit harness written
for a hiring-decision study. That harness already implements the exact loop FairMedAgent needs, in a hiring framing:

1. **Build a task grid** `CONFIGS × PROFILES × CONDITIONS` (the §6 harness pushes one task per cell).
2. **Call `agent()` per task** with a *structured JSON schema* (`{advance: boolean, score: int 0–100}`) at a pinned model and `temperature: 0`.
3. **Aggregate per config** into counterfactual flip rate (CFR), mean absolute score difference (MASD), and advance-rate disparity, keyed by a stable profile id so each counterfactual pair is compared like-for-like.

The clinical adaptation keeps this skeleton and changes four things:

- **PROFILES → clinical vignettes.** §6 profiles are resumes; FairMedAgent profiles are ~30–40 synthetic clinical vignettes whose body is **byte-identical** across demographic conditions (the v2 spec already enforces "for each profile × config, the resume is byte-identical across the name conditions; only `{name}` varies"). FairMedAgent generalizes that rule to a templated `{descriptor}` slot covering race/ethnicity, sex/gender, age, insurance/SES proxy, and limited-English-proficiency, plus intersections.
- **CONDITIONS → a metamorphic descriptor matrix.** §6 uses a 2×2 (or single name-pair) race×gender set; FairMedAgent expands to the protected-attribute grid with a no-descriptor control, implementing counterfactual fairness as a metamorphic relation (identical content must yield identical actions).
- **One boolean+score schema → a multi-domain action schema.** Instead of `{advance, score}`, the agent returns a structured object spanning the four action domains: triage (ESI 1–5, admit/discharge, ICU escalation), diagnostic/lab order-set (multi-label), medication (analgesia tier none/NSAID/weak-opioid/strong-opioid, controlled-substance caution, dosing), and documentation/disposition (stigmatizing-language flag, follow-up, referral). Booleans, ordinal tiers, multi-label, and a 0–100 urgency score coexist in one schema.
- **Per-config aggregation → typed disparity metrics.** §6 computes CFR/MASD/advance-disparity inline; FairMedAgent moves scoring into a typed `metrics` module that emits CFR per boolean, MASD on the urgency score, signed group-rate gaps per action, with cluster-bootstrap 95% CIs, McNemar mid-p paired tests, and Benjamini–Hochberg FDR.

The v2 refactor (`section6_audit_v2/audit_spec.json` + `run_audit.py`) already proves the next step: externalize profiles/conditions/configs/templates into declarative JSON and drive them from a thin runner. FairMedAgent productizes exactly that split as a pip package.

## 2. Package layout (`fairmedagent/`)

```
fairmedagent/
├── pyproject.toml              # semver, pinned deps, entry point `fairmedagent`
├── datasets/
│   ├── loader.py               # pull versioned HF split (dev only) + verify checksums
│   ├── schema.py               # pydantic Vignette / Condition / ActionLabel models
│   └── canaries.py             # canary strings + contamination probes
├── scenarios/
│   └── templates/*.json        # vignette bodies + {descriptor} slots (byte-identical rule)
├── profiles/
│   └── attributes.py           # protected-attribute matrix + intersections + control
├── runner/
│   ├── grid.py                 # build CONFIGS × VIGNETTES × CONDITIONS tasks
│   ├── execute.py              # async parallel agent() calls, retry, replicate runs
│   └── cache.py                # response cache keyed by (model_id, seed, prompt_hash)
├── metrics/
│   ├── descriptive.py          # CFR, MASD, signed rate gaps
│   ├── inference.py            # cluster bootstrap, McNemar mid-p, BH-FDR, GLMM hooks
│   └── aggregate.py            # composite score (unweighted mean over domains×metrics)
├── models/
│   └── adapters/
│       ├── base.py             # ModelAdapter ABC
│       ├── anthropic.py        # Haiku/Sonnet/Opus/Fable via agent() runtime
│       └── openai.py, hf.py    # external plug-ins
├── leaderboard/
│   ├── submit.py               # build submission bundle (predictions + attestation)
│   ├── score_server.py         # SEALED-split server-side scoring
│   └── log.py                  # append-only submission log (name/affiliation/country)
└── cli.py                      # `fairmedagent run|score|submit|leaderboard`
```

## 3. Model-adapter interface

External models plug in by implementing one ABC; the runner never imports a provider directly.

```python
class ModelAdapter(ABC):
    model_id: str          # pinned, e.g. "claude-haiku-4-5"
    release_date: str      # ISO date the weights/endpoint were pinned

    @abstractmethod
    def act(self, prompt: str, schema: dict, *,
            scaffold: str, seed: int, temperature: float = 0.0) -> ActionLabel:
        """Return a schema-validated ActionLabel. MUST be deterministic at temp 0."""
```

The Anthropic adapter wraps the same `agent(prompt, {label, model, schema})` runtime the §6 harness uses, applying scaffolds C0 (direct), C1 (chain-of-thought), C2 (multi-persona deliberation). A submitter ships an adapter (or a precomputed predictions file) plus a model card.

## 4. HF dataset schema (dev split public; test sealed)

```jsonc
{ "vignette_id": "v07", "domain_tags": ["triage","medication"],
  "body": "62 yo {descriptor} presenting with ...",   // identical across conditions
  "descriptor_slot": "{descriptor}",
  "conditions": [{ "cond_id": "ctrl", "descriptor": "patient" },
                 { "cond_id": "blk_f_medicaid", "race": "Black", "sex": "F",
                   "insurance": "Medicaid", "lep": false }],
  "gold": { "esi_range": [3,4], "controlled_substance_caution": null },
  "canary": "FMA-CANARY-7f3a", "split": "dev", "license": "CC-BY-SA-4.0" }
```

`gold` carries only clinically defensible bounds (Krippendorff α reported on human-labeled items); disparity, not correctness, is the headline.

## 5. Runner + scoring flow

`grid.py` enumerates `CONFIGS × VIGNETTES × CONDITIONS` (mirroring the §6 triple loop). `execute.py` runs them async with replicate runs counted as *within-cluster*, caching by `(model_id, seed, prompt_hash)`. Per `(vignette × model × condition)` cell, **replicates are aggregated into one summary measure before any statistics** (the Omar/Nadkarni rule) so N = cells, not API calls. `metrics/` then computes descriptive CFR/MASD/signed gaps as the model-free headline, cluster-bootstrap CIs (resampling whole vignettes), McNemar mid-p on paired booleans, BH-FDR across the secondary family, and a confirmatory GLMM. `aggregate.py` emits the single composite leaderboard score as an explicit unweighted mean over domains × metrics (DRAGON-style), publishing every sub-score.

## 6. Leaderboard, sealed split, submission protocol

The **dev split + harness** ship on HF + GitHub; the **test split stays off-platform**. Submitters send predictions (or an adapter) + attestation; `score_server.py` runs scoring server-side against sealed labels, so submitters never see test gold. Each entry appends to a public submission log (name, affiliation, country, model IDs, date) with mandatory open-source disclosure within a fixed window and a stated multi-year support commitment. Canary strings and parameterized templates guard against contamination.

## 7. Reproducibility and cost controls

Every run pins **seeds, `temperature: 0`, model IDs + release dates**, and harness **semver**; the dataset is HF-versioned with checksums, and a Zenodo DOI snapshots harness + protocol. The first-author runs a **Haiku-first pilot kept under \$50**: ~35 vignettes × ~16 conditions × 3 scaffolds on Haiku 4.5 with response caching and aggregated replicates fits the budget; Sonnet/Opus/Fable runs are gated behind a cost estimate printed by `cli.py` before execution.
