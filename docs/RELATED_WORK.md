# FairMedAgent. Related Work & Differentiation (Phase 1, verified citations)

*All citations below were verified via web search or drawn from the human-verified 202-entry `references.bib`. Items with uncorroborated 2026-dated arXiv stamps were EXCLUDED (honesty bar). Load-bearing cites (★) to be re-confirmed at camera-ready.*

## The gap (one sentence)
No verified benchmark combines **(1)** a clinical decision-support **agent taking multi-step actions** (triage acuity, lab/diagnostic ordering, medication choice, escalation, documentation), **(2)** **counterfactual** synthetic demographic patient profiles, and **(3)** a **standardized public leaderboard**. FairMedAgent occupies that intersection.

## 1. Static medical-QA / single-recommendation bias (prior art. NOT agentic, NOT action-level)
- ★ **Pfohl et al. 2024, EquityMedQA**: *Nature Medicine* 30:3590 / arXiv:2403.12025. Surfaces equity harms in long-form medical-QA *answers* (7 adversarial datasets, 4,619 Qs, human rubric). → Evaluates answer text, not agent actions; manual, no leaderboard.
- ★ **Zack et al. 2024, "Coding Inequity"**: *Lancet Digital Health* 6(1):e12. GPT-4 racial/gender bias in vignette generation, diagnosis, plan. → Descriptive single-model audit; not a reusable benchmark.
- **Omiye et al. 2023, "LLMs propagate race-based medicine"**: *npj Digital Medicine* 6:195 (Stanford). Race-myth knowledge in open Q&A. → Factual myths, not operational action disparity.
- **Hanna et al. 2024**: arXiv:2404.15149. 8 LLMs, demographic red-teaming of CDS vignette QA (pain-med skew). → Single-turn QA, no agent trajectory, no leaderboard.

## 2. Counterfactual clinical recommendation disparity (CLOSEST prior. still not agentic, no leaderboard)
- ★ **Omar/Nadkarni et al. 2025, "Sociodemographic biases in medical decision making by LLMs"**: *Nature Medicine* s41591-025-03626-6 (Mount Sinai). 1,000 ED cases × 32 sociodemographic variations, ~1.7M outputs; disparities in urgency, invasive intervention, mental-health referral. → **Strongest counterfactual design in prior art**, but single-turn text recommendations from a chat model, not a multi-action agent loop, and **ships no public benchmark/leaderboard**. This is the paper to differentiate from most explicitly.
- **ED-triage bias**: arXiv:2504.16273 (2025). Counterfactual intersectional (sex×race) bias on triage acuity. → One action type only (triage); no broader action set; no leaderboard.

## 3. Medical agent / capability benchmarks (agentic OR leaderboard. but NO fairness axis)
- **MedAgentBench**: Jiang/Chen et al. 2025, arXiv:2501.14654 (Stanford; NEJM AI). Virtual EHR, 300 physician-written tool/EHR action tasks, pass@1 *correctness*. → Closest action-level harness, but measures whether the action is *right*, never whether it *differs by demographics*. Methodological precedent for our action space.
- **AgentClinic**: Schmidgall et al. 2024, arXiv:2405.07960. Simulated clinical dialogue agents; injects biases but as *accuracy degraders*. → Treats bias as noise hurting accuracy, not a measured equity metric across actions.
- **MedHELM**: Bedi et al. 2025, arXiv:2505.23802 (Stanford CRFM; public leaderboard). 121 clinician-validated capability tasks. → Leaderboard infrastructure exists but has no counterfactual demographic action-fairness metric. (Target for eventual integration, adoption play.)
- **MedQA**: Jin et al. 2021, arXiv:2009.13081. USMLE MCQ accuracy. → Capability only.

## 4. Fairness metric foundations (grounds our metrics. all verified)
- ★ **Kusner, Loftus, Russell, Silva 2017, Counterfactual Fairness**: NeurIPS 2017 / arXiv:1703.06856. → Basis for **CFR** (counterfactual flip rate).
- ★ **Bertrand & Mullainathan 2004**: *AER* 94(4):991. Name-swap correspondence audit. → Canonical precedent for the attribute-swap counterfactual probe (clinical content held fixed).
- **Hardt, Price, Srebro 2016, Equality of Opportunity**: NeurIPS 2016 / arXiv:1610.02413. → Grounds **equalized-odds-style gaps**.
- **Dwork et al. 2012, Fairness Through Awareness**: ITCS '12 / arXiv:1104.3913. → Grounds **action-level disparity / demographic-parity gaps**.
- **Haim, Salinas, Nyarko 2024, "What's in a Name?"**: arXiv:2402.14875. LLM name-only audit (worst for Black-women names). → Precedent for LLM counterfactual name-swap probing + **FDR (Benjamini–Hochberg)** across many subgroup×scenario comparisons.
- **Gaebler, Goel, Huq, Tambe 2024/2025**: arXiv:2404.03086 / *Behavioral Science & Policy*. LLM correspondence experiments (name/pronoun swaps). → Audit-design precedent.

## 5. Reusable verified bib keys (from the 202-entry corpus. do not re-verify)
related work / clinical: `omar2025sociodemographic`, `poulain2024bias`, `benkirane2024diagnose`, `zack2024coding`, `obermeyer2019dissecting`, `pfohl2024toolbox`, `li2025actions`, `xu2026ducx`(†), `vatsal2026agentic`(†) · metrics: `kusner2017counterfactual`, `hardt2016equality`, `dwork2012fairness`, `mehrabi2021survey`, `chouldechova2017fair`, `ghosh2025medequalqa`, `parziale2025systematic`(†), `adappanavar2025mfarm` · agent scaffolds: `yao2023react`, `schick2023toolformer`, `shinn2023reflexion` · benchmark methodology: `xiao2025fairmedqa`(†, closest-named comparator, re-verify contents), `wu2024fmbench`.
(† = 2025/26-dated; from the verified bib but re-confirm the most load-bearing before citing.)

## Honesty notes
- Excluded as unverifiable (2026 arXiv stamps not corroborated): EQUITRIAGE (2605.03998), "Counterfactual Evaluation… Clinical LLMs and Agents" (2605.30590), 2601.15306, 2511.17124, "Dr. Bias" (2510.09162).
- `FairMedQA` (arXiv:2505.19562) appears real but contents not fully verified, so re-check before positioning it as a comparator. (Our name "FairMedAgent" is distinct: *agent/action* focus, not QA.)
- Differentiation line for the paper: "Prior clinical-fairness work audits **static answers or a single recommendation**; capability benchmarks score **agent accuracy**. FairMedAgent is the first to measure **demographic disparity in the multi-step *actions* of clinical agents** over counterfactual profiles, with a public leaderboard."
