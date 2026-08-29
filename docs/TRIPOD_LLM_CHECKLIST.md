# TRIPOD-LLM reporting checklist — FairMedAgent (item → section map)

*Reporting standard: TRIPOD-LLM (Gallifant et al., Nature Medicine 2025) with parent TRIPOD+AI (Collins et al., BMJ 2024). This maps our coverage to the guideline's domains with section pointers. **Fill the exact item numbers/wording from the official interactive checklist (tripod-llm.vercel.app) before submission** — we deliberately do not transcribe item text here to avoid error.*

| TRIPOD-LLM domain | Covered where | Notes |
|---|---|---|
| Title / abstract — identify as LLM evaluation, task, data | Title, Abstract | Title contains "agentic" + "benchmark"; abstract states task, counterfactual design, metrics. |
| Background / objective | §I Introduction | Clinical-disparity grounding + gap + contributions. |
| Data / vignettes — source, synthetic nature, no PHI | §IV-A, Datasheet | Synthetic; no human subjects; generation documented. |
| Model(s) — identity, version, date, access | §IV-C | Pinned model IDs + dates; temperature 0; scaffolds C0/C1/C2. |
| Task / inputs / prompts | §III-B, Supplement | Fixed-form injection rendered verbatim in Supplement; per-step prompts released. |
| Outcome / action definition | §III-A/B | Formal "action" + 5-step agentic loop; per-task output schemas. |
| Analysis / metrics | §III-D, §IV-D | CFR, MASD, within-range disparity; wild cluster bootstrap, McNemar, BH-FDR. |
| Human oversight / labeling | §IV-B | ≥2 blinded clinician labelers; Krippendorff α; adjudication; band sensitivity. \final{α} |
| Results — performance/disparity, uncertainty, subgroups | §V | Preliminary pilot (labeled) + \final{} primary; G reported with CIs; disaggregated by attribute×domain. |
| Fairness / subgroup reporting | §V, Model Cards | Disaggregated disparity per model×scaffold; intersectional cells. |
| Discussion / limitations | §VI | In-silico bounding; small G; ceiling; excluded axes. |
| Reproducibility / open science | §IV-E, Availability | Pip harness, versioned dataset, Zenodo DOI, one-command regeneration. |
| Ethics / governance | Ethics section | Synthetic; dual-use + responsible disclosure; leaderboard governance. |
| Funding / conflicts / AI disclosure | Acknowledgment | IEEE-mandated AI-use disclosure included. |

**Self-audit (PROBAST+AI evaluation domains):** participants/data-source (synthetic representativeness — stated limitation), predictors/inputs (fixed-form injection controlled), outcome/action definition (clinician acceptable-range), analysis (multiplicity via BH-FDR; small-G bootstrap; discordant-pair budget). Residual risks disclosed in §VI.
