# FairMedAgent. Related work

*Prior work grouped by what it measures. Citations were checked against the source record; entries marked with a star are the ones the design relies on most.*

## The gap (one sentence)
The works surveyed here do not combine **(1)** a clinical decision-support **agent taking multi-step actions** (triage acuity, lab/diagnostic ordering, medication choice, escalation, documentation), **(2)** **counterfactual** synthetic demographic patient profiles, and **(3)** a standardized public leaderboard. FairMedAgent targets that combination; the leaderboard is planned.

## 1. Static medical-QA / single-recommendation bias (prior art. NOT agentic, NOT action-level)
- ★ **Pfohl et al. 2024, EquityMedQA**: *Nature Medicine* 30:3590 / arXiv:2403.12025. Surfaces equity harms in long-form medical-QA *answers* (7 adversarial datasets, 4,619 Qs, human rubric). → Evaluates answer text, not agent actions; manual, no leaderboard.
- ★ **Zack et al. 2024, "Coding Inequity"**: *Lancet Digital Health* 6(1):e12. GPT-4 racial/gender bias in vignette generation, diagnosis, plan. → Descriptive single-model audit; not a reusable benchmark.
- **Omiye et al. 2023, "LLMs propagate race-based medicine"**: *npj Digital Medicine* 6:195 (Stanford). Race-myth knowledge in open Q&A. → Factual myths, not operational action disparity.
- **Hanna et al. 2024**: arXiv:2404.15149. 8 LLMs, demographic red-teaming of CDS vignette QA (pain-med skew). → Single-turn QA, no agent trajectory, no leaderboard.

## 2. Counterfactual clinical recommendation disparity (CLOSEST prior. still not agentic, no leaderboard)
- ★ **Omar/Nadkarni et al. 2025, "Sociodemographic biases in medical decision making by LLMs"**: *Nature Medicine* s41591-025-03626-6 (Mount Sinai). 1,000 ED cases × 32 sociodemographic variations, ~1.7M outputs; disparities in urgency, invasive intervention, mental-health referral. → Strongest counterfactual design in the prior work surveyed, but single-turn text recommendations from a chat model, not a multi-action agent loop, and **ships no public benchmark/leaderboard**.
- **ED-triage bias**: arXiv:2504.16273 (2025). Counterfactual intersectional (sex×race) bias on triage acuity. → One action type only (triage); no broader action set; no leaderboard.

## 3. Medical agent / capability benchmarks (agentic OR leaderboard. but NO fairness axis)
- **MedAgentBench**: Jiang/Chen et al. 2025, arXiv:2501.14654 (Stanford; NEJM AI). Virtual EHR, 300 physician-written tool/EHR action tasks, pass@1 *correctness*. → Closest action-level harness, but measures whether the action is *right*, never whether it *differs by demographics*. Methodological precedent for our action space.
- **AgentClinic**: Schmidgall et al. 2024, arXiv:2405.07960. Simulated clinical dialogue agents; injects biases but as *accuracy degraders*. → Treats bias as noise hurting accuracy, not a measured equity metric across actions.
- **MedHELM**: Bedi et al. 2025, arXiv:2505.23802 (Stanford CRFM; public leaderboard). 121 clinician-validated capability tasks. → Leaderboard infrastructure exists but has no counterfactual demographic action-fairness metric.
- **MedQA**: Jin et al. 2021, arXiv:2009.13081. USMLE MCQ accuracy. → Capability only.

## 4. Fairness metric foundations (grounds our metrics. all verified)
- ★ **Kusner, Loftus, Russell, Silva 2017, Counterfactual Fairness**: NeurIPS 2017 / arXiv:1703.06856. → Basis for **CFR** (counterfactual flip rate).
- ★ **Bertrand & Mullainathan 2004**: *AER* 94(4):991. Name-swap correspondence audit. → Canonical precedent for the attribute-swap counterfactual probe (clinical content held fixed).
- **Hardt, Price, Srebro 2016, Equality of Opportunity**: NeurIPS 2016 / arXiv:1610.02413. → Grounds **equalized-odds-style gaps**.
- **Dwork et al. 2012, Fairness Through Awareness**: ITCS '12 / arXiv:1104.3913. → Grounds **action-level disparity / demographic-parity gaps**.
- **Haim, Salinas, Nyarko 2024, "What's in a Name?"**: arXiv:2402.14875. LLM name-only audit (worst for Black-women names). → Precedent for LLM counterfactual name-swap probing + **FDR (Benjamini–Hochberg)** across many subgroup×scenario comparisons.
- **Gaebler, Goel, Huq, Tambe 2024/2025**: arXiv:2404.03086 / *Behavioral Science & Policy*. LLM correspondence experiments (name/pronoun swaps). → Audit-design precedent.
